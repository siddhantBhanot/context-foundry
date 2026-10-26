from typing import Any, AsyncIterator, Dict, List, Optional, Protocol, runtime_checkable

from .models import Chunk, LLMResponse, Message


@runtime_checkable
class LLMProvider(Protocol):
    """
    Protocol defining the interface for language model providers.
    Ensures application logic is completely decoupled from concrete LLM APIs
    (Bedrock, Gemini, Groq, OpenAI).
    """

    async def generate(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate a complete text response given messages, prompt, and optional model override."""
        ...

    async def stream(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Stream chunks of response text asynchronously."""
        ...


@runtime_checkable
class EmbeddingProvider(Protocol):
    """
    Protocol defining the interface for dense text embedding providers.
    Decoupled from Bedrock Titan, OpenAI embeddings, or local models.
    """

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Compute dense vector embeddings for a list of text strings."""
        ...

    async def embed_query(self, text: str) -> List[float]:
        """Compute dense vector embedding for a single query string."""
        ...

    @property
    def dimension(self) -> int:
        """Return the vector dimension produced by this model."""
        ...


@runtime_checkable
class VectorStore(Protocol):
    """
    Protocol defining vector database persistence and similarity search.
    Decoupled from Qdrant, Milvus, pgvector, or in-memory stores.
    """

    async def upsert(self, chunks: List[Chunk]) -> int:
        """
        Store chunks along with their vector embeddings and service metadata.
        Returns the number of chunks successfully stored.
        """
        ...

    async def search(
        self,
        query_vector: List[float],
        limit: int = 5,
        service_filter: Optional[str] = None,
        filter_dict: Optional[Dict[str, Any]] = None,
        score_threshold: Optional[float] = None,
    ) -> List[Chunk]:
        """
        Perform nearest neighbor semantic search with service-level or arbitrary metadata filtering.
        """
        ...

    async def delete(self, chunk_ids: List[str]) -> bool:
        """Delete specific chunks by identifier."""
        ...
