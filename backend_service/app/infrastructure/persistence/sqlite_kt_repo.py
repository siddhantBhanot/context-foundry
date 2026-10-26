from datetime import datetime, timezone
import json
from typing import List, Optional
import uuid

from backend_service.app.domain.interfaces.kt_repo import IKTRepository
from backend_service.app.domain.models.conversation import SourceCitation
from backend_service.app.domain.models.kt import CachedLesson, CourseEnrollment, LessonDoubt
from backend_service.app.infrastructure.persistence.database import Database, get_database


class SQLiteKTRepository(IKTRepository):
    """
    SQLite implementation for Knowledge Cafe progress, cached lessons, and doubts.
    """

    def __init__(self, db: Optional[Database] = None):
        self.db = db or get_database()

    async def get_enrollment(self, user_id: str, course_id: str) -> Optional[CourseEnrollment]:
        async with self.db.connection() as conn:
            cursor = await conn.execute(
                """
                SELECT id, user_id, course_id, current_lesson_index, completed_lessons_json,
                       overall_progress, is_completed, knowledge_check_results_json,
                       created_at, updated_at
                FROM kt_course_enrollments
                WHERE user_id = ? AND course_id = ?
                """,
                (user_id, course_id),
            )
            row = await cursor.fetchone()
            if not row:
                return None

            completed_lessons = json.loads(row["completed_lessons_json"]) if row["completed_lessons_json"] else []
            kc_results = json.loads(row["knowledge_check_results_json"]) if row["knowledge_check_results_json"] else {}

            return CourseEnrollment(
                id=row["id"],
                user_id=row["user_id"],
                course_id=row["course_id"],
                current_lesson_index=row["current_lesson_index"],
                completed_lessons=completed_lessons,
                overall_progress=row["overall_progress"],
                is_completed=bool(row["is_completed"]),
                knowledge_check_results=kc_results,
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )

    async def list_user_enrollments(self, user_id: str) -> List[CourseEnrollment]:
        async with self.db.connection() as conn:
            cursor = await conn.execute(
                """
                SELECT id, user_id, course_id, current_lesson_index, completed_lessons_json,
                       overall_progress, is_completed, knowledge_check_results_json,
                       created_at, updated_at
                FROM kt_course_enrollments
                WHERE user_id = ?
                ORDER BY updated_at DESC
                """,
                (user_id,),
            )
            rows = await cursor.fetchall()
            enrollments = []
            for row in rows:
                completed = json.loads(row["completed_lessons_json"]) if row["completed_lessons_json"] else []
                kc = json.loads(row["knowledge_check_results_json"]) if row["knowledge_check_results_json"] else {}
                enrollments.append(
                    CourseEnrollment(
                        id=row["id"],
                        user_id=row["user_id"],
                        course_id=row["course_id"],
                        current_lesson_index=row["current_lesson_index"],
                        completed_lessons=completed,
                        overall_progress=row["overall_progress"],
                        is_completed=bool(row["is_completed"]),
                        knowledge_check_results=kc,
                        created_at=datetime.fromisoformat(row["created_at"]),
                        updated_at=datetime.fromisoformat(row["updated_at"]),
                    )
                )
            return enrollments

    async def save_enrollment(self, enrollment: CourseEnrollment) -> CourseEnrollment:
        now_iso = datetime.now(timezone.utc).isoformat()
        if not enrollment.id:
            enrollment.id = str(uuid.uuid4())

        completed_json = json.dumps(enrollment.completed_lessons)
        kc_json = json.dumps(enrollment.knowledge_check_results)

        async with self.db.connection() as conn:
            await conn.execute(
                """
                INSERT INTO kt_course_enrollments (
                    id, user_id, course_id, current_lesson_index, completed_lessons_json,
                    overall_progress, is_completed, knowledge_check_results_json,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, course_id) DO UPDATE SET
                    current_lesson_index = excluded.current_lesson_index,
                    completed_lessons_json = excluded.completed_lessons_json,
                    overall_progress = excluded.overall_progress,
                    is_completed = excluded.is_completed,
                    knowledge_check_results_json = excluded.knowledge_check_results_json,
                    updated_at = excluded.updated_at
                """,
                (
                    enrollment.id,
                    enrollment.user_id,
                    enrollment.course_id,
                    enrollment.current_lesson_index,
                    completed_json,
                    enrollment.overall_progress,
                    1 if enrollment.is_completed else 0,
                    kc_json,
                    enrollment.created_at.isoformat(),
                    now_iso,
                ),
            )
            await conn.commit()
            enrollment.updated_at = datetime.fromisoformat(now_iso)
            return enrollment

    async def get_cached_lesson(
        self, course_id: str, lesson_id: str, model: str = "default"
    ) -> Optional[CachedLesson]:
        async with self.db.connection() as conn:
            cursor = await conn.execute(
                """
                SELECT id, course_id, lesson_id, model, content, sources_json, takeaways_json, created_at
                FROM kt_cached_lessons
                WHERE course_id = ? AND lesson_id = ? AND model = ?
                """,
                (course_id, lesson_id, model),
            )
            row = await cursor.fetchone()
            if not row:
                return None

            sources_raw = json.loads(row["sources_json"]) if row["sources_json"] else []
            sources = [SourceCitation.from_dict(s) for s in sources_raw]
            takeaways = json.loads(row["takeaways_json"]) if row["takeaways_json"] else []

            return CachedLesson(
                id=row["id"],
                course_id=row["course_id"],
                lesson_id=row["lesson_id"],
                model=row["model"],
                content=row["content"],
                sources=sources,
                takeaways=takeaways,
                created_at=datetime.fromisoformat(row["created_at"]),
            )

    async def save_cached_lesson(self, cached_lesson: CachedLesson) -> CachedLesson:
        now_iso = datetime.now(timezone.utc).isoformat()
        if not cached_lesson.id:
            cached_lesson.id = str(uuid.uuid4())

        sources_json = json.dumps([s.to_dict() for s in cached_lesson.sources])
        takeaways_json = json.dumps(cached_lesson.takeaways)

        async with self.db.connection() as conn:
            await conn.execute(
                """
                INSERT INTO kt_cached_lessons (
                    id, course_id, lesson_id, model, content, sources_json, takeaways_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(course_id, lesson_id, model) DO UPDATE SET
                    content = excluded.content,
                    sources_json = excluded.sources_json,
                    takeaways_json = excluded.takeaways_json
                """,
                (
                    cached_lesson.id,
                    cached_lesson.course_id,
                    cached_lesson.lesson_id,
                    cached_lesson.model,
                    cached_lesson.content,
                    sources_json,
                    takeaways_json,
                    now_iso,
                ),
            )
            await conn.commit()
            return cached_lesson

    async def add_doubt(self, doubt: LessonDoubt) -> LessonDoubt:
        now_iso = datetime.now(timezone.utc).isoformat()
        if not doubt.id:
            doubt.id = str(uuid.uuid4())

        sources_json = json.dumps([s.to_dict() for s in doubt.sources])

        async with self.db.connection() as conn:
            await conn.execute(
                """
                INSERT INTO kt_lesson_doubts (
                    id, user_id, course_id, lesson_id, question, answer, sources_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    doubt.id,
                    doubt.user_id,
                    doubt.course_id,
                    doubt.lesson_id,
                    doubt.question,
                    doubt.answer,
                    sources_json,
                    now_iso,
                ),
            )
            await conn.commit()
            doubt.created_at = datetime.fromisoformat(now_iso)
            return doubt

    async def list_lesson_doubts(
        self, course_id: str, lesson_id: str, user_id: Optional[str] = None
    ) -> List[LessonDoubt]:
        async with self.db.connection() as conn:
            if user_id:
                cursor = await conn.execute(
                    """
                    SELECT id, user_id, course_id, lesson_id, question, answer, sources_json, created_at
                    FROM kt_lesson_doubts
                    WHERE course_id = ? AND lesson_id = ? AND user_id = ?
                    ORDER BY created_at ASC
                    """,
                    (course_id, lesson_id, user_id),
                )
            else:
                cursor = await conn.execute(
                    """
                    SELECT id, user_id, course_id, lesson_id, question, answer, sources_json, created_at
                    FROM kt_lesson_doubts
                    WHERE course_id = ? AND lesson_id = ?
                    ORDER BY created_at ASC
                    """,
                    (course_id, lesson_id),
                )
            rows = await cursor.fetchall()
            doubts = []
            for row in rows:
                sources_raw = json.loads(row["sources_json"]) if row["sources_json"] else []
                sources = [SourceCitation.from_dict(s) for s in sources_raw]
                doubts.append(
                    LessonDoubt(
                        id=row["id"],
                        user_id=row["user_id"],
                        course_id=row["course_id"],
                        lesson_id=row["lesson_id"],
                        question=row["question"],
                        answer=row["answer"],
                        sources=sources,
                        created_at=datetime.fromisoformat(row["created_at"]),
                    )
                )
            return doubts

    async def reset_enrollments(
        self, user_id: Optional[str] = None, course_id: Optional[str] = None
    ) -> int:
        async with self.db.connection() as conn:
            if user_id and course_id:
                cursor = await conn.execute(
                    "DELETE FROM kt_course_enrollments WHERE user_id = ? AND course_id = ?",
                    (user_id, course_id),
                )
            elif user_id:
                cursor = await conn.execute(
                    "DELETE FROM kt_course_enrollments WHERE user_id = ?",
                    (user_id,),
                )
            elif course_id:
                cursor = await conn.execute(
                    "DELETE FROM kt_course_enrollments WHERE course_id = ?",
                    (course_id,),
                )
            else:
                cursor = await conn.execute("DELETE FROM kt_course_enrollments")
            await conn.commit()
            return cursor.rowcount

    async def reset_doubts(
        self, user_id: Optional[str] = None, course_id: Optional[str] = None
    ) -> int:
        async with self.db.connection() as conn:
            if user_id and course_id:
                cursor = await conn.execute(
                    "DELETE FROM kt_lesson_doubts WHERE user_id = ? AND course_id = ?",
                    (user_id, course_id),
                )
            elif user_id:
                cursor = await conn.execute(
                    "DELETE FROM kt_lesson_doubts WHERE user_id = ?",
                    (user_id,),
                )
            elif course_id:
                cursor = await conn.execute(
                    "DELETE FROM kt_lesson_doubts WHERE course_id = ?",
                    (course_id,),
                )
            else:
                cursor = await conn.execute("DELETE FROM kt_lesson_doubts")
            await conn.commit()
            return cursor.rowcount

    async def clear_cached_lessons(self, course_id: Optional[str] = None) -> int:
        async with self.db.connection() as conn:
            if course_id:
                cursor = await conn.execute(
                    "DELETE FROM kt_cached_lessons WHERE course_id = ?",
                    (course_id,),
                )
            else:
                cursor = await conn.execute("DELETE FROM kt_cached_lessons")
            await conn.commit()
            return cursor.rowcount
