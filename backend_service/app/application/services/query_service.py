import json
import time
from typing import Any, AsyncIterator, Dict, List, Optional
import uuid

from backend_service.app.domain.exceptions.base import EntityNotFoundException, ValidationException
from backend_service.app.domain.interfaces.conversation_repository import ConversationRepository
from backend_service.app.domain.interfaces.rag_client import RAGClientProtocol
from backend_service.app.domain.models.conversation import Conversation, Message, MessageRole


class QueryService:
    """
    Application service orchestrating multi-turn user conversation management,
    dispatching queries to the RAG client, and persisting messages and citations.
    """

    def __init__(
        self,
        conversation_repo: ConversationRepository,
        rag_client: RAGClientProtocol,
    ):
        self.conversation_repo = conversation_repo
        self.rag_client = rag_client

    async def execute_query(
        self,
        query_text: str,
        conversation_id: Optional[str] = None,
        service: str = "income-assessment-service",
        top_k: int = 5,
        user_id: Optional[str] = None,
        share_token: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        cleaned_query = query_text.strip()
        if not cleaned_query:
            raise ValidationException("Query text cannot be empty.")

        title_snippet = cleaned_query[:60] + ("..." if len(cleaned_query) > 60 else "")
        forked = False
        forked_from = None

        # 1. Resolve or Fork Conversation
        if share_token:
            shared_conv = await self.conversation_repo.get_conversation_by_share_token(share_token)
            if not shared_conv:
                raise EntityNotFoundException("Shared Conversation", share_token)

            if user_id and shared_conv.user_id != user_id:
                # Fork on reply! Clone messages into a brand-new conversation for this viewing user
                conversation = await self.conversation_repo.fork_conversation(
                    source_conversation_id=shared_conv.id,
                    new_user_id=user_id,
                )
                forked = True
                forked_from = shared_conv.id
            else:
                # Original owner replying to their own shared thread
                conversation = shared_conv

        elif conversation_id:
            # Check if conversation exists and belongs to current user
            existing_conv = await self.conversation_repo.get_conversation(
                conversation_id=conversation_id,
                user_id=user_id,
            )
            if existing_conv:
                conversation = existing_conv
            else:
                # Check if it is a shared conversation owned by another user
                source_conv = await self.conversation_repo.get_conversation(
                    conversation_id=conversation_id,
                    user_id=None,
                )
                if source_conv and source_conv.share_token and user_id and source_conv.user_id != user_id:
                    # Fork on reply!
                    conversation = await self.conversation_repo.fork_conversation(
                        source_conversation_id=source_conv.id,
                        new_user_id=user_id,
                    )
                    forked = True
                    forked_from = source_conv.id
                else:
                    conversation = await self.conversation_repo.get_or_create_conversation(
                        conversation_id=conversation_id,
                        service=service,
                        title=title_snippet,
                        user_id=user_id,
                    )
        else:
            conversation = await self.conversation_repo.get_or_create_conversation(
                conversation_id=None,
                service=service,
                title=title_snippet,
                user_id=user_id,
            )

        # 2. Persist user message
        user_msg = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content=cleaned_query,
        )
        await self.conversation_repo.add_message(conversation.id, user_msg)

        # 3. Retrieve prior conversation history for multi-turn context (includes cloned messages if forked)
        history = await self.conversation_repo.get_messages(conversation.id, limit=20)

        # 4. Dispatch query to RAG client
        rag_result = await self.rag_client.query(
            query_text=cleaned_query,
            service=service,
            history=history,
            top_k=top_k,
            model=model,
        )

        # 5. Persist assistant response with verified sources
        assistant_msg = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content=rag_result.answer,
            sources=rag_result.sources,
        )
        await self.conversation_repo.add_message(conversation.id, assistant_msg)

        # 6. Format response
        return {
            "conversation_id": conversation.id,
            "message_id": assistant_msg.id,
            "answer": rag_result.answer,
            "sources": [s.to_dict() for s in rag_result.sources],
            "service": rag_result.service,
            "latency_ms": rag_result.latency_ms,
            "provider": rag_result.provider,
            "model": rag_result.model,
            "forked": forked,
            "forked_from": forked_from,
            "created_at": assistant_msg.created_at.isoformat(),
        }

    async def execute_query_stream(
        self,
        query_text: str,
        conversation_id: Optional[str] = None,
        service: str = "income-assessment-service",
        top_k: int = 5,
        user_id: Optional[str] = None,
        share_token: Optional[str] = None,
        model: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """
        Execute streaming query yielding standard SSE data events.
        Persists user message upfront and saves full assistant response once generation completes.
        """
        cleaned_query = query_text.strip()
        if not cleaned_query:
            raise ValidationException("Query string cannot be empty.")

        title_snippet = cleaned_query[:40] + ("..." if len(cleaned_query) > 40 else "")
        forked = False
        forked_from = None

        # 1. Resolve conversation thread or fork
        if share_token:
            shared_conv = await self.conversation_repo.get_conversation_by_share_token(share_token)
            if not shared_conv:
                raise EntityNotFoundException("Shared Conversation", share_token)
            if user_id and shared_conv.user_id != user_id:
                conversation = await self.conversation_repo.fork_conversation(
                    source_conversation_id=shared_conv.id,
                    new_user_id=user_id,
                )
                forked = True
                forked_from = shared_conv.id
            else:
                conversation = shared_conv
        elif conversation_id:
            existing_conv = await self.conversation_repo.get_conversation(
                conversation_id=conversation_id,
                user_id=user_id,
            )
            if existing_conv:
                conversation = existing_conv
            else:
                source_conv = await self.conversation_repo.get_conversation(
                    conversation_id=conversation_id,
                    user_id=None,
                )
                if source_conv and source_conv.share_token and user_id and source_conv.user_id != user_id:
                    conversation = await self.conversation_repo.fork_conversation(
                        source_conversation_id=source_conv.id,
                        new_user_id=user_id,
                    )
                    forked = True
                    forked_from = source_conv.id
                else:
                    conversation = await self.conversation_repo.get_or_create_conversation(
                        conversation_id=conversation_id,
                        service=service,
                        title=title_snippet,
                        user_id=user_id,
                    )
        else:
            conversation = await self.conversation_repo.get_or_create_conversation(
                conversation_id=None,
                service=service,
                title=title_snippet,
                user_id=user_id,
            )

        # 2. Persist user message
        user_msg = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content=cleaned_query,
        )
        await self.conversation_repo.add_message(conversation.id, user_msg)

        # 3. Retrieve prior conversation history
        history = await self.conversation_repo.get_messages(conversation.id, limit=20)

        # 4. Initiate RAG stream
        start_time = time.perf_counter()
        assistant_msg_id = str(uuid.uuid4())

        try:
            stream_iter, sources, meta = await self.rag_client.stream_query(
                query_text=cleaned_query,
                service=service,
                history=history,
                top_k=top_k,
                model=model,
            )

            # 5. Emit initial metadata event
            meta_payload = {
                "type": "metadata",
                "conversation_id": conversation.id,
                "message_id": assistant_msg_id,
                "sources": [s.to_dict() for s in sources],
                "service": meta.get("service", service),
                "provider": meta.get("provider", "groq"),
                "model": meta.get("model", model or "default"),
                "forked": forked,
                "forked_from": forked_from,
            }
            yield f"data: {json.dumps(meta_payload)}\n\n"

            # 6. Stream token chunks
            full_chunks = []
            async for chunk in stream_iter:
                if chunk:
                    full_chunks.append(chunk)
                    yield f"data: {json.dumps({'type': 'chunk', 'text': chunk})}\n\n"

            # 7. Persist completed assistant message
            full_answer = "".join(full_chunks)
            latency_ms = (time.perf_counter() - start_time) * 1000
            assistant_msg = Message(
                id=assistant_msg_id,
                conversation_id=conversation.id,
                role=MessageRole.ASSISTANT,
                content=full_answer,
                sources=sources,
            )
            await self.conversation_repo.add_message(conversation.id, assistant_msg)

            # 8. Emit done event
            done_payload = {
                "type": "done",
                "message_id": assistant_msg_id,
                "conversation_id": conversation.id,
                "latency_ms": round(latency_ms, 2),
                "complete": True,
            }
            yield f"data: {json.dumps(done_payload)}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"


    async def create_share_token(self, conversation_id: str, user_id: str) -> str:
        return await self.conversation_repo.generate_share_token(
            conversation_id=conversation_id,
            user_id=user_id,
        )

    async def get_shared_conversation(self, share_token: str) -> Conversation:
        conversation = await self.conversation_repo.get_conversation_by_share_token(share_token)
        if not conversation:
            raise EntityNotFoundException("Shared Conversation", share_token)
        return conversation

    async def get_conversation_history(
        self,
        conversation_id: str,
        user_id: Optional[str] = None,
    ) -> Conversation:
        conversation = await self.conversation_repo.get_conversation(
            conversation_id=conversation_id,
            user_id=user_id,
        )
        if not conversation:
            raise EntityNotFoundException("Conversation", conversation_id)
        return conversation

    async def list_conversations(
        self,
        service: Optional[str] = None,
        limit: int = 20,
        user_id: Optional[str] = None,
    ) -> List[Conversation]:
        return await self.conversation_repo.list_conversations(
            service=service,
            limit=limit,
            user_id=user_id,
        )

    async def list_models(self) -> Dict[str, Any]:
        models = await self.rag_client.list_models()
        default_model = next(
            (m["id"] for m in models if m.get("is_default")),
            models[0]["id"] if models else "default",
        )
        return {
            "models": models,
            "default_model": default_model,
        }



