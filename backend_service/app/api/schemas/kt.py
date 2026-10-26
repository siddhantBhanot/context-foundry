from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend_service.app.api.schemas.query import SourceCitationSchema


class KnowledgeCheckSchema(BaseModel):
    question: str
    type: str = "multiple_choice"
    options: List[str]
    correct_option_index: Optional[int] = None
    explanation: Optional[str] = None


class LessonSummarySchema(BaseModel):
    id: str
    lesson_index: int
    title: str
    summary: str
    context_files: List[str] = Field(default_factory=list)
    status: Optional[str] = "upcoming"  # upcoming, current, completed
    knowledge_check: Optional[KnowledgeCheckSchema] = None
    knowledge_checks: Optional[List[KnowledgeCheckSchema]] = Field(default_factory=list)


class CourseEnrollmentSummary(BaseModel):
    id: str
    course_id: str
    current_lesson_index: int
    completed_lessons: List[str]
    overall_progress: int
    is_completed: bool
    knowledge_check_results: Optional[Dict[str, Any]] = None
    updated_at: str


class CourseSummaryResponse(BaseModel):
    id: str
    title: str
    description: str
    target_service: str
    domain: str
    target_audience: str
    difficulty: str
    estimated_duration: str
    icon: str = "Layers"
    group: str = "technical"
    tags: List[str] = Field(default_factory=list)
    total_lessons: int
    enrollment: Optional[CourseEnrollmentSummary] = None


class CourseDetailResponse(BaseModel):
    id: str
    title: str
    description: str
    target_service: str
    domain: str
    target_audience: str
    difficulty: str
    estimated_duration: str
    icon: str = "Layers"
    group: str = "technical"
    tags: List[str] = Field(default_factory=list)
    total_lessons: int
    enrollment: Optional[CourseEnrollmentSummary] = None
    lessons: List[LessonSummarySchema]


class LessonDetailResponse(BaseModel):
    course_id: str
    lesson_id: str
    lesson_index: int
    title: str
    summary: str
    content: str
    takeaways: List[str] = Field(default_factory=list)
    sources: List[SourceCitationSchema] = Field(default_factory=list)
    knowledge_check: Optional[KnowledgeCheckSchema] = None
    knowledge_checks: Optional[List[KnowledgeCheckSchema]] = Field(default_factory=list)
    doubts: List[Dict[str, Any]] = Field(default_factory=list)
    is_completed: bool = False
    model: str = "default"


class CompleteLessonResponse(BaseModel):
    enrollment: CourseEnrollmentSummary
    completed_lesson_id: str
    next_lesson: Optional[LessonSummarySchema] = None
    is_course_completed: bool


class DoubtRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=1000)
    model: Optional[str] = None


class DoubtResponse(BaseModel):
    id: str
    user_id: str
    course_id: str
    lesson_id: str
    question: str
    answer: str
    sources: List[SourceCitationSchema] = Field(default_factory=list)
    created_at: str


class KnowledgeCheckSubmitRequest(BaseModel):
    selected_option_index: Optional[int] = Field(default=None, ge=0)
    question_index: Optional[int] = Field(default=0, ge=0)
    answers: Optional[List[int]] = None


class KnowledgeCheckSubmitResponse(BaseModel):
    lesson_id: str
    is_correct: bool
    correct_option_index: Optional[int] = None
    explanation: Optional[str] = None
    question_index: Optional[int] = 0
    results: Optional[List[Dict[str, Any]]] = None
    score: Optional[int] = None
    total: Optional[int] = None


class EnrollResponse(BaseModel):
    enrollment: CourseEnrollmentSummary
    course: CourseDetailResponse
    current_lesson: Optional[LessonSummarySchema] = None
