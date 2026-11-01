import asyncio
import tempfile
import unittest
from pathlib import Path
from typing import Dict, Optional

from backend_service.app.application.services.auth_service import AuthService
from backend_service.app.domain.exceptions.base import AuthenticationException, ForbiddenException
from backend_service.app.domain.models.user import User
from backend_service.app.infrastructure.configuration.settings import Settings
from backend_service.app.infrastructure.persistence.database import Database
from backend_service.app.infrastructure.persistence.sqlite_user_repo import SqliteUserRepository
from backend_service.app.infrastructure.security.jwt_handler import hash_password

DEMO_EMAIL = "engineer@contextfoundry.dev"


class InMemoryUserRepo:
    def __init__(self) -> None:
        self.users: Dict[str, User] = {}

    async def create_user(self, user: User) -> User:
        self.users[user.email.lower()] = user
        return user

    async def upsert_user(self, user: User) -> User:
        key = user.email.lower()
        existing = self.users.get(key)
        if existing:
            updated = User(
                id=existing.id,
                email=key,
                name=user.name,
                role=user.role,
                password_hash=user.password_hash,
                created_at=existing.created_at,
            )
            self.users[key] = updated
            return updated
        self.users[key] = user
        return user

    async def get_by_email(self, email: str) -> Optional[User]:
        return self.users.get(email.lower())

    async def get_by_id(self, user_id: str) -> Optional[User]:
        return next((u for u in self.users.values() if u.id == user_id), None)


def make_service(allow: bool, repo: Optional[InMemoryUserRepo] = None) -> AuthService:
    settings = Settings(
        allow_user_registration=allow,
        admin_email=None,
        admin_password=None,
        admin_password_hash=None,
    )
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

    def test_admin_user_seeded_and_survives_ephemeral_db_wipe(self) -> None:
        admin_hash = "pbkdf2_sha256$100000$bd82e28a920cf74d81446840384ce9d2$9df44e645d17eb9b9c2559d9c4c7165f0e665fdbb18282862cf224d16d0e0ef6"
        settings = Settings(
            allow_user_registration=False,
            admin_email="siddhant@contextfoundry.dev",
            admin_password=None,
            admin_password_hash=admin_hash,
            admin_name="Siddhant Bhanot",
            admin_role="developer",
        )
        repo1 = InMemoryUserRepo()
        svc1 = AuthService(user_repo=repo1, settings=settings)
        seeded1 = run(svc1.ensure_admin_user())
        self.assertIsNotNone(seeded1)
        assert seeded1 is not None
        self.assertEqual(seeded1.email, "siddhant@contextfoundry.dev")

        # Login works when ALLOW_USER_REGISTRATION=false
        login_res = run(svc1.login("siddhant@contextfoundry.dev", "India@contextfoundry.dev"))
        token = login_res["access_token"]
        self.assertEqual(login_res["user"]["id"], seeded1.id)

        # Simulate Render container restart wiping SQLite (fresh empty repository)
        repo2 = InMemoryUserRepo()
        svc2 = AuthService(user_repo=repo2, settings=settings)
        # Even before explicit login, existing JWT resolves the re-seeded admin user with identical ID
        recovered_user = run(svc2.get_user_from_token(token))
        self.assertEqual(recovered_user.id, seeded1.id)
        self.assertEqual(recovered_user.email, "siddhant@contextfoundry.dev")

        # And login after a fresh wipe works immediately
        repo3 = InMemoryUserRepo()
        svc3 = AuthService(user_repo=repo3, settings=settings)
        login_res2 = run(svc3.login("siddhant@contextfoundry.dev", "India@contextfoundry.dev"))
        self.assertEqual(login_res2["user"]["id"], seeded1.id)

    def test_sqlite_admin_seed_and_restart_persistence(self) -> None:
        admin_hash = "pbkdf2_sha256$100000$bd82e28a920cf74d81446840384ce9d2$9df44e645d17eb9b9c2559d9c4c7165f0e665fdbb18282862cf224d16d0e0ef6"
        with tempfile.TemporaryDirectory() as tmpdir:
            db_file = Path(tmpdir) / "test_cf.db"
            settings = Settings(
                database_path=str(db_file),
                allow_user_registration=False,
                admin_email="siddhant@contextfoundry.dev",
                admin_password=None,
                admin_password_hash=admin_hash,
                admin_name="Siddhant Bhanot",
                admin_role="developer",
            )
            db1 = Database(settings=settings)
            run(db1.init_schema())
            svc1 = AuthService(user_repo=SqliteUserRepository(db=db1), settings=settings)
            u1 = run(svc1.ensure_admin_user())
            self.assertIsNotNone(u1)
            # Re-running ensure_admin_user is idempotent on existing SQLite DB
            u1_again = run(svc1.ensure_admin_user())
            assert u1 is not None and u1_again is not None
            self.assertEqual(u1.id, u1_again.id)
            login1 = run(svc1.login("siddhant@contextfoundry.dev", "India@contextfoundry.dev"))
            token = login1["access_token"]

            # Simulate container replacement on Render: delete the SQLite files
            for p in Path(tmpdir).glob("test_cf.db*"):
                p.unlink()

            db2 = Database(settings=settings)
            run(db2.init_schema())
            svc2 = AuthService(user_repo=SqliteUserRepository(db=db2), settings=settings)
            u2 = run(svc2.ensure_admin_user())
            assert u2 is not None
            self.assertEqual(u1.id, u2.id)
            recovered = run(svc2.get_user_from_token(token))
            self.assertEqual(recovered.email, "siddhant@contextfoundry.dev")


if __name__ == "__main__":
    unittest.main()

