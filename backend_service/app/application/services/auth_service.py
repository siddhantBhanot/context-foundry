from datetime import timedelta
import re
from typing import Any, Dict, Optional
import uuid

from backend_service.app.domain.exceptions.base import (
    AuthenticationException,
    ForbiddenException,
    ValidationException,
)
from backend_service.app.domain.interfaces.user_repository import UserRepository
from backend_service.app.domain.models.user import User
from backend_service.app.infrastructure.configuration.settings import Settings, get_settings
from backend_service.app.infrastructure.security.jwt_handler import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


class AuthService:
    """Application service for user registration, authentication, and token management."""

    EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    DEMO_EMAILS = frozenset({"engineer@contextfoundry.dev", "dev@contextfoundry.dev"})

    def __init__(
        self,
        user_repo: UserRepository,
        settings: Optional[Settings] = None,
    ):
        self.user_repo = user_repo
        self.settings = settings or get_settings()

    @property
    def registration_enabled(self) -> bool:
        return bool(self.settings.allow_user_registration)

    async def ensure_admin_user(self) -> Optional[User]:
        """
        Idempotently seed or synchronize the configured administrator account.
        Uses a deterministic UUIDv5 derived from the admin email so JWT tokens
        remain valid across container restarts on ephemeral filesystems (e.g., Render).
        """
        raw_email = (self.settings.admin_email or "").strip().lower()
        raw_password = self.settings.admin_password
        raw_hash = (self.settings.admin_password_hash or "").strip()

        if not raw_email or (not raw_password and not raw_hash):
            return None

        existing = await self.user_repo.get_by_email(raw_email)
        if raw_password:
            if existing and verify_password(raw_password, existing.password_hash):
                pw_hash = existing.password_hash
            else:
                pw_hash = hash_password(raw_password)
        else:
            pw_hash = raw_hash

        clean_role = (self.settings.admin_role or "developer").strip().lower()
        if clean_role not in {"developer", "banking_staff"}:
            clean_role = "developer"

        admin_id = existing.id if existing else str(
            uuid.uuid5(uuid.NAMESPACE_DNS, f"contextfoundry-admin:{raw_email}")
        )
        admin_user = User(
            id=admin_id,
            email=raw_email,
            name=(self.settings.admin_name or "Administrator").strip(),
            role=clean_role,
            password_hash=pw_hash,
        )
        if hasattr(self.user_repo, "upsert_user"):
            return await self.user_repo.upsert_user(admin_user)
        if not existing:
            return await self.user_repo.create_user(admin_user)
        return existing

    async def signup(self, email: str, password: str, name: str, role: str = "developer") -> Dict[str, Any]:
        if not self.registration_enabled:
            raise ForbiddenException("Account creation is disabled on this deployment.")

        clean_email = email.lower().strip()
        clean_name = name.strip()
        clean_role = (role or "developer").strip().lower()
        if clean_role not in {"developer", "banking_staff"}:
            clean_role = "developer"

        if not clean_email or not self.EMAIL_REGEX.match(clean_email):
            raise ValidationException("A valid email address is required.")

        if not clean_name:
            raise ValidationException("Full name is required.")

        if len(password) < 6:
            raise ValidationException("Password must be at least 6 characters long.")

        existing = await self.user_repo.get_by_email(clean_email)
        if existing:
            raise ValidationException(f"An account with email '{clean_email}' already exists.")

        hashed_pw = hash_password(password)
        user = User(
            id=str(uuid.uuid4()),
            email=clean_email,
            name=clean_name,
            role=clean_role,
            password_hash=hashed_pw,
        )
        saved_user = await self.user_repo.create_user(user)

        token = create_access_token(
            data={"sub": saved_user.id, "email": saved_user.email, "name": saved_user.name, "role": saved_user.role},
            secret_key=self.settings.jwt_secret_key,
            expires_delta=timedelta(minutes=self.settings.jwt_access_token_expire_minutes),
        )

        return {
            "access_token": token,
            "token_type": "bearer",
            "user": saved_user.to_public_dict(),
        }

    async def login(self, email: str, password: str) -> Dict[str, Any]:
        clean_email = email.lower().strip()
        if not clean_email or not password:
            raise ValidationException("Email and password are required.")

        user = await self.user_repo.get_by_email(clean_email)

        if (
            not user
            and self.settings.admin_email
            and clean_email == self.settings.admin_email.strip().lower()
        ):
            user = await self.ensure_admin_user()

        # The hardcoded demo account (known password) is only usable when registration is enabled,
        # even if it already exists in the database. Otherwise anyone could log in with it.
        if clean_email in self.DEMO_EMAILS:
            if not self.registration_enabled:
                raise AuthenticationException("Invalid email or password.")
            # Auto-provision on first use (non-production environments only)
            if not user and self.settings.environment.lower() != "production":
                user = await self.user_repo.create_user(User(
                    id=str(uuid.uuid4()),
                    email=clean_email,
                    name="Hritik (Engineering)",
                    role="developer",
                    password_hash=hash_password("password123"),
                ))

        if not user or not verify_password(password, user.password_hash):
            raise AuthenticationException("Invalid email or password.")

        token = create_access_token(
            data={"sub": user.id, "email": user.email, "name": user.name, "role": user.role},
            secret_key=self.settings.jwt_secret_key,
            expires_delta=timedelta(minutes=self.settings.jwt_access_token_expire_minutes),
        )

        return {
            "access_token": token,
            "token_type": "bearer",
            "user": user.to_public_dict(),
        }

    async def get_user_from_token(self, token: str) -> User:
        if not token:
            raise AuthenticationException("Authorization token is missing.")

        try:
            payload = decode_access_token(token, self.settings.jwt_secret_key)
        except ValueError as e:
            raise AuthenticationException(f"Invalid or expired token: {str(e)}")

        user_id = payload.get("sub")
        if not user_id:
            raise AuthenticationException("Malformed token payload.")

        user = await self.user_repo.get_by_id(user_id)
        if not user and self.settings.admin_email:
            await self.ensure_admin_user()
            user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise AuthenticationException("User account associated with this token not found.")

        return user
