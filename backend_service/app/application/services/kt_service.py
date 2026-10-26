from datetime import datetime, timezone
import json
import logging
import re
import time
from typing import Any, AsyncIterator, Dict, List, Optional
import uuid

from backend_service.app.domain.exceptions.base import EntityNotFoundException, ValidationException
from backend_service.app.domain.interfaces.kt_repo import IKTRepository
from backend_service.app.domain.interfaces.rag_client import RAGClientProtocol
from backend_service.app.domain.models.conversation import SourceCitation
from backend_service.app.domain.models.knowledge import DocumentView
from backend_service.app.domain.models.kt import CachedLesson, CourseEnrollment, LessonDoubt

logger = logging.getLogger("backend_service.application.kt_service")


class KTService:
    """
    Application service managing Knowledge Cafe business operations:
    Course catalog, enrollments, progressive lesson synthesis, in-lesson doubts,
    knowledge checks, and course document viewing.
    """

    def __init__(self, kt_repo: IKTRepository, rag_client: RAGClientProtocol):
        self.kt_repo = kt_repo
        self.rag_client = rag_client

    async def list_courses(self, user_id: Optional[str] = None, group: Optional[str] = None) -> List[Dict[str, Any]]:
        courses = await self.rag_client.list_courses(group=group)
        user_enrollments: Dict[str, CourseEnrollment] = {}
        if user_id:
            enrollments = await self.kt_repo.list_user_enrollments(user_id)
            user_enrollments = {e.course_id: e for e in enrollments}

        result = []
        for c in courses:
            c_copy = dict(c)
            enrolled = user_enrollments.get(c["id"])
            if enrolled:
                c_copy["enrollment"] = enrolled.to_dict()
            else:
                c_copy["enrollment"] = None
            result.append(c_copy)
        return result

    async def get_course(self, course_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        course = await self.rag_client.get_course_detail(course_id)
        if not course:
            raise EntityNotFoundException(entity_name="Course", entity_id=course_id)

        enrolled = await self.kt_repo.get_enrollment(user_id, course_id) if user_id else None
        course_dict = dict(course)
        course_dict["enrollment"] = enrolled.to_dict() if enrolled else None

        # Annotate lesson statuses based on enrollment
        completed_set = set(enrolled.completed_lessons) if enrolled else set()
        current_idx = enrolled.current_lesson_index if enrolled else 0

        annotated_lessons = []
        for idx, lesson in enumerate(course.get("lessons", [])):
            l_copy = dict(lesson)
            if l_copy["id"] in completed_set:
                l_copy["status"] = "completed"
            elif idx == current_idx:
                l_copy["status"] = "current"
            elif idx < current_idx:
                l_copy["status"] = "completed"
            else:
                l_copy["status"] = "upcoming"
            annotated_lessons.append(l_copy)

        course_dict["lessons"] = annotated_lessons
        return course_dict

    async def enroll_or_resume(self, course_id: str, user_id: str) -> Dict[str, Any]:
        course = await self.rag_client.get_course_detail(course_id)
        if not course:
            raise EntityNotFoundException(entity_name="Course", entity_id=course_id)

        enrollment = await self.kt_repo.get_enrollment(user_id, course_id)
        if not enrollment:
            enrollment = CourseEnrollment(
                user_id=user_id,
                course_id=course_id,
                current_lesson_index=0,
                completed_lessons=[],
                overall_progress=0,
                is_completed=False,
            )
            enrollment = await self.kt_repo.save_enrollment(enrollment)

        lessons = course.get("lessons", [])
        current_lesson = lessons[enrollment.current_lesson_index] if enrollment.current_lesson_index < len(lessons) else (lessons[0] if lessons else None)

        return {
            "enrollment": enrollment.to_dict(),
            "course": course,
            "current_lesson": current_lesson,
        }
    async def restart_course(self, course_id: str, user_id: str) -> Dict[str, Any]:
        """
        Restart a course for a user back to Lesson 1 with 0% progress and cleared checks.
        """
        course = await self.rag_client.get_course_detail(course_id)
        if not course:
            raise EntityNotFoundException(entity_name="Course", entity_id=course_id)

        enrollment = CourseEnrollment(
            user_id=user_id,
            course_id=course_id,
            current_lesson_index=0,
            completed_lessons=[],
            overall_progress=0,
            is_completed=False,
            knowledge_check_results={},
        )
        saved = await self.kt_repo.save_enrollment(enrollment)
        await self.kt_repo.reset_doubts(user_id=user_id, course_id=course_id)

        lessons = course.get("lessons", [])
        return {
            "status": "success",
            "message": f"Course '{course.get('title')}' restarted successfully.",
            "enrollment": saved.to_dict(),
            "course": course,
            "current_lesson": lessons[0] if lessons else None,
        }
    async def get_lesson_content(
        self,
        course_id: str,
        lesson_id: str,
        user_id: str,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        course = await self.rag_client.get_course_detail(course_id)
        if not course:
            raise EntityNotFoundException(entity_name="Course", entity_id=course_id)

        lesson = None
        for l in course.get("lessons", []):
            if l["id"] == lesson_id:
                lesson = l
                break

        if not lesson:
            raise EntityNotFoundException(entity_name="Lesson", entity_id=lesson_id)

        effective_model = model or "default"

        # 1. Check database cache
        cached = await self.kt_repo.get_cached_lesson(course_id, lesson_id, effective_model)
        if cached:
            content = cached.content
            sources = [s.to_dict() for s in cached.sources]
            takeaways = cached.takeaways
        else:
            # 2. Synthesize using dedicated course context files
            # Build previous lesson summary for progressive learning
            prev_lessons = [l for l in course.get("lessons", []) if l["lesson_index"] < lesson["lesson_index"]]
            if prev_lessons:
                prev_summary = "Earlier lessons covered: " + "; ".join(
                    [f"Lesson {pl['lesson_index']+1} ({pl['title']}): {pl['summary']}" for pl in prev_lessons[-3:]]
                )
            else:
                prev_summary = "This is the first lesson of the course."

            synth_res = await self.rag_client.synthesize_lesson(
                course_id=course_id,
                lesson_id=lesson_id,
                previous_summary=prev_summary,
                model=model,
            )
            content = synth_res["content"]
            sources = synth_res.get("sources", [])
            takeaways = synth_res.get("takeaways", [])

            # Save to cache
            new_cache = CachedLesson(
                course_id=course_id,
                lesson_id=lesson_id,
                model=effective_model,
                content=content,
                sources=[SourceCitation.from_dict(s) for s in sources],
                takeaways=takeaways,
            )
            await self.kt_repo.save_cached_lesson(new_cache)

        # 3. Retrieve in-lesson doubts asked by user
        doubts = await self.kt_repo.list_lesson_doubts(course_id, lesson_id, user_id=user_id)

        # 4. Check user enrollment status for this lesson
        enrollment = await self.kt_repo.get_enrollment(user_id, course_id)
        is_completed = lesson_id in (enrollment.completed_lessons if enrollment else [])

        return {
            "course_id": course_id,
            "lesson_id": lesson_id,
            "lesson_index": lesson["lesson_index"],
            "title": lesson["title"],
            "summary": lesson["summary"],
            "content": content,
            "takeaways": takeaways,
            "sources": sources,
            "knowledge_check": lesson.get("knowledge_check"),
            "knowledge_checks": lesson.get("knowledge_checks") or ([lesson.get("knowledge_check")] if lesson.get("knowledge_check") else []),
            "doubts": [d.to_dict() for d in doubts],
            "is_completed": is_completed,
            "model": effective_model,
        }

    async def get_lesson_content_stream(
        self,
        course_id: str,
        lesson_id: str,
        user_id: str,
        model: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """
        Stream progressive lesson synthesis tokens in real-time.
        If the lesson is already cached, emits cached content directly.
        """
        course = await self.rag_client.get_course_detail(course_id)
        if not course:
            raise EntityNotFoundException(entity_name="Course", entity_id=course_id)

        lesson = None
        for l in course.get("lessons", []):
            if l["id"] == lesson_id:
                lesson = l
                break

        if not lesson:
            raise EntityNotFoundException(entity_name="Lesson", entity_id=lesson_id)

        effective_model = model or "default"
        cached = await self.kt_repo.get_cached_lesson(course_id, lesson_id, effective_model)

        doubts = await self.kt_repo.list_lesson_doubts(course_id, lesson_id, user_id=user_id)
        enrollment = await self.kt_repo.get_enrollment(user_id, course_id)
        is_completed = lesson_id in (enrollment.completed_lessons if enrollment else [])

        if cached:
            # Already synthesized & cached in SQLite
            meta_payload = {
                "type": "metadata",
                "course_id": course_id,
                "lesson_id": lesson_id,
                "lesson_index": lesson["lesson_index"],
                "title": lesson["title"],
                "summary": lesson["summary"],
                "takeaways": cached.takeaways,
                "sources": [s.to_dict() for s in cached.sources],
                "knowledge_check": lesson.get("knowledge_check"),
                "knowledge_checks": lesson.get("knowledge_checks") or ([lesson.get("knowledge_check")] if lesson.get("knowledge_check") else []),
                "doubts": [d.to_dict() for d in doubts],
                "is_completed": is_completed,
                "model": effective_model,
                "is_cached": True,
            }
            yield f"data: {json.dumps(meta_payload)}\n\n"
            yield f"data: {json.dumps({'type': 'chunk', 'text': cached.content})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'takeaways': cached.takeaways, 'clean_content': cached.content, 'latency_ms': 0, 'complete': True})}\n\n"
            return

        # Not cached yet: synthesize with live token streaming
        start_time = time.perf_counter()
        prev_lessons = [l for l in course.get("lessons", []) if l["lesson_index"] < lesson["lesson_index"]]
        if prev_lessons:
            prev_summary = "Earlier lessons covered: " + "; ".join(
                [f"Lesson {pl['lesson_index']+1} ({pl['title']}): {pl['summary']}" for pl in prev_lessons[-3:]]
            )
        else:
            prev_summary = "This is the first lesson of the course."

        try:
            stream_iter, sources, meta = await self.rag_client.stream_synthesize_lesson(
                course_id=course_id,
                lesson_id=lesson_id,
                previous_summary=prev_summary,
                model=model,
            )

            meta_payload = {
                "type": "metadata",
                "course_id": course_id,
                "lesson_id": lesson_id,
                "lesson_index": lesson["lesson_index"],
                "title": lesson["title"],
                "summary": lesson["summary"],
                "sources": [s.to_dict() for s in sources],
                "knowledge_check": lesson.get("knowledge_check"),
                "knowledge_checks": lesson.get("knowledge_checks") or ([lesson.get("knowledge_check")] if lesson.get("knowledge_check") else []),
                "doubts": [d.to_dict() for d in doubts],
                "is_completed": is_completed,
                "model": effective_model,
                "is_cached": False,
            }
            yield f"data: {json.dumps(meta_payload)}\n\n"

            raw_chunks = []
            async for chunk in stream_iter:
                if chunk:
                    raw_chunks.append(chunk)
                    yield f"data: {json.dumps({'type': 'chunk', 'text': chunk})}\n\n"

            raw_content = "".join(raw_chunks)
            latency_ms = (time.perf_counter() - start_time) * 1000

            # Parse takeaways block
            clean_content = raw_content
            takeaways = []
            takeaway_match = re.search(r"```takeaways\s*([\s\S]*?)\s*```", raw_content, re.IGNORECASE)
            if takeaway_match:
                lines = takeaway_match.group(1).strip().splitlines()
                for line in lines:
                    clean_line = line.strip().lstrip("-*•").strip()
                    if clean_line:
                        takeaways.append(clean_line)
                clean_content = raw_content[:takeaway_match.start()].rstrip() + "\n\n" + raw_content[takeaway_match.end():].lstrip()

            if not takeaways:
                takeaways = [
                    f"Mastered core principles of {lesson['title']}",
                    f"Understood integration points and domain boundaries",
                    f"Reviewed verified implementation patterns and error-handling paths",
                ]

            # Save synthesized lesson to SQLite cache
            new_cache = CachedLesson(
                course_id=course_id,
                lesson_id=lesson_id,
                model=effective_model,
                content=clean_content.strip(),
                sources=sources,
                takeaways=takeaways,
            )
            await self.kt_repo.save_cached_lesson(new_cache)

            done_payload = {
                "type": "done",
                "takeaways": takeaways,
                "clean_content": clean_content.strip(),
                "latency_ms": round(latency_ms, 2),
                "complete": True,
            }
            yield f"data: {json.dumps(done_payload)}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"


    async def complete_lesson(
        self,
        course_id: str,
        lesson_id: str,
        user_id: str,
    ) -> Dict[str, Any]:
        course = await self.rag_client.get_course_detail(course_id)
        if not course:
            raise EntityNotFoundException(entity_name="Course", entity_id=course_id)

        enrollment = await self.kt_repo.get_enrollment(user_id, course_id)
        if not enrollment:
            enrollment = CourseEnrollment(
                user_id=user_id,
                course_id=course_id,
                current_lesson_index=0,
                completed_lessons=[],
                overall_progress=0,
                is_completed=False,
            )

        lessons = course.get("lessons", [])
        total_lessons = len(lessons) if lessons else 1

        if lesson_id not in enrollment.completed_lessons:
            enrollment.completed_lessons.append(lesson_id)

        # Calculate overall progress percentage
        enrollment.overall_progress = min(100, int((len(enrollment.completed_lessons) / total_lessons) * 100))
        enrollment.is_completed = len(enrollment.completed_lessons) >= total_lessons

        # Find next lesson in creator sequence
        current_lesson_idx = 0
        for idx, l in enumerate(lessons):
            if l["id"] == lesson_id:
                current_lesson_idx = idx
                break

        next_lesson = None
        if current_lesson_idx + 1 < len(lessons):
            next_lesson = lessons[current_lesson_idx + 1]
            enrollment.current_lesson_index = current_lesson_idx + 1

        updated_enrollment = await self.kt_repo.save_enrollment(enrollment)

        return {
            "enrollment": updated_enrollment.to_dict(),
            "completed_lesson_id": lesson_id,
            "next_lesson": next_lesson,
            "is_course_completed": enrollment.is_completed,
        }

    async def ask_doubt(
        self,
        course_id: str,
        lesson_id: str,
        question: str,
        user_id: str,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not question or not question.strip():
            raise ValidationException("Question text cannot be empty.")

        # Optional: fetch lesson cached content snippet to inject
        cached = await self.kt_repo.get_cached_lesson(course_id, lesson_id, model or "default")
        snippet = cached.content[:1500] if cached else ""

        ans_res = await self.rag_client.answer_doubt(
            course_id=course_id,
            lesson_id=lesson_id,
            question=question.strip(),
            lesson_content_snippet=snippet,
            model=model,
        )

        sources = [SourceCitation.from_dict(s) for s in ans_res.get("sources", [])]
        doubt = LessonDoubt(
            user_id=user_id,
            course_id=course_id,
            lesson_id=lesson_id,
            question=question.strip(),
            answer=ans_res["answer"],
            sources=sources,
        )
        saved_doubt = await self.kt_repo.add_doubt(doubt)
        return saved_doubt.to_dict()

    async def ask_doubt_stream(
        self,
        course_id: str,
        lesson_id: str,
        question: str,
        user_id: str,
        model: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """
        Stream tokens for in-lesson doubt answering in real-time.
        Yields standard SSE events and persists the completed doubt to SQLite.
        """
        if not question or not question.strip():
            raise ValidationException("Question text cannot be empty.")

        cached = await self.kt_repo.get_cached_lesson(course_id, lesson_id, model or "default")
        snippet = cached.content[:1500] if cached else ""

        start_time = time.perf_counter()
        try:
            stream_iter, sources, meta = await self.rag_client.stream_answer_doubt(
                course_id=course_id,
                lesson_id=lesson_id,
                question=question.strip(),
                lesson_content_snippet=snippet,
                model=model,
            )

            doubt_id = str(uuid.uuid4())
            # 1. Emit metadata
            meta_payload = {
                "type": "metadata",
                "doubt_id": doubt_id,
                "sources": [s.to_dict() for s in sources],
                "model": meta.get("model", model or "default"),
            }
            yield f"data: {json.dumps(meta_payload)}\n\n"

            # 2. Stream chunks
            full_chunks = []
            async for chunk in stream_iter:
                if chunk:
                    full_chunks.append(chunk)
                    yield f"data: {json.dumps({'type': 'chunk', 'text': chunk})}\n\n"

            # 3. Persist completed doubt
            full_answer = "".join(full_chunks)
            latency_ms = (time.perf_counter() - start_time) * 1000

            doubt = LessonDoubt(
                id=doubt_id,
                user_id=user_id,
                course_id=course_id,
                lesson_id=lesson_id,
                question=question.strip(),
                answer=full_answer.strip(),
                sources=sources,
            )
            saved_doubt = await self.kt_repo.add_doubt(doubt)

            # 4. Emit done
            done_payload = {
                "type": "done",
                "doubt": saved_doubt.to_dict(),
                "latency_ms": round(latency_ms, 2),
                "complete": True,
            }
            yield f"data: {json.dumps(done_payload)}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"


    async def submit_knowledge_check(
        self,
        course_id: str,
        lesson_id: str,
        user_id: str,
        selected_option_index: Optional[int] = None,
        question_index: int = 0,
        answers: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        course = await self.rag_client.get_course_detail(course_id)
        if not course:
            raise EntityNotFoundException(entity_name="Course", entity_id=course_id)

        lesson = None
        for l in course.get("lessons", []):
            if l["id"] == lesson_id:
                lesson = l
                break

        if not lesson:
            raise EntityNotFoundException(entity_name="Lesson", entity_id=lesson_id)

        kcs = lesson.get("knowledge_checks") or []
        if not kcs and lesson.get("knowledge_check"):
            kcs = [lesson.get("knowledge_check")]

        if not kcs:
            raise ValidationException(f"Lesson '{lesson_id}' does not have a knowledge check.")

        enrollment = await self.kt_repo.get_enrollment(user_id, course_id)

        # Batch submission across all questions
        if answers is not None and len(answers) > 0:
            results = []
            correct_count = 0
            for idx, ans in enumerate(answers):
                if idx < len(kcs):
                    target_kc = kcs[idx]
                    correct_idx = target_kc.get("correct_option_index", 0)
                    is_corr = (ans == correct_idx)
                    if is_corr:
                        correct_count += 1
                    results.append({
                        "question_index": idx,
                        "selected_option_index": ans,
                        "is_correct": is_corr,
                        "correct_option_index": correct_idx,
                        "explanation": target_kc.get("explanation", ""),
                    })

            all_correct = (correct_count == len(results))
            if enrollment:
                enrollment.knowledge_check_results[lesson_id] = {
                    "answers": answers,
                    "score": correct_count,
                    "total": len(results),
                    "is_correct": all_correct,
                    "submitted_at": datetime.now(timezone.utc).isoformat(),
                }
                await self.kt_repo.save_enrollment(enrollment)

            first_res = results[0] if results else {}
            return {
                "lesson_id": lesson_id,
                "is_correct": all_correct,
                "correct_option_index": first_res.get("correct_option_index", 0),
                "explanation": first_res.get("explanation", ""),
                "question_index": 0,
                "results": results,
                "score": correct_count,
                "total": len(results),
            }

        # Single question submission
        target_idx = question_index if (0 <= question_index < len(kcs)) else 0
        target_kc = kcs[target_idx]
        correct_idx = target_kc.get("correct_option_index", 0)
        sel_idx = selected_option_index if selected_option_index is not None else 0
        is_correct = (sel_idx == correct_idx)

        if enrollment:
            curr_res = enrollment.knowledge_check_results.get(lesson_id, {})
            if not isinstance(curr_res, dict):
                curr_res = {}
            curr_res[f"q_{target_idx}"] = {
                "selected_option_index": sel_idx,
                "is_correct": is_correct,
                "submitted_at": datetime.now(timezone.utc).isoformat(),
            }
            curr_res["selected_option_index"] = sel_idx
            curr_res["is_correct"] = is_correct
            enrollment.knowledge_check_results[lesson_id] = curr_res
            await self.kt_repo.save_enrollment(enrollment)

        return {
            "lesson_id": lesson_id,
            "is_correct": is_correct,
            "correct_option_index": correct_idx,
            "explanation": target_kc.get("explanation", ""),
            "question_index": target_idx,
            "results": [{
                "question_index": target_idx,
                "selected_option_index": sel_idx,
                "is_correct": is_correct,
                "correct_option_index": correct_idx,
                "explanation": target_kc.get("explanation", ""),
            }],
            "score": 1 if is_correct else 0,
            "total": 1,
        }

    async def get_course_document(self, course_id: str, file_path: str) -> DocumentView:
        return await self.rag_client.get_course_document(course_id=course_id, file_path=file_path)

    async def reset_progress(
        self,
        user_id: Optional[str] = None,
        course_id: Optional[str] = None,
        clear_doubts: bool = True,
        clear_cache: bool = False,
    ) -> Dict[str, Any]:
        """
        Reset course enrollments and progress for a specific user, specific course, or all users.
        """
        enrollments_reset = await self.kt_repo.reset_enrollments(user_id=user_id, course_id=course_id)
        doubts_reset = 0
        if clear_doubts:
            doubts_reset = await self.kt_repo.reset_doubts(user_id=user_id, course_id=course_id)
        cache_cleared = 0
        if clear_cache:
            cache_cleared = await self.kt_repo.clear_cached_lessons(course_id=course_id)

        logger.info(
            f"Reset Knowledge Cafe progress: user_id={user_id}, course_id={course_id}, "
            f"enrollments_cleared={enrollments_reset}, doubts_cleared={doubts_reset}, cache_cleared={cache_cleared}"
        )
        return {
            "status": "success",
            "message": "Knowledge Cafe progress reset successfully",
            "enrollments_cleared": enrollments_reset,
            "doubts_cleared": doubts_reset,
            "cache_cleared": cache_cleared,
            "user_id": user_id,
            "course_id": course_id,
        }

    async def clear_cached_lessons(self, course_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Purge cached lesson content so materials are re-synthesized afresh.
        """
        cleared = await self.kt_repo.clear_cached_lessons(course_id=course_id)
        logger.info(f"Purged cached lessons: course_id={course_id}, count={cleared}")
        return {
            "status": "success",
            "message": f"Purged {cleared} cached lesson(s). Lessons will now be generated afresh.",
            "lessons_purged": cleared,
            "course_id": course_id,
        }

