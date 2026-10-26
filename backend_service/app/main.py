from contextlib import asynccontextmanager
import logging
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend_service.app.api.middleware.request_id import RequestIdMiddleware, get_current_request_id
from backend_service.app.api.routes import auth, documents, feedback, health, knowledge, kt, models, query, saathi, services
from backend_service.app.api.schemas.common import ErrorResponse
from backend_service.app.domain.exceptions.base import (
    AuthenticationException,
    DomainException,
    EntityNotFoundException,
    ForbiddenException,
    RAGServiceException,
    ValidationException,
)

from backend_service.app.infrastructure.configuration.settings import get_settings
from backend_service.app.infrastructure.persistence.database import get_database

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [req:%(name)s] %(message)s",
)
logger = logging.getLogger("backend_service")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    logger.info("Initializing SQLite database persistence...")
    db = get_database()
    await db.init_schema()
    logger.info("SQLite schema initialized at: %s", settings.database_path)
    logger.info("RAG Client Adapter mode: %s", settings.rag_client_mode)
    yield
    logger.info("Shutting down backend_service...")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="FC Central — Engineering Intelligence Backend API",
        description="Clean Architecture backend orchestrating RAG microservice intelligence, conversations, and feedback.",
        version="1.0.0",
        lifespan=lifespan,
    )

    # 1. Attach Request ID Middleware
    app.add_middleware(RequestIdMiddleware)

    # 2. Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    # 3. Global Exception Handlers (Standardized JSON, no raw stack traces)
    @app.exception_handler(EntityNotFoundException)
    async def not_found_handler(request: Request, exc: EntityNotFoundException):
        req_id = getattr(request.state, "request_id", get_current_request_id())
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=ErrorResponse(
                code=exc.code,
                message=exc.message,
                request_id=req_id,
                details=exc.details,
            ).model_dump(),
        )

    @app.exception_handler(ValidationException)
    async def validation_handler(request: Request, exc: ValidationException):
        req_id = getattr(request.state, "request_id", get_current_request_id())
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=ErrorResponse(
                code=exc.code,
                message=exc.message,
                request_id=req_id,
                details=exc.details,
            ).model_dump(),
        )

    @app.exception_handler(RAGServiceException)
    async def rag_error_handler(request: Request, exc: RAGServiceException):
        req_id = getattr(request.state, "request_id", get_current_request_id())
        logger.error("RAG Service failure [%s]: %s", req_id, exc.message)
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content=ErrorResponse(
                code=exc.code,
                message=exc.message,
                request_id=req_id,
                details=exc.details,
            ).model_dump(),
        )

    @app.exception_handler(AuthenticationException)
    async def auth_error_handler(request: Request, exc: AuthenticationException):
        req_id = getattr(request.state, "request_id", get_current_request_id())
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Bearer"},
            content=ErrorResponse(
                code=exc.code,
                message=exc.message,
                request_id=req_id,
                details=exc.details,
            ).model_dump(),
        )

    @app.exception_handler(ForbiddenException)
    async def forbidden_error_handler(request: Request, exc: ForbiddenException):
        req_id = getattr(request.state, "request_id", get_current_request_id())
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content=ErrorResponse(
                code=exc.code,
                message=exc.message,
                request_id=req_id,
                details=exc.details,
            ).model_dump(),
        )

    @app.exception_handler(DomainException)
    async def domain_error_handler(request: Request, exc: DomainException):
        req_id = getattr(request.state, "request_id", get_current_request_id())
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse(
                code=exc.code,
                message=exc.message,
                request_id=req_id,
                details=exc.details,
            ).model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(request: Request, exc: RequestValidationError):
        req_id = getattr(request.state, "request_id", get_current_request_id())
        errors = exc.errors()
        logger.warning("Request validation error [%s]: %s", req_id, errors)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=ErrorResponse(
                code="REQUEST_VALIDATION_ERROR",
                message="Invalid request payload or parameters.",
                request_id=req_id,
                details={"errors": errors},
            ).model_dump(),
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        req_id = getattr(request.state, "request_id", get_current_request_id())
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                code="HTTP_ERROR",
                message=str(exc.detail),
                request_id=req_id,
            ).model_dump(),
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        req_id = getattr(request.state, "request_id", get_current_request_id())
        logger.exception("Unhandled server exception [%s]: %s", req_id, str(exc))
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                code="INTERNAL_SERVER_ERROR",
                message="An unexpected internal server error occurred. Please contact support referencing the request_id.",
                request_id=req_id,
            ).model_dump(),
        )

    # 4. Register Versioned Routes under /api/v1
    from fastapi import APIRouter
    api_v1 = APIRouter(prefix="/api/v1")
    api_v1.include_router(auth.router)
    api_v1.include_router(health.router)
    api_v1.include_router(query.router)
    api_v1.include_router(feedback.router)
    api_v1.include_router(knowledge.router)
    api_v1.include_router(services.router)
    api_v1.include_router(documents.router)
    api_v1.include_router(models.router)
    api_v1.include_router(kt.router)
    api_v1.include_router(saathi.router)

    app.include_router(api_v1)

    # Root probe
    @app.get("/")
    async def root():
        return {
            "name": "FC Central — Engineering Intelligence Backend Service",
            "version": "1.0.0",
            "docs": "/docs",
            "health": "/api/v1/health",
        }

    return app


app = create_app()
