from typing import Any, Dict, Generic, Optional, TypeVar
from pydantic import BaseModel, Field

DataT = TypeVar("DataT")


class ErrorResponse(BaseModel):
    """Standardized error response returned across all API endpoints."""
    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error description")
    request_id: str = Field(..., description="Correlation ID for log tracing")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Optional error metadata")


class APIResponse(BaseModel, Generic[DataT]):
    """Standard generic envelope for successful API responses."""
    success: bool = True
    data: DataT
    request_id: Optional[str] = None
