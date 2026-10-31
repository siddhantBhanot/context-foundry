from pathlib import Path
from typing import Any, Dict, List, Optional

from rag_service.domain.models import Chunk
from rag_service.domain.protocols import EmbeddingProvider, VectorStore
from rag_service.ingestion.chunkers.java_chunker import JavaChunker
from rag_service.ingestion.chunkers.kotlin_chunker import KotlinChunker
from rag_service.ingestion.chunkers.markdown_chunker import MarkdownChunker
from rag_service.ingestion.chunkers.python_chunker import PythonChunker
from rag_service.ingestion.repo_map import RepoMapBuilder
from rag_service.ingestion.symbol_graph import SymbolGraphBuilder


class IngestionPipeline:
    """
    Coordinates loading, structural AST/regex chunking, scope header injection,
    embedding generation, RepoMap construction, and vector store upsertion for
    engineering documentation and source code (.kt, .kts, .java, .py, .md, .pdf).
    """

    def __init__(
        self,
        vector_store: VectorStore,
        embedding_provider: EmbeddingProvider,
        default_service: str = "default-service",
    ) -> None:
        self.vector_store = vector_store
        self.embedding_provider = embedding_provider
        self.default_service = default_service
        self.md_chunker = MarkdownChunker(service=default_service)
        self.kt_chunker = KotlinChunker(service=default_service)
        self.java_chunker = JavaChunker(service=default_service)
        self.py_chunker = PythonChunker(service=default_service)

    async def ingest_file(
        self,
        file_path: Path | str,
        service: Optional[str] = None,
        source: str = "local",
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Chunk]:
        """
        Ingest a single Kotlin (.kt, .kts), Java (.java), Python (.py), Markdown (.md), or PDF (.pdf) file.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found for ingestion: {path}")

        target_service = service or self.default_service
        suffix = path.suffix.lower()
        if suffix in [".kt", ".kts"]:
            content = path.read_text(encoding="utf-8", errors="replace")
            chunker = KotlinChunker(service=target_service)
            chunks = chunker.chunk(
                content=content,
                file_path=str(path),
                source=source,
                extra_metadata=extra_metadata,
            )
        elif suffix == ".java":
            content = path.read_text(encoding="utf-8", errors="replace")
            chunker = JavaChunker(service=target_service)
            chunks = chunker.chunk(
                content=content,
                file_path=str(path),
                source=source,
                extra_metadata=extra_metadata,
            )
        elif suffix == ".py":
            content = path.read_text(encoding="utf-8", errors="replace")
            chunker = PythonChunker(service=target_service)
            chunks = chunker.chunk(
                content=content,
                file_path=str(path),
                source=source,
                extra_metadata=extra_metadata,
            )
        elif suffix == ".pdf":
            try:
                from pypdf import PdfReader
                reader = PdfReader(str(path))
                pages_text = []
                for page_num, page in enumerate(reader.pages, start=1):
                    t = page.extract_text() or ""
                    if t.strip():
                        pages_text.append(f"## Page {page_num}\n\n{t.strip()}")
                content = "\n\n".join(pages_text) if pages_text else "Empty PDF document"
            except Exception as e:
                content = f"Error reading PDF {path.name}: {e}"
            chunker = MarkdownChunker(service=target_service)
            meta = dict(extra_metadata or {})
            meta["file_type"] = "pdf"
            chunks = chunker.chunk(
                content=content,
                file_path=str(path),
                source=source,
                extra_metadata=meta,
            )
        elif suffix in [".md", ".markdown"]:
            content = path.read_text(encoding="utf-8", errors="replace")
            chunker = MarkdownChunker(service=target_service)
            chunks = chunker.chunk(
                content=content,
                file_path=str(path),
                source=source,
                extra_metadata=extra_metadata,
            )
        else:
            # Default text chunking via markdown chunker
            content = path.read_text(encoding="utf-8", errors="replace")
            chunker = MarkdownChunker(service=target_service)
            chunks = chunker.chunk(
                content=content,
                file_path=str(path),
                source=source,
                extra_metadata=extra_metadata,
            )

        if not chunks:
            return []

        # Batch embed chunk texts
        texts = [c.content for c in chunks]
        embeddings = await self.embedding_provider.embed(texts)

        for chunk, emb in zip(chunks, embeddings):
            chunk.embedding = emb

        # Upsert into vector store
        await self.vector_store.upsert(chunks)
        return chunks

    async def ingest_directory(
        self,
        directory_path: Path | str,
        service: Optional[str] = None,
        pattern: str = "**/*",
    ) -> Dict[str, Any]:
        """
        Recursively ingest all matching Kotlin, Java, Python, Markdown, and PDF files in a directory,
        and build the microservice RepoMap (_repo_map.json).
        """
        dir_path = Path(directory_path)
        if not dir_path.is_dir():
            raise NotADirectoryError(f"Directory not found: {dir_path}")

        target_service = service or self.default_service
        allowed_extensions = {".md", ".markdown", ".pdf", ".kt", ".kts", ".java", ".py"}
        total_chunks = 0
        ingested_files: List[str] = []
        all_chunks: List[Chunk] = []

        for p in sorted(dir_path.glob(pattern)):
            if (
                p.is_file()
                and p.suffix.lower() in allowed_extensions
                and not p.name.startswith(".")
                and "pending" not in p.parts
            ):
                chunks = await self.ingest_file(p, service=target_service)
                total_chunks += len(chunks)
                ingested_files.append(str(p))
                all_chunks.extend(chunks)

        if all_chunks:
            RepoMapBuilder.build_and_save(
                directory_path=dir_path,
                service=target_service,
                chunks=all_chunks,
            )
            try:
                SymbolGraphBuilder.build_and_save(
                    directory_path=dir_path,
                    service=target_service,
                )
            except Exception as e:
                # Keep ingestion robust if symbol graph generation encounters issues
                pass

        return {
            "service": target_service,
            "total_files": len(ingested_files),
            "total_chunks": total_chunks,
            "files": ingested_files,
        }
