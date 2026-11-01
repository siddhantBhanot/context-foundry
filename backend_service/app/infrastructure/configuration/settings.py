import os
from pathlib import Path
from typing import Any, List, Optional, Union
from pydantic import Field, field_validator

try:
    from dotenv import load_dotenv
    _possible_env_paths = [
        Path.cwd() / ".env",
        Path.cwd() / "backend_service" / ".env",
        Path.cwd() / "rag_service" / ".env",
        Path(__file__).resolve().parents[4] / ".env",
        Path(__file__).resolve().parents[4] / "backend_service" / ".env",
        Path(__file__).resolve().parents[4] / "rag_service" / ".env",
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
    Centralized configuration for backend_service.
    All parameters are externalized through environment variables.
    """
    if _HAS_SETTINGS:
        model_config = SettingsConfigDict(
            env_file=[".env", "backend_service/.env", "rag_service/.env"],
            env_file_encoding="utf-8",
            extra="ignore",
        )

    # Server configuration
    host: str = Field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))
    port: int = Field(default_factory=lambda: int(os.getenv("PORT", "8000")))
    environment: str = Field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    # When false: the signup endpoint is disabled, the hardcoded demo account cannot be
    # auto-provisioned or used to log in, and the UI hides both. Set to false in cloud deployments.
    allow_user_registration: bool = Field(
        default_factory=lambda: os.getenv("ALLOW_USER_REGISTRATION", "true").strip().lower()
        in {"1", "true", "yes", "on"}
    )
    cors_origins: Union[List[str], str] = Field(
        default=["http://localhost:5173", "http://localhost:3000"]
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            import json
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return [x for x in parsed if x != "*"]
            except Exception:
                pass
            return [orig.strip() for orig in v.split(",") if orig.strip() and orig.strip() != "*"]
        elif isinstance(v, list):
            return [x for x in v if x != "*"]
        return ["http://localhost:5173", "http://localhost:3000"]

    # Persistence configuration
    database_path: str = Field(
        default_factory=lambda: os.getenv(
            "DATABASE_PATH",
            str(Path(__file__).resolve().parents[3] / "data" / "contextfoundry.db"),
        )
    )

    # Security / JWT configuration
    jwt_secret_key: str = Field(
        default_factory=lambda: os.getenv("JWT_SECRET_KEY", "contextfoundry-dev-secret-key-32chars-minimum-required")
    )
    jwt_access_token_expire_minutes: int = Field(
        default_factory=lambda: int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    )

    # Bootstrap / Admin Account Auto-Seeding (survives ephemeral container restarts)
    admin_email: Optional[str] = Field(
        default_factory=lambda: os.getenv("ADMIN_EMAIL") or None
    )
    admin_password: Optional[str] = Field(
        default_factory=lambda: os.getenv("ADMIN_PASSWORD") or None
    )
    admin_password_hash: Optional[str] = Field(
        default_factory=lambda: os.getenv("ADMIN_PASSWORD_HASH") or None
    )
    admin_name: str = Field(
        default_factory=lambda: os.getenv("ADMIN_NAME", "Siddhant Bhanot")
    )
    admin_role: str = Field(
        default_factory=lambda: os.getenv("ADMIN_ROLE", "developer")
    )

    # RAG Client adapter mode ("direct" bridges to rag_service, "mock" is standalone offline)
    rag_client_mode: str = Field(default_factory=lambda: os.getenv("RAG_CLIENT_MODE", "direct"))
    default_service: str = Field(default_factory=lambda: os.getenv("DEFAULT_SERVICE", "income-assessment-service"))
    default_top_k: int = Field(default_factory=lambda: int(os.getenv("DEFAULT_TOP_K", "5")))



_settings: Optional[Settings] = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
