from fastapi import APIRouter, Depends, Query

from backend_service.app.api.dependencies import get_current_user, get_rag_client
from backend_service.app.api.schemas.documents import DocumentDetailResponse
from backend_service.app.domain.exceptions.base import (
    EntityNotFoundException,
    ForbiddenException,
    ValidationException,
)
from backend_service.app.domain.interfaces.rag_client import RAGClientProtocol
from backend_service.app.domain.models.user import User


router = APIRouter(prefix="/documents", tags=["Documents"])


@router.get("", response_model=DocumentDetailResponse)
async def get_document(
    service: str = Query(..., min_length=1, description="Target microservice identifier"),
    file: str = Query(..., min_length=1, description="Documentation file name or relative path"),
    current_user: User = Depends(get_current_user),
    rag_client: RAGClientProtocol = Depends(get_rag_client),
) -> DocumentDetailResponse:
    """
    Safely retrieve the full content of a source documentation file (.md, .markdown, .txt, .rst).
    Protected endpoint: requires authenticated engineer access.
    Enforces strict path traversal verification and extension whitelist.
    """
    try:
        doc = await rag_client.get_document(service=service, file_path=file)
        return DocumentDetailResponse(
            file=doc.file,
            service=doc.service,
            content=doc.content,
            content_type=doc.content_type,
            total_lines=doc.total_lines,
            size_bytes=doc.size_bytes,
        )
    except PermissionError as pe:
        raise ForbiddenException(str(pe)) from pe
    except FileNotFoundError as fe:
        raise EntityNotFoundException(entity_name="Document", entity_id=file) from fe
    except ValueError as ve:
        raise ValidationException(str(ve)) from ve
