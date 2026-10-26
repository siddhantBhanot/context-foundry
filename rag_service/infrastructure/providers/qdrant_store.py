import asyncio
import logging
from typing import Any, Dict, List, Optional
import uuid

from rag_service.domain.models import Chunk, DocumentType, ServiceMetadata
from rag_service.domain.protocols import VectorStore
from rag_service.infrastructure.config import Settings, get_settings

logger = logging.getLogger(__name__)


class QdrantVectorStoreAdapter:
    """
    Qdrant Cloud vector database adapter conforming to VectorStore protocol.
    Provides semantic search with service-level metadata isolation and an in-memory fallback.
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        collection_name: Optional[str] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.url = self.settings.qdrant_url
        self.api_key = self.settings.qdrant_api_key
        self.collection_name = collection_name or self.settings.qdrant_collection_name
        self.dimension = self.settings.embedding_dimension
        self._client = None
        self._memory_chunks: Dict[str, Chunk] = {}  # Local fallback when offline
        self._init_client()

    def _init_client(self) -> None:
        if not self.url:
            return

        try:
            from qdrant_client import QdrantClient
            from qdrant_client.http.models import Distance, VectorParams, PayloadSchemaType

            port = None if self.url.startswith("https://") else 6333
            self._client = QdrantClient(url=self.url, port=port, api_key=self.api_key)

            collections = self._client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)
            if not exists:
                self._client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=self.dimension, distance=Distance.COSINE),
                )
            else:
                try:
                    info = self._client.get_collection(self.collection_name)
                    remote_dim = info.config.params.vectors.size
                    if remote_dim != self.dimension:
                        logger.warning(
                            f"Qdrant collection dimension mismatch ({remote_dim} != {self.dimension}). Recreating collection."
                        )
                        self._client.delete_collection(self.collection_name)
                        self._client.create_collection(
                            collection_name=self.collection_name,
                            vectors_config=VectorParams(size=self.dimension, distance=Distance.COSINE),
                        )
                except Exception as e:
                    logger.warning(f"Failed to verify collection schema: {e}")

            try:
                self._client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="service",
                    field_schema=PayloadSchemaType.KEYWORD,
                )
                self._client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="course_id",
                    field_schema=PayloadSchemaType.KEYWORD,
                )
                self._client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="customer_id",
                    field_schema=PayloadSchemaType.KEYWORD,
                )
                self._client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="doc_type",
                    field_schema=PayloadSchemaType.KEYWORD,
                )
            except Exception:
                pass
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant Cloud client: {e}")
            self._client = None

    async def upsert(self, chunks: List[Chunk]) -> int:
        """
        Store chunks with dense vector embeddings in Qdrant Cloud.
        """
        if not chunks:
            return 0

        if self._client is None:
            for c in chunks:
                self._memory_chunks[c.id] = c
            return len(chunks)

        try:
            from qdrant_client.http.models import PointStruct

            points = []
            for c in chunks:
                if c.embedding is None:
                    continue

                point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, c.id))
                payload = c.metadata.to_dict()
                payload["content"] = c.content
                payload["chunk_id"] = c.id
                payload["index"] = c.index

                points.append(
                    PointStruct(
                        id=point_id,
                        vector=c.embedding,
                        payload=payload,
                    )
                )

            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                lambda: self._client.upsert(
                    collection_name=self.collection_name,
                    points=points,
                ),
            )
            return len(points)
        except Exception as e:
            raise RuntimeError(f"Qdrant upsert failed: {e}") from e

    async def search(
        self,
        query_vector: List[float],
        limit: int = 5,
        service_filter: Optional[str] = None,
        filter_dict: Optional[Dict[str, Any]] = None,
        score_threshold: Optional[float] = None,
    ) -> List[Chunk]:
        """
        Search nearest neighbor chunks with service-level or arbitrary metadata filtering.
        """
        if self._client is None:
            return self._memory_search(query_vector, limit, service_filter, filter_dict)

        try:
            from qdrant_client.http.models import FieldCondition, Filter, MatchValue

            conditions = []
            if service_filter:
                conditions.append(
                    FieldCondition(
                        key="service",
                        match=MatchValue(value=service_filter),
                    )
                )
            if filter_dict:
                for k, v in filter_dict.items():
                    if v is not None:
                        conditions.append(
                            FieldCondition(
                                key=k,
                                match=MatchValue(value=v),
                            )
                        )

            q_filter: Optional[Filter] = Filter(must=conditions) if conditions else None

            def _do_search():
                if hasattr(self._client, "query_points"):
                    res = self._client.query_points(
                        collection_name=self.collection_name,
                        query=query_vector,
                        query_filter=q_filter,
                        limit=limit,
                        score_threshold=score_threshold,
                    )
                    return res.points if hasattr(res, "points") else res
                return self._client.search(
                    collection_name=self.collection_name,
                    query_vector=query_vector,
                    query_filter=q_filter,
                    limit=limit,
                    score_threshold=score_threshold,
                )

            loop = asyncio.get_running_loop()
            results = await loop.run_in_executor(None, _do_search)

            chunks: List[Chunk] = []
            for hit in results:
                payload = hit.payload or {}
                content = payload.pop("content", "")
                chunk_id = payload.pop("chunk_id", str(hit.id))
                index = payload.pop("index", 0)

                doc_type_str = payload.get("document_type", "markdown")
                try:
                    doc_type = DocumentType(doc_type_str)
                except ValueError:
                    doc_type = DocumentType.OTHER

                metadata = ServiceMetadata(
                    service=payload.get("service", service_filter or "unknown"),
                    document_type=doc_type,
                    source=payload.get("source", "knowledge_base"),
                    file_path=payload.get("file_path", ""),
                    language=payload.get("language", "markdown"),
                    package=payload.get("package"),
                    class_name=payload.get("class_name"),
                    method_name=payload.get("method_name"),
                    endpoint=payload.get("endpoint"),
                    start_line=payload.get("start_line"),
                    end_line=payload.get("end_line"),
                    git_commit=payload.get("git_commit"),
                    extra={k: v for k, v in payload.items() if k not in {
                        "service", "document_type", "source", "file_path", "language",
                        "package", "class_name", "method_name", "endpoint", "start_line", "end_line", "git_commit"
                    }},
                )

                chunks.append(
                    Chunk(
                        id=chunk_id,
                        content=content,
                        metadata=metadata,
                        index=index,
                    )
                )

            return chunks
        except Exception as e:
            logger.error(f"Qdrant search failed, falling back to local memory: {e}")
            return self._memory_search(query_vector, limit, service_filter, filter_dict)

    def _memory_search(
        self,
        query_vector: List[float],
        limit: int = 5,
        service_filter: Optional[str] = None,
        filter_dict: Optional[Dict[str, Any]] = None,
    ) -> List[Chunk]:
        matched = []
        for c in self._memory_chunks.values():
            if service_filter and c.metadata.service != service_filter:
                continue
            if filter_dict:
                meta_dict = c.metadata.to_dict()
                match = True
                for k, v in filter_dict.items():
                    if meta_dict.get(k) != v:
                        match = False
                        break
                if not match:
                    continue
            matched.append(c)

        if not query_vector or not matched:
            return matched[:limit]

        def cosine_sim(v1: List[float], v2: List[float]) -> float:
            if not v1 or not v2 or len(v1) != len(v2):
                return 0.0
            dot = sum(a * b for a, b in zip(v1, v2))
            norm1 = sum(a * a for a in v1) ** 0.5
            norm2 = sum(b * b for b in v2) ** 0.5
            return dot / (norm1 * norm2) if (norm1 * norm2) > 0 else 0.0

        scored = [(cosine_sim(query_vector, c.embedding or []), c) for c in matched]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored[:limit]]

    async def delete(self, chunk_ids: List[str]) -> bool:
        """Delete points by IDs."""
        if self._client is None:
            for cid in chunk_ids:
                self._memory_chunks.pop(cid, None)
            return True

        try:
            from qdrant_client.http.models import PointIdsList

            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                lambda: self._client.delete(
                    collection_name=self.collection_name,
                    points_selector=PointIdsList(points=chunk_ids),
                ),
            )
            return True
        except Exception as e:
            raise RuntimeError(f"Qdrant delete failed: {e}") from e
