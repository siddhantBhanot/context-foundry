import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import Field

try:
    from dotenv import load_dotenv
    # Search for .env in current working dir, rag_service package dir, and parent dirs
    _possible_env_paths = [
        Path.cwd() / ".env",
        Path.cwd() / "rag_service" / ".env",
        Path(__file__).resolve().parent.parent / ".env",
        Path(__file__).resolve().parent.parent.parent / ".env",
    ]
    for _p in _possible_env_paths:
        if _p.is_file():
            load_dotenv(_p, override=False)
except ImportError:
    pass

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
    _HAS_SETTINGS = True
except ImportError:
    from pydantic import BaseModel as BaseSettings  # type: ignore
    SettingsConfigDict = dict  # type: ignore
    _HAS_SETTINGS = False


class Settings(BaseSettings):
    """
    RAG Service centralized configuration.
    All credentials and endpoint URLs are externalized through environment variables.
    """
    if _HAS_SETTINGS:
        model_config = SettingsConfigDict(
            env_file=[".env", "rag_service/.env"],
            env_file_encoding="utf-8",
            extra="ignore",
        )

    # Provider Selection
    llm_provider: str = Field(
        default_factory=lambda: os.getenv(
            "LLM_PROVIDER",
            "openai" if (os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY")) else "bedrock",
        )
    )
    embedding_provider: str = Field(
        default_factory=lambda: os.getenv(
            "EMBEDDING_PROVIDER",
            "bedrock",
        )
    )
    vector_store_type: str = Field(default_factory=lambda: os.getenv("VECTOR_STORE", "qdrant"))

    # AWS Bedrock Settings
    aws_region: str = Field(default_factory=lambda: os.getenv("AWS_REGION", "ap-south-1"))
    aws_access_key_id: Optional[str] = Field(default_factory=lambda: os.getenv("AWS_ACCESS_KEY_ID"))
    aws_secret_access_key: Optional[str] = Field(default_factory=lambda: os.getenv("AWS_SECRET_ACCESS_KEY"))
    aws_bearer_token_bedrock: Optional[str] = Field(
        default_factory=lambda: os.getenv("AWS_BEARER_TOKEN_BEDROCK")
    )
    bedrock_llm_model_id: str = Field(
        default_factory=lambda: os.getenv("BEDROCK_LLM_MODEL_ID", "qwen.qwen3-235b-a22b-2507")
    )
    bedrock_models: str = Field(
        default_factory=lambda: os.getenv(
            "BEDROCK_MODELS",
            "qwen.qwen3-235b-a22b-2507:Qwen 3 235B A22B:Advanced open-weight reasoning model on AWS Bedrock,"
            "anthropic.claude-3-5-sonnet-20240620-v1:0:Claude 3.5 Sonnet:High-intelligence AWS Bedrock Claude model,"
            "anthropic.claude-3-haiku-20240307-v1:0:Claude 3 Haiku:Fast and lightweight AWS Bedrock model",
        )
    )
    bedrock_embedding_model_id: str = Field(
        default_factory=lambda: os.getenv("BEDROCK_EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0")
    )

    def get_configured_bedrock_models(self) -> List[Dict[str, Any]]:
        """Parse configured Bedrock models from JSON or comma-separated id:name:description string."""
        import json
        raw = (self.bedrock_models or "").strip()
        if not raw:
            return []

        # Try JSON parsing
        if raw.startswith("[") and raw.endswith("]"):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    return [
                        {
                            "id": item.get("id"),
                            "name": item.get("name") or item.get("id"),
                            "provider": "bedrock",
                            "description": item.get("description") or "AWS Bedrock model",
                        }
                        for item in parsed
                        if isinstance(item, dict) and item.get("id")
                    ]
            except Exception:
                pass

        # Parse comma-separated "id:name:desc"
        models: List[Dict[str, Any]] = []
        for entry in raw.split(","):
            parts = entry.strip().split(":")
            if not parts or not parts[0]:
                continue
            m_id = parts[0].strip()
            # If colon is part of version like anthropic.claude-3-5-sonnet:0, check segments
            if len(parts) == 1:
                models.append({
                    "id": m_id,
                    "name": m_id,
                    "provider": "bedrock",
                    "description": "AWS Bedrock model",
                })
            elif len(parts) == 2:
                models.append({
                    "id": m_id,
                    "name": parts[1].strip(),
                    "provider": "bedrock",
                    "description": "AWS Bedrock model",
                })
            else:
                # e.g. "qwen.qwen3-235b-a22b-2507:Qwen 3 235B A22B:Advanced model"
                # or if model_id itself contains colons like "anthropic.claude-v1:0:Claude:Desc"
                if parts[1].isdigit() and len(parts) >= 4:
                    full_id = f"{parts[0]}:{parts[1]}"
                    name = parts[2].strip()
                    desc = ":".join(parts[3:]).strip()
                else:
                    full_id = parts[0].strip()
                    name = parts[1].strip()
                    desc = ":".join(parts[2:]).strip()
                models.append({
                    "id": full_id,
                    "name": name,
                    "provider": "bedrock",
                    "description": desc,
                })
        return models

    # OpenAI / Groq / OpenAI-Compatible Settings
    groq_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("GROQ_API_KEY"))
    openai_api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY")
    )
    openai_base_url: str = Field(
        default_factory=lambda: os.getenv(
            "OPENAI_BASE_URL",
            "https://api.groq.com/openai/v1" if os.getenv("GROQ_API_KEY") else "https://api.openai.com/v1",
        )
    )
    openai_model_id: str = Field(
        default_factory=lambda: os.getenv(
            "OPENAI_MODEL_ID",
            "openai/gpt-oss-120b" if os.getenv("GROQ_API_KEY") else "gpt-4o",
        )
    )

    # Google Gemini Settings
    gemini_api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    )
    gemini_model_id: str = Field(
        default_factory=lambda: os.getenv("GEMINI_MODEL_ID", "gemini-3.7-flash")
    )
    gemini_embedding_model_id: str = Field(
        default_factory=lambda: os.getenv("GEMINI_EMBEDDING_MODEL_ID", "gemini-embedding-001")
    )
    gemini_first_token_timeout_seconds: float = Field(
        default_factory=lambda: float(os.getenv("GEMINI_FIRST_TOKEN_TIMEOUT_SECONDS", "25"))
    )
    gemini_models: str = Field(
        default_factory=lambda: os.getenv(
            "GEMINI_MODELS",
            "gemini-3.7-flash:Gemini 3.7 Flash:Fast 1M-context reasoning and coding model,"
            "gemini-3.6-flash:Gemini 3.6 Flash:Balanced 1M-context architectural and coding model,"
            "gemini-3.5-flash:Gemini 3.5 Flash:High-throughput 1M-context reasoning and code model,"
            "gemini-3.5-flash-lite:Gemini 3.5 Flash Lite:Ultra-fast low-latency 1M-context model,"
            "gemma-4-26b-a4b-it:Gemma 4 26B MoE IT:Open-weight Gemma 4 26B (4B active) instruction model",
        )
    )

    def has_valid_gemini_key(self) -> bool:
        raw = (self.gemini_api_key or "").strip()
        return bool(
            raw
            and not raw.startswith("your_")
            and not raw.startswith("AIza_your_")
            and raw != "changeme"
        )

    def get_configured_gemini_models(self) -> List[Dict[str, Any]]:
        """Parse configured Gemini models from comma-separated id:name:description string."""
        raw = (self.gemini_models or "").strip()
        if not raw:
            return []
        models: List[Dict[str, Any]] = []
        for entry in raw.split(","):
            parts = entry.strip().split(":")
            if not parts or not parts[0]:
                continue
            m_id = parts[0].strip()
            name = parts[1].strip() if len(parts) >= 2 else m_id
            desc = ":".join(parts[2:]).strip() if len(parts) >= 3 else "Google Gemini model"
            models.append({
                "id": m_id,
                "name": name,
                "provider": "gemini",
                "description": desc,
            })
        return models

    # Qdrant Cloud Settings
    qdrant_url: Optional[str] = Field(default_factory=lambda: os.getenv("QDRANT_URL"))
    qdrant_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("QDRANT_API_KEY"))
    qdrant_collection_name: str = Field(
        default_factory=lambda: os.getenv("QDRANT_COLLECTION_NAME", "engineering_knowledge_base")
    )
    qdrant_kt_collection_name: str = Field(
        default_factory=lambda: os.getenv("QDRANT_KT_COLLECTION_NAME", "knowledge_cafe_collection")
    )
    qdrant_embedding_model: str = Field(
        default_factory=lambda: os.getenv(
            "QDRANT_EMBEDDING_MODEL", "jinaai/jina-embeddings-v2-base-code"
        )
    )
    # Toggle for heavy local ONNX Jina-Code-v2 embeddings (~900MB RAM).
    # Defaults to False so cloud deployments use lightweight Gemini API embeddings.
    use_local_jina_embeddings: bool = Field(
        default_factory=lambda: os.getenv("USE_LOCAL_JINA_EMBEDDINGS", "false").strip().lower()
        in {"1", "true", "yes", "on"}
    )

    # Domain Defaults
    default_microservice: str = Field(
        default_factory=lambda: os.getenv("DEFAULT_MICROSERVICE", "default-service")
    )
    embedding_dimension: int = Field(
        default_factory=lambda: int(
            os.getenv(
                "EMBEDDING_DIMENSION",
                "1024" if (os.getenv("EMBEDDING_PROVIDER") == "bedrock" and (os.getenv("AWS_BEARER_TOKEN_BEDROCK") or os.getenv("AWS_ACCESS_KEY_ID"))) else "768",
            )
        )
    )
    max_history_messages: int = Field(
        default_factory=lambda: int(os.getenv("MAX_HISTORY_MESSAGES", "6"))
    )


_settings: Optional[Settings] = None
_last_env_mtime: float = 0.0


def _current_env_mtime() -> float:
    mtime = 0.0
    for p in (
        Path.cwd() / ".env",
        Path(__file__).resolve().parent.parent.parent / ".env",
    ):
        try:
            if p.is_file():
                mtime = max(mtime, p.stat().st_mtime)
        except Exception:
            pass
    return mtime


def get_settings() -> Settings:
    global _settings, _last_env_mtime
    curr_mtime = _current_env_mtime()
    if _settings is None or (curr_mtime > 0 and curr_mtime != _last_env_mtime):
        is_reload = _last_env_mtime > 0 and curr_mtime != _last_env_mtime
        try:
            from dotenv import load_dotenv
            for p in (
                Path.cwd() / ".env",
                Path(__file__).resolve().parent.parent.parent / ".env",
            ):
                if p.is_file():
                    load_dotenv(p, override=is_reload)
        except ImportError:
            pass
        _last_env_mtime = curr_mtime
        _settings = Settings()
    return _settings
