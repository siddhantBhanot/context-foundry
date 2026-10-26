from fastapi import APIRouter, Depends

from backend_service.app.api.dependencies import get_query_service
from backend_service.app.api.schemas.models import ModelListResponse
from backend_service.app.application.services.query_service import QueryService

router = APIRouter(tags=["Models"])


@router.get("/models", response_model=ModelListResponse)
async def list_models(
    query_service: QueryService = Depends(get_query_service),
) -> ModelListResponse:
    """
    List configured LLM models available for runtime inference.
    Returns only models supported by active server-side credentials and configuration.
    """
    result = await query_service.list_models()
    return ModelListResponse(**result)
