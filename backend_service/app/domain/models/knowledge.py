from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
import uuid


class IngestionStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class IngestionJob:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    service: str = "income-assessment-service"
    source_path: str = ""
    status: IngestionStatus = IngestionStatus.PENDING
    total_files: int = 0
    total_chunks: int = 0
    files_indexed: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None


@dataclass
class DocumentView:
    file: str
    service: str
    content: str
    content_type: str = "text/markdown"
    total_lines: int = 0
    size_bytes: int = 0
