from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from backend_service.app.domain.models.conversation import SourceCitation


@dataclass
class CourseEnrollment:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    course_id: str = ""
    current_lesson_index: int = 0
    completed_lessons: List[str] = field(default_factory=list)
    overall_progress: int = 0
    is_completed: bool = False
    knowledge_check_results: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "course_id": self.course_id,
            "current_lesson_index": self.current_lesson_index,
            "completed_lessons": self.completed_lessons,
            "overall_progress": self.overall_progress,
            "is_completed": self.is_completed,
            "knowledge_check_results": self.knowledge_check_results,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class CachedLesson:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    course_id: str = ""
    lesson_id: str = ""
    model: str = "default"
    content: str = ""
    sources: List[SourceCitation] = field(default_factory=list)
    takeaways: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class LessonDoubt:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    course_id: str = ""
    lesson_id: str = ""
    question: str = ""
    answer: str = ""
    sources: List[SourceCitation] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "course_id": self.course_id,
            "lesson_id": self.lesson_id,
            "question": self.question,
            "answer": self.answer,
            "sources": [s.to_dict() for s in self.sources],
            "created_at": self.created_at.isoformat(),
        }
