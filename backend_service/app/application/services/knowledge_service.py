from typing import Any, Dict, List, Optional
from backend_service.app.domain.exceptions.base import ValidationException
from backend_service.app.domain.interfaces.rag_client import RAGClientProtocol


class KnowledgeService:
    """Application service for uploading, staging, and ingesting microservice knowledge."""

    def __init__(self, rag_client: RAGClientProtocol):
        self.rag_client = rag_client

    async def upload_document(
        self,
        service: str,
        file_name: str,
        content_bytes: bytes,
    ) -> Dict[str, Any]:
        cleaned_service = service.strip()
        if not cleaned_service:
            raise ValidationException("service identifier cannot be empty.")
        if not file_name or not file_name.strip():
            raise ValidationException("file_name cannot be empty.")
        if len(content_bytes) == 0:
            raise ValidationException("Uploaded file is empty.")

        try:
            return await self.rag_client.upload_document(
                service=cleaned_service,
                file_name=file_name,
                content_bytes=content_bytes,
            )
        except ValueError as ve:
            raise ValidationException(str(ve)) from ve

    async def list_files(
        self,
        service: str = "income-assessment-service",
    ) -> List[Dict[str, Any]]:
        cleaned_service = service.strip()
        if not cleaned_service:
            raise ValidationException("service identifier cannot be empty.")

        return await self.rag_client.list_service_files(service=cleaned_service)

    async def trigger_ingestion(
        self,
        service: str = "income-assessment-service",
        source_directory: Optional[str] = None,
    ) -> Dict[str, Any]:
        cleaned_service = service.strip()
        if not cleaned_service:
            raise ValidationException("service identifier cannot be empty.")

        job = await self.rag_client.trigger_ingestion(
            service=cleaned_service,
            source_directory=source_directory,
        )

        return {
            "job_id": job.id,
            "service": job.service,
            "status": job.status.value,
            "source_path": job.source_path,
            "total_files": job.total_files,
            "total_chunks": job.total_chunks,
            "files_indexed": job.files_indexed,
            "error_message": job.error_message,
            "created_at": job.created_at.isoformat(),
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        }

    async def upload_course(
        self,
        file_name: str,
        content_bytes: bytes,
    ) -> Dict[str, Any]:
        if not file_name or not file_name.strip():
            raise ValidationException("file_name cannot be empty.")
        if len(content_bytes) == 0:
            raise ValidationException("Uploaded course zip file is empty.")

        try:
            return await self.rag_client.upload_course_zip(
                file_name=file_name,
                content_bytes=content_bytes,
            )
        except ValueError as ve:
            raise ValidationException(str(ve)) from ve

    async def list_pending_courses(self) -> List[Dict[str, Any]]:
        return await self.rag_client.list_pending_courses()

    async def trigger_course_ingestion(self, course_id: str) -> Dict[str, Any]:
        cleaned = course_id.strip()
        if not cleaned:
            raise ValidationException("course_id cannot be empty.")

        return await self.rag_client.trigger_course_ingestion(course_id=cleaned)
