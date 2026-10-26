from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import uuid


class FeedbackRating(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"


@dataclass
class Feedback:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    message_id: str = ""
    conversation_id: str = ""
    rating: FeedbackRating = FeedbackRating.POSITIVE
    comment: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
