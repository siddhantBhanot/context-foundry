import hashlib
import logging
from typing import Any, Dict, List, Optional

from rag_service.domain.models import Chunk, DocumentType, ServiceMetadata
from rag_service.domain.protocols import EmbeddingProvider, VectorStore
from rag_service.knowledge_cafe.course_loader import CourseLoader, get_course_loader

logger = logging.getLogger("rag_service.knowledge_cafe.indexer")


class CourseIndexer:
    """
    Indexes creator-defined Knowledge Cafe course context files into the dedicated
    Qdrant `knowledge_cafe_collection`. Every chunk is tagged with `course_id` and `lesson_id`
    for strict pre-filtered semantic retrieval.
    """

    def __init__(
        self,
        vector_store: VectorStore,
        embedding_provider: EmbeddingProvider,
        course_loader: Optional[CourseLoader] = None,
    ) -> None:
        self.vector_store = vector_store
        self.embedding_provider = embedding_provider
        self.course_loader = course_loader or get_course_loader()
        self._indexed_hashes: Dict[str, str] = {}

    def _split_markdown_chunks(
        self,
        content: str,
        max_chunk_size: int = 1200,
        min_chunk_size: int = 100,
    ) -> List[str]:
        """Split markdown content by sections or paragraphs to maintain pedagogical coherence."""
        sections = content.split("\n## ")
        raw_chunks: List[str] = []

        for i, section in enumerate(sections):
            text = section if i == 0 else f"## {section}"
            text = text.strip()
            if not text:
                continue

            if len(text) <= max_chunk_size:
                raw_chunks.append(text)
            else:
                # Split large sections by paragraphs
                paras = text.split("\n\n")
                current_buf = []
                current_len = 0

                for p in paras:
                    p = p.strip()
                    if not p:
                        continue
                    if current_len + len(p) > max_chunk_size and current_buf:
                        raw_chunks.append("\n\n".join(current_buf))
                        current_buf = [p]
                        current_len = len(p)
                    else:
                        current_buf.append(p)
                        current_len += len(p)

                if current_buf:
                    raw_chunks.append("\n\n".join(current_buf))

        # Filter out trivial fragments
        return [c for c in raw_chunks if len(c) >= min_chunk_size]

    async def index_course(self, course_id: str, force: bool = False) -> int:
        """
        Index all lesson context files for a specific course into the dedicated vector store.
        Returns the number of chunks upserted.
        """
        course = self.course_loader.get_course(course_id)
        if not course:
            logger.warning(f"Course '{course_id}' not found for indexing.")
            return 0

        chunks_to_upsert: List[Chunk] = []

        for lesson in course.lessons:
            file_contents = self.course_loader.read_lesson_context_files(course_id, lesson.id)

            for file_name, content in file_contents:
                content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
                file_key = f"{course_id}:{lesson.id}:{file_name}"

                if not force and self._indexed_hashes.get(file_key) == content_hash:
                    continue  # Unchanged content, skip re-embedding

                splits = self._split_markdown_chunks(content)
                if not splits:
                    splits = [content] if len(content.strip()) > 30 else []

                for idx, text in enumerate(splits):
                    chunk_id = f"{course_id}_{lesson.id}_{file_name}_{idx}"
                    metadata = ServiceMetadata(
                        service=course.target_service,
                        document_type=DocumentType.MARKDOWN,
                        source="knowledge_cafe",
                        file_path=f"{course_id}/{lesson.id}/{file_name}",
                        extra={
                            "course_id": course.id,
                            "course_title": course.title,
                            "lesson_id": lesson.id,
                            "lesson_title": lesson.title,
                            "lesson_index": lesson.lesson_index,
                            "file_name": file_name,
                            "content_hash": content_hash,
                        },
                    )
                    chunk = Chunk(
                        id=chunk_id,
                        content=text,
                        metadata=metadata,
                        index=idx,
                    )
                    chunks_to_upsert.append(chunk)

                self._indexed_hashes[file_key] = content_hash

        if not chunks_to_upsert:
            logger.info(f"Course '{course_id}' is already up-to-date in vector store.")
            return 0

        logger.info(
            f"Embedding and indexing {len(chunks_to_upsert)} chunks for course '{course_id}'..."
        )
        texts = [c.content for c in chunks_to_upsert]
        embeddings = await self.embedding_provider.embed(texts)

        for chunk, emb in zip(chunks_to_upsert, embeddings):
            chunk.embedding = emb

        count = await self.vector_store.upsert(chunks_to_upsert)
        logger.info(
            f"Successfully indexed {count} chunks for course '{course_id}' into knowledge_cafe_collection."
        )
        return count

    async def index_all_courses(self, force: bool = False) -> Dict[str, int]:
        """Index all available courses in the course catalog."""
        courses = self.course_loader.list_courses()
        results = {}
        for c in courses:
            try:
                count = await self.index_course(c.id, force=force)
                results[c.id] = count
            except Exception as e:
                logger.error(f"Failed to index course '{c.id}': {e}", exc_info=True)
                results[c.id] = 0
        return results
