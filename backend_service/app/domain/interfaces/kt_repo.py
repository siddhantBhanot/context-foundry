from typing import List, Optional, Protocol

from backend_service.app.domain.models.kt import CachedLesson, CourseEnrollment, LessonDoubt


class IKTRepository(Protocol):
    """Abstract repository protocol for Knowledge Cafe persistence."""

    async def get_enrollment(self, user_id: str, course_id: str) -> Optional[CourseEnrollment]:
        """Fetch active user enrollment for a course."""
        ...

    async def list_user_enrollments(self, user_id: str) -> List[CourseEnrollment]:
        """List all course enrollments for a user."""
        ...

    async def save_enrollment(self, enrollment: CourseEnrollment) -> CourseEnrollment:
        """Upsert course enrollment progress."""
        ...

    async def get_cached_lesson(
        self, course_id: str, lesson_id: str, model: str = "default"
    ) -> Optional[CachedLesson]:
        """Retrieve pre-synthesized lesson content from database cache."""
        ...

    async def save_cached_lesson(self, cached_lesson: CachedLesson) -> CachedLesson:
        """Cache synthesized lesson content."""
        ...

    async def add_doubt(self, doubt: LessonDoubt) -> LessonDoubt:
        """Save a new question/doubt answered during a lesson."""
        ...

    async def list_lesson_doubts(
        self, course_id: str, lesson_id: str, user_id: Optional[str] = None
    ) -> List[LessonDoubt]:
        """List questions/doubts for a lesson, optionally filtered by user."""
        ...

    async def reset_enrollments(
        self, user_id: Optional[str] = None, course_id: Optional[str] = None
    ) -> int:
        """Reset/delete enrollments for a user, a course, or all users if unconstrained."""
        ...

    async def reset_doubts(
        self, user_id: Optional[str] = None, course_id: Optional[str] = None
    ) -> int:
        """Reset/delete lesson doubts for a user, a course, or all users if unconstrained."""
        ...

    async def clear_cached_lessons(self, course_id: Optional[str] = None) -> int:
        """Clear cached lesson materials for a specific course or all courses."""
        ...
