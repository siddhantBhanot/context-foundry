from typing import List, Optional
from pydantic import BaseModel, Field


class SourceCitationSchema(BaseModel):
    file: str = Field(..., description="Source file name or path")
    service: Optional[str] = Field(default=None, description="Service identifier the source document belongs to")
    class_name: Optional[str] = Field(default=None, description="Extracted class name if code file")
    endpoint: Optional[str] = Field(default=None, description="Extracted REST endpoint if handler")
    start_line: Optional[int] = Field(default=None, description="Starting line number")
    end_line: Optional[int] = Field(default=None, description="Ending line number")
    doc_type: Optional[str] = Field(default=None, description="Document type: markdown or kotlin")
    snippet: Optional[str] = Field(default=None, description="Text preview snippet")


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, description="User question or engineering prompt")
    conversation_id: Optional[str] = Field(
        default=None, description="Existing conversation ID to continue multi-turn session"
    )
    share_token: Optional[str] = Field(
        default=None, description="Share token if replying to or continuing a shared thread"
    )
    service: str = Field(
        default="income-assessment-service",
        description="Target microservice identifier",
    )
    model: Optional[str] = Field(
        default=None,
        description="Optional LLM model override for runtime inference",
    )
    top_k: int = Field(default=5, ge=1, le=20, description="Number of context chunks to retrieve")


class QueryResponse(BaseModel):
    conversation_id: str = Field(..., description="Active conversation identifier")
    message_id: str = Field(..., description="Identifier of the generated assistant message")
    answer: str = Field(..., description="Grounded natural language answer")
    sources: List[SourceCitationSchema] = Field(
        default_factory=list, description="Verified source citations"
    )
    service: str = Field(..., description="Target microservice")
    latency_ms: float = Field(..., description="Total query execution latency in milliseconds")
    provider: str = Field(default="groq", description="LLM provider category")
    model: str = Field(default="default", description="Model identifier used for inference")
    forked: bool = Field(default=False, description="Whether this query caused a branch from a shared conversation")
    forked_from: Optional[str] = Field(default=None, description="Source conversation ID if forked")
    created_at: str = Field(..., description="ISO 8601 timestamp")


class MessageSchema(BaseModel):
    id: str
    role: str
    content: str
    sources: List[SourceCitationSchema] = Field(default_factory=list)
    created_at: str


class ConversationDetailResponse(BaseModel):
    id: str
    service: str
    title: Optional[str] = None
    share_token: Optional[str] = None
    forked_from: Optional[str] = None
    created_at: str
    updated_at: str
    messages: List[MessageSchema] = Field(default_factory=list)


class ConversationSummary(BaseModel):
    id: str
    service: str
    title: Optional[str] = None
    share_token: Optional[str] = None
    forked_from: Optional[str] = None
    created_at: str
    updated_at: str


class ShareConversationResponse(BaseModel):
    conversation_id: str = Field(..., description="Target conversation ID")
    share_token: str = Field(..., description="Unique shareable UUID token")
    share_url: str = Field(..., description="Frontend share URL path")


class SharedConversationDetailResponse(BaseModel):
    id: str
    share_token: str
    service: str
    title: Optional[str] = None
    forked_from: Optional[str] = None
    is_owner: bool = Field(default=False, description="Whether the requesting user owns this conversation")
    created_at: str
    updated_at: str
    messages: List[MessageSchema] = Field(default_factory=list)

