from dataclasses import dataclass, field
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple
import yaml


@dataclass
class KnowledgeCheckOption:
    text: str
    is_correct: bool = False


@dataclass
class KnowledgeCheck:
    question: str
    type: str = "multiple_choice"
    options: List[str] = field(default_factory=list)
    correct_option_index: int = 0
    explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "question": self.question,
            "type": self.type,
            "options": self.options,
            "correct_option_index": self.correct_option_index,
            "explanation": self.explanation,
        }


@dataclass
class LessonMetadata:
    id: str
    lesson_index: int
    title: str
    summary: str
    context_files: List[str] = field(default_factory=list)
    knowledge_check: Optional[KnowledgeCheck] = None
    knowledge_checks: List[KnowledgeCheck] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        primary_kc = self.knowledge_check or (self.knowledge_checks[0] if self.knowledge_checks else None)
        active_kcs = self.knowledge_checks[:3] if len(self.knowledge_checks) > 3 else self.knowledge_checks
        return {
            "id": self.id,
            "lesson_index": self.lesson_index,
            "title": self.title,
            "summary": self.summary,
            "context_files": self.context_files,
            "knowledge_check": primary_kc.to_dict() if primary_kc else None,
            "knowledge_checks": [kc.to_dict() for kc in active_kcs],
        }


@dataclass
class CourseDefinition:
    id: str
    title: str
    description: str
    target_service: str
    domain: str = "Engineering"
    target_audience: str = "All Engineers"
    difficulty: str = "Intermediate"
    estimated_duration: str = "1 hour"
    icon: str = "Layers"
    group: str = "technical"
    tags: List[str] = field(default_factory=list)
    lessons: List[LessonMetadata] = field(default_factory=list)
    course_dir: Optional[Path] = None

    def to_summary_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "target_service": self.target_service,
            "domain": self.domain,
            "target_audience": self.target_audience,
            "difficulty": self.difficulty,
            "estimated_duration": self.estimated_duration,
            "icon": self.icon,
            "group": self.group,
            "tags": self.tags,
            "total_lessons": len(self.lessons),
        }

    def to_dict(self) -> Dict[str, Any]:
        data = self.to_summary_dict()
        data["lessons"] = [l.to_dict() for l in self.lessons]
        return data


