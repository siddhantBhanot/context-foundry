from typing import Optional
from pydantic import BaseModel, Field


class FeedbackRequest(BaseModel):
    message_id: str = Field(..., description="ID of the assistant message being rated")
    conversation_id: str = Field(..., description="Associated conversation identifier")
    rating: str = Field(..., description="Rating value: 'positive' or 'negative'")
    comment: Optional[str] = Field(default=None, max_length=1000, description="Optional user feedback text")


class FeedbackResponse(BaseModel):
    id: str = Field(..., description="Unique feedback record identifier")
    message_id: str
    conversation_id: str
    rating: str
    comment: Optional[str] = None
    status: str = Field(default="recorded")
    created_at: str
