from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from backend_service.app.api.dependencies import get_current_user, get_query_service
from backend_service.app.api.schemas.query import (
    ConversationDetailResponse,
    ConversationSummary,
    MessageSchema,
    QueryRequest,
    QueryResponse,
    ShareConversationResponse,
    SharedConversationDetailResponse,
    SourceCitationSchema,
)
from backend_service.app.application.services.query_service import QueryService
from backend_service.app.domain.models.user import User

router = APIRouter(tags=["Query & Conversations"])


@router.post("/query", response_model=QueryResponse)
async def execute_query(
    payload: QueryRequest,
    current_user: User = Depends(get_current_user),
    query_service: QueryService = Depends(get_query_service),
) -> QueryResponse:
    """
    Execute a natural language query against indexed microservice knowledge.
    Manages multi-turn conversation persistence scoped to the authenticated user and returns grounded source citations.
    Automatically forks thread if replying to another user's shared conversation.
    """
    result = await query_service.execute_query(
        query_text=payload.query,
        conversation_id=payload.conversation_id,
        service=payload.service,
        top_k=payload.top_k,
        user_id=current_user.id,
        share_token=payload.share_token,
        model=payload.model,
    )
    return QueryResponse(**result)


@router.post("/query/stream")
async def execute_query_stream(
    payload: QueryRequest,
    current_user: User = Depends(get_current_user),
    query_service: QueryService = Depends(get_query_service),
) -> StreamingResponse:
    """
    Execute streaming natural language query via Server-Sent Events (SSE).
    Yields initial metadata (sources, model, IDs), incremental text chunks, and final metrics.
    """
    generator = query_service.execute_query_stream(
        query_text=payload.query,
        conversation_id=payload.conversation_id,
        service=payload.service,
        top_k=payload.top_k,
        user_id=current_user.id,
        share_token=payload.share_token,
        model=payload.model,
    )
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )



@router.post("/conversations/{conversation_id}/share", response_model=ShareConversationResponse)
async def share_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    query_service: QueryService = Depends(get_query_service),
) -> ShareConversationResponse:
    """
    Generate or retrieve a unique share_token (UUID) for a conversation owned by the authenticated user.
    """
    token = await query_service.create_share_token(
        conversation_id=conversation_id,
        user_id=current_user.id,
    )
    return ShareConversationResponse(
        conversation_id=conversation_id,
        share_token=token,
        share_url=f"/?share={token}",
    )


@router.get("/shared/{share_token}", response_model=SharedConversationDetailResponse)
async def get_shared_conversation(
    share_token: str,
    current_user: User = Depends(get_current_user),
    query_service: QueryService = Depends(get_query_service),
) -> SharedConversationDetailResponse:
    """
    Retrieve read-only conversation history and source citations using a share_token.
    Requires authentication (returns 401 if unauthenticated).
    """
    conversation = await query_service.get_shared_conversation(share_token=share_token)
    messages = [
        MessageSchema(
            id=m.id,
            role=m.role.value,
            content=m.content,
            sources=[SourceCitationSchema(**s.to_dict()) for s in m.sources],
            created_at=m.created_at.isoformat(),
        )
        for m in conversation.messages
    ]
    return SharedConversationDetailResponse(
        id=conversation.id,
        share_token=share_token,
        service=conversation.service,
        title=conversation.title,
        forked_from=conversation.forked_from,
        is_owner=(conversation.user_id == current_user.id),
        created_at=conversation.created_at.isoformat(),
        updated_at=conversation.updated_at.isoformat(),
        messages=messages,
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    query_service: QueryService = Depends(get_query_service),
) -> ConversationDetailResponse:
    """
    Retrieve full message history and metadata for a conversation session owned by the authenticated user.
    """
    conversation = await query_service.get_conversation_history(
        conversation_id=conversation_id,
        user_id=current_user.id,
    )
    messages = [
        MessageSchema(
            id=m.id,
            role=m.role.value,
            content=m.content,
            sources=[SourceCitationSchema(**s.to_dict()) for s in m.sources],
            created_at=m.created_at.isoformat(),
        )
        for m in conversation.messages
    ]
    return ConversationDetailResponse(
        id=conversation.id,
        service=conversation.service,
        title=conversation.title,
        share_token=conversation.share_token,
        forked_from=conversation.forked_from,
        created_at=conversation.created_at.isoformat(),
        updated_at=conversation.updated_at.isoformat(),
        messages=messages,
    )


@router.get("/conversations", response_model=List[ConversationSummary])
async def list_conversations(
    service: Optional[str] = Query(default=None, description="Filter by service name"),
    limit: int = Query(default=20, ge=1, le=100, description="Max conversations to return"),
    current_user: User = Depends(get_current_user),
    query_service: QueryService = Depends(get_query_service),
) -> List[ConversationSummary]:
    """
    List conversations belonging exclusively to the authenticated user, ordered chronologically by last activity.
    """
    conversations = await query_service.list_conversations(
        service=service,
        limit=limit,
        user_id=current_user.id,
    )
    return [
        ConversationSummary(
            id=c.id,
            service=c.service,
            title=c.title,
            share_token=c.share_token,
            forked_from=c.forked_from,
            created_at=c.created_at.isoformat(),
            updated_at=c.updated_at.isoformat(),
        )
        for c in conversations
    ]


