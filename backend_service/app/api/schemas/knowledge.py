from typing import List, Optional
from pydantic import BaseModel, Field


class KnowledgeIngestRequest(BaseModel):
    service: str = Field(
        default="income-assessment-service",
        description="Target microservice identifier",
    )
    source_path: Optional[str] = Field(
        default=None,
        description="Optional local filesystem path to ingest; defaults to service sample data directory",
    )


class KnowledgeIngestResponse(BaseModel):
    job_id: str = Field(..., description="Unique ingestion job identifier")
    service: str = Field(..., description="Target microservice identifier")
    status: str = Field(..., description="Job status: pending, processing, completed, failed")
    source_path: str = Field(..., description="Resolved directory path scanned for ingestion")
    total_files: int = Field(default=0, description="Total number of markdown and code files ingested")
    total_chunks: int = Field(default=0, description="Total number of semantic chunks indexed")
    files_indexed: List[str] = Field(default_factory=list, description="List of file names indexed")
    error_message: Optional[str] = Field(default=None, description="Error explanation if status is failed")
    created_at: str
    completed_at: Optional[str] = None


class KnowledgeUploadResponse(BaseModel):
    filename: str = Field(..., description="Name of the uploaded file")
    service: str = Field(..., description="Target microservice identifier")
    size_bytes: int = Field(..., description="Size of the file in bytes")
    status: str = Field(default="pending", description="Staging status (pending review)")
    extracted_files_count: Optional[int] = Field(default=None, description="Count of extracted files if zip archive")
    message: str = Field(..., description="Human-readable status message")


class KnowledgeFileInfo(BaseModel):
    name: str = Field(..., description="File name")
    path: str = Field(..., description="Relative path in service storage")
    service: str = Field(..., description="Target microservice identifier")
    format: str = Field(..., description="MD or PDF")
    size_bytes: int = Field(..., description="File size in bytes")
    status: str = Field(..., description="pending or ingested")
    modified_at: str = Field(..., description="ISO timestamp of file modification")


class CourseUploadResponse(BaseModel):
    course_id: str = Field(..., description="Identifier of the course parsed from course-structure.md")
    title: str = Field(..., description="Title of the course")
    target_service: str = Field(..., description="Microservice targeted by the course")
    total_lessons: int = Field(..., description="Total lessons configured in the curriculum")
    status: str = Field(default="pending", description="Staging status")
    message: str = Field(..., description="Status feedback message")


class PendingCourseInfo(BaseModel):
    course_id: str = Field(..., description="Course ID")
    title: str = Field(..., description="Course Title")
    target_service: str = Field(..., description="Microservice targeted")
    domain: str = Field(..., description="Course Domain")
    difficulty: str = Field(..., description="Difficulty level")
    total_lessons: int = Field(..., description="Number of lessons")
    status: str = Field(default="pending", description="Staged status")
    staged_at: str = Field(..., description="ISO timestamp when staged")


class CourseIngestRequest(BaseModel):
    course_id: str = Field(..., description="Course ID to publish and index into Knowledge Cafe")


class CourseIngestResponse(BaseModel):
    course_id: str = Field(..., description="Course ID")
    status: str = Field(..., description="Ingestion status (completed, failed)")
    chunks_indexed: int = Field(default=0, description="Total lesson context chunks upserted")
    message: str = Field(..., description="Status message")
