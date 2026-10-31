import asyncio
import logging
from typing import List, Optional

from rag_service.domain.protocols import EmbeddingProvider
from rag_service.infrastructure.config import Settings, get_settings

logger = logging.getLogger(__name__)


class QdrantEmbeddingProvider:
    """
    Qdrant semantic embedding provider conforming to EmbeddingProvider protocol.
    Powered by Qdrant's official FastEmbed engine.
    Defaults to `jinaai/jina-embeddings-v2-base-code` (768-dim, 8192-token context)
    for code-aware and documentation-aware semantic representation.
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        model_name: Optional[str] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.model_name = (
            model_name
            or getattr(self.settings, "qdrant_embedding_model", None)
            or "jinaai/jina-embeddings-v2-base-code"
        )
        self._model = None
        self._dim = 768
        self._init_model()

    def _init_model(self) -> None:
        try:
            from fastembed import TextEmbedding

            try:
                self._model = TextEmbedding(model_name=self.model_name)
            except Exception as inner_e:
                logger.warning(
                    "Could not load embedding model '%s' (%s), falling back to 'sentence-transformers/all-MiniLM-L6-v2'",
                    self.model_name,
                    inner_e,
                )
                self.model_name = "sentence-transformers/all-MiniLM-L6-v2"
                self._model = TextEmbedding(model_name=self.model_name)

            # Verify dimension dynamically
            test_res = list(self._model.embed(["probe"]))
            if test_res:
                self._dim = len(test_res[0])
        except Exception as e:
            raise RuntimeError(
                f"Failed to initialize Qdrant embedding model '{self.model_name}': {e}"
            ) from e

    @property
    def dimension(self) -> int:
        return self._dim

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Compute dense semantic embeddings for a batch of text chunks."""
        if not texts:
            return []
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._sync_embed, texts)

    def _sync_embed(self, texts: List[str]) -> List[List[float]]:
        results: List[List[float]] = []
        for emb in self._model.embed(texts):
            results.append([float(x) for x in emb])
        return results

    async def embed_query(self, text: str) -> List[float]:
        """Compute dense semantic embedding for a user query."""
        if not text:
            return [0.0] * self._dim
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._sync_embed_query, text)

    def _sync_embed_query(self, text: str) -> List[float]:
        for emb in self._model.query_embed([text]):
            return [float(x) for x in emb]
        return [0.0] * self._dim
