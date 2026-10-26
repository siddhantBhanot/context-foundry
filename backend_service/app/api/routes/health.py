from typing import Any, Dict
from fastapi import APIRouter, Depends
from backend_service.app.infrastructure.configuration.settings import Settings, get_settings
from backend_service.app.infrastructure.persistence.database import Database
from backend_service.app.api.dependencies import get_db_instance

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", response_model=Dict[str, Any])
async def check_health(
    settings: Settings = Depends(get_settings),
    db: Database = Depends(get_db_instance),
) -> Dict[str, Any]:
    """
    Health check verifying service status, database responsiveness, and configuration.
    """
    db_status = "healthy"
    try:
        async with db.connection() as conn:
            cursor = await conn.execute("SELECT 1;")
            await cursor.fetchone()
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "service": "backend_service",
        "environment": settings.environment,
        "database": db_status,
        "rag_mode": settings.rag_client_mode,
        "default_microservice": settings.default_service,
    }
