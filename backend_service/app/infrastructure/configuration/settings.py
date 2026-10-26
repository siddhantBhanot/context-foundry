import os
from pathlib import Path
from typing import List, Optional
from pydantic import Field

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
    cors_origins: List[str] = Field(
        default_factory=lambda: [
            orig.strip()
            for orig in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000,*").split(",")
            if orig.strip()
        ]
    )

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
