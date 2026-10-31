---
trigger: glob
globs: backend_service/app/**
---

# Backend Service Rules

## 1. Service Responsibility

`backend_service` is responsible for the application's backend API,
application-level orchestration, user authentication, and data persistence.

It serves as the engineering intelligence hub for an individual developer
or small team, managing:

-   Authentication & user sessions (PBKDF2-HMAC-SHA256 & JWT)
-   Dynamic microservice registration and lifecycle management
-   Document & source code upload staging (.kt, .kts, .java, .py, .md, .pdf, .zip)
-   Triggering RAG indexing, RepoMap generation, and re-indexing into vector storage
-   Real-time grounded query streaming (SSE) with hybrid retrieval, 1-hop dependency expansion, and line-level citations
-   Knowledge Cafe tutorial authoring, publishing, enrollment, and quizzes

It must provide a clean API boundary between the frontend and the
underlying RAG/vector infrastructure.

The backend must not directly expose provider-specific implementation
details (Qdrant, Groq, Bedrock) to the frontend.

------------------------------------------------------------------------

# 2. Technology Stack

Use:

-   Python 3.12+
-   FastAPI
-   Pydantic v2 & Pydantic-Settings
-   AsyncIO / aiosqlite for persistence
-   Uvicorn

Follow idiomatic Python practices and strict type annotations.

------------------------------------------------------------------------

# 3. Backend Structure

Prefer a clean hexagonal structure:

``` text
backend_service/
├── app/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── auth.py
│   │   │   ├── services.py
│   │   │   ├── knowledge.py
│   │   │   ├── query.py
│   │   │   ├── kt.py
│   │   │   ├── feedback.py
│   │   │   └── health.py
│   │   └── schemas/
│   │
│   ├── application/
│   │   └── services/
│   │       ├── auth_service.py
│   │       ├── knowledge_service.py
│   │       ├── kt_service.py
│   │       └── ...
│   │
│   ├── domain/
│   │   ├── models/
│   │   ├── interfaces/
│   │   └── exceptions/
│   │
│   ├── infrastructure/
│   │   ├── clients/
│   │   │   └── direct_rag_client.py
│   │   ├── persistence/
│   │   │   └── sqlite_repositories.py
│   │   ├── security/
│   │   │   └── jwt_handler.py
│   │   └── configuration/
│   │       └── settings.py
│   │
│   └── main.py
│
├── data/
│   └── contextfoundry.db
├── Dockerfile
├── requirements.txt
└── ...
```

Uploaded files and staging assets should be placed in a dedicated persistent
data directory (e.g. `data/storage/services/<service_id>/`), rather than within
the application code tree.

------------------------------------------------------------------------

# 4. API Design

Use REST APIs with explicit Pydantic request/response schemas.

Version all endpoints under:

``` text
/api/v1/...
```

Expected endpoint groups include:

``` text
# Authentication
POST /api/v1/auth/signup
POST /api/v1/auth/login
GET  /api/v1/auth/me

# Microservice Management
GET  /api/v1/services
POST /api/v1/services

# Knowledge Ingestion & Staging
POST /api/v1/knowledge/upload          # Upload .kt, .kts, .md, .pdf, or .zip
GET  /api/v1/knowledge/files           # Staged and ingested files per service
POST /api/v1/knowledge                 # Trigger semantic chunking & indexing
POST /api/v1/knowledge/reindex         # Clean and re-index a service

# Grounded Q&A
POST /api/v1/query/stream              # Real-time SSE streaming with citations

# Knowledge Cafe (Tutorials & Quizzes)
GET  /api/v1/kt/courses                # Browse courses with enrollment progress
POST /api/v1/kt/courses                # Create and publish a new tutorial
GET  /api/v1/kt/courses/{id}           # Full curriculum roadmap
POST /api/v1/kt/courses/{id}/enroll    # Enroll or resume
GET  /api/v1/kt/courses/{id}/lessons/{id}/stream # Stream lesson synthesis
POST /api/v1/kt/courses/{id}/lessons/{id}/doubts/stream # In-lesson Q&A
POST /api/v1/kt/courses/{id}/lessons/{id}/check  # Interactive quiz grading
POST /api/v1/knowledge/course/upload   # Upload course zip bundle

# Health & Feedback
GET  /api/v1/health
POST /api/v1/feedback
```

The backend must own API contracts. Do not expose internal provider
classes or SDK response objects directly.

# 5. Dependency Injection

Use dependency injection where it improves modularity.

Do not instantiate external infrastructure directly inside route
handlers.

Avoid:

``` python
def query():
    client = SomeExternalClient(...)
```

Prefer:

``` text
API Route
    ↓
Application Service / Use Case
    ↓
Interface
    ↓
Infrastructure Implementation
```

Dependencies should be constructed in a centralized
composition/configuration layer where practical.

------------------------------------------------------------------------

# 6. Database Abstraction

Application logic must not depend directly on a particular database
implementation.

Prefer:

``` text
Application
    ↓
Repository Interface
    ↓
SQLite implementation
```

A future implementation may be:

``` text
Application
    ↓
Repository Interface
    ↓
PostgreSQL / RDS implementation
```

Do not spread SQL/database-specific logic throughout the application
layer.

------------------------------------------------------------------------

# 7. Conversation and Feedback

The backend owns application-level persistence for:

-   Conversations
-   Messages
-   Feedback
-   Audit information where required

The initial implementation may use lightweight local persistence.

Do not make AWS-hosted databases mandatory for local development.

The LLM must not be assumed to remember previous API calls. Conversation
context must be explicitly managed by the application.

------------------------------------------------------------------------

# 8. Error Handling

Return consistent API error responses.

Handle:

-   Invalid requests
-   Authentication failures
-   Authorization failures
-   RAG service failures
-   Provider failures
-   Timeouts
-   Dependency failures
-   Unexpected exceptions

Never return raw exception traces to clients.

Use request IDs to correlate API requests with backend logs where
practical.