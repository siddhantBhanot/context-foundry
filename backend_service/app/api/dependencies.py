from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from functools import lru_cache
from typing import Optional

from backend_service.app.application.services.auth_service import AuthService
from backend_service.app.application.services.feedback_service import FeedbackService
from backend_service.app.application.services.knowledge_service import KnowledgeService
from backend_service.app.application.services.query_service import QueryService
from backend_service.app.domain.exceptions.base import AuthenticationException
from backend_service.app.domain.interfaces.conversation_repository import ConversationRepository
from backend_service.app.domain.interfaces.feedback_repository import FeedbackRepository
from backend_service.app.domain.interfaces.rag_client import RAGClientProtocol
from backend_service.app.domain.interfaces.user_repository import UserRepository
from backend_service.app.domain.models.user import User
from backend_service.app.infrastructure.clients.direct_rag_client import DirectRAGClient
from backend_service.app.infrastructure.clients.mock_rag_client import MockRAGClient
from backend_service.app.infrastructure.configuration.settings import Settings, get_settings
from backend_service.app.infrastructure.persistence.database import Database, get_database
from backend_service.app.infrastructure.persistence.sqlite_conversation_repo import SqliteConversationRepository
from backend_service.app.infrastructure.persistence.sqlite_feedback_repo import SqliteFeedbackRepository
from backend_service.app.infrastructure.persistence.sqlite_user_repo import SqliteUserRepository


_security = HTTPBearer(auto_error=False)


@lru_cache
def get_db_instance() -> Database:
    return get_database()


@lru_cache
def get_user_repository() -> UserRepository:
    return SqliteUserRepository(db=get_db_instance())


@lru_cache
def get_conversation_repository() -> ConversationRepository:
    return SqliteConversationRepository(db=get_db_instance())


@lru_cache
def get_feedback_repository() -> FeedbackRepository:
    return SqliteFeedbackRepository(db=get_db_instance())


@lru_cache
def get_rag_client() -> RAGClientProtocol:
    settings = get_settings()
    if settings.rag_client_mode.lower() == "mock":
        return MockRAGClient()
    return DirectRAGClient()


def get_auth_service() -> AuthService:
    return AuthService(
        user_repo=get_user_repository(),
        settings=get_settings(),
    )


def get_query_service() -> QueryService:
    return QueryService(
        conversation_repo=get_conversation_repository(),
        rag_client=get_rag_client(),
    )


def get_feedback_service() -> FeedbackService:
    return FeedbackService(
        feedback_repo=get_feedback_repository(),
    )


def get_knowledge_service() -> KnowledgeService:
    return KnowledgeService(
        rag_client=get_rag_client(),
    )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_security),
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    """
    Extract and validate JWT token from Bearer header.
    Raises AuthenticationException if token is missing, invalid, or expired.
    """
    if not credentials or not credentials.credentials:
        raise AuthenticationException("Authentication required. Please provide a valid Bearer token.")

    return await auth_service.get_user_from_token(credentials.credentials)



@lru_cache
def get_db_instance() -> Database:
    return get_database()


@lru_cache
def get_conversation_repository() -> ConversationRepository:
    return SqliteConversationRepository(db=get_db_instance())


@lru_cache
def get_feedback_repository() -> FeedbackRepository:
    return SqliteFeedbackRepository(db=get_db_instance())


@lru_cache
def get_rag_client() -> RAGClientProtocol:
    settings = get_settings()
    if settings.rag_client_mode.lower() == "mock":
        return MockRAGClient()
    return DirectRAGClient()


def get_query_service() -> QueryService:
    return QueryService(
        conversation_repo=get_conversation_repository(),
        rag_client=get_rag_client(),
    )


def get_feedback_service() -> FeedbackService:
    return FeedbackService(
        feedback_repo=get_feedback_repository(),
    )


def get_knowledge_service() -> KnowledgeService:
    return KnowledgeService(
        rag_client=get_rag_client(),
    )


@lru_cache
def get_kt_repository():
    from backend_service.app.infrastructure.persistence.sqlite_kt_repo import SQLiteKTRepository
    return SQLiteKTRepository(db=get_db_instance())


def get_kt_service():
    from backend_service.app.application.services.kt_service import KTService
    return KTService(
        kt_repo=get_kt_repository(),
        rag_client=get_rag_client(),
    )


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_security),
    auth_service: AuthService = Depends(get_auth_service),
) -> Optional[User]:
    """Optionally extract authenticated user if token present, or return None."""
    if not credentials or not credentials.credentials:
        return None
    try:
        return await auth_service.get_user_from_token(credentials.credentials)
    except Exception:
        return None
