from typing import List
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile

from backend_service.app.api.dependencies import get_current_user, get_knowledge_service
from backend_service.app.api.schemas.knowledge import (
    CourseIngestRequest,
    CourseIngestResponse,
    CourseUploadResponse,
    KnowledgeFileInfo,
    KnowledgeIngestRequest,
    KnowledgeIngestResponse,
    KnowledgeUploadResponse,
    PendingCourseInfo,
)
from backend_service.app.application.services.knowledge_service import KnowledgeService
from backend_service.app.domain.models.user import User

router = APIRouter(prefix="/knowledge", tags=["Knowledge & Ingestion"])


@router.post("/upload", response_model=KnowledgeUploadResponse)
async def upload_knowledge_document(
    file: UploadFile = File(...),
    service: str = Form(default="income-assessment-service"),
    current_user: User = Depends(get_current_user),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
) -> KnowledgeUploadResponse:
    """
    Upload a documentation file (.md or .pdf) to rag_service staging.
    Stages the file under pending review without triggering the RAG ingestion pipeline.
    """
    content_bytes = await file.read()
    result = await knowledge_service.upload_document(
        service=service,
        file_name=file.filename or "uploaded_document.md",
        content_bytes=content_bytes,
    )
    return KnowledgeUploadResponse(**result)


@router.get("/files", response_model=List[KnowledgeFileInfo])
async def list_knowledge_files(
    service: str = Query(default="income-assessment-service"),
    current_user: User = Depends(get_current_user),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
) -> List[KnowledgeFileInfo]:
    """
    List all documentation files (pending review and ingested) for a microservice.
    """
    results = await knowledge_service.list_files(service=service)
    return [KnowledgeFileInfo(**f) for f in results]


@router.post("", response_model=KnowledgeIngestResponse)
async def trigger_knowledge_ingestion(
    payload: KnowledgeIngestRequest,
    current_user: User = Depends(get_current_user),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
) -> KnowledgeIngestResponse:
    """
    Trigger semantic chunking, embedding generation, and vector persistence for a microservice.
    Promotes staged pending files and executes RAG indexing.
    Protected endpoint: requires authenticated maintainer/engineer access.
    """
    result = await knowledge_service.trigger_ingestion(
        service=payload.service,
        source_directory=payload.source_path,
    )
    return KnowledgeIngestResponse(**result)


@router.post("/course/upload", response_model=CourseUploadResponse)
async def upload_course_archive(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
) -> CourseUploadResponse:
    """
    Upload a Knowledge Cafe course package (.zip archive containing course-structure.md).
    Validates and stages the course under pending review without indexing it into vector storage.
    """
    content_bytes = await file.read()
    result = await knowledge_service.upload_course(
        file_name=file.filename or "course.zip",
        content_bytes=content_bytes,
    )
    return CourseUploadResponse(**result)


@router.get("/course/pending", response_model=List[PendingCourseInfo])
async def list_pending_courses(
    current_user: User = Depends(get_current_user),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
) -> List[PendingCourseInfo]:
    """
    List all Knowledge Cafe courses staged for manual review.
    """
    results = await knowledge_service.list_pending_courses()
    return [PendingCourseInfo(**c) for c in results]


@router.post("/course/ingest", response_model=CourseIngestResponse)
async def trigger_course_ingestion(
    payload: CourseIngestRequest,
    current_user: User = Depends(get_current_user),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
) -> CourseIngestResponse:
    """
    Promote a staged Knowledge Cafe course and index its lesson contexts into Qdrant vector store.
    Protected maintainer action.
    """
    result = await knowledge_service.trigger_course_ingestion(course_id=payload.course_id)
    return CourseIngestResponse(**result)

