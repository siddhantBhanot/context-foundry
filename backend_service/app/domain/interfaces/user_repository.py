from typing import Optional, Protocol
from backend_service.app.domain.models.user import User


class UserRepository(Protocol):
    """Abstract persistence interface for user accounts."""

    async def create_user(self, user: User) -> User:
        """Persist a new user entity."""
        ...

    async def get_by_email(self, email: str) -> Optional[User]:
        """Lookup a user by email address (case-insensitive)."""
        ...

    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Lookup a user by unique identifier."""
        ...
