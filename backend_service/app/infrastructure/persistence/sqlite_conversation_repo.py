from datetime import datetime, timezone
import json
from typing import List, Optional
import uuid

from backend_service.app.domain.exceptions.base import EntityNotFoundException, ForbiddenException
from backend_service.app.domain.interfaces.conversation_repository import ConversationRepository
from backend_service.app.domain.models.conversation import Conversation, Message, MessageRole, SourceCitation
from backend_service.app.infrastructure.persistence.database import Database, get_database


class SqliteConversationRepository(ConversationRepository):
    """SQLite implementation of ConversationRepository using aiosqlite."""

    def __init__(self, db: Optional[Database] = None):
        self.db = db or get_database()

    async def get_or_create_conversation(
        self,
        conversation_id: Optional[str] = None,
        service: str = "income-assessment-service",
        title: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Conversation:
        cid = conversation_id or str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        async with self.db.connection() as conn:
            cursor = await conn.execute(
                "SELECT id, user_id, service, title, share_token, forked_from, created_at, updated_at FROM conversations WHERE id = ?",
                (cid,),
            )
            row = await cursor.fetchone()
            if row:
                row_user_id = row["user_id"] if "user_id" in row.keys() else None
                # If conversation belongs to another user, create a new isolated conversation
                if user_id and row_user_id and row_user_id != user_id:
                    cid = str(uuid.uuid4())
                else:
                    messages = await self.get_messages(cid)
                    return Conversation(
                        id=row["id"],
                        user_id=row_user_id,
                        service=row["service"],
                        title=row["title"],
                        share_token=row["share_token"] if "share_token" in row.keys() else None,
                        forked_from=row["forked_from"] if "forked_from" in row.keys() else None,
                        created_at=datetime.fromisoformat(row["created_at"]),
                        updated_at=datetime.fromisoformat(row["updated_at"]),
                        messages=messages,
                    )

            # Insert new conversation
            await conn.execute(
                "INSERT INTO conversations (id, user_id, service, title, share_token, forked_from, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (cid, user_id, service, title, None, None, now, now),
            )
            await conn.commit()

            return Conversation(
                id=cid,
                user_id=user_id,
                service=service,
                title=title,
                share_token=None,
                forked_from=None,
                created_at=datetime.fromisoformat(now),
                updated_at=datetime.fromisoformat(now),
                messages=[],
            )

    async def get_conversation(
        self,
        conversation_id: str,
        user_id: Optional[str] = None,
    ) -> Optional[Conversation]:
        async with self.db.connection() as conn:
            cursor = await conn.execute(
                "SELECT id, user_id, service, title, share_token, forked_from, created_at, updated_at FROM conversations WHERE id = ?",
                (conversation_id,),
            )
            row = await cursor.fetchone()
            if not row:
                return None

            row_user_id = row["user_id"] if "user_id" in row.keys() else None
            # Enforce user isolation: reject access if conversation belongs to another user
            if user_id and row_user_id and row_user_id != user_id:
                return None

            messages = await self.get_messages(conversation_id)
            return Conversation(
                id=row["id"],
                user_id=row_user_id,
                service=row["service"],
                title=row["title"],
                share_token=row["share_token"] if "share_token" in row.keys() else None,
                forked_from=row["forked_from"] if "forked_from" in row.keys() else None,
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
                messages=messages,
            )

    async def add_message(self, conversation_id: str, message: Message) -> Message:
        now = datetime.now(timezone.utc).isoformat()
        sources_json = json.dumps([s.to_dict() for s in message.sources])

        async with self.db.connection() as conn:
            # Ensure conversation exists
            cursor = await conn.execute(
                "SELECT id FROM conversations WHERE id = ?", (conversation_id,)
            )
            if not await cursor.fetchone():
                await conn.execute(
                    "INSERT INTO conversations (id, service, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                    (conversation_id, "income-assessment-service", None, now, now),
                )

            await conn.execute(
                """
                INSERT INTO messages (id, conversation_id, role, content, sources_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    message.id,
                    conversation_id,
                    message.role.value if isinstance(message.role, MessageRole) else str(message.role),
                    message.content,
                    sources_json,
                    message.created_at.isoformat(),
                ),
            )
            await conn.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (now, conversation_id),
            )
            await conn.commit()

        message.conversation_id = conversation_id
        return message

    async def get_messages(self, conversation_id: str, limit: int = 50) -> List[Message]:
        async with self.db.connection() as conn:
            cursor = await conn.execute(
                """
                SELECT id, conversation_id, role, content, sources_json, created_at
                FROM messages
                WHERE conversation_id = ?
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (conversation_id, limit),
            )
            rows = await cursor.fetchall()
            messages = []
            for row in rows:
                raw_sources = json.loads(row["sources_json"]) if row["sources_json"] else []
                sources = [SourceCitation.from_dict(s) for s in raw_sources]
                messages.append(
                    Message(
                        id=row["id"],
                        conversation_id=row["conversation_id"],
                        role=MessageRole(row["role"]),
                        content=row["content"],
                        sources=sources,
                        created_at=datetime.fromisoformat(row["created_at"]),
                    )
                )
            return messages

    async def list_conversations(
        self,
        service: Optional[str] = None,
        limit: int = 20,
        user_id: Optional[str] = None,
    ) -> List[Conversation]:
        async with self.db.connection() as conn:
            query_parts = ["SELECT id, user_id, service, title, share_token, forked_from, created_at, updated_at FROM conversations"]
            where_clauses = []
            params = []

            if user_id is not None:
                where_clauses.append("user_id = ?")
                params.append(user_id)

            if service:
                where_clauses.append("service = ?")
                params.append(service)

            if where_clauses:
                query_parts.append("WHERE " + " AND ".join(where_clauses))

            query_parts.append("ORDER BY updated_at DESC LIMIT ?")
            params.append(limit)

            sql = " ".join(query_parts)
            cursor = await conn.execute(sql, tuple(params))
            rows = await cursor.fetchall()
            conversations = []
            for row in rows:
                conversations.append(
                    Conversation(
                        id=row["id"],
                        user_id=row["user_id"] if "user_id" in row.keys() else None,
                        service=row["service"],
                        title=row["title"],
                        share_token=row["share_token"] if "share_token" in row.keys() else None,
                        forked_from=row["forked_from"] if "forked_from" in row.keys() else None,
                        created_at=datetime.fromisoformat(row["created_at"]),
                        updated_at=datetime.fromisoformat(row["updated_at"]),
                    )
                )
            return conversations

    async def generate_share_token(self, conversation_id: str, user_id: str) -> str:
        """Generate or retrieve a unique share_token for a conversation owned by user_id."""
        async with self.db.connection() as conn:
            cursor = await conn.execute(
                "SELECT id, user_id, share_token FROM conversations WHERE id = ?",
                (conversation_id,),
            )
            row = await cursor.fetchone()
            if not row:
                raise EntityNotFoundException("Conversation", conversation_id)
            if row["user_id"] != user_id:
                raise ForbiddenException("Only the conversation owner can generate a share link.")

            existing_token = row["share_token"] if "share_token" in row.keys() else None
            if existing_token:
                return existing_token

            new_token = str(uuid.uuid4())
            await conn.execute(
                "UPDATE conversations SET share_token = ? WHERE id = ?",
                (new_token, conversation_id),
            )
            await conn.commit()
            return new_token

    async def get_conversation_by_share_token(self, share_token: str) -> Optional[Conversation]:
        """Retrieve conversation and full message history by share_token."""
        async with self.db.connection() as conn:
            cursor = await conn.execute(
                "SELECT id, user_id, service, title, share_token, forked_from, created_at, updated_at FROM conversations WHERE share_token = ?",
                (share_token,),
            )
            row = await cursor.fetchone()
            if not row:
                return None

            messages = await self.get_messages(row["id"])
            return Conversation(
                id=row["id"],
                user_id=row["user_id"] if "user_id" in row.keys() else None,
                service=row["service"],
                title=row["title"],
                share_token=row["share_token"] if "share_token" in row.keys() else None,
                forked_from=row["forked_from"] if "forked_from" in row.keys() else None,
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
                messages=messages,
            )

    async def fork_conversation(
        self,
        source_conversation_id: str,
        new_user_id: str,
    ) -> Conversation:
        """Clone all previous messages from source conversation into a new conversation for new_user_id."""
        async with self.db.connection() as conn:
            # 1. Fetch source conversation metadata
            cursor = await conn.execute(
                "SELECT id, service, title FROM conversations WHERE id = ?",
                (source_conversation_id,),
            )
            source_row = await cursor.fetchone()
            if not source_row:
                raise EntityNotFoundException("Source Conversation", source_conversation_id)

            service = source_row["service"]
            title = source_row["title"]
            new_cid = str(uuid.uuid4())
            now = datetime.now(timezone.utc).isoformat()

            # 2. Insert new forked conversation
            await conn.execute(
                "INSERT INTO conversations (id, user_id, service, title, share_token, forked_from, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (new_cid, new_user_id, service, title, None, source_conversation_id, now, now),
            )

            # 3. Retrieve source messages
            source_messages = await self.get_messages(source_conversation_id)

            # 4. Clone messages into new conversation with new IDs and original content/citations
            cloned_messages: List[Message] = []
            for sm in source_messages:
                new_mid = str(uuid.uuid4())
                sources_json = json.dumps([s.to_dict() for s in sm.sources])
                await conn.execute(
                    """
                    INSERT INTO messages (id, conversation_id, role, content, sources_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        new_mid,
                        new_cid,
                        sm.role.value if isinstance(sm.role, MessageRole) else str(sm.role),
                        sm.content,
                        sources_json,
                        sm.created_at.isoformat(),
                    ),
                )
                cloned_messages.append(
                    Message(
                        id=new_mid,
                        conversation_id=new_cid,
                        role=sm.role,
                        content=sm.content,
                        sources=sm.sources,
                        created_at=sm.created_at,
                    )
                )

            await conn.commit()

            return Conversation(
                id=new_cid,
                user_id=new_user_id,
                service=service,
                title=title,
                share_token=None,
                forked_from=source_conversation_id,
                created_at=datetime.fromisoformat(now),
                updated_at=datetime.fromisoformat(now),
                messages=cloned_messages,
            )


