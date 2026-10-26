import logging
import re
import time
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

from rag_service.domain.models import Message, MessageRole
from rag_service.domain.protocols import EmbeddingProvider, LLMProvider, VectorStore
from rag_service.knowledge_cafe.course_loader import (
    CourseDefinition,
    CourseLoader,
    LessonMetadata,
    get_course_loader,
)
from rag_service.prompts.loader import PromptLoader, get_prompt_loader

logger = logging.getLogger("rag_service.knowledge_cafe.engine")


class KTEngine:
    """
    Core engine for Knowledge Cafe e-learning sessions.
    Synthesizes guided lessons grounded strictly in creator-defined course context files.
    Answers in-lesson doubts with adaptive explanations.
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
        course_loader: Optional[CourseLoader] = None,
        prompt_loader: Optional[PromptLoader] = None,
        kt_vector_store: Optional[VectorStore] = None,
        embedding_provider: Optional[EmbeddingProvider] = None,
    ):
        self.llm_provider = llm_provider
        self.course_loader = course_loader or get_course_loader()
        self.prompt_loader = prompt_loader or get_prompt_loader()
        self.kt_vector_store = kt_vector_store
        self.embedding_provider = embedding_provider

    def list_courses(self, group: Optional[str] = None) -> List[Dict[str, Any]]:
        courses = self.course_loader.list_courses(group=group)
        return [c.to_summary_dict() for c in courses]

    def get_course_detail(self, course_id: str) -> Optional[Dict[str, Any]]:
        course = self.course_loader.get_course(course_id)
        if not course:
            return None
        return course.to_dict()

    def _build_lesson_context(
        self,
        course_id: str,
        lesson_id: str,
        lesson_summary: str,
        service: str,
        max_total_chars: int = 15000,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        file_contents = self.course_loader.read_lesson_context_files(course_id, lesson_id)
        if not file_contents:
            return f"Overview: {lesson_summary}", []

        total_chars = sum(len(c) for _, c in file_contents)
        context_blocks = []
        sources = []
        num_files = len(file_contents)

        for file_name, content in file_contents:
            if total_chars > max_total_chars:
                per_file_budget = max(3500, max_total_chars // num_files)
                if len(content) > per_file_budget:
                    trimmed = content[:per_file_budget] + "\n\n... [Remaining operational sections condensed for context window] ..."
                else:
                    trimmed = content
            else:
                trimmed = content

            context_blocks.append(f"=== File: {file_name} ===\n{trimmed}\n")
            sources.append({
                "file": file_name,
                "service": service,
                "doc_type": "course_context",
                "snippet": content[:200] + "..." if len(content) > 200 else content,
            })

        context_text = "\n---------------------\n".join(context_blocks)
        return context_text, sources

    async def synthesize_lesson(
        self,
        course_id: str,
        lesson_id: str,
        previous_summary: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Synthesizes a comprehensive, pedagogical lesson using ONLY the lesson's context files.
        """
        start_time = time.perf_counter()
        course = self.course_loader.get_course(course_id)
        if not course:
            raise ValueError(f"Course '{course_id}' not found.")

        lesson = None
        for l in course.lessons:
            if l.id == lesson_id:
                lesson = l
                break

        if not lesson:
            raise ValueError(f"Lesson '{lesson_id}' not found in course '{course_id}'.")

        # 1. Read dedicated context files for this lesson with safety token budget
        context_text, sources = self._build_lesson_context(
            course_id=course_id,
            lesson_id=lesson_id,
            lesson_summary=lesson.summary,
            service=course.target_service,
        )

        # 2. Render prompt
        prev_summary_text = previous_summary or "This is the first lesson of the course."
        prompt_content = self.prompt_loader.render(
            "kt_lesson_synthesis",
            course_title=course.title,
            domain=course.domain,
            target_service=course.target_service,
            lesson_number=lesson.lesson_index + 1,
            lesson_title=lesson.title,
            lesson_summary=lesson.summary,
            previous_context_summary=prev_summary_text,
            lesson_context=context_text,
        )

        messages = [Message(role=MessageRole.USER, content=prompt_content)]
        system_prompt = (
            f"You are an expert Principal Engineer delivering an authoritative, engaging Knowledge Transfer "
            f"masterclass on '{course.title}'. Teach with exceptional technical clarity, clean formatting, "
            f"and strict adherence to the provided course documentation. "
            f"Strict Grounding Rule: Never fabricate, extrapolate, or hallucinate sample scripts (such as Jenkinsfiles, Groovy scripts, or code), parameters, or steps that are not explicitly present in the provided context."
        )

        llm_response = await self.llm_provider.generate(
            messages=messages,
            system_prompt=system_prompt,
            temperature=0.0,
            model=model,
        )

        raw_content = llm_response.content
        latency_ms = int((time.perf_counter() - start_time) * 1000)

        # 3. Extract takeaways if present
        clean_content = raw_content
        takeaways = []
        takeaway_match = re.search(r"```takeaways\s*([\s\S]*?)\s*```", raw_content, re.IGNORECASE)
        if takeaway_match:
            lines = takeaway_match.group(1).strip().splitlines()
            for line in lines:
                clean_line = line.strip().lstrip("-*•").strip()
                if clean_line:
                    takeaways.append(clean_line)
            # Remove takeaways code block from main markdown to keep it clean
            clean_content = raw_content[:takeaway_match.start()].rstrip() + "\n\n" + raw_content[takeaway_match.end():].lstrip()

        # Fallback takeaways if model didn't format block
        if not takeaways:
            takeaways = [
                f"Mastered core principles of {lesson.title}",
                f"Understood integration points and domain boundaries for {course.target_service}",
                f"Reviewed verified implementation patterns and error-handling paths",
            ]

        return {
            "course_id": course_id,
            "lesson_id": lesson_id,
            "lesson_index": lesson.lesson_index,
            "title": lesson.title,
            "summary": lesson.summary,
            "content": clean_content.strip(),
            "takeaways": takeaways,
            "sources": sources,
            "latency_ms": latency_ms,
            "model": llm_response.model or model or "default",
        }

    async def _resolve_doubt_context(
        self,
        course: CourseDefinition,
        lesson: LessonMetadata,
        question: str,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Retrieve context for answering an in-lesson doubt.
        If Qdrant kt_vector_store is available, queries knowledge_cafe_collection
        strictly pre-filtered by course_id so only this course's material is retrieved.
        Also combines the active lesson's local context files for complete grounding.
        """
        context_blocks: List[str] = []
        sources: List[Dict[str, Any]] = []
        seen_files = set()

        # 1. Semantic search across the whole knowledge_cafe_collection filtered strictly by course_id
        if self.kt_vector_store and self.embedding_provider:
            try:
                query_vector = await self.embedding_provider.embed_query(question)
                matched_chunks = await self.kt_vector_store.search(
                    query_vector=query_vector,
                    limit=6,
                    filter_dict={"course_id": course.id},
                )
                for chunk in matched_chunks:
                    fn = chunk.metadata.extra.get("file_name") or chunk.metadata.file_path
                    lesson_title = chunk.metadata.extra.get("lesson_title", "")
                    label = f"Course Material: {fn}" + (f" ({lesson_title})" if lesson_title else "")
                    context_blocks.append(f"=== {label} ===\n{chunk.content}\n")
                    seen_files.add(fn)
                    sources.append({
                        "file": fn,
                        "service": course.id,
                        "doc_type": "course_context",
                        "snippet": chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content,
                    })
            except Exception as e:
                logger.warning(
                    f"Vector search in knowledge_cafe_collection failed, falling back to local files: {e}"
                )

        # 2. Fallback to local lesson context files only if vector DB search returned no results
        if not context_blocks:
            file_contents = self.course_loader.read_lesson_context_files(course.id, lesson.id)
            for file_name, content in file_contents:
                context_blocks.append(f"=== Lesson Context: {file_name} ===\n{content}\n")
                sources.append({
                    "file": file_name,
                    "service": course.id,
                    "doc_type": "course_context",
                    "snippet": content[:200] + "..." if len(content) > 200 else content,
                })

        context_text = "\n---------------------\n".join(context_blocks) if context_blocks else lesson.summary
        return context_text, sources

    async def answer_doubt(
        self,
        course_id: str,
        lesson_id: str,
        question: str,
        lesson_content_snippet: str = "",
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Answers an in-lesson developer doubt grounded strictly in the course's vetted context files.
        """
        start_time = time.perf_counter()
        course = self.course_loader.get_course(course_id)
        if not course:
            raise ValueError(f"Course '{course_id}' not found.")

        lesson = self.course_loader.get_lesson(course_id, lesson_id)
        if not lesson:
            raise ValueError(f"Lesson '{lesson_id}' not found.")

        context_text, sources = await self._resolve_doubt_context(course, lesson, question)

        prompt_content = self.prompt_loader.render(
            "kt_lesson_doubt",
            course_title=course.title,
            lesson_number=lesson.lesson_index + 1,
            lesson_title=lesson.title,
            lesson_context=context_text,
            lesson_content_snippet=lesson_content_snippet[:1500],
            question=question,
        )

        messages = [Message(role=MessageRole.USER, content=prompt_content)]
        system_prompt = (
            f"You are a Principal Engineer mentoring a developer during a Knowledge Transfer session for "
            f"'{course.title}'. Answer doubts strictly and concisely using ONLY the provided course documentation. "
            f"Strict Grounding: Never fabricate, extrapolate, or hallucinate sample scripts (such as Jenkinsfiles, Groovy scripts, or code), parameters, or steps that are not explicitly present in the provided context."
        )

        llm_response = await self.llm_provider.generate(
            messages=messages,
            system_prompt=system_prompt,
            temperature=0.0,
            model=model,
        )

        latency_ms = int((time.perf_counter() - start_time) * 1000)
        return {
            "answer": llm_response.content.strip(),
            "sources": sources,
            "latency_ms": latency_ms,
            "model": llm_response.model or model or "default",
        }

    async def stream_synthesize_lesson(
        self,
        course_id: str,
        lesson_id: str,
        previous_summary: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Tuple[AsyncIterator[str], List[Dict[str, Any]], Dict[str, Any]]:
        """
        Stream progressive lesson synthesis tokens in real-time.
        Returns (stream_iterator, sources, metadata).
        """
        course = self.course_loader.get_course(course_id)
        if not course:
            raise ValueError(f"Course '{course_id}' not found.")

        lesson = None
        for l in course.lessons:
            if l.id == lesson_id:
                lesson = l
                break

        if not lesson:
            raise ValueError(f"Lesson '{lesson_id}' not found in course '{course_id}'.")

        # 1. Read dedicated context files for this lesson with safety token budget
        context_text, sources = self._build_lesson_context(
            course_id=course_id,
            lesson_id=lesson_id,
            lesson_summary=lesson.summary,
            service=course.target_service,
        )

        # 2. Render prompt
        prev_summary_text = previous_summary or "This is the first lesson of the course."
        prompt_content = self.prompt_loader.render(
            "kt_lesson_synthesis",
            course_title=course.title,
            domain=course.domain,
            target_service=course.target_service,
            lesson_number=lesson.lesson_index + 1,
            lesson_title=lesson.title,
            lesson_summary=lesson.summary,
            previous_context_summary=prev_summary_text,
            lesson_context=context_text,
        )

        messages = [Message(role=MessageRole.USER, content=prompt_content)]
        system_prompt = (
            f"You are an expert Principal Engineer delivering an authoritative, engaging Knowledge Transfer "
            f"masterclass on '{course.title}'. Teach with exceptional technical clarity, clean formatting, "
            f"and strict adherence to the provided course documentation. "
            f"Strict Grounding Rule: Never fabricate, extrapolate, or hallucinate sample scripts (such as Jenkinsfiles, Groovy scripts, or code), parameters, or steps that are not explicitly present in the provided context."
        )

        stream_iter = self.llm_provider.stream(
            messages=messages,
            system_prompt=system_prompt,
            temperature=0.0,
            model=model,
        )

        meta = {
            "course_id": course_id,
            "lesson_id": lesson_id,
            "lesson_title": lesson.title,
            "summary": lesson.summary,
            "model": model or getattr(self.llm_provider, "model_id", "default"),
        }
        return stream_iter, sources, meta

    async def stream_answer_doubt(
        self,
        course_id: str,
        lesson_id: str,
        question: str,
        lesson_content_snippet: str = "",
        model: Optional[str] = None,
    ) -> Tuple[AsyncIterator[str], List[Dict[str, Any]], Dict[str, Any]]:
        """
        Stream tokens for in-lesson doubt answering in real-time.
        Returns (stream_iterator, sources, metadata).
        """
        course = self.course_loader.get_course(course_id)
        if not course:
            raise ValueError(f"Course '{course_id}' not found.")

        lesson = self.course_loader.get_lesson(course_id, lesson_id)
        if not lesson:
            raise ValueError(f"Lesson '{lesson_id}' not found.")

        context_text, sources = await self._resolve_doubt_context(course, lesson, question)

        prompt_content = self.prompt_loader.render(
            "kt_lesson_doubt",
            course_title=course.title,
            lesson_number=lesson.lesson_index + 1,
            lesson_title=lesson.title,
            lesson_context=context_text,
            lesson_content_snippet=lesson_content_snippet[:1500],
            question=question,
        )

        messages = [Message(role=MessageRole.USER, content=prompt_content)]
        system_prompt = (
            f"You are a Principal Engineer mentoring a developer during a Knowledge Transfer session for "
            f"'{course.title}'. Answer doubts strictly and concisely using ONLY the provided course documentation. "
            f"Strict Grounding: Never fabricate, extrapolate, or hallucinate sample scripts (such as Jenkinsfiles, Groovy scripts, or code), parameters, or steps that are not explicitly present in the provided context."
        )

        stream_iter = self.llm_provider.stream(
            messages=messages,
            system_prompt=system_prompt,
            temperature=0.0,
            model=model,
        )

        meta = {
            "course_id": course_id,
            "lesson_id": lesson_id,
            "model": model or getattr(self.llm_provider, "model_id", "default"),
        }
        return stream_iter, sources, meta

    def read_document(self, course_id: str, file_path: str) -> Tuple[str, str]:
        return self.course_loader.read_course_document(course_id, file_path)
