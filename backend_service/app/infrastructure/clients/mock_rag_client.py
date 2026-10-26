import asyncio
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple
import uuid

from backend_service.app.domain.interfaces.rag_client import RAGClientProtocol, RAGQueryResult
from backend_service.app.domain.models.conversation import Message, SourceCitation
from backend_service.app.domain.models.knowledge import DocumentView, IngestionJob, IngestionStatus


class MockRAGClient(RAGClientProtocol):
    """
    Mock adapter for testing and offline environments.
    Simulates grounded RAG responses and ingestion jobs without external network calls.
    """

    async def list_models(self) -> List[dict]:
        """Return simulated models available in mock adapter mode."""
        return [
            {
                "id": "mock-gpt-oss",
                "name": "Mock GPT-OSS 120B",
                "provider": "mock",
                "description": "Simulated open-weight reasoning model for local testing",
                "is_default": True,
            },
            {
                "id": "mock-llama-3",
                "name": "Mock Llama 3.3 70B",
                "provider": "mock",
                "description": "Simulated Meta model for testing",
                "is_default": False,
            },
            {
                "id": "mock-claude-3",
                "name": "Mock Claude 3.5 Sonnet",
                "provider": "mock",
                "description": "Simulated Bedrock Claude model for testing",
                "is_default": False,
            },
        ]

    async def query(
        self,
        query_text: str,
        service: str = "income-assessment-service",
        history: Optional[List[Message]] = None,
        top_k: int = 5,
        model: Optional[str] = None,
    ) -> RAGQueryResult:
        await asyncio.sleep(0.05)  # Simulate brief processing latency

        # Grounded-style simulated response
        answer = (
            f"### Assessment Analysis for `{service}`\n\n"
            f"Based on the indexed architecture and code contracts for **{service}**:\n\n"
            f"1. **Query Evaluated**: \"{query_text}\"\n"
            f"2. **Orchestration**: The request flows through Spring Boot REST Controllers into application domain services.\n"
            f"3. **Integration Anchors**: Interacts with downstream gateways (Zenith AA-Orch, Perfios, CAP) and emits telemetry.\n"
            f"4. **State Management**: Results are persisted to MongoDB and published to Kafka."
        )

        citations = [
            SourceCitation(
                file="01-architecture.md",
                service=service,
                doc_type="Markdown Documentation",
                start_line=1,
                end_line=45,
                snippet="Integration architecture and gateway orchestration overview.",
            ),
            SourceCitation(
                file="FourWheelerPersonalAssessmentHandler.kt",
                service=service,
                class_name="FourWheelerPersonalAssessmentHandler",
                endpoint="/api/v1/assess",
                start_line=23,
                end_line=40,
                doc_type="Kotlin Source",
                snippet="Business handler implementing POST /api/v1/assess",
            ),
        ]

        return RAGQueryResult(
            answer=answer,
            sources=citations,
            service=service,
            latency_ms=52.4,
            provider="mock-local",
            model=model or "mock-gpt-oss",
        )

    async def stream_query(
        self,
        query_text: str,
        service: str = "income-assessment-service",
        history: Optional[List[Message]] = None,
        top_k: int = 5,
        model: Optional[str] = None,
    ) -> Tuple[AsyncIterator[str], List[SourceCitation], Dict[str, Any]]:
        async def _gen():
            chunks = ["### Assessment Analysis for ", f"`{service}`\n\n", "1. **Query Evaluated**: ", f"\"{query_text}\"\n\n", "2. **Orchestration**: Spring Boot reactive processing.\n"]
            for c in chunks:
                await asyncio.sleep(0.01)
                yield c

        sources = [
            SourceCitation(file="00-overview.md", service=service, doc_type="markdown", snippet="Overview of income assessment"),
        ]
        meta = {"service": service, "provider": "mock", "model": model or "mock-gpt-oss"}
        return _gen(), sources, meta

    async def get_document(
        self,
        service: str,
        file_path: str,
    ) -> DocumentView:
        await asyncio.sleep(0.01)
        from pathlib import Path
        _project_root = Path(__file__).resolve().parents[4]
        sample_dir = _project_root / "rag_service" / "sample_data"

        from rag_service.infrastructure.document_reader import DocumentReader
        from backend_service.app.domain.models.knowledge import DocumentView

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
        await asyncio.sleep(0.01)
        return {
            "filename": file_name,
            "service": service,
            "size_bytes": len(content_bytes),
            "status": "pending",
            "message": f"Mock: File '{file_name}' staged for review.",
        }

    async def list_service_files(
        self,
        service: str,
    ) -> List[dict]:
        await asyncio.sleep(0.01)
        return [
            {
                "name": "01-architecture.md",
                "path": "01-architecture.md",
                "service": service,
                "format": "MD",
                "size_bytes": 1024,
                "status": "ingested",
                "modified_at": datetime.now(timezone.utc).isoformat(),
            }
        ]

    async def upload_course_zip(
        self,
        file_name: str,
        content_bytes: bytes,
    ) -> dict:
        await asyncio.sleep(0.01)
        return {
            "course_id": "mock-course-kt",
            "title": "Mock Course",
            "target_service": "income-assessment-service",
            "total_lessons": 5,
            "status": "pending",
            "message": "Mock course uploaded and staged for review.",
        }

    async def list_pending_courses(self) -> List[dict]:
        await asyncio.sleep(0.01)
        return []

    async def trigger_course_ingestion(self, course_id: str) -> dict:
        await asyncio.sleep(0.01)
        return {
            "course_id": course_id,
            "status": "completed",
            "chunks_indexed": 15,
            "message": f"Mock course '{course_id}' indexed successfully.",
        }

    async def trigger_ingestion(
        self,
        service: str = "income-assessment-service",
        source_directory: Optional[str] = None,
    ) -> IngestionJob:
        await asyncio.sleep(0.05)
        now = datetime.now(timezone.utc)
        return IngestionJob(
            id=str(uuid.uuid4()),
            service=service,
            source_path=source_directory or f"sample_data/{service}",
            status=IngestionStatus.COMPLETED,
            total_files=3,
            created_at=now,
            completed_at=now,
        )

    async def list_courses(self, group: Optional[str] = None) -> List[dict]:
        try:
            from rag_service.knowledge_cafe.course_loader import get_course_loader
            return [c.to_summary_dict() for c in get_course_loader().list_courses(group=group)]
        except Exception:
            return [{
                "id": "income-assessment-kt",
                "title": "Income Assessment — KT",
                "description": "Learn the architecture, workflows, and integrations for income-assessment-service.",
                "target_service": "income-assessment-service",
                "domain": "Banking & Credit Microservices",
                "target_audience": "New Backend Engineers",
                "difficulty": "Intermediate",
                "estimated_duration": "1.5 hours",
                "icon": "Layers",
                "tags": ["Spring Boot", "WebFlux", "MongoDB"],
                "total_lessons": 10,
            }]

    async def get_course_detail(self, course_id: str) -> Optional[dict]:
        try:
            from rag_service.knowledge_cafe.course_loader import get_course_loader
            c = get_course_loader().get_course(course_id)
            return c.to_dict() if c else None
        except Exception:
            return None

    async def synthesize_lesson(
        self,
        course_id: str,
        lesson_id: str,
        previous_summary: Optional[str] = None,
        model: Optional[str] = None,
    ) -> dict:
        return {
            "course_id": course_id,
            "lesson_id": lesson_id,
            "lesson_index": 0,
            "title": "Mock Lesson",
            "summary": "Simulated lesson content for testing",
            "content": f"## Mock Lesson for {lesson_id}\n\nThis is simulated lesson content.",
            "takeaways": ["Takeaway 1", "Takeaway 2"],
            "sources": [{"file": "01-overview.md", "service": "income-assessment-service", "doc_type": "course_context", "snippet": "Overview"}],
            "latency_ms": 50,
            "model": model or "mock",
        }

    async def stream_synthesize_lesson(
        self,
        course_id: str,
        lesson_id: str,
        previous_summary: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Tuple[AsyncIterator[str], List[SourceCitation], Dict[str, Any]]:
        async def _gen():
            chunks = [f"## Mock Lesson for {lesson_id}\n\n", "This is simulated ", "streaming lesson content.\n"]
            for c in chunks:
                await asyncio.sleep(0.01)
                yield c
        sources = [SourceCitation(file="01-overview.md", service=course_id, doc_type="course_context", snippet="Overview")]
        meta = {"course_id": course_id, "lesson_id": lesson_id, "model": model or "mock"}
        return _gen(), sources, meta

    async def answer_doubt(
        self,
        course_id: str,
        lesson_id: str,
        question: str,
        lesson_content_snippet: str = "",
        model: Optional[str] = None,
    ) -> dict:
        return {
            "answer": f"Simulated answer for question: '{question}'",
            "sources": [{"file": "01-overview.md", "service": "income-assessment-service", "doc_type": "course_context", "snippet": "Overview"}],
            "latency_ms": 40,
            "model": model or "mock",
        }

    async def stream_answer_doubt(
        self,
        course_id: str,
        lesson_id: str,
        question: str,
        lesson_content_snippet: str = "",
        model: Optional[str] = None,
    ) -> Tuple[AsyncIterator[str], List[SourceCitation], Dict[str, Any]]:
        async def _gen():
            chunks = ["Simulated answer ", "for question: ", f"'{question}'"]
            for c in chunks:
                await asyncio.sleep(0.01)
                yield c
        sources = [SourceCitation(file="01-overview.md", service=course_id, doc_type="course_context", snippet="Overview")]
        meta = {"course_id": course_id, "lesson_id": lesson_id, "model": model or "mock"}
        return _gen(), sources, meta

    async def get_course_document(
        self,
        course_id: str,
        file_path: str,
    ) -> DocumentView:
        from rag_service.knowledge_cafe.course_loader import get_course_loader
        name, content = get_course_loader().read_course_document(course_id, file_path)
        return DocumentView(
            file=name,
            service=course_id,
            content=content,
            content_type="text/markdown",
            total_lines=len(content.splitlines()),
            size_bytes=len(content.encode("utf-8")),
        )
