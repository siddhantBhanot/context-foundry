import asyncio
import json
import logging
from typing import List, Optional
import urllib.parse

import httpx

from rag_service.domain.protocols import EmbeddingProvider
from rag_service.infrastructure.config import Settings, get_settings

logger = logging.getLogger(__name__)


class BedrockEmbeddingProvider:
    """
    AWS Bedrock dense embedding provider conforming to EmbeddingProvider protocol.
    Supports direct Bedrock Runtime REST API via Bearer token (AWS_BEARER_TOKEN_BEDROCK),
    LlamaIndex BedrockEmbedding, and direct boto3 bedrock-runtime.
    """

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self.model_id = self.settings.bedrock_embedding_model_id
        self.region = self.settings.aws_region or "ap-south-1"
        self._dim = self.settings.embedding_dimension
        if "titan-embed-text-v2" in self.model_id and self._dim not in (256, 512, 1024):
            self._dim = 1024
        self.bearer_token = self.settings.aws_bearer_token_bedrock
        self.endpoint_base = f"https://bedrock-runtime.{self.region}.amazonaws.com"
        self._embed_model = None
        if not self.bearer_token:
            self._init_client()

    def _init_client(self) -> None:
        try:
            from llama_index.embeddings.bedrock import BedrockEmbedding

            kwargs = {
                "model_name": self.model_id,
                "region_name": self.region,
            }
            if self.settings.aws_access_key_id and self.settings.aws_secret_access_key:
                kwargs["aws_access_key_id"] = self.settings.aws_access_key_id
                kwargs["aws_secret_access_key"] = self.settings.aws_secret_access_key

            self._embed_model = BedrockEmbedding(**kwargs)
        except (ImportError, Exception):
            self._embed_model = None

    @property
    def dimension(self) -> int:
        return self._dim

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Compute dense vector embeddings for a list of strings."""
        if not texts:
            return []

        if self.bearer_token:
            return await self._http_embed_batch(texts)

        if self._embed_model is not None:
            try:
                return await self._embed_model.aget_text_embedding_batch(texts)
            except Exception as e:
                raise RuntimeError(f"Bedrock embedding error: {e}") from e

        # Direct boto3 fallback
        return await self._boto3_embed_batch(texts)

    async def embed_query(self, text: str) -> List[float]:
        """Compute embedding for a single query."""
        res = await self.embed([text])
        return res[0] if res else []

    async def _http_embed_batch(self, texts: List[str]) -> List[List[float]]:
        encoded_model_id = urllib.parse.quote(self.model_id, safe=":")
        url = f"{self.endpoint_base}/model/{encoded_model_id}/invoke"
        headers = {
            "Authorization": f"Bearer {self.bearer_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        semaphore = asyncio.Semaphore(10)

        async def _embed_one(client: httpx.AsyncClient, text: str) -> List[float]:
            async with semaphore:
                payload = {
                    "inputText": text,
                    "dimensions": self._dim,
                    "normalize": True,
                }
                res = await client.post(url, headers=headers, json=payload)
                if res.status_code != 200:
                    raise RuntimeError(f"Bedrock embedding HTTP {res.status_code}: {res.text}")
                data = res.json()
                return data.get("embedding", [])

        async with httpx.AsyncClient(timeout=30.0) as client:
            tasks = [_embed_one(client, t) for t in texts]
            return await asyncio.gather(*tasks)

    async def _boto3_embed_batch(self, texts: List[str]) -> List[List[float]]:
        try:
            import boto3

            client = boto3.client(
                "bedrock-runtime",
                region_name=self.region,
                aws_access_key_id=self.settings.aws_access_key_id,
                aws_secret_access_key=self.settings.aws_secret_access_key,
            )

            loop = asyncio.get_running_loop()
            results: List[List[float]] = []

            for text in texts:
                # Titan text embedding v2 payload format
                payload = json.dumps({"inputText": text, "dimensions": self._dim})
                response = await loop.run_in_executor(
                    None,
                    lambda: client.invoke_model(
                        modelId=self.model_id,
                        body=payload,
                        contentType="application/json",
                        accept="application/json",
                    ),
                )
                body = json.loads(response["body"].read())
                embedding = body.get("embedding", [])
                results.append(embedding)

            return results
        except Exception as e:
            raise RuntimeError(f"Bedrock batch embedding failed: {e}") from e
