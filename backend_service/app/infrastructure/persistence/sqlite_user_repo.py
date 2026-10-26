from datetime import datetime
from typing import Optional

from backend_service.app.domain.interfaces.user_repository import UserRepository
from backend_service.app.domain.models.user import User
from backend_service.app.infrastructure.persistence.database import Database, get_database


class SqliteUserRepository(UserRepository):
    """SQLite implementation of UserRepository using aiosqlite."""

    def __init__(self, db: Optional[Database] = None):
        self.db = db or get_database()

    async def create_user(self, user: User) -> User:
        async with self.db.connection() as conn:
            await conn.execute(
                """
                INSERT INTO users (id, email, name, role, password_hash, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    user.id,
                    user.email.lower().strip(),
                    user.name.strip(),
                    user.role or "developer",
                    user.password_hash,
                    user.created_at.isoformat(),
                ),
            )
            await conn.commit()
        return user

    async def get_by_email(self, email: str) -> Optional[User]:
        normalized_email = email.lower().strip()
        async with self.db.connection() as conn:
            cursor = await conn.execute(
                "SELECT id, email, name, COALESCE(role, 'developer') AS role, password_hash, created_at FROM users WHERE email = ?",
                (normalized_email,),
            )
            row = await cursor.fetchone()
            if not row:
                return None
            return User(
                id=row["id"],
                email=row["email"],
                name=row["name"],
                role=row["role"],
                password_hash=row["password_hash"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )

    async def get_by_id(self, user_id: str) -> Optional[User]:
        async with self.db.connection() as conn:
            cursor = await conn.execute(
                "SELECT id, email, name, COALESCE(role, 'developer') AS role, password_hash, created_at FROM users WHERE id = ?",
                (user_id,),
            )
            row = await cursor.fetchone()
            if not row:
                return None
            return User(
                id=row["id"],
                email=row["email"],
                name=row["name"],
                role=row["role"],
                password_hash=row["password_hash"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )
