import asyncio
from typing import List, Optional

from rag_service.domain.protocols import EmbeddingProvider
from rag_service.infrastructure.config import Settings, get_settings


class QdrantEmbeddingProvider:
    """
    Qdrant semantic embedding provider conforming to EmbeddingProvider protocol.
    Powered by Qdrant's official FastEmbed engine with Qdrant Cloud Inference compatibility.
    Uses sentence-transformers/all-MiniLM-L6-v2 by default for neural semantic search.
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
            or "sentence-transformers/all-MiniLM-L6-v2"
        )
        self._model = None
        self._dim = 384
        self._init_model()

    def _init_model(self) -> None:
        try:
            from fastembed import TextEmbedding

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
