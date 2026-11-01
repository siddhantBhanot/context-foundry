import logging
from typing import Any, List, Optional

from rag_service.domain.protocols import EmbeddingProvider
from rag_service.infrastructure.config import Settings, get_settings

logger = logging.getLogger(__name__)


class GeminiEmbeddingProvider:
    """
    Google Gemini semantic embedding provider conforming to EmbeddingProvider protocol.
    Uses the official `google-genai` SDK (`from google import genai`) and `gemini-embedding-001`
    with configurable Matryoshka output dimensionality (defaults to 768-dim to match Qdrant schema).
    Operates entirely via cloud API with zero in-process ONNX model memory overhead.
    """

    MAX_BATCH_SIZE: int = 100

    def __init__(
        self,
        settings: Optional[Settings] = None,
        model_name: Optional[str] = None,
        dimension: int = 768,
    ) -> None:
        self.settings = settings or get_settings()
        raw_model = (
            model_name
            or getattr(self.settings, "gemini_embedding_model_id", None)
            or "gemini-embedding-001"
        ).strip()
        for prefix in ("gemini/", "google/", "models/"):
            if raw_model.startswith(prefix):
                raw_model = raw_model[len(prefix):]
        self.model_name = raw_model
        self.api_key = (self.settings.gemini_api_key or "").strip()
        self._dim = dimension
        self._client: Optional[Any] = None
        self._client_api_key: Optional[str] = None

    def _get_client(self) -> Any:
        current_key = (self.settings.gemini_api_key or self.api_key or "").strip()
        if self._client is None or self._client_api_key != current_key:
            from google import genai

            self._client = genai.Client(api_key=current_key)
            self._client_api_key = current_key
        return self._client

    @property
    def dimension(self) -> int:
        return self._dim

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Compute dense semantic embeddings for a batch of text chunks via Gemini API."""
        if not texts:
            return []

        from google.genai import types

        client = self._get_client()
        config = types.EmbedContentConfig(
            output_dimensionality=self._dim,
            task_type="RETRIEVAL_DOCUMENT",
        )

        results: List[List[float]] = []
        for i in range(0, len(texts), self.MAX_BATCH_SIZE):
            batch = [t if t and t.strip() else " " for t in texts[i : i + self.MAX_BATCH_SIZE]]
            response = await client.aio.models.embed_content(
                model=self.model_name,
                contents=batch,
                config=config,
            )
            if response and response.embeddings:
                for emb in response.embeddings:
                    results.append([float(x) for x in (emb.values or [])])

        return results

    async def embed_query(self, text: str) -> List[float]:
        """Compute dense semantic embedding for a user search query via Gemini API."""
        if not text or not text.strip():
            return [0.0] * self._dim

        from google.genai import types

        client = self._get_client()
        config = types.EmbedContentConfig(
            output_dimensionality=self._dim,
            task_type="RETRIEVAL_QUERY",
        )
        response = await client.aio.models.embed_content(
            model=self.model_name,
            contents=text,
            config=config,
        )
        if response and response.embeddings and response.embeddings[0].values:
            return [float(x) for x in response.embeddings[0].values]
        return [0.0] * self._dim

