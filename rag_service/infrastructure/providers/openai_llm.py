import asyncio
from typing import Any, AsyncIterator, List, Optional

from rag_service.domain.models import LLMResponse, Message, MessageRole
from rag_service.domain.protocols import LLMProvider
from rag_service.infrastructure.config import Settings, get_settings


class OpenAiClientProvider:
    """
    OpenAI-compatible LLM Provider conforming to LLMProvider protocol.
    Supports OpenAI, Groq, vLLM, Ollama, and any OpenAI API-compatible endpoint.
    """

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self.model_id = self.settings.openai_model_id
        self.base_url = self.settings.openai_base_url
        self.api_key = self.settings.openai_api_key or "no-key-provided"

    async def generate(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Generate response using OpenAI-compatible chat completions API.
        """
        target_model = model or kwargs.pop("model", None) or self.model_id
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

            formatted_messages = []
            if system_prompt:
                formatted_messages.append({"role": "system", "content": system_prompt})

            for m in messages:
                formatted_messages.append({"role": m.role.value, "content": m.content})

            response = await client.chat.completions.create(
                model=target_model,
                messages=formatted_messages,  # type: ignore
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )

            choice = response.choices[0]
            provider_name = "groq" if "groq.com" in (self.base_url or "") else "openai-compatible"
            return LLMResponse(
                content=choice.message.content or "",
                model=target_model,
                provider=provider_name,
                metadata={"finish_reason": choice.finish_reason},
                total_tokens=response.usage.total_tokens if response.usage else None,
            )
        except Exception as e:
            raise RuntimeError(f"OpenAI-compatible generation error: {e}") from e

    async def stream(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Stream chunks using AsyncOpenAI completions."""
        target_model = model or kwargs.pop("model", None) or self.model_id
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

            formatted_messages = []
            if system_prompt:
                formatted_messages.append({"role": "system", "content": system_prompt})

            for m in messages:
                formatted_messages.append({"role": m.role.value, "content": m.content})

            stream_res = await client.chat.completions.create(
                model=target_model,
                messages=formatted_messages,  # type: ignore
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                **kwargs,
            )

            async for chunk in stream_res:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    yield delta
        except Exception as e:
            raise RuntimeError(f"OpenAI-compatible streaming error: {e}") from e
