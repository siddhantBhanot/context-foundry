from datetime import datetime
from typing import List, Optional

from backend_service.app.domain.interfaces.feedback_repository import FeedbackRepository
from backend_service.app.domain.models.feedback import Feedback, FeedbackRating
from backend_service.app.infrastructure.persistence.database import Database, get_database


class SqliteFeedbackRepository(FeedbackRepository):
    """SQLite implementation of FeedbackRepository using aiosqlite."""

    def __init__(self, db: Optional[Database] = None):
        self.db = db or get_database()

    async def save_feedback(self, feedback: Feedback) -> Feedback:
        async with self.db.connection() as conn:
            await conn.execute(
                """
                INSERT INTO feedback (id, message_id, conversation_id, rating, comment, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    feedback.id,
                    feedback.message_id,
                    feedback.conversation_id,
                    feedback.rating.value if isinstance(feedback.rating, FeedbackRating) else str(feedback.rating),
                    feedback.comment,
                    feedback.created_at.isoformat(),
                ),
            )
            await conn.commit()
        return feedback

    async def get_feedback_by_message(self, message_id: str) -> List[Feedback]:
        async with self.db.connection() as conn:
            cursor = await conn.execute(
                "SELECT id, message_id, conversation_id, rating, comment, created_at FROM feedback WHERE message_id = ?",
                (message_id,),
            )
            rows = await cursor.fetchall()
            return [
                Feedback(
                    id=row["id"],
                    message_id=row["message_id"],
                    conversation_id=row["conversation_id"],
                    rating=FeedbackRating(row["rating"]),
                    comment=row["comment"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                )
                for row in rows
            ]

    async def get_feedback_by_conversation(self, conversation_id: str) -> List[Feedback]:
        async with self.db.connection() as conn:
            cursor = await conn.execute(
                "SELECT id, message_id, conversation_id, rating, comment, created_at FROM feedback WHERE conversation_id = ?",
                (conversation_id,),
            )
            rows = await cursor.fetchall()
            return [
                Feedback(
                    id=row["id"],
                    message_id=row["message_id"],
                    conversation_id=row["conversation_id"],
                    rating=FeedbackRating(row["rating"]),
                    comment=row["comment"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                )
                for row in rows
            ]

    async def list_feedback(self, limit: int = 50, offset: int = 0) -> List[Feedback]:
        async with self.db.connection() as conn:
            cursor = await conn.execute(
                "SELECT id, message_id, conversation_id, rating, comment, created_at FROM feedback ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            )
            rows = await cursor.fetchall()
            return [
                Feedback(
                    id=row["id"],
                    message_id=row["message_id"],
                    conversation_id=row["conversation_id"],
                    rating=FeedbackRating(row["rating"]),
                    comment=row["comment"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                )
                for row in rows
            ]

