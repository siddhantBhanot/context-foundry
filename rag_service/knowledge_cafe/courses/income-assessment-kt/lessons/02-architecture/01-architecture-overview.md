# Income Assessment — Runtime Architecture Overview

## 1. Architectural Style
`income-assessment-service` is designed as a **reactive stateful business orchestrator**. It decouples synchronous client requests from long-running third-party financial assessments through asynchronous state transitions and event streaming.

## 2. Key Architectural Layers
1. **REST Ingress Layer**: Exposes non-blocking endpoints (`ApplicationController`) returning `Mono<ResponseEntity<ApiResponse>>`.
2. **Context Enrichment & KeyData Layer**: Normalizes HTTP headers, tenant IDs, and client payloads into an immutable `KeyData` domain context.
3. **Version Resolution Layer**: Employs `CommonVersionResolver` to dynamically select whether a request should be dispatched to legacy handlers (V1) or revamped modular handlers (V2).
4. **Assessment Handlers**: Journey-specific orchestrators implementing `AssessmentHandler` (e.g., `FourWheelerPersonalAssessmentHandler`).
5. **Gateway / Integration Layer**: Encapsulates external third-party communication via Spring `WebClient` with circuit breaking and retries.
6. **Persistence & Messaging Layer**: Reactive Mongo repositories (`AssessmentRepository`) and Kafka publishers (`OutcomeEventPublisher`).
