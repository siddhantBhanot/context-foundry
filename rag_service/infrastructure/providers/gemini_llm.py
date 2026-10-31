import logging
from typing import Any, AsyncIterator, List, Optional

from rag_service.domain.models import LLMResponse, Message, MessageRole
from rag_service.infrastructure.config import Settings, get_settings

logger = logging.getLogger(__name__)


class GeminiLLMProvider:
    """
    Google Gemini LLM Provider conforming to LLMProvider protocol.
    Uses the official current `google-genai` SDK (`from google import genai`).
    """

    provider_name: str = "gemini"

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self.model_id = self.settings.gemini_model_id
        self.api_key = self.settings.gemini_api_key or ""

    def _normalize_model_id(self, model: Optional[str]) -> str:
        target = (model or self.model_id or "gemini-3.7-flash").strip()
        for prefix in ("gemini/", "google/", "models/"):
            if target.startswith(prefix):
                target = target[len(prefix):]
        return target

    def _candidate_models(self, primary_model: str) -> List[str]:
        candidates = [primary_model]
        for fallback in ("gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.6-flash", "gemma-4-26b-a4b-it"):
            if fallback not in candidates:
                candidates.append(fallback)
        return candidates

    def _build_contents_and_config(
        self,
        messages: List[Message],
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int,
    ):
        from google.genai import types

        contents: List[types.Content] = []
        system_parts: List[str] = []
        if system_prompt:
            system_parts.append(system_prompt)

        for m in messages:
            if m.role == MessageRole.SYSTEM:
                if m.content:
                    system_parts.append(m.content)
                continue
            role_str = "model" if m.role == MessageRole.ASSISTANT else "user"
            contents.append(
                types.Content(
                    role=role_str,
                    parts=[types.Part.from_text(text=m.content)],
                )
            )

        if not contents:
            contents.append(
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text="Hello")],
                )
            )

        combined_system = "\n\n".join(system_parts) if system_parts else None
        config = types.GenerateContentConfig(
            system_instruction=combined_system,
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
        return contents, config

    async def generate(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate response using Google GenAI async client (`client.aio.models.generate_content`)."""
        target_model = self._normalize_model_id(model or kwargs.pop("model", None))
        from google import genai
        from google.genai import types

        client = genai.Client(
            api_key=self.api_key,
            http_options=types.HttpOptions(
                retry_options=types.HttpRetryOptions(attempts=1)
            ),
        )
        contents, config = self._build_contents_and_config(
            messages=messages,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        primary_err: Optional[Exception] = None
        for cand_model in self._candidate_models(target_model):
            try:
                response = await client.aio.models.generate_content(
                    model=cand_model,
                    contents=contents,
                    config=config,
                )

                text = response.text or ""
                usage = getattr(response, "usage_metadata", None)
                total_tokens = getattr(usage, "total_token_count", None) if usage else None

                return LLMResponse(
                    content=text,
                    model=cand_model,
                    provider="gemini",
                    metadata={},
                    total_tokens=total_tokens,
                )
            except Exception as e:
                if primary_err is None:
                    primary_err = e
                logger.warning("Gemini model '%s' failed during generate (%s), trying next fallback...", cand_model, e)

        raise RuntimeError(f"Gemini generation error ({target_model}): {primary_err}") from primary_err

    async def stream(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Stream chunks asynchronously using `client.aio.models.generate_content_stream`."""
        target_model = self._normalize_model_id(model or kwargs.pop("model", None))
        from google import genai
        from google.genai import types

        client = genai.Client(
            api_key=self.api_key,
            http_options=types.HttpOptions(
                retry_options=types.HttpRetryOptions(attempts=1)
            ),
        )
        contents, config = self._build_contents_and_config(
            messages=messages,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        primary_err: Optional[Exception] = None
        for cand_model in self._candidate_models(target_model):
            try:
                stream_res = await client.aio.models.generate_content_stream(
                    model=cand_model,
                    contents=contents,
                    config=config,
                )
                yielded_any = False
                async for chunk in stream_res:
                    if chunk.text:
                        yielded_any = True
                        yield chunk.text
                if yielded_any:
                    return
            except Exception as e:
                if primary_err is None:
                    primary_err = e
                logger.warning("Gemini model '%s' failed during stream (%s), trying next fallback...", cand_model, e)

        raise RuntimeError(f"Gemini streaming error ({target_model}): {primary_err}") from primary_err

