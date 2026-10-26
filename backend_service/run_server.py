#!/usr/bin/env python3
"""
Convenience launcher for the backend_service FastAPI application.
Run locally with:
    python backend_service/run_server.py
"""

import os
from pathlib import Path
import sys

# Ensure context-foundry root is in sys.path
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from backend_service.app.infrastructure.configuration.settings import get_settings

if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    print("=" * 70)
    print("🚀 FC Central — Engineering Intelligence Backend Service")
    print("=" * 70)
    print(f"  • Host          : {settings.host}")
    print(f"  • Port          : {settings.port}")
    print(f"  • Environment   : {settings.environment}")
    print(f"  • Database Path : {settings.database_path}")
    print(f"  • RAG Mode      : {settings.rag_client_mode}")
    print("=" * 70)
    print(f"  • Swagger Docs  : http://{settings.host if settings.host != '0.0.0.0' else 'localhost'}:{settings.port}/docs")
    print(f"  • Health Probe  : http://{settings.host if settings.host != '0.0.0.0' else 'localhost'}:{settings.port}/api/v1/health")
    print("=" * 70 + "\n")

    uvicorn.run(
        "backend_service.app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )
