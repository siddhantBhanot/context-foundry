from typing import List, Protocol
from backend_service.app.domain.models.feedback import Feedback


class FeedbackRepository(Protocol):
    """Abstract persistence interface for user feedback ratings and comments."""

    async def save_feedback(self, feedback: Feedback) -> Feedback:
        """Persist user feedback for a message/conversation."""
        ...

    async def get_feedback_by_message(self, message_id: str) -> List[Feedback]:
        """Retrieve feedback associated with a specific message."""
        ...

    async def get_feedback_by_conversation(self, conversation_id: str) -> List[Feedback]:
        """Retrieve feedback associated with a conversation."""
        ...

    async def list_feedback(self, limit: int = 50, offset: int = 0) -> List[Feedback]:
        """Retrieve recent feedback entries with pagination."""
        ...
