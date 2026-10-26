import asyncio
import json
import logging
import struct
from typing import Any, AsyncIterator, List, Optional
import urllib.parse

import httpx

from rag_service.domain.models import LLMResponse, Message, MessageRole
from rag_service.domain.protocols import LLMProvider
from rag_service.infrastructure.config import Settings, get_settings

logger = logging.getLogger(__name__)


class BedrockLLMProvider:
    """
    AWS Bedrock LLM Provider conforming to LLMProvider protocol.
    Supports direct Bedrock Runtime Converse REST API via Bearer token (AWS_BEARER_TOKEN_BEDROCK)
    and IAM credentials fallback via boto3.
    """

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self.model_id = self.settings.bedrock_llm_model_id
        self.region = self.settings.aws_region or "ap-south-1"
        self.bearer_token = self.settings.aws_bearer_token_bedrock
        self.endpoint_base = f"https://bedrock-runtime.{self.region}.amazonaws.com"

    def _format_converse_messages(
        self, messages: List[Message]
    ) -> List[dict[str, Any]]:
        """Format messages for Bedrock Converse API."""
        converse_messages = []
        for m in messages:
            if m.role == MessageRole.SYSTEM:
                continue
            role = "user" if m.role == MessageRole.USER else "assistant"
            converse_messages.append({
                "role": role,
                "content": [{"text": m.content}],
            })
        return converse_messages

    @staticmethod
    def _normalize_model_id(model_id: str) -> str:
        if model_id.startswith("bedrock/"):
            model_id = model_id[len("bedrock/"):]
        if model_id == "qwen.qwen3-235b-a22b-2507":
            return "qwen.qwen3-235b-a22b-2507-v1:0"
        if model_id in ("anthropic.claude-sonnet-4-6", "claude-sonnet-4-6"):
            return "global.anthropic.claude-sonnet-4-6"
        return model_id

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
        Generate text response through AWS Bedrock Runtime Converse API.
        """
        target_model = model or kwargs.pop("model", None) or self.model_id
        target_model = self._normalize_model_id(target_model)

        # 1. Bearer Token REST execution (Primary mode when AWS_BEARER_TOKEN_BEDROCK is set)
        if self.bearer_token:
            return await self._http_converse_generate(
                messages=messages,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                model_id=target_model,
            )

        # 2. Boto3 execution if IAM credentials are provided
        if self.settings.aws_access_key_id and self.settings.aws_secret_access_key:
            return await self._boto3_converse_generate(
                messages=messages,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                model_id=target_model,
            )

        raise RuntimeError(
            "AWS Bedrock configuration missing. Please provide AWS_BEARER_TOKEN_BEDROCK "
            "or AWS_ACCESS_KEY_ID & AWS_SECRET_ACCESS_KEY."
        )

    async def _http_converse_generate(
        self,
        messages: List[Message],
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int,
        model_id: str,
    ) -> LLMResponse:
        encoded_model_id = urllib.parse.quote(model_id, safe=":")
        url = f"{self.endpoint_base}/model/{encoded_model_id}/converse"
        headers = {
            "Authorization": f"Bearer {self.bearer_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        payload: dict[str, Any] = {
            "messages": self._format_converse_messages(messages),
            "inferenceConfig": {
                "temperature": temperature,
                "maxTokens": max_tokens,
            },
        }
        if system_prompt:
            payload["system"] = [{"text": system_prompt}]

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(url, headers=headers, json=payload)
                if response.status_code != 200:
                    raise RuntimeError(
                        f"Bedrock HTTP {response.status_code}: {response.text}"
                    )
                data = response.json()
                content = ""
                output_msg = data.get("output", {}).get("message", {})
                for block in output_msg.get("content", []):
                    if "text" in block:
                        content += block["text"]

                return LLMResponse(
                    content=content,
                    model=model_id,
                    provider="bedrock",
                    metadata=data.get("usage", {}),
                )
            except Exception as e:
                logger.error(f"Bedrock Converse REST error for model '{model_id}': {e}")
                raise RuntimeError(f"Bedrock invocation failed: {e}") from e

    async def _boto3_converse_generate(
        self,
        messages: List[Message],
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int,
        model_id: str,
    ) -> LLMResponse:
        try:
            import boto3

            client = boto3.client(
                "bedrock-runtime",
                region_name=self.region,
                aws_access_key_id=self.settings.aws_access_key_id,
                aws_secret_access_key=self.settings.aws_secret_access_key,
            )

            kwargs: dict[str, Any] = {
                "modelId": model_id,
                "messages": self._format_converse_messages(messages),
                "inferenceConfig": {
                    "temperature": temperature,
                    "maxTokens": max_tokens,
                },
            }
            if system_prompt:
                kwargs["system"] = [{"text": system_prompt}]

            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None,
                lambda: client.converse(**kwargs),
            )

            content = ""
            output_msg = response.get("output", {}).get("message", {})
            for block in output_msg.get("content", []):
                if "text" in block:
                    content += block["text"]

            return LLMResponse(
                content=content,
                model=model_id,
                provider="bedrock",
                metadata=response.get("usage", {}),
            )
        except Exception as e:
            logger.error(f"Bedrock Boto3 Converse error for model '{model_id}': {e}")
            raise RuntimeError(f"Bedrock invocation failed: {e}") from e

    async def stream(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Stream chunks of response text."""
        target_model = model or kwargs.pop("model", None) or self.model_id
        target_model = self._normalize_model_id(target_model)

        # Streaming via HTTP converse-stream
        if self.bearer_token:
            encoded_model_id = urllib.parse.quote(target_model, safe=":")
            url = f"{self.endpoint_base}/model/{encoded_model_id}/converse-stream"
            headers = {
                "Authorization": f"Bearer {self.bearer_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            payload: dict[str, Any] = {
                "messages": self._format_converse_messages(messages),
                "inferenceConfig": {
                    "temperature": temperature,
                    "maxTokens": max_tokens,
                },
            }
            if system_prompt:
                payload["system"] = [{"text": system_prompt}]

            streamed_any = False
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    async with client.stream("POST", url, headers=headers, json=payload) as resp:
                        if resp.status_code == 200:
                            buf = bytearray()
                            async for chunk in resp.aiter_bytes():
                                buf.extend(chunk)
                                # Decode binary AWS EventStream frames
                                while len(buf) >= 12:
                                    total_len, headers_len = struct.unpack(">II", buf[:8])
                                    if len(buf) < total_len:
                                        break
                                    frame = buf[:total_len]
                                    buf = buf[total_len:]

                                    payload_bytes = frame[12 + headers_len : total_len - 4]
                                    try:
                                        event_data = json.loads(payload_bytes.decode("utf-8"))
                                        delta_text = (
                                            event_data.get("contentBlockDelta", {})
                                            .get("delta", {})
                                            .get("text")
                                            or event_data.get("delta", {}).get("text")
                                        )
                                        if delta_text:
                                            streamed_any = True
                                            yield delta_text
                                    except Exception:
                                        pass
            except Exception as e:
                logger.warning(f"Bedrock converse-stream failed, falling back to complete generation: {e}")

            if streamed_any:
                return

        # Fallback to full generation and yield content
        res = await self.generate(
            messages=messages,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            model=target_model,
            **kwargs,
        )
        yield res.content
