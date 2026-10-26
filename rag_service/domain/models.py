from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(BaseModel):
    role: MessageRole = MessageRole.USER
    content: str


class DocumentType(str, Enum):
    MARKDOWN = "markdown"
    SOURCE_CODE = "source_code"
    API_SCHEMA = "api_schema"
    OTHER = "other"


class ServiceMetadata(BaseModel):
    service: str = Field(..., description="Target microservice ID, e.g. income-assessment-service")
    document_type: DocumentType = Field(default=DocumentType.MARKDOWN)
    source: str = Field(..., description="Source origin, e.g. repository, confluence, api_doc")
    file_path: str = Field(..., description="Relative or absolute file path")
    language: str = Field(default="markdown", description="Language of chunk, e.g. kotlin, markdown")
    package: Optional[str] = Field(default=None, description="Kotlin package name")
    class_name: Optional[str] = Field(default=None, description="Class or interface name")
    method_name: Optional[str] = Field(default=None, description="Method or function name")
    endpoint: Optional[str] = Field(default=None, description="HTTP endpoint if controller, e.g. /api/v1/assess")
    start_line: Optional[int] = Field(default=None)
    end_line: Optional[int] = Field(default=None)
    git_commit: Optional[str] = Field(default=None)
    extra: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = self.model_dump(exclude={"extra"})
        if self.extra:
            data.update(self.extra)
        # Ensure enum serializes as string
        data["document_type"] = self.document_type.value
        return data


class Chunk(BaseModel):
    id: str = Field(..., description="Deterministic or unique chunk identifier")
    content: str = Field(..., description="Text content of the chunk")
    metadata: ServiceMetadata = Field(..., description="Service-level and provenance metadata")
    index: int = Field(default=0, description="Chunk sequence index within document")
    embedding: Optional[List[float]] = Field(default=None, description="Dense vector embedding")


class Document(BaseModel):
    id: str
    content: str
    metadata: ServiceMetadata


class SourceReference(BaseModel):
    file: str
    service: Optional[str] = None
    document_type: str = "markdown"
    class_name: Optional[str] = None
    method_name: Optional[str] = None
    endpoint: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    snippet: Optional[str] = None
    score: Optional[float] = None


class DocumentContent(BaseModel):
    file: str
    service: str
    content: str
    content_type: str = "text/markdown"
    total_lines: int
    size_bytes: int


class LLMResponse(BaseModel):
    content: str
    model: str
    provider: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    total_tokens: Optional[int] = None


class QueryResult(BaseModel):
    answer: str
    service: str
    sources: List[SourceReference] = Field(default_factory=list)
    provider: str
    model: str
    latency_ms: float
    retrieved_chunks_count: int
