from pydantic import BaseModel, Field


class DocumentDetailResponse(BaseModel):
    file: str = Field(..., description="Document file name")
    service: str = Field(..., description="Target microservice ID")
    content: str = Field(..., description="Full text/markdown content of the document")
    content_type: str = Field(default="text/markdown", description="MIME type or content format")
    total_lines: int = Field(default=0, description="Total lines in document")
    size_bytes: int = Field(default=0, description="File size in bytes")
