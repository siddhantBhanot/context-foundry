from typing import Any, Dict, List
from fastapi import APIRouter, Depends

from backend_service.app.api.dependencies import get_feedback_service
from backend_service.app.api.schemas.feedback import FeedbackRequest, FeedbackResponse
from backend_service.app.application.services.feedback_service import FeedbackService

router = APIRouter(prefix="/feedback", tags=["Feedback"])


@router.post("", response_model=FeedbackResponse)
async def submit_feedback(
    payload: FeedbackRequest,
    feedback_service: FeedbackService = Depends(get_feedback_service),
) -> FeedbackResponse:
    """
    Submit user feedback (positive or negative rating + optional comment) on an answer.
    """
    result = await feedback_service.submit_feedback(
        message_id=payload.message_id,
        conversation_id=payload.conversation_id,
        rating=payload.rating,
        comment=payload.comment,
    )
    return FeedbackResponse(**result)


@router.get("", response_model=List[Dict[str, Any]])
async def list_all_feedback(
    limit: int = 50,
    offset: int = 0,
    feedback_service: FeedbackService = Depends(get_feedback_service),
) -> List[Dict[str, Any]]:
    """
    List all user feedback entries across conversations with pagination.
    """
    return await feedback_service.list_feedback(limit=limit, offset=offset)


@router.get("/{message_id}", response_model=List[Dict[str, Any]])
async def get_message_feedback(
    message_id: str,
    feedback_service: FeedbackService = Depends(get_feedback_service),
) -> List[Dict[str, Any]]:
    """
    Retrieve all feedback entries associated with a specific message.
    """
    return await feedback_service.get_message_feedback(message_id)

