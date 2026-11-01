import asyncio
import logging
import re
from typing import Any, Dict, List, Optional
import uuid

from rag_service.domain.models import Chunk, DocumentType, ServiceMetadata
from rag_service.domain.protocols import VectorStore
from rag_service.infrastructure.config import Settings, get_settings

logger = logging.getLogger(__name__)

_SPARSE_MODEL_INSTANCE = None
_SHARED_QDRANT_CLIENTS: Dict[tuple, Any] = {}
_VERIFIED_COLLECTIONS: set = set()
MAX_MEMORY_FALLBACK_CHUNKS: int = 2000


def _get_sparse_bm25_model():
    global _SPARSE_MODEL_INSTANCE
    if _SPARSE_MODEL_INSTANCE is None:
        try:
            from fastembed import SparseTextEmbedding

            _SPARSE_MODEL_INSTANCE = SparseTextEmbedding(model_name="Qdrant/bm25")
        except Exception as e:
            logger.warning("Failed to initialize SparseTextEmbedding('Qdrant/bm25'): %s", e)
            _SPARSE_MODEL_INSTANCE = False
    return _SPARSE_MODEL_INSTANCE if _SPARSE_MODEL_INSTANCE is not False else None


class QdrantVectorStoreAdapter:
    """
    Qdrant Cloud vector database adapter conforming to VectorStore protocol.
    Provides Hybrid Search (Dense Jina-Code-v2 + Sparse BM25 with Reciprocal Rank Fusion),
    1-hop symbol expansion, service-level metadata isolation, self-healing collections,
    and an in-memory fallback.
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

    def _ensure_collection(self, force: bool = False) -> None:
        """
        Ensure the target Qdrant collection, sparse BM25 vector config,
        and required keyword payload indexes exist.
        """
        if self._client is None:
            return

        cache_key = (self.url, self.collection_name, self.dimension)
        if not force and cache_key in _VERIFIED_COLLECTIONS:
            return

        from qdrant_client.http.models import (
            Distance,
            Modifier,
            PayloadSchemaType,
            SparseVectorParams,
            VectorParams,
        )

        collections = self._client.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)
        sparse_cfg = {"bm25": SparseVectorParams(modifier=Modifier.IDF)}
        existing_indexes: set = set()

        if not exists:
            logger.info(
                f"Creating Qdrant hybrid collection '{self.collection_name}' (dim={self.dimension} + BM25)..."
            )
            self._client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=self.dimension, distance=Distance.COSINE),
                sparse_vectors_config=sparse_cfg,
            )
        else:
            try:
                info = self._client.get_collection(self.collection_name)
                remote_dim = info.config.params.vectors.size
                sparse_params = getattr(info.config.params, "sparse_vectors", None) or {}
                has_bm25 = "bm25" in sparse_params
                existing_indexes = set((getattr(info, "payload_schema", None) or {}).keys())
                if remote_dim != self.dimension or not has_bm25:
                    logger.warning(
                        f"Qdrant collection schema upgrade required for '{self.collection_name}' "
                        f"(dim: {remote_dim}->{self.dimension}, has_bm25: {has_bm25}). Recreating collection."
                    )
                    self._client.delete_collection(self.collection_name)
                    self._client.create_collection(
                        collection_name=self.collection_name,
                        vectors_config=VectorParams(size=self.dimension, distance=Distance.COSINE),
                        sparse_vectors_config=sparse_cfg,
                    )
                    existing_indexes = set()
            except Exception as e:
                logger.warning(f"Failed to verify collection schema: {e}")

        for field_name in ("service", "course_id", "customer_id", "doc_type", "class_name"):
            if field_name in existing_indexes:
                continue
            try:
                self._client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name=field_name,
                    field_schema=PayloadSchemaType.KEYWORD,
                )
            except Exception:
                pass

        _VERIFIED_COLLECTIONS.add(cache_key)

    def _init_client(self) -> None:
        if not self.url:
            return

        try:
            from qdrant_client import QdrantClient

            client_key = (self.url, self.api_key)
            if client_key not in _SHARED_QDRANT_CLIENTS:
                port = None if self.url.startswith("https://") else 6333
                _SHARED_QDRANT_CLIENTS[client_key] = QdrantClient(
                    url=self.url,
                    port=port,
                    api_key=self.api_key,
                )
            self._client = _SHARED_QDRANT_CLIENTS[client_key]
            self._ensure_collection()
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant Cloud client: {e}")
            self._client = None

    async def upsert(self, chunks: List[Chunk]) -> int:
        """
        Store chunks with dense vector embeddings + sparse BM25 embeddings in Qdrant Cloud.
        Automatically recreates the collection if it was manually deleted remotely.
        """
        if not chunks:
            return 0

        if self._client is None:
            for c in chunks:
                if len(self._memory_chunks) >= MAX_MEMORY_FALLBACK_CHUNKS and c.id not in self._memory_chunks:
                    oldest_key = next(iter(self._memory_chunks))
                    self._memory_chunks.pop(oldest_key, None)
                self._memory_chunks[c.id] = c
            return len(chunks)

        try:
            from qdrant_client.http.models import PointStruct, SparseVector

            valid_chunks = [c for c in chunks if c.embedding is not None]
            if not valid_chunks:
                return 0

            def _build_and_upsert():
                sparse_model = _get_sparse_bm25_model()
                sparse_embeddings = []
                if sparse_model is not None:
                    try:
                        sparse_embeddings = list(
                            sparse_model.embed([c.content for c in valid_chunks])
                        )
                    except Exception as se:
                        logger.warning("BM25 sparse embedding failed during upsert: %s", se)
                        sparse_embeddings = []

                points = []
                for idx, c in enumerate(valid_chunks):
                    point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, c.id))
                    payload = c.metadata.to_dict()
                    payload["content"] = c.content
                    payload["chunk_id"] = c.id
                    payload["index"] = c.index

                    if idx < len(sparse_embeddings):
                        sp = sparse_embeddings[idx]
                        vec_data: Any = {
                            "": c.embedding,
                            "bm25": SparseVector(
                                indices=sp.indices.tolist(),
                                values=sp.values.tolist(),
                            ),
                        }
                    else:
                        vec_data = c.embedding

                    points.append(
                        PointStruct(
                            id=point_id,
                            vector=vec_data,
                            payload=payload,
                        )
                    )

                try:
                    self._client.upsert(
                        collection_name=self.collection_name,
                        points=points,
                    )
                except Exception as exc:
                    err_str = str(exc).lower()
                    if (
                        "404" in err_str
                        or "not found" in err_str
                        or "doesn't exist" in err_str
                        or "bm25" in err_str
                        or "dimension" in err_str
                    ):
                        logger.warning(
                            f"Collection '{self.collection_name}' missing or outdated during upsert. Auto-creating and retrying..."
                        )
                        self._ensure_collection(force=True)
                        self._client.upsert(
                            collection_name=self.collection_name,
                            points=points,
                        )
                    else:
                        raise
                return len(points)

            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, _build_and_upsert)
        except Exception as e:
            raise RuntimeError(f"Qdrant upsert failed: {e}") from e

    def _hit_to_chunk(self, hit: Any, default_service: Optional[str] = None) -> Chunk:
        payload = dict(hit.payload or {})
        content = payload.pop("content", "")
        chunk_id = payload.pop("chunk_id", str(hit.id))
        index = payload.pop("index", 0)

        doc_type_str = payload.get("document_type", "markdown")
        try:
            doc_type = DocumentType(doc_type_str)
        except ValueError:
            doc_type = DocumentType.OTHER

        metadata = ServiceMetadata(
            service=payload.get("service", default_service or "unknown"),
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
            extra={
                k: v
                for k, v in payload.items()
                if k
                not in {
                    "service",
                    "document_type",
                    "source",
                    "file_path",
                    "language",
                    "package",
                    "class_name",
                    "method_name",
                    "endpoint",
                    "start_line",
                    "end_line",
                    "git_commit",
                }
            },
        )

        return Chunk(
            id=chunk_id,
            content=content,
            metadata=metadata,
            index=index,
        )

    async def search(
        self,
        query_vector: List[float],
        limit: int = 5,
        service_filter: Optional[str] = None,
        filter_dict: Optional[Dict[str, Any]] = None,
        score_threshold: Optional[float] = None,
        query_text: Optional[str] = None,
    ) -> List[Chunk]:
        """
        Execute Hybrid Search (Dense + Sparse BM25 with Reciprocal Rank Fusion) when query_text
        is provided, or fallback to Dense Vector Search with service-level metadata filtering.
        """
        if self._client is None:
            return self._memory_search(query_vector, limit, service_filter, filter_dict, query_text)

        try:
            from qdrant_client.http.models import (
                FieldCondition,
                Filter,
                Fusion,
                FusionQuery,
                MatchValue,
                Prefetch,
                SparseVector,
            )

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
                try:
                    sparse_model = _get_sparse_bm25_model() if query_text else None
                    if query_text and sparse_model is not None and hasattr(self._client, "query_points"):
                        try:
                            sparse_q_list = list(sparse_model.query_embed([query_text]))
                            if sparse_q_list and len(sparse_q_list[0].indices) > 0:
                                sp_q = sparse_q_list[0]
                                prefetch_limit = max(limit * 2, 12)
                                res = self._client.query_points(
                                    collection_name=self.collection_name,
                                    prefetch=[
                                        Prefetch(
                                            query=query_vector,
                                            filter=q_filter,
                                            limit=prefetch_limit,
                                        ),
                                        Prefetch(
                                            query=SparseVector(
                                                indices=sp_q.indices.tolist(),
                                                values=sp_q.values.tolist(),
                                            ),
                                            using="bm25",
                                            filter=q_filter,
                                            limit=prefetch_limit,
                                        ),
                                    ],
                                    query=FusionQuery(fusion=Fusion.RRF),
                                    query_filter=q_filter,
                                    limit=limit,
                                )
                                return res.points if hasattr(res, "points") else res
                        except Exception as hybrid_err:
                            logger.debug("Hybrid RRF query fallback to dense search: %s", hybrid_err)

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
                except Exception as exc:
                    err_str = str(exc).lower()
                    if "404" in err_str or "not found" in err_str or "doesn't exist" in err_str:
                        logger.warning(
                            f"Collection '{self.collection_name}' missing during search. Auto-creating empty collection..."
                        )
                        self._ensure_collection(force=True)
                        return []
                    raise

            loop = asyncio.get_running_loop()
            results = await loop.run_in_executor(None, _do_search)

            return [self._hit_to_chunk(hit, service_filter) for hit in results]
        except Exception as e:
            logger.error(f"Qdrant search failed, falling back to local memory: {e}")
            return self._memory_search(query_vector, limit, service_filter, filter_dict, query_text)

    async def fetch_by_symbols(
        self,
        service: str,
        symbols: List[str],
        limit: int = 3,
    ) -> List[Chunk]:
        """
        Retrieve chunks defining specific collaborator classes/symbols for 1-Hop Dependency Expansion.
        """
        if not symbols or limit <= 0:
            return []

        if self._client is None:
            found: List[Chunk] = []
            seen_classes = set()
            for c in self._memory_chunks.values():
                if c.metadata.service == service and c.metadata.class_name in symbols:
                    if c.metadata.class_name not in seen_classes:
                        found.append(c)
                        seen_classes.add(c.metadata.class_name)
                        if len(found) >= limit:
                            break
            return found

        try:
            from qdrant_client.http.models import FieldCondition, Filter, MatchAny, MatchValue

            q_filter = Filter(
                must=[
                    FieldCondition(key="service", match=MatchValue(value=service)),
                    FieldCondition(key="class_name", match=MatchAny(any=list(symbols)[:15])),
                ]
            )

            def _do_scroll():
                try:
                    records, _ = self._client.scroll(
                        collection_name=self.collection_name,
                        scroll_filter=q_filter,
                        limit=max(limit * 8, 30),
                        with_payload=True,
                        with_vectors=False,
                    )
                    return records
                except Exception:
                    return []

            loop = asyncio.get_running_loop()
            records = await loop.run_in_executor(None, _do_scroll)

            symbol_priority = {sym: idx for idx, sym in enumerate(symbols)}
            chunks_from_records = [self._hit_to_chunk(rec, service) for rec in records]
            chunks_from_records.sort(
                key=lambda c: (
                    symbol_priority.get(c.metadata.class_name or "", 999),
                    c.metadata.start_line or 0,
                )
            )

            expanded: List[Chunk] = []
            seen_classes = set()
            for chunk in chunks_from_records:
                cls_name = chunk.metadata.class_name
                if cls_name and cls_name not in seen_classes:
                    seen_classes.add(cls_name)
                    expanded.append(chunk)
                    if len(expanded) >= limit:
                        break
            return expanded
        except Exception as e:
            logger.debug("1-hop symbol expansion skipped: %s", e)
            return []

    async def fetch_by_methods(
        self,
        service: str,
        methods: List[str],
        limit: int = 4,
    ) -> List[Chunk]:
        """
        Retrieve chunks defining specific target methods for multi-hop call-chain traversal.
        """
        if not methods or limit <= 0:
            return []

        raw_methods: List[str] = []
        for m in methods:
            short = m.split(".")[-1].split("#")[-1]
            if short and short not in raw_methods:
                raw_methods.append(short)
            if m not in raw_methods:
                raw_methods.append(m)

        if self._client is None:
            found: List[Chunk] = []
            seen_ids = set()
            for c in self._memory_chunks.values():
                if c.metadata.service == service:
                    m_name = c.metadata.method_name or ""
                    full_m = f"{c.metadata.class_name}.{m_name}" if c.metadata.class_name else m_name
                    if m_name in raw_methods or full_m in methods:
                        if c.id not in seen_ids:
                            seen_ids.add(c.id)
                            found.append(c)
                            if len(found) >= limit:
                                break
            return found

        try:
            from qdrant_client.http.models import FieldCondition, Filter, MatchAny, MatchValue

            q_filter = Filter(
                must=[
                    FieldCondition(key="service", match=MatchValue(value=service)),
                    FieldCondition(key="method_name", match=MatchAny(any=raw_methods[:20])),
                ]
            )

            def _do_scroll():
                try:
                    records, _ = self._client.scroll(
                        collection_name=self.collection_name,
                        scroll_filter=q_filter,
                        limit=max(limit * 6, 20),
                        with_payload=True,
                        with_vectors=False,
                    )
                    return records
                except Exception:
                    return []

            loop = asyncio.get_running_loop()
            records = await loop.run_in_executor(None, _do_scroll)

            chunks_from_records = [self._hit_to_chunk(rec, service) for rec in records]
            method_priority = {m: idx for idx, m in enumerate(raw_methods)}
            chunks_from_records.sort(
                key=lambda c: (
                    method_priority.get(c.metadata.method_name or "", 999),
                    c.metadata.start_line or 0,
                )
            )

            expanded: List[Chunk] = []
            seen_methods = set()
            for chunk in chunks_from_records:
                m_key = f"{chunk.metadata.class_name}#{chunk.metadata.method_name}"
                if m_key not in seen_methods:
                    seen_methods.add(m_key)
                    expanded.append(chunk)
                    if len(expanded) >= limit:
                        break
            return expanded
        except Exception as e:
            logger.debug("Method-level graph expansion skipped: %s", e)
            return []

    def _memory_search(
        self,
        query_vector: List[float],
        limit: int = 5,
        service_filter: Optional[str] = None,
        filter_dict: Optional[Dict[str, Any]] = None,
        query_text: Optional[str] = None,
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

        query_tokens = set(re.findall(r"[a-zA-Z0-9_]+", (query_text or "").lower()))

        def hybrid_score(c: Chunk) -> float:
            dense = cosine_sim(query_vector, c.embedding or [])
            if not query_tokens:
                return dense
            doc_tokens = set(re.findall(r"[a-zA-Z0-9_]+", c.content.lower()))
            overlap = len(query_tokens & doc_tokens) / max(len(query_tokens), 1)
            return 0.7 * dense + 0.3 * overlap

        scored = [(hybrid_score(c), c) for c in matched]
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

    async def delete_by_service(self, service: str) -> bool:
        """Delete all indexed vectors matching a specific service identifier."""
        if self._client is None:
            to_remove = [cid for cid, c in self._memory_chunks.items() if c.metadata.service == service]
            for cid in to_remove:
                self._memory_chunks.pop(cid, None)
            return True

        try:
            from qdrant_client.http.models import Filter, FieldCondition, MatchValue, FilterSelector

            q_filter = Filter(
                must=[
                    FieldCondition(
                        key="service",
                        match=MatchValue(value=service),
                    )
                ]
            )
            def _do_delete():
                try:
                    self._client.delete(
                        collection_name=self.collection_name,
                        points_selector=FilterSelector(filter=q_filter),
                    )
                except Exception as exc:
                    err_str = str(exc).lower()
                    if "404" in err_str or "not found" in err_str or "doesn't exist" in err_str:
                        logger.warning(
                            f"Collection '{self.collection_name}' missing during delete_by_service. Auto-creating..."
                        )
                        self._ensure_collection(force=True)
                    else:
                        raise

            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, _do_delete)
            logger.info(f"Successfully purged all points for service '{service}' in '{self.collection_name}'.")
            return True
        except Exception as e:
            logger.error(f"Failed to delete points for service '{service}': {e}")
            raise RuntimeError(f"Qdrant delete_by_service failed: {e}") from e
