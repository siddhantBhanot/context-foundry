import asyncio
from datetime import datetime, timezone
from pathlib import Path
import sys
import time
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple
import uuid

# Ensure project root is in sys.path
_project_root = Path(__file__).resolve().parents[4]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from backend_service.app.domain.exceptions.base import (
    DomainException,
    RAGServiceException,
    ValidationException,
)
from backend_service.app.domain.interfaces.rag_client import RAGClientProtocol, RAGQueryResult
from backend_service.app.domain.models.conversation import Message, SourceCitation
from backend_service.app.domain.models.knowledge import DocumentView, IngestionJob, IngestionStatus


class DirectRAGClient(RAGClientProtocol):
    """
    Direct adapter invoking the verified rag_service pipeline in-process.
    Provides complete multi-turn grounded retrieval using Groq/OpenAI/Bedrock and Qdrant.
    """

    def __init__(self):
        self._pipeline = None
        self._ingestion = None
        self._kt_engine = None
        self._course_indexer = None
        self._indexed_courses: set = set()
        self._init_rag()

    def _init_rag(self) -> None:
        try:
            from rag_service.infrastructure.config import get_settings as get_rag_settings
            from rag_service.infrastructure.providers.bedrock_embedding import BedrockEmbeddingProvider
            from rag_service.infrastructure.providers.bedrock_llm import BedrockLLMProvider
            from rag_service.infrastructure.providers.openai_llm import OpenAiClientProvider
            from rag_service.infrastructure.providers.qdrant_embedding import QdrantEmbeddingProvider
            from rag_service.infrastructure.providers.qdrant_store import QdrantVectorStoreAdapter
            from rag_service.infrastructure.providers.multi_provider import MultiProviderLLMAdapter
            from rag_service.ingestion.pipeline import IngestionPipeline
            from rag_service.pipeline.rag_engine import RAGPipeline
            from rag_service.prompts.loader import PromptLoader

            settings = get_rag_settings()
            has_aws = bool(
                settings.aws_bearer_token_bedrock
                or (settings.aws_access_key_id and settings.aws_secret_access_key)
            )
            has_openai = bool(settings.openai_api_key)
            has_groq = bool(settings.groq_api_key)

            # Embedder: Use Bedrock if explicitly configured and AWS credentials exist; otherwise use Qdrant FastEmbed
            if settings.embedding_provider == "bedrock" and has_aws:
                embedding_provider = BedrockEmbeddingProvider(settings)
            else:
                embedding_provider = QdrantEmbeddingProvider(settings)

            # Vector Store
            settings.embedding_dimension = embedding_provider.dimension
            vector_store = QdrantVectorStoreAdapter(settings)

            # LLM Provider with Multi-Provider Routing
            bedrock_provider = BedrockLLMProvider(settings) if has_aws else None
            openai_provider = OpenAiClientProvider(settings) if has_openai else None

            if bedrock_provider and openai_provider:
                default_p = openai_provider if has_groq else bedrock_provider
                multi_adapter = MultiProviderLLMAdapter(
                    default_provider=default_p,
                    providers={
                        "groq": openai_provider,
                        "openai": openai_provider,
                        "bedrock": bedrock_provider,
                    },
                )
                for bm in settings.get_configured_bedrock_models():
                    multi_adapter.register_model(bm["id"], "bedrock")
                multi_adapter.register_model(settings.bedrock_llm_model_id, "bedrock")
                llm_provider = multi_adapter
            elif bedrock_provider:
                llm_provider = bedrock_provider
            elif openai_provider:
                llm_provider = openai_provider
            else:
                # Standalone fallback if neither is present
                from rag_service.run_local import LocalSimulatedLLM
                llm_provider = LocalSimulatedLLM()

            prompts_dir = _project_root / "rag_service" / "prompts"
            prompt_loader = PromptLoader(prompts_dir=prompts_dir)

            self._pipeline = RAGPipeline(
                vector_store=vector_store,
                embedding_provider=embedding_provider,
                llm_provider=llm_provider,
                prompt_loader=prompt_loader,
                default_service=settings.default_microservice,
                max_history_messages=settings.max_history_messages,
            )

            self._ingestion = IngestionPipeline(
                vector_store=vector_store,
                embedding_provider=embedding_provider,
                default_service=settings.default_microservice,
            )

            from rag_service.infrastructure.providers.qdrant_store import QdrantVectorStoreAdapter
            from rag_service.knowledge_cafe.kt_engine import KTEngine
            from rag_service.knowledge_cafe.course_indexer import CourseIndexer

            kt_vector_store = QdrantVectorStoreAdapter(
                settings=settings,
                collection_name=settings.qdrant_kt_collection_name,
            )
            self._kt_engine = KTEngine(
                llm_provider=llm_provider,
                prompt_loader=prompt_loader,
                kt_vector_store=kt_vector_store,
                embedding_provider=embedding_provider,
            )
            self._course_indexer = CourseIndexer(
                vector_store=kt_vector_store,
                embedding_provider=embedding_provider,
            )
        except Exception as e:
            self._pipeline = None
            self._ingestion = None
            self._kt_engine = None
            self._course_indexer = None

    def _ensure_initialized(self):
        if self._pipeline is None or self._kt_engine is None:
            self._init_rag()
        if self._pipeline is None:
            raise RAGServiceException(
                "RAG pipeline could not be initialized. Please check rag_service dependencies and configuration."
            )

    async def list_models(self) -> List[dict]:
        """Discover available LLM models strictly based on active server configuration."""
        from rag_service.infrastructure.config import get_settings
        settings = get_settings()

        has_groq = bool(settings.groq_api_key)
        has_openai = bool(settings.openai_api_key)
        has_aws = bool(
            settings.aws_bearer_token_bedrock
            or (settings.aws_access_key_id and settings.aws_secret_access_key)
        )

        models: List[dict] = []

        if has_groq or (has_openai and "groq" in (settings.openai_base_url or "").lower()):
            models.extend([
                {
                    "id": "openai/gpt-oss-120b",
                    "name": "GPT-OSS 120B",
                    "provider": "groq",
                    "description": "High-capacity open-weight reasoning model via Groq",
                },
                {
                    "id": "openai/gpt-oss-20b",
                    "name": "GPT-OSS 20B",
                    "provider": "groq",
                    "description": "Fast low-latency open-weight reasoning model",
                },
                {
                    "id": "qwen/qwen3.8-27b",
                    "name": "Qwen 3.8 27B",
                    "provider": "groq",
                    "description": "Advanced multilingual reasoning model",
                },
                {
                    "id": "qwen/qwen3.6-27b",
                    "name": "Qwen 3.6 27B",
                    "provider": "groq",
                    "description": "High-speed analytical reasoning model",
                },
                {
                    "id": "groq/compound",
                    "name": "Groq Compound",
                    "provider": "groq",
                    "description": "Groq optimized multi-turn reasoning engine",
                },
                {
                    "id": "groq/compound-mini",
                    "name": "Groq Compound Mini",
                    "provider": "groq",
                    "description": "Ultra-fast low-latency inference engine",
                },
            ])
        elif has_openai:
            models.extend([
                {
                    "id": "gpt-4o",
                    "name": "GPT-4o",
                    "provider": "openai",
                    "description": "OpenAI flagship omni-model",
                },
                {
                    "id": "gpt-4o-mini",
                    "name": "GPT-4o Mini",
                    "provider": "openai",
                    "description": "Fast and efficient OpenAI model",
                },
            ])

        if has_aws:
            configured_bedrock = settings.get_configured_bedrock_models()
            if configured_bedrock:
                models.extend(configured_bedrock)
            else:
                models.extend([
                    {
                        "id": settings.bedrock_llm_model_id or "qwen.qwen3-235b-a22b-2507",
                        "name": "Qwen 3 235B A22B",
                        "provider": "bedrock",
                        "description": "Advanced open-weight reasoning model on AWS Bedrock",
                    },
                    {
                        "id": "anthropic.claude-3-5-sonnet-20240620-v1:0",
                        "name": "Claude 3.5 Sonnet",
                        "provider": "bedrock",
                        "description": "High-intelligence AWS Bedrock Claude model",
                    },
                    {
                        "id": "anthropic.claude-3-haiku-20240307-v1:0",
                        "name": "Claude 3 Haiku",
                        "provider": "bedrock",
                        "description": "Fast and lightweight AWS Bedrock model",
                    },
                ])

        if not models:
            return [
                {
                    "id": "local-simulated-engine",
                    "name": "Local Simulated LLM",
                    "provider": "local",
                    "description": "Simulated local offline inference",
                    "is_default": True,
                }
            ]

        # Determine default model
        target_default = None
        if settings.llm_provider and settings.llm_provider.lower() == "bedrock" and has_aws:
            target_default = settings.bedrock_llm_model_id
        elif has_groq or has_openai:
            target_default = settings.openai_model_id

        found_default = False
        for m in models:
            if target_default and m["id"] == target_default:
                m["is_default"] = True
                found_default = True
            else:
                m["is_default"] = False

        if not found_default and models:
            models[0]["is_default"] = True

        return models

    async def query(
        self,
        query_text: str,
        service: str = "income-assessment-service",
        history: Optional[List[Message]] = None,
        top_k: int = 5,
        model: Optional[str] = None,
    ) -> RAGQueryResult:
        if self._pipeline is None:
            self._init_rag()
        if self._pipeline is None:
            raise RAGServiceException(
                "RAG pipeline could not be initialized. Please check rag_service dependencies and configuration."
            )

        # Validate requested model if explicitly provided
        if model:
            available = await self.list_models()
            valid_ids = {m["id"] for m in available}
            if model not in valid_ids:
                from backend_service.app.domain.exceptions.base import ValidationException
                raise ValidationException(
                    f"Model '{model}' is not available or configured. Available models: {', '.join(sorted(valid_ids))}"
                )

        try:
            # Map conversation history to RAG Message models
            from rag_service.domain.models import Message as RAGMessage
            rag_history = []
            if history:
                for m in history:
                    rag_history.append(RAGMessage(role=m.role.value, content=m.content))

            result = await self._pipeline.query(
                query_text=query_text,
                service=service,
                chat_history=rag_history if rag_history else None,
                top_k=top_k,
                model=model,
            )

            # Map source references back to domain SourceCitation
            citations = []
            for src in result.sources:
                doc_type_val = getattr(src, "document_type", getattr(src, "doc_type", "markdown"))
                snippet_val = getattr(src, "snippet", getattr(src, "content_snippet", None))
                citations.append(
                    SourceCitation(
                        file=src.file,
                        service=getattr(src, "service", None) or result.service,
                        class_name=src.class_name,
                        endpoint=src.endpoint,
                        start_line=src.start_line,
                        end_line=src.end_line,
                        doc_type=doc_type_val.value if hasattr(doc_type_val, "value") else str(doc_type_val),
                        snippet=snippet_val,
                    )
                )

            return RAGQueryResult(
                answer=result.answer,
                sources=citations,
                service=result.service,
                latency_ms=result.latency_ms,
                provider=result.provider,
                model=result.model,
            )
        except DomainException:
            raise
        except Exception as e:
            raise RAGServiceException(f"Error querying RAG pipeline: {e}", details={"error": str(e)}) from e

    async def stream_query(
        self,
        query_text: str,
        service: str = "income-assessment-service",
        history: Optional[List[Message]] = None,
        top_k: int = 5,
        model: Optional[str] = None,
    ) -> Tuple[AsyncIterator[str], List[SourceCitation], Dict[str, Any]]:
        """Stream chunks from RAG pipeline with upfront source citations and metadata."""
        self._ensure_initialized()

        if model:
            available_models = await self.list_models()
            valid_ids = {m["id"] for m in available_models}
            if model not in valid_ids:
                from backend_service.app.domain.exceptions.base import ValidationException
                raise ValidationException(
                    f"Model '{model}' is not available or configured. Available models: {', '.join(sorted(valid_ids))}"
                )

        try:
            from rag_service.domain.models import Message as RAGMessage
            rag_history = []
            if history:
                for m in history:
                    rag_history.append(RAGMessage(role=m.role.value, content=m.content))

            stream_iter, sources, meta = await self._pipeline.stream_query(
                query_text=query_text,
                service=service,
                chat_history=rag_history if rag_history else None,
                top_k=top_k,
                model=model,
            )

            citations = []
            for src in sources:
                doc_type_val = getattr(src, "document_type", getattr(src, "doc_type", "markdown"))
                snippet_val = getattr(src, "snippet", getattr(src, "content_snippet", None))
                citations.append(
                    SourceCitation(
                        file=src.file,
                        service=getattr(src, "service", None) or service,
                        class_name=src.class_name,
                        endpoint=src.endpoint,
                        start_line=src.start_line,
                        end_line=src.end_line,
                        doc_type=doc_type_val.value if hasattr(doc_type_val, "value") else str(doc_type_val),
                        snippet=snippet_val,
                    )
                )

            return stream_iter, citations, meta
        except DomainException:
            raise
        except Exception as e:
            raise RAGServiceException(f"Error in streaming RAG pipeline: {e}", details={"error": str(e)}) from e

    async def get_document(
        self,
        service: str,
        file_path: str,
    ) -> DocumentView:
        from rag_service.infrastructure.document_reader import DocumentReader
        from backend_service.app.domain.models.knowledge import DocumentView

        sample_dir = _project_root / "rag_service" / "sample_data"
        reader = DocumentReader(data_dir=sample_dir)
        doc = reader.read_document(service=service, file_path=file_path)
        return DocumentView(
            file=doc.file,
            service=doc.service,
            content=doc.content,
            content_type=doc.content_type,
            total_lines=doc.total_lines,
            size_bytes=doc.size_bytes,
        )

    async def upload_document(
        self,
        service: str,
        file_name: str,
        content_bytes: bytes,
    ) -> dict:
        import re

        service_pattern = re.compile(r"^[a-zA-Z0-9_\-]+$")
        if not service or not service_pattern.match(service):
            raise ValueError(f"Invalid service identifier: '{service}'")

        safe_name = Path(file_name).name
        suffix = Path(safe_name).suffix.lower()
        if suffix not in {".md", ".markdown", ".pdf", ".kt", ".kts", ".zip"}:
            raise ValueError(
                f"Unsupported file format '{suffix}'. Supported formats: .kt, .kts, .md, .pdf, or .zip archive."
            )

        pending_dir = _project_root / "rag_service" / "sample_data" / service / "pending"
        pending_dir.mkdir(parents=True, exist_ok=True)

        if suffix == ".zip":
            import io
            import zipfile

            extracted_files = []
            try:
                with zipfile.ZipFile(io.BytesIO(content_bytes)) as zf:
                    # Security check: zip-slip check
                    for member in zf.infolist():
                        p = Path(member.filename)
                        if p.is_absolute() or ".." in p.parts:
                            raise ValueError(f"Malicious zip entry detected: {member.filename}")

                    allowed_inner = {".md", ".markdown", ".pdf", ".kt", ".kts"}
                    for member in zf.infolist():
                        if member.is_dir():
                            continue
                        inner_path = Path(member.filename)
                        if inner_path.suffix.lower() in allowed_inner and not inner_path.name.startswith("."):
                            target_file = pending_dir / inner_path
                            target_file.parent.mkdir(parents=True, exist_ok=True)
                            target_file.write_bytes(zf.read(member.filename))
                            extracted_files.append(str(inner_path))

                if not extracted_files:
                    raise ValueError(
                        "No valid Kotlin source (.kt, .kts), Markdown (.md), or PDF (.pdf) files were found in the uploaded zip archive."
                    )

                return {
                    "filename": safe_name,
                    "service": service,
                    "size_bytes": len(content_bytes),
                    "status": "pending",
                    "extracted_files_count": len(extracted_files),
                    "message": f"Archive '{safe_name}' unpacked successfully. {len(extracted_files)} source/documentation file(s) staged under pending review. Ingestion not triggered.",
                }
            except zipfile.BadZipFile:
                raise ValueError("Corrupted or invalid ZIP archive.")

        target_file = pending_dir / safe_name
        target_file.write_bytes(content_bytes)

        return {
            "filename": safe_name,
            "service": service,
            "size_bytes": len(content_bytes),
            "status": "pending",
            "extracted_files_count": None,
            "message": f"File '{safe_name}' uploaded successfully. It is staged under pending review and has NOT triggered RAG ingestion.",
        }

    async def list_service_files(
        self,
        service: str,
    ) -> List[dict]:
        import re

        service_pattern = re.compile(r"^[a-zA-Z0-9_\-]+$")
        if not service or not service_pattern.match(service):
            raise ValueError(f"Invalid service identifier: '{service}'")

        service_dir = _project_root / "rag_service" / "sample_data" / service
        if not service_dir.is_dir():
            return []

        def _get_format(sfx: str) -> str:
            s = sfx.lower()
            if s == ".pdf":
                return "PDF"
            if s in {".kt", ".kts"}:
                return "KT"
            return "MD"

        allowed_exts = {".md", ".markdown", ".pdf", ".kt", ".kts"}
        results = []

        # 1. Check pending directory (recursive)
        pending_dir = service_dir / "pending"
        if pending_dir.is_dir():
            for p in pending_dir.rglob("*"):
                if p.is_file() and p.suffix.lower() in allowed_exts:
                    stat = p.stat()
                    rel_path = str(p.relative_to(service_dir))
                    results.append({
                        "name": p.name,
                        "path": rel_path,
                        "service": service,
                        "format": _get_format(p.suffix),
                        "size_bytes": stat.st_size,
                        "status": "pending",
                        "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                    })

        # 2. Check service root and subdirectories for ingested documents (excluding pending)
        seen_paths = set()
        for p in service_dir.rglob("*"):
            if (
                p.is_file()
                and p.suffix.lower() in allowed_exts
                and "pending" not in p.parts
            ):
                stat = p.stat()
                rel_path = str(p.relative_to(service_dir))
                if rel_path not in seen_paths:
                    results.append({
                        "name": p.name,
                        "path": rel_path,
                        "service": service,
                        "format": _get_format(p.suffix),
                        "size_bytes": stat.st_size,
                        "status": "ingested",
                        "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                    })
                    seen_paths.add(rel_path)

        # Sort pending first, then by name
        results.sort(key=lambda x: (0 if x["status"] == "pending" else 1, x["name"].lower()))
        return results

    async def trigger_ingestion(
        self,
        service: str = "income-assessment-service",
        source_directory: Optional[str] = None,
    ) -> IngestionJob:
        import shutil
        if self._ingestion is None:
            self._init_rag()
        if self._ingestion is None:
            raise RAGServiceException("RAG Ingestion pipeline could not be initialized.")

        target_dir = (
            Path(source_directory)
            if source_directory
            else _project_root / "rag_service" / "sample_data" / service
        )

        job = IngestionJob(
            id=str(uuid.uuid4()),
            service=service,
            source_path=str(target_dir),
            status=IngestionStatus.PROCESSING,
        )

        try:
            if not target_dir.exists():
                job.status = IngestionStatus.FAILED
                job.error_message = f"Source directory '{target_dir}' does not exist."
                job.completed_at = datetime.now(timezone.utc)
                return job

            # Promote pending files to target_dir before ingestion
            pending_dir = target_dir / "pending"
            if pending_dir.is_dir():
                for p in list(pending_dir.rglob("*")):
                    if p.is_file() and p.suffix.lower() in {".md", ".markdown", ".pdf", ".kt", ".kts"}:
                        rel = p.relative_to(pending_dir)
                        dest = target_dir / rel
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(p), str(dest))
                shutil.rmtree(pending_dir, ignore_errors=True)

            ingest_result = await self._ingestion.ingest_directory(target_dir, service=service)
            job.total_files = ingest_result.get("total_files", 0)
            job.total_chunks = ingest_result.get("total_chunks", 0)
            job.files_indexed = [Path(f).name for f in ingest_result.get("files", [])]
            job.status = IngestionStatus.COMPLETED
            job.completed_at = datetime.now(timezone.utc)
            return job
        except Exception as e:
            job.status = IngestionStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.now(timezone.utc)
            return job

    async def upload_course_zip(
        self,
        file_name: str,
        content_bytes: bytes,
    ) -> dict:
        import io
        import shutil
        import tempfile
        import zipfile
        from pathlib import Path

        if not file_name.lower().endswith(".zip"):
            raise ValueError("Only .zip archives are supported for Knowledge Cafe course uploads.")

        if len(content_bytes) == 0:
            raise ValueError("Uploaded zip file is empty.")

        try:
            with zipfile.ZipFile(io.BytesIO(content_bytes)) as zf:
                # Security: prevent zip-slip attacks
                for member in zf.infolist():
                    target_path = Path(member.filename)
                    if target_path.is_absolute() or ".." in target_path.parts:
                        raise ValueError(f"Malicious zip entry detected: {member.filename}")

                with tempfile.TemporaryDirectory() as tmpdir:
                    zf.extractall(tmpdir)
                    tmp_path = Path(tmpdir)

                    # Look for course-structure.md
                    structure_files = list(tmp_path.rglob("course-structure.md"))
                    if not structure_files:
                        raise ValueError(
                            "Invalid course package: 'course-structure.md' was not found in the uploaded zip archive."
                        )

                    structure_file = structure_files[0]
                    course_dir = structure_file.parent

                    from rag_service.knowledge_cafe.course_loader import get_course_loader
                    loader = get_course_loader()
                    course = loader._parse_course_structure(structure_file, course_dir)
                    if not course or not course.id:
                        raise ValueError("Failed to parse valid course definition from course-structure.md")

                    pending_root = _project_root / "rag_service" / "knowledge_cafe" / "pending"
                    pending_root.mkdir(parents=True, exist_ok=True)
                    dest_dir = pending_root / course.id
                    if dest_dir.exists():
                        shutil.rmtree(dest_dir)
                    shutil.copytree(course_dir, dest_dir)

                    return {
                        "course_id": course.id,
                        "title": course.title,
                        "target_service": course.target_service,
                        "total_lessons": len(course.lessons),
                        "status": "pending",
                        "message": f"Course '{course.title}' ({course.id}) uploaded and staged for review. Ingestion not triggered.",
                    }
        except zipfile.BadZipFile:
            raise ValueError("Corrupted or invalid ZIP archive.")

    async def list_pending_courses(self) -> List[dict]:
        from datetime import datetime, timezone
        from rag_service.knowledge_cafe.course_loader import get_course_loader

        pending_root = _project_root / "rag_service" / "knowledge_cafe" / "pending"
        if not pending_root.is_dir():
            return []

        loader = get_course_loader()
        courses = []
        for item in sorted(pending_root.iterdir()):
            if item.is_dir():
                sf = item / "course-structure.md"
                if sf.is_file():
                    try:
                        c = loader._parse_course_structure(sf, item)
                        if c:
                            courses.append({
                                "course_id": c.id,
                                "title": c.title,
                                "target_service": c.target_service,
                                "domain": c.domain,
                                "difficulty": c.difficulty,
                                "total_lessons": len(c.lessons),
                                "status": "pending",
                                "staged_at": datetime.fromtimestamp(item.stat().st_mtime, timezone.utc).isoformat(),
                            })
                    except Exception:
                        pass
        return courses

    async def trigger_course_ingestion(self, course_id: str) -> dict:
        import shutil
        if self._course_indexer is None:
            self._init_rag()
        if self._course_indexer is None:
            raise RAGServiceException("Knowledge Cafe Course Indexer could not be initialized.")

        pending_dir = _project_root / "rag_service" / "knowledge_cafe" / "pending" / course_id
        courses_dir = _project_root / "rag_service" / "knowledge_cafe" / "courses" / course_id

        if pending_dir.is_dir():
            if courses_dir.exists():
                shutil.rmtree(courses_dir)
            courses_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(pending_dir, courses_dir)
            shutil.rmtree(pending_dir)

        if not courses_dir.is_dir():
            raise FileNotFoundError(f"Course '{course_id}' not found in pending staging or published courses.")

        chunks_count = await self._course_indexer.index_course(course_id, force=True)
        return {
            "course_id": course_id,
            "status": "completed",
            "chunks_indexed": chunks_count,
            "message": f"Course '{course_id}' successfully indexed into Knowledge Cafe vector store with {chunks_count} chunks.",
        }

    async def _ensure_kt_indexed(self, course_id: Optional[str] = None):
        if not self._course_indexer:
            return
        try:
            import asyncio
            if course_id:
                if course_id not in self._indexed_courses:
                    self._indexed_courses.add(course_id)
                    asyncio.create_task(self._course_indexer.index_course(course_id))
            else:
                from rag_service.knowledge_cafe.course_loader import get_course_loader
                loader = get_course_loader()
                for c in loader.list_courses():
                    if c.id not in self._indexed_courses:
                        self._indexed_courses.add(c.id)
                        asyncio.create_task(self._course_indexer.index_course(c.id))
        except Exception as e:
            logger.warning(f"Failed to trigger async KT course indexing: {e}")

    async def list_courses(self, group: Optional[str] = None) -> List[dict]:
        if self._kt_engine is None:
            self._init_rag()
        if self._kt_engine is None:
            return []
        return self._kt_engine.list_courses(group=group)

    async def get_course_detail(self, course_id: str) -> Optional[dict]:
        if self._kt_engine is None:
            self._init_rag()
        if self._kt_engine is None:
            return None
        return self._kt_engine.get_course_detail(course_id)

    async def synthesize_lesson(
        self,
        course_id: str,
        lesson_id: str,
        previous_summary: Optional[str] = None,
        model: Optional[str] = None,
    ) -> dict:
        if self._kt_engine is None:
            self._init_rag()
        if self._kt_engine is None:
            raise RAGServiceException("Knowledge Cafe engine could not be initialized.")
        try:
            return await self._kt_engine.synthesize_lesson(
                course_id=course_id,
                lesson_id=lesson_id,
                previous_summary=previous_summary,
                model=model,
            )
        except ValueError as ve:
            from backend_service.app.domain.exceptions.base import EntityNotFoundException
            raise EntityNotFoundException(entity_name="Course/Lesson", entity_id=f"{course_id}/{lesson_id}") from ve
        except Exception as e:
            raise RAGServiceException(f"Error synthesizing lesson: {e}") from e

    async def stream_synthesize_lesson(
        self,
        course_id: str,
        lesson_id: str,
        previous_summary: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Tuple[AsyncIterator[str], List[SourceCitation], Dict[str, Any]]:
        if self._kt_engine is None:
            self._init_rag()
        if self._kt_engine is None:
            raise RAGServiceException("Knowledge Cafe engine could not be initialized.")
        try:
            stream_iter, raw_sources, meta = await self._kt_engine.stream_synthesize_lesson(
                course_id=course_id,
                lesson_id=lesson_id,
                previous_summary=previous_summary,
                model=model,
            )
            citations = [
                SourceCitation(
                    file=s.get("file", ""),
                    service=s.get("service"),
                    doc_type=s.get("doc_type", "course_context"),
                    snippet=s.get("snippet"),
                )
                for s in raw_sources
            ]
            return stream_iter, citations, meta
        except Exception as e:
            raise RAGServiceException(f"Error in stream synthesizing lesson: {e}") from e

    async def answer_doubt(
        self,
        course_id: str,
        lesson_id: str,
        question: str,
        lesson_content_snippet: str = "",
        model: Optional[str] = None,
    ) -> dict:
        if self._kt_engine is None:
            self._init_rag()
        if self._kt_engine is None:
            raise RAGServiceException("Knowledge Cafe engine could not be initialized.")
        try:
            await self._ensure_kt_indexed(course_id)
            return await self._kt_engine.answer_doubt(
                course_id=course_id,
                lesson_id=lesson_id,
                question=question,
                lesson_content_snippet=lesson_content_snippet,
                model=model,
            )
        except Exception as e:
            raise RAGServiceException(f"Error answering lesson doubt: {e}") from e

    async def stream_answer_doubt(
        self,
        course_id: str,
        lesson_id: str,
        question: str,
        lesson_content_snippet: str = "",
        model: Optional[str] = None,
    ) -> Tuple[AsyncIterator[str], List[SourceCitation], Dict[str, Any]]:
        if self._kt_engine is None:
            self._init_rag()
        if self._kt_engine is None:
            raise RAGServiceException("Knowledge Cafe engine could not be initialized.")
        try:
            await self._ensure_kt_indexed(course_id)
            stream_iter, raw_sources, meta = await self._kt_engine.stream_answer_doubt(
                course_id=course_id,
                lesson_id=lesson_id,
                question=question,
                lesson_content_snippet=lesson_content_snippet,
                model=model,
            )
            citations = [
                SourceCitation(
                    file=s.get("file", ""),
                    service=s.get("service"),
                    doc_type=s.get("doc_type", "course_context"),
                    snippet=s.get("snippet"),
                )
                for s in raw_sources
            ]
            return stream_iter, citations, meta
        except Exception as e:
            raise RAGServiceException(f"Error in streaming answer doubt: {e}") from e

    async def get_course_document(
        self,
        course_id: str,
        file_path: str,
    ) -> DocumentView:
        if self._kt_engine is None:
            self._init_rag()
        if self._kt_engine is None:
            raise RAGServiceException("Knowledge Cafe engine could not be initialized.")
        try:
            name, content = self._kt_engine.read_document(course_id, file_path)
            total_lines = len(content.splitlines())
            size_bytes = len(content.encode("utf-8"))
            return DocumentView(
                file=name,
                service=course_id,
                content=content,
                content_type="text/markdown",
                total_lines=total_lines,
                size_bytes=size_bytes,
            )
        except FileNotFoundError as fe:
            from backend_service.app.domain.exceptions.base import EntityNotFoundException
            raise EntityNotFoundException(entity_name="CourseDocument", entity_id=file_path) from fe
        except PermissionError as pe:
            from backend_service.app.domain.exceptions.base import ForbiddenException
            raise ForbiddenException(str(pe)) from pe
