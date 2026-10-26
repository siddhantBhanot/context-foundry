import asyncio
import json
from pathlib import Path
from typing import AsyncGenerator, Optional
import aiosqlite

from backend_service.app.infrastructure.configuration.settings import Settings, get_settings


from contextlib import asynccontextmanager

class Database:
    """Manages asynchronous SQLite database connection and schema initialization."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.db_path = Path(self.settings.database_path).resolve()

    def _ensure_dir(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @asynccontextmanager
    async def connection(self) -> AsyncGenerator[aiosqlite.Connection, None]:
        self._ensure_dir()
        conn = await aiosqlite.connect(str(self.db_path))
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA foreign_keys = ON;")
        try:
            yield conn
        finally:
            await conn.close()

    async def init_schema(self) -> None:
        """Create tables and indexes if they do not already exist."""
        async with self.connection() as conn:
            await conn.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    role TEXT DEFAULT 'developer',
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    service TEXT NOT NULL,
                    title TEXT,
                    share_token TEXT UNIQUE,
                    forked_from TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    sources_json TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS feedback (
                    id TEXT PRIMARY KEY,
                    message_id TEXT NOT NULL,
                    conversation_id TEXT NOT NULL,
                    rating TEXT NOT NULL,
                    comment TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS ingestion_jobs (
                    id TEXT PRIMARY KEY,
                    service TEXT NOT NULL,
                    source_path TEXT,
                    status TEXT NOT NULL,
                    total_files INTEGER DEFAULT 0,
                    total_chunks INTEGER DEFAULT 0,
                    files_json TEXT,
                    error_message TEXT,
                    created_at TEXT NOT NULL,
                    completed_at TEXT
                );

                CREATE TABLE IF NOT EXISTS kt_course_enrollments (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    course_id TEXT NOT NULL,
                    current_lesson_index INTEGER DEFAULT 0,
                    completed_lessons_json TEXT DEFAULT '[]',
                    overall_progress INTEGER DEFAULT 0,
                    is_completed BOOLEAN DEFAULT 0,
                    knowledge_check_results_json TEXT DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(user_id, course_id),
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS kt_cached_lessons (
                    id TEXT PRIMARY KEY,
                    course_id TEXT NOT NULL,
                    lesson_id TEXT NOT NULL,
                    model TEXT NOT NULL,
                    content TEXT NOT NULL,
                    sources_json TEXT NOT NULL,
                    takeaways_json TEXT,
                    created_at TEXT NOT NULL,
                    UNIQUE(course_id, lesson_id, model)
                );

                CREATE TABLE IF NOT EXISTS kt_lesson_doubts (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    course_id TEXT NOT NULL,
                    lesson_id TEXT NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    sources_json TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
                CREATE INDEX IF NOT EXISTS idx_conversations_service ON conversations(service);
                CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
                CREATE INDEX IF NOT EXISTS idx_feedback_message ON feedback(message_id);
                CREATE INDEX IF NOT EXISTS idx_kt_enrollments_user ON kt_course_enrollments(user_id);
                CREATE INDEX IF NOT EXISTS idx_kt_doubts_lesson ON kt_lesson_doubts(course_id, lesson_id);
            """)

            # Ensure role column exists in users
            cursor_users = await conn.execute("PRAGMA table_info(users);")
            user_columns = [row["name"] for row in await cursor_users.fetchall()]
            if "role" not in user_columns:
                try:
                    await conn.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'developer';")
                except Exception:
                    pass

            # Ensure user_id, share_token, and forked_from columns exist if table was created in an earlier schema version
            cursor = await conn.execute("PRAGMA table_info(conversations);")
            columns = [row["name"] for row in await cursor.fetchall()]
            if "user_id" not in columns:
                try:
                    await conn.execute("ALTER TABLE conversations ADD COLUMN user_id TEXT;")
                except Exception:
                    pass

            if "share_token" not in columns:
                try:
                    await conn.execute("ALTER TABLE conversations ADD COLUMN share_token TEXT;")
                except Exception:
                    pass

            if "forked_from" not in columns:
                try:
                    await conn.execute("ALTER TABLE conversations ADD COLUMN forked_from TEXT;")
                except Exception:
                    pass

            await conn.execute("CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);")
            await conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_conversations_share_token ON conversations(share_token);")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_conversations_forked_from ON conversations(forked_from);")
            await conn.commit()




_db: Optional[Database] = None


def get_database() -> Database:
    global _db
    if _db is None:
        _db = Database()
    return _db
