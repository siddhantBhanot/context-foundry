from typing import Any, Dict, List, Optional
import uuid

from backend_service.app.domain.exceptions.base import ValidationException
from backend_service.app.domain.interfaces.feedback_repository import FeedbackRepository
from backend_service.app.domain.models.feedback import Feedback, FeedbackRating


class FeedbackService:
    """Application service for recording and retrieving user feedback on answers."""

    def __init__(self, feedback_repo: FeedbackRepository):
        self.feedback_repo = feedback_repo

    async def submit_feedback(
        self,
        message_id: str,
        conversation_id: str,
        rating: str,
        comment: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not message_id or not conversation_id:
            raise ValidationException("message_id and conversation_id are required.")

        normalized_rating = rating.lower().strip()
        if normalized_rating not in ["positive", "negative"]:
            raise ValidationException("rating must be either 'positive' or 'negative'.")

        feedback_obj = Feedback(
            id=str(uuid.uuid4()),
            message_id=message_id,
            conversation_id=conversation_id,
            rating=FeedbackRating(normalized_rating),
            comment=comment.strip() if comment else None,
        )

        saved = await self.feedback_repo.save_feedback(feedback_obj)
        return {
            "id": saved.id,
            "message_id": saved.message_id,
            "conversation_id": saved.conversation_id,
            "rating": saved.rating.value,
            "comment": saved.comment,
            "status": "recorded",
            "created_at": saved.created_at.isoformat(),
        }

    async def get_message_feedback(self, message_id: str) -> List[Dict[str, Any]]:
        feedbacks = await self.feedback_repo.get_feedback_by_message(message_id)
        return [
            {
                "id": f.id,
                "message_id": f.message_id,
                "conversation_id": f.conversation_id,
                "rating": f.rating.value,
                "comment": f.comment,
                "created_at": f.created_at.isoformat(),
            }
            for f in feedbacks
        ]

    async def list_feedback(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        feedbacks = await self.feedback_repo.list_feedback(limit=limit, offset=offset)
        return [
            {
                "id": f.id,
                "message_id": f.message_id,
                "conversation_id": f.conversation_id,
                "rating": f.rating.value,
                "comment": f.comment,
                "created_at": f.created_at.isoformat(),
            }
            for f in feedbacks
        ]

