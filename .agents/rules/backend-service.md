---
trigger: glob
globs: backend_service/app/**
---

# Backend Service Rules

## 1. Service Responsibility

`backend_service` is responsible for the application's backend API and
application-level orchestration.

It should provide a clean API boundary between the frontend and the
underlying RAG/infrastructure services.

The backend must not contain frontend-specific logic.

The backend must not directly expose provider-specific implementation
details to the frontend.

------------------------------------------------------------------------

# 2. Technology Stack

Use:

-   Python
-   FastAPI
-   Pydantic
-   AsyncIO where appropriate

Follow idiomatic Python practices.

Use type hints throughout the codebase.

------------------------------------------------------------------------

# 3. Backend Structure

Prefer a structure similar to:

``` text
backend_service/
├── app/
│   ├── api/
│   │   ├── routes/
│   │   └── schemas/
│   │
│   ├── application/
│   │   ├── services/
│   │   └── use_cases/
│   │
│   ├── domain/
│   │   ├── models/
│   │   ├── interfaces/
│   │   └── exceptions/
│   │
│   ├── infrastructure/
│   │   ├── clients/
│   │   ├── persistence/
│   │   └── configuration/
│   │
│   └── main.py
│
├── Dockerfile
├── requirements.txt
└── ...
```

The exact structure may evolve, but responsibilities must remain clearly
separated.

------------------------------------------------------------------------

# 4. API Design

Use REST APIs with explicit request/response schemas.

Prefer versioned APIs:

``` text
/api/v1/...
```

Expected endpoints include:

``` text
POST /api/v1/query
POST /api/v1/feedback
POST /api/v1/knowledge
GET  /api/v1/health
```

The backend should own API contracts. Do not expose internal provider
classes or SDK response objects directly.

For example, the frontend should not need to know whether the RAG system
uses Bedrock, Gemini, Groq, or another provider.

------------------------------------------------------------------------

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