class CourseLoader:
    """
    Dynamically loads and validates Knowledge Cafe courses from course-structure.md files.
    Ensures strict course-specific context isolation and path traversal security.
    """

    def __init__(self, courses_dir: Optional[Path | str] = None):
        if courses_dir:
            self.courses_dir = Path(courses_dir).resolve()
        else:
            self.courses_dir = (Path(__file__).resolve().parent / "courses").resolve()

    def list_courses(self, group: Optional[str] = None) -> List[CourseDefinition]:
        courses: List[CourseDefinition] = []
        if not self.courses_dir.exists():
            return courses

        for item in sorted(self.courses_dir.iterdir()):
            if item.is_dir():
                structure_file = item / "course-structure.md"
                if structure_file.is_file():
                    try:
                        course = self._parse_course_structure(structure_file, item)
                        if course:
                            courses.append(course)
                    except Exception as e:
                        # Log and continue so one invalid course doesn't break catalog
                        pass
        if group:
            courses = [c for c in courses if c.group.lower() == group.lower()]
        return courses

    def get_course(self, course_id: str) -> Optional[CourseDefinition]:
        for course in self.list_courses():
            if course.id == course_id:
                return course
        return None

    def get_lesson(self, course_id: str, lesson_id: str) -> Optional[LessonMetadata]:
        course = self.get_course(course_id)
        if not course:
            return None
        for lesson in course.lessons:
            if lesson.id == lesson_id:
                return lesson
        return None

    def read_lesson_context_files(
        self, course_id: str, lesson_id: str
    ) -> List[Tuple[str, str]]:
        """
        Securely read all dedicated context files associated with a specific lesson.
        Returns list of tuples: (relative_file_path, file_content)
        """
        course = self.get_course(course_id)
        if not course or not course.course_dir:
            return []

        lesson = None
        for l in course.lessons:
            if l.id == lesson_id:
                lesson = l
                break

        if not lesson:
            return []

        results: List[Tuple[str, str]] = []
        for rel_path in lesson.context_files:
            clean_rel = rel_path.strip().lstrip("/\\")
            full_path = (course.course_dir / clean_rel).resolve()
            # Enforce path traversal security: must be strictly inside course directory
            if not full_path.is_relative_to(course.course_dir):
                continue
            if full_path.is_file():
                try:
                    content = full_path.read_text(encoding="utf-8", errors="replace")
                    results.append((full_path.name, content))
                except Exception:
                    pass
        return results

    def read_course_document(self, course_id: str, file_name_or_path: str) -> Tuple[str, str]:
        """
        Securely read a course context file by relative path or file name.
        Returns (file_name, content).
        Raises FileNotFoundError or PermissionError.
        """
        course = self.get_course(course_id)
        if not course or not course.course_dir:
            raise FileNotFoundError(f"Course '{course_id}' not found.")

        clean = file_name_or_path.strip().lstrip("/\\")
        candidate = (course.course_dir / clean).resolve()

        if not candidate.is_relative_to(course.course_dir):
            raise PermissionError("Path traversal detected outside course boundary.")

        if candidate.is_file():
            return candidate.name, candidate.read_text(encoding="utf-8", errors="replace")

        # Search recursively inside lessons folder by filename
        for f in course.course_dir.rglob("*.md"):
            if f.name == clean or f.name == Path(clean).name:
                if f.is_relative_to(course.course_dir):
                    return f.name, f.read_text(encoding="utf-8", errors="replace")

        raise FileNotFoundError(f"Context document '{file_name_or_path}' not found in course '{course_id}'.")

    def _parse_single_question_chunk(self, chunk: str) -> Optional[KnowledgeCheck]:
        """Parse an individual question and its options from a markdown chunk."""
        q_match = re.search(r"-\s*\*\*Question(?:\s*\d+)?\*\*:\s*(.+)", chunk)
        if not q_match:
            q_match = re.search(r"\*\*Question(?:\s*\d+)?\*\*:\s*(.+)", chunk)
        if not q_match:
            return None

        type_match = re.search(r"\*\*Type\*\*:\s*(.+)", chunk)
        exp_match = re.search(r"\*\*Explanation\*\*:\s*(.+)", chunk)

        options: List[str] = []
        correct_idx = 0

        opts_idx = chunk.find("**Options**:")
        if opts_idx != -1:
            opts_sub = chunk[opts_idx:].splitlines()[1:]
            for opt_line in opts_sub:
                s_line = opt_line.strip()
                if not s_line:
                    continue
                # Stop if encountering another bold metadata field like - **Explanation**: or next - **Question**:
                if re.match(r"^-\s*\*\*(?:Explanation|Question|Type)[A-Za-z0-9_ ]*\*\*:", s_line):
                    break
                if s_line.startswith("-") or s_line.startswith("*"):
                    item = s_line.lstrip("-*").strip()
                    if item.startswith("**"):
                        break
                    if item.startswith("[x]") or item.startswith("[X]"):
                        correct_idx = len(options)
                        item = item[3:].strip()
                    elif item.startswith("[ ]"):
                        item = item[3:].strip()
                    if item:
                        options.append(item)

        if q_match and options:
            return KnowledgeCheck(
                question=q_match.group(1).strip(),
                type=type_match.group(1).strip() if type_match else "multiple_choice",
                options=options,
                correct_option_index=correct_idx,
                explanation=exp_match.group(1).strip() if exp_match else "",
            )
        return None

    def _parse_knowledge_check_blocks(self, text: str) -> List[KnowledgeCheck]:
        """
        Parse all creator-defined Knowledge Check questions from markdown text.
        Supports:
        - Multiple `- **Knowledge Check**:` blocks
        - Single block with multiple `- **Question**:` or `- **Question 1**:` blocks
        - Dedicated `## Knowledge Check` section
        """
        if not text:
            return []

        results: List[KnowledgeCheck] = []

        # 1. Multiple "- **Knowledge Check**:" sections
        kc_sections = re.split(r"(?:^|\n)(?:-\s*)?\*\*(?:Knowledge Check|Quiz)\*\*:\s*\n", text)
        if len(kc_sections) > 1:
            for sec in kc_sections[1:]:
                q_splits = re.split(r"(?=(?:^|\n)\s*-\s*\*\*Question(?:\s*\d+)?\*\*:)", sec)
                for q_chunk in q_splits:
                    parsed = self._parse_single_question_chunk(q_chunk)
                    if parsed and parsed.question not in [r.question for r in results]:
                        results.append(parsed)
            if results:
                return results

        # 2. Check for "## Knowledge Check" heading
        heading_match = re.search(r"(?:^|\n)##+\s*(?:Knowledge Check|Quiz)\s*\n([\s\S]*?)(?=\n##|\Z)", text)
        if heading_match:
            body = heading_match.group(1)
            q_splits = re.split(r"(?=(?:^|\n)\s*-\s*\*\*Question(?:\s*\d+)?\*\*:)", body)
            for q_chunk in q_splits:
                parsed = self._parse_single_question_chunk(q_chunk)
                if parsed and parsed.question not in [r.question for r in results]:
                    results.append(parsed)
            if results:
                return results

        # 3. Fallback: search for any - **Question** blocks across the text
        q_splits = re.split(r"(?=(?:^|\n)\s*-\s*\*\*Question(?:\s*\d+)?\*\*:)", text)
        for q_chunk in q_splits:
            parsed = self._parse_single_question_chunk(q_chunk)
            if parsed and parsed.question not in [r.question for r in results]:
                results.append(parsed)

        return results

    def _parse_knowledge_check_block(self, text: str) -> Optional[KnowledgeCheck]:
        """Legacy helper returning the first parsed knowledge check."""
        checks = self._parse_knowledge_check_blocks(text)
        return checks[0] if checks else None

    def _parse_course_structure(self, file_path: Path, course_dir: Path) -> Optional[CourseDefinition]:
        text = file_path.read_text(encoding="utf-8", errors="replace")

        # 1. Parse YAML Frontmatter
        frontmatter_data: Dict[str, Any] = {}
        content_markdown = text

        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                try:
                    frontmatter_data = yaml.safe_load(parts[1]) or {}
                    content_markdown = parts[2]
                except Exception:
                    pass

        course_id = frontmatter_data.get("id") or course_dir.name
        title = frontmatter_data.get("title") or course_dir.name.replace("-", " ").title()
        description = frontmatter_data.get("description", "")
        target_service = frontmatter_data.get("target_service", "default-service")
        domain = frontmatter_data.get("domain", "Microservices & Engineering")
        target_audience = frontmatter_data.get("target_audience", "Engineers")
        difficulty = frontmatter_data.get("difficulty", "Intermediate")
        estimated_duration = frontmatter_data.get("estimated_duration", "1 hour")
        icon = frontmatter_data.get("icon", "Layers")
        tags = frontmatter_data.get("tags") or []
        
        group = frontmatter_data.get("group")
        if not group:
            domain_lower = domain.lower()
            if any(k in domain_lower for k in ["bank", "wealth", "credit", "lending", "nri", "compliance", "management"]):
                group = "banking"
            else:
                group = "technical"
        else:
            group = str(group).lower()

        # 2. Parse Lessons from Markdown Headings (## XX. Title or ## Title)
        lessons: List[LessonMetadata] = []
        sections = re.split(r"\n(?=##\s+)", content_markdown)

        lesson_idx = 0
        for sec in sections:
            sec = sec.strip()
            if not sec.startswith("##"):
                continue

            lines = sec.splitlines()
            header_line = lines[0].lstrip("#").strip()

            # Parse title and optional index number
            m = re.match(r"^(\d+)\.?\s*(.*)", header_line)
            if m:
                lesson_title = m.group(2).strip() or header_line
            else:
                lesson_title = header_line

            slug_id = re.sub(r"[^a-zA-Z0-9]+", "-", lesson_title.lower()).strip("-")
            formatted_id = f"{lesson_idx+1:02d}-{slug_id}"

            # Extract fields from body
            body = "\n".join(lines[1:])
            summary = ""
            context_files: List[str] = []
            knowledge_check: Optional[KnowledgeCheck] = None

            # Summary regex
            sum_match = re.search(r"-\s*\*\*Summary\*\*:\s*(.+)", body)
            if sum_match:
                summary = sum_match.group(1).strip()

            # Context files regex (stop before next top-level bullet like - **Knowledge Check**)
            context_match = re.search(r"-\s*\*\*Context\*\*:\s*\n((?:[ \t]+-\s+[^\n]+\n?)+)", body)
            if context_match:
                context_block = context_match.group(1)
                for c_line in context_block.splitlines():
                    c_line = c_line.strip()
                    if c_line.startswith("-"):
                        c_file = c_line.lstrip("-").strip().strip("`")
                        if c_file and not c_file.startswith("**"):
                            context_files.append(c_file)

            # Knowledge check:
            # 1. Parse directly from course-structure.md lesson body
            knowledge_checks = self._parse_knowledge_check_blocks(body)

            # 2. If not defined in course-structure.md, check for dedicated knowledge-check.md in lesson directory
            if not knowledge_checks and course_dir:
                lesson_folder_candidates = [
                    course_dir / "lessons" / formatted_id / "knowledge-check.md",
                    course_dir / "lessons" / formatted_id / "quiz.md",
                ]
                for cand in lesson_folder_candidates:
                    if cand.is_file():
                        cand_text = cand.read_text(encoding="utf-8", errors="replace")
                        knowledge_checks = self._parse_knowledge_check_blocks(cand_text)
                        if knowledge_checks:
                            break

                # 3. Check inside referenced context files for an embedded Knowledge Check
                if not knowledge_checks:
                    for cf in context_files:
                        cf_clean = cf.strip().lstrip("/\\")
                        cf_path = (course_dir / cf_clean).resolve()
                        if cf_path.is_file() and cf_path.is_relative_to(course_dir):
                            cf_text = cf_path.read_text(encoding="utf-8", errors="replace")
                            if "**Knowledge Check**" in cf_text or "## Knowledge Check" in cf_text:
                                knowledge_checks = self._parse_knowledge_check_blocks(cf_text)
                                if knowledge_checks:
                                    break

            primary_kc = knowledge_checks[0] if knowledge_checks else None

            lessons.append(
                LessonMetadata(
                    id=formatted_id,
                    lesson_index=lesson_idx,
                    title=lesson_title,
                    summary=summary,
                    context_files=context_files,
                    knowledge_check=primary_kc,
                    knowledge_checks=knowledge_checks,
                )
            )
            lesson_idx += 1

        return CourseDefinition(
            id=course_id,
            title=title,
            description=description,
            target_service=target_service,
            domain=domain,
            target_audience=target_audience,
            difficulty=difficulty,
            estimated_duration=estimated_duration,
            icon=icon,
            group=group,
            tags=tags,
            lessons=lessons,
            course_dir=course_dir,
        )


_course_loader: Optional[CourseLoader] = None


def get_course_loader() -> CourseLoader:
    global _course_loader
    if _course_loader is None:
        _course_loader = CourseLoader()
    return _course_loader
