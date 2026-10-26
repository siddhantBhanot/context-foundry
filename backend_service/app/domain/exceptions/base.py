from typing import Any, Dict, Optional


class DomainException(Exception):
    """Base exception for all domain-level business errors."""
    def __init__(self, message: str, code: str = "DOMAIN_ERROR", details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


class EntityNotFoundException(DomainException):
    """Raised when an entity is not found in the persistence store."""
    def __init__(self, entity_name: str, entity_id: str):
        super().__init__(
            message=f"{entity_name} with id '{entity_id}' not found.",
            code="ENTITY_NOT_FOUND",
            details={"entity": entity_name, "id": entity_id},
        )


class ValidationException(DomainException):
    """Raised when input parameters fail domain validation rules."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            details=details or {},
        )


class RAGServiceException(DomainException):
    """Raised when upstream RAG pipeline fails to process query or ingestion."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="RAG_SERVICE_FAILURE",
            details=details or {},
        )


class AuthenticationException(DomainException):
    """Raised when authentication credentials or token are missing, invalid, or expired."""
    def __init__(self, message: str = "Authentication required or invalid credentials.", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="AUTHENTICATION_FAILED",
            details=details or {},
        )


class ForbiddenException(DomainException):
    """Raised when an authenticated user attempts to access a resource they do not own."""
    def __init__(self, message: str = "You do not have permission to access this resource.", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="FORBIDDEN",
            details=details or {},
        )

