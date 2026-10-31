import asyncio
import unittest
from typing import Dict, Optional

from backend_service.app.application.services.auth_service import AuthService
from backend_service.app.domain.exceptions.base import AuthenticationException, ForbiddenException
from backend_service.app.domain.models.user import User
from backend_service.app.infrastructure.configuration.settings import Settings
from backend_service.app.infrastructure.security.jwt_handler import hash_password

DEMO_EMAIL = "engineer@contextfoundry.dev"


class InMemoryUserRepo:
    def __init__(self) -> None:
        self.users: Dict[str, User] = {}

    async def create_user(self, user: User) -> User:
        self.users[user.email] = user
        return user

    async def get_by_email(self, email: str) -> Optional[User]:
        return self.users.get(email.lower())

    async def get_by_id(self, user_id: str) -> Optional[User]:
        return next((u for u in self.users.values() if u.id == user_id), None)


def make_service(allow: bool, repo: Optional[InMemoryUserRepo] = None) -> AuthService:
    settings = Settings(allow_user_registration=allow)
    return AuthService(user_repo=repo or InMemoryUserRepo(), settings=settings)


def run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


class TestRegistrationToggle(unittest.TestCase):
    def test_signup_allowed_when_enabled(self) -> None:
        svc = make_service(True)
        res = run(svc.signup("new@example.com", "secret123", "New User"))
        self.assertIn("access_token", res)

    def test_signup_blocked_when_disabled(self) -> None:
        repo = InMemoryUserRepo()
        svc = make_service(False, repo)
        with self.assertRaises(ForbiddenException):
            run(svc.signup("new@example.com", "secret123", "New User"))
        self.assertEqual(repo.users, {})

    def test_demo_user_autoprovisioned_when_enabled(self) -> None:
        svc = make_service(True)
        res = run(svc.login(DEMO_EMAIL, "password123"))
        self.assertIn("access_token", res)

    def test_demo_user_not_provisioned_when_disabled(self) -> None:
        repo = InMemoryUserRepo()
        svc = make_service(False, repo)
        with self.assertRaises(AuthenticationException):
            run(svc.login(DEMO_EMAIL, "password123"))
        self.assertEqual(repo.users, {})

    def test_existing_demo_user_cannot_login_when_disabled(self) -> None:
        repo = InMemoryUserRepo()
        run(repo.create_user(User(
            id="demo-id", email=DEMO_EMAIL, name="Demo", role="developer",
            password_hash=hash_password("password123"),
        )))
        with self.assertRaises(AuthenticationException):
            run(make_service(False, repo).login(DEMO_EMAIL, "password123"))
        # Still works when the flag is on
        self.assertIn("access_token", run(make_service(True, repo).login(DEMO_EMAIL, "password123")))

    def test_existing_real_user_can_still_login_when_disabled(self) -> None:
        repo = InMemoryUserRepo()
        run(repo.create_user(User(
            id="u1", email="owner@example.com", name="Owner", role="developer",
            password_hash=hash_password("ownerpass1"),
        )))
        res = run(make_service(False, repo).login("owner@example.com", "ownerpass1"))
        self.assertIn("access_token", res)


if __name__ == "__main__":
    unittest.main()

