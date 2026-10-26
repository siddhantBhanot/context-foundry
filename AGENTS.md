# Engineering Intelligence Platform --- Universal Project Rules

## 1. Project Objective

This project is an internal **Engineering Intelligence Platform for
Microservices**.

The platform is composed of multiple independently responsible services,
including:

-   `backend_service`
-   `rag_service`
-   `frontend-service`

The architecture must remain modular so that additional microservices,
LLM providers, embedding providers, vector databases, and knowledge
sources can be added later without significant changes to unrelated
components.

Do not over-engineer the MVP. Prefer simple, production-quality
abstractions over speculative infrastructure.

------------------------------------------------------------------------

# 2. Universal Architectural Principles

Follow **Clean Architecture / Hexagonal Architecture principles where
they provide real value**, without introducing unnecessary abstractions.

Each service should maintain clear separation between presentation/API,
application/use-case logic, domain logic, and infrastructure/external
systems where applicable.

Dependencies should point toward stable abstractions rather than
concrete infrastructure implementations.

External systems must be accessed through clearly defined interfaces,
ports, clients, or adapters when doing so prevents provider-specific
implementation details from leaking into application logic.

Prefer:

-   Single Responsibility Principle
-   Dependency Inversion
-   Composition over inheritance
-   Explicit interfaces
-   Small focused modules
-   Clear separation of concerns
-   Dependency injection where useful
-   Strong typing
-   Meaningful naming

Avoid:

-   Giant classes
-   Giant functions
-   Global mutable state
-   Circular dependencies
-   Unnecessary inheritance hierarchies
-   Duplicated infrastructure logic
-   Magic constants
-   Hardcoded environment-specific values

Do not introduce abstractions solely for theoretical purity. An
abstraction should solve a real maintainability, or
extensibility problem.

------------------------------------------------------------------------

# 3. Provider and Infrastructure Independence

Application logic must not become tightly coupled to a specific external
provider.

Provider-specific implementation details should remain behind
appropriate adapters/interfaces.

The architecture must allow infrastructure providers to be changed with
minimal impact to application logic.

Examples include:

-   LLM provider
-   Embedding provider
-   Vector database
-   Database
-   External APIs
-   Knowledge-source integrations

Changing an external provider should primarily require:

1.  Implementing or configuring the new adapter.
2.  Updating configuration.
3.  Registering the implementation.

It should not require rewriting unrelated application logic.

------------------------------------------------------------------------

# 4. Configuration

All environment-specific configuration must be externalized.

Never hardcode:

-   API keys
-   Credentials
-   Secrets
-   URLs
-   Model IDs
-   Database connection strings
-   Environment-specific configuration

Use environment variables or an appropriate configuration mechanism.

Provide `.env.example` files where appropriate.

Never commit secrets.

------------------------------------------------------------------------

# 5. Security

Never expose secrets in:

-   Source code
-   Git
-   Dockerfiles
-   Frontend/browser code
-   Logs
-   API responses

Credentials for privileged external services must remain server-side.

Sensitive information should only be logged when there is a clear
operational requirement and it is safe to do so.

------------------------------------------------------------------------

# 6. Error Handling and Observability

Handle expected failures explicitly.

Differentiate between appropriate categories of errors such as:

-   Validation errors
-   Authentication/authorization errors
-   External provider errors
-   Persistence errors
-   Configuration errors
-   Network errors
-   Unexpected application errors

Do not expose raw stack traces, credentials, or internal implementation
details to end users.

Use structured logging where practical.

Important operations should be observable through useful logs, request
IDs, latency information, and success/failure status.

Avoid logging sensitive prompts, responses, tokens, credentials, or
secrets unnecessarily.

------------------------------------------------------------------------

# 7. API and Contract Stability

API contracts should be explicit, typed, and versioned where
appropriate.

Prefer backward-compatible changes.

Do not expose internal implementation details in public API contracts.

Provider-specific concepts should not leak into generic API models
unless there is a concrete requirement.

When changing an API contract, update:

-   Backend implementation
-   Frontend client/types
-   Relevant documentation

------------------------------------------------------------------------

# 8. Docker and Local Development

All application services must be Dockerizable.

Use Docker Compose for local orchestration where multiple services need
to run together.

Services should be configurable through environment variables.

Do not embed credentials in Dockerfiles or Docker images.

Use multi-stage builds where useful.

Keep images reasonably small.

The complete local application should be straightforward to start and
stop.

------------------------------------------------------------------------

# 10. Extensibility

The architecture should allow future additions without major redesign.

Potential future additions include:

-   Additional microservices
-   Additional LLM providers
-   Additional embedding providers
-   Additional vector databases
-   Additional databases
-   Confluence
-   Git repositories
-   Kibana/Elastic logs
-   Metrics
-   Traces
-   Deployment information

New integrations should be added through clear boundaries rather than by
spreading provider-specific logic across the codebase.

------------------------------------------------------------------------

# 11. MVP Discipline

This is a hackathon project with a short implementation timeline.

Prioritize:

1.  Working end-to-end functionality
2.  Correctness
3.  Good developer/user experience
4.  Clean modular architecture
5.  Dockerized local execution

Do NOT prematurely introduce:

-   Kubernetes
-   Kafka
-   Redis
-   Knowledge graphs
-   Multi-agent systems
-   Fine-tuning
-   Custom model hosting
-   GPU infrastructure
-   Complex distributed systems
-   Microservice decomposition without a demonstrated need

Prefer the simplest design that satisfies the actual requirement.

------------------------------------------------------------------------

# 12. Rules for AI Agent

Before implementing a feature:

1.  Understand the existing architecture.
2.  Identify the correct service and layer.
3.  Reuse existing abstractions.
4.  Avoid duplicating functionality.
5.  Preserve existing API contracts unless a change is explicitly
    required.
6.  Keep changes localized.
7.  Update documentation when architecture or behavior changes.

Do not make unrelated refactors while implementing a feature.

Do not silently replace an existing technology or architectural
decision.

When uncertain between a simpler and more complex implementation, prefer
the simpler implementation unless the additional complexity provides a
concrete, demonstrated benefit.
