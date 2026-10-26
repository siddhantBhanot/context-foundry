from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass
class SourceCitation:
    file: str
    service: Optional[str] = None
    class_name: Optional[str] = None
    endpoint: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    doc_type: Optional[str] = None
    snippet: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file": self.file,
            "service": self.service,
            "class_name": self.class_name,
            "endpoint": self.endpoint,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "doc_type": self.doc_type,
            "snippet": self.snippet,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SourceCitation":
        return cls(
            file=data.get("file", ""),
            service=data.get("service"),
            class_name=data.get("class_name"),
            endpoint=data.get("endpoint"),
            start_line=data.get("start_line"),
            end_line=data.get("end_line"),
            doc_type=data.get("doc_type"),
            snippet=data.get("snippet"),
        )


@dataclass
class Message:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    conversation_id: str = ""
    role: MessageRole = MessageRole.USER
    content: str = ""
    sources: List[SourceCitation] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "role": self.role.value if isinstance(self.role, MessageRole) else str(self.role),
            "content": self.content,
            "sources": [s.to_dict() for s in self.sources],
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class Conversation:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    service: str = "income-assessment-service"
    title: Optional[str] = None
    share_token: Optional[str] = None
    forked_from: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    messages: List[Message] = field(default_factory=list)


