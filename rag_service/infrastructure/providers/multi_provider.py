import logging
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

from rag_service.domain.models import LLMResponse, Message
from rag_service.domain.protocols import LLMProvider

logger = logging.getLogger(__name__)


class MultiProviderLLMAdapter:
    """
    Multi-provider router conforming to LLMProvider protocol.
    Dynamically routes LLM generation and streaming requests to the correct
    provider (AWS Bedrock, Groq, OpenAI) based on the requested model ID.
    """

    def __init__(
        self,
        default_provider: LLMProvider,
        providers: Optional[Dict[str, LLMProvider]] = None,
        model_to_provider: Optional[Dict[str, str]] = None,
    ) -> None:
        self.default_provider = default_provider
        self.providers: Dict[str, LLMProvider] = providers or {}
        self.model_to_provider: Dict[str, str] = model_to_provider or {}

    def register_provider(self, name: str, provider: LLMProvider) -> None:
        self.providers[name] = provider

    def register_model(self, model_id: str, provider_name: str) -> None:
        self.model_to_provider[model_id] = provider_name

    def _resolve_provider(self, model: Optional[str]) -> LLMProvider:
        """Resolve appropriate underlying LLMProvider for a given model ID."""
        if not model:
            return self.default_provider

        # 1. Exact match in registered model map
        if model in self.model_to_provider:
            p_name = self.model_to_provider[model]
            if p_name in self.providers:
                return self.providers[p_name]

        # 2. Explicit prefix match (e.g. bedrock/model-id)
        if model.startswith("bedrock/") and "bedrock" in self.providers:
            return self.providers["bedrock"]
        if (model.startswith("groq/") or model.startswith("openai/")) and "groq" in self.providers:
            return self.providers["groq"]

        # 3. Known model family heuristics
        lower_model = model.lower()
        if any(prefix in lower_model for prefix in ["anthropic.claude", "amazon.nova", "amazon.titan", "qwen3-235b", "235b"]):
            if "bedrock" in self.providers:
                return self.providers["bedrock"]

        if any(prefix in lower_model for prefix in ["gpt-oss", "qwen3.8", "qwen3.6", "compound", "llama-3"]):
            if "groq" in self.providers:
                return self.providers["groq"]

        # Fallback to default configured provider
        return self.default_provider

    def _get_candidate_providers(self, model: Optional[str]) -> List[Tuple[LLMProvider, Optional[str]]]:
        """
        Build an ordered list of (provider, model_id) candidates for failover.
        The primary resolved provider is first; remaining providers are fallbacks.
        """
        primary = self._resolve_provider(model)
        candidates: List[Tuple[LLMProvider, Optional[str]]] = [(primary, model)]
        
        # Add remaining registered providers
        for p_name, provider in self.providers.items():
            if provider is not primary and all(provider is not c[0] for c in candidates):
                candidates.append((provider, None))
                
        if all(self.default_provider is not c[0] for c in candidates):
            candidates.append((self.default_provider, None))
            
        return candidates

    async def generate(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        candidates = self._get_candidate_providers(model)
        last_err: Optional[Exception] = None

        for idx, (provider, candidate_model) in enumerate(candidates):
            try:
                return await provider.generate(
                    messages=messages,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    model=candidate_model,
                    **kwargs,
                )
            except Exception as e:
                p_name = provider.__class__.__name__
                logger.warning(
                    f"LLM provider {p_name} (candidate #{idx+1}) failed during generate: {e}. "
                    f"Attempting fallback to next available provider..."
                )
                last_err = e

        if last_err:
            raise last_err
        raise RuntimeError("No LLM provider available.")

    async def stream(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        candidates = self._get_candidate_providers(model)
        last_err: Optional[Exception] = None

        for idx, (provider, candidate_model) in enumerate(candidates):
            try:
                iterator = provider.stream(
                    messages=messages,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    model=candidate_model,
                    **kwargs,
                )
                first_chunk = None
                async for chunk in iterator:
                    first_chunk = chunk
                    yield chunk
                    break

                if first_chunk is not None:
                    async for chunk in iterator:
                        yield chunk
                    return
            except Exception as e:
                p_name = provider.__class__.__name__
                logger.warning(
                    f"LLM provider {p_name} (candidate #{idx+1}) failed during stream: {e}. "
                    f"Attempting fallback to next available provider..."
                )
                last_err = e

        if last_err:
            raise last_err
        raise RuntimeError("No LLM provider available.")
