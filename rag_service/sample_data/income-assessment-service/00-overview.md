# Income Assessment Knowledge Base

This folder is the context pack for **RAG-based developer assistance and onboarding** for the `income-assessment-service`.

The knowledge base is designed to help developers quickly understand the service's **business domain, architecture, request flows, APIs, integrations, persistence, events, configuration, and troubleshooting paths** without having to inspect the entire repository manually.

The primary focus is on **production behavior that can be established from the current repository code and configuration**.

---

## 1. Service Overview

### Service

`income-assessment-service`

### Technology

* Language: Kotlin
* Framework: Spring WebFlux
* Persistence: MongoDB
* Messaging: Kafka
* Configuration: Spring/application configuration and service-specific configuration files

### Business Domain

The service is responsible for **income verification and assessment**.

The service supports income-assessment journeys involving:

* Statement-based income assessment
* ITR-based income assessment

Different journeys may follow different execution paths, business rules, integrations, and state transitions.

---

## 2. Major Integrations

The service interacts with multiple internal and external systems as part of the income-assessment lifecycle.

The major integrations currently identified in the repository include:

| Integration      | Purpose                                             |
| ---------------- | --------------------------------------------------- |
| Perfios          | Statement/bank-based income assessment              |
| Zenith / AA-Orch | Account Aggregator/orchestration-related processing |
| Finacle          | Banking/core-system interaction                     |
| CAP              | Application/orchestration-related integration       |
| Document Service | Document-related operations                         |
| Auth             | Authentication/authorization-related interaction    |
| MongoDB          | Persistence of income-assessment data               |
| Kafka            | Asynchronous event-driven communication             |

The exact role of each integration, APIs, payloads, failure handling, and calling components are documented in:

`05-integrations.md`

Journey-specific interaction sequences are documented under:

`flows/`

---

## 3. High-Level Mental Model

At a high level, the Income Assessment service receives requests from upstream applications/services, determines the appropriate income-assessment flow, executes the required business logic, interacts with internal/external systems, and persists or publishes the resulting state.

A simplified representation is:

Upstream Application / Service
             |
             v
       REST Controller
             |
             v
     Application / Domain
          Services
             |
             +-------------------+
             |                   |
             v                   v
       Business Logic       Integration
       / Journey Flow          Gateways
                                 |
              +------------------+------------------+
              |                  |                  |
              v                  v                  v
           Perfios          Zenith/AA-Orch       CAP/Finacle
              |
              v
       External Assessment

             |
             +------------------+
             |                  |
             v                  v
          MongoDB             Kafka


This is a conceptual view only. Individual journeys may skip or add components depending on the execution path.

The authoritative implementation of a specific flow should always be determined from the relevant Kotlin classes and configuration.

---

## 4. Architecture and Execution Model

The service contains multiple layers/components responsible for different parts of the request lifecycle.

The repository includes:

* Controllers responsible for exposing HTTP APIs.
* Application/service components responsible for orchestrating business operations.
* Domain components representing business concepts and processing.
* Repository components responsible for persistence.
* Gateway/integration components responsible for communication with other systems.
* Kafka-related components for asynchronous processing.
* Configuration and transformer definitions supporting runtime behavior and integration flows.

A major execution path is implemented through the **Revamp/V3 service model**.

Primary V3 application-service anchor:

src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/
revamp/service/impl/IncomeAssessmentApplicationServiceV3.kt


The V3 implementation should generally be treated as the **first implementation to inspect when investigating current income-assessment execution behavior**.

Older implementations such as V2 should be used when:

* Investigating backward compatibility.
* Understanding an older execution path.
* Comparing behavior between versions.
* A flow explicitly routes through the older implementation.

Detailed architecture information is maintained in:

`01-architecture.md`

---

## 5. Primary Code Anchors

The following repository locations are important starting points when navigating the service.

### Controllers

src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/controller/


Use this location to identify:

* Exposed APIs
* HTTP methods
* Request models
* Response models
* Controller-to-service delegation

### Revamp / V3 Application Service

src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/
revamp/service/impl/IncomeAssessmentApplicationServiceV3.kt


This is a primary anchor for understanding the current V3 application execution model.

### Zenith Gateway

src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/
zenithorch/gateway/ZenithOrchestratorGateway.kt


This is a primary integration anchor for communication with the Zenith/AA-Orch layer.

### Domain

src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/domain/


Use this area to understand domain models and business concepts.

### Persistence / Repository

src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/repository/


Use this area to understand MongoDB persistence and repository access patterns.

### Runtime Configuration

src/main/resources/application.yaml


This is an important source for:

* Environment configuration
* Integration configuration
* Feature/toggle configuration
* Runtime behavior

### Event Schemas / Transformers

src/main/resources/configurations/
src/main/resources/transformers/


These locations contain configuration and transformation definitions relevant to event/integration processing.

---

## 6. Knowledge Base Structure

The knowledge base is organized by developer questions rather than by repository package structure.

### `01-architecture.md`

Contains:

* Service architecture
* Major components
* Layering
* Component responsibilities
* V2/V3 execution model
* Important code relationships
* Architectural dependencies

### `02-request-flows.md`

Contains end-to-end request flows.

Examples:

* Application initiation
* Income-assessment journey execution
* Statement-based assessment
* ITR-based assessment
* Callback/request continuation flows
* Important API-to-integration flows

The goal is to answer questions such as:

> What happens after this API is called?

### `03-api-contracts.md`

Contains the important API contracts derived from controllers and related request/response models.

For each important API, the document should capture:

* Endpoint
* HTTP method
* Caller
* Request model
* Important fields
* Response model
* Downstream calls
* Relevant implementation classes
* Important error scenarios

### `04-business-logic.md`

Contains domain-specific processing logic, including:

* Assessment statuses
* Journey types
* State transitions
* Decision rules
* Handler selection
* Business conditions
* Important business methods

This document should answer questions such as:

> Which business handler executes for `FOUR_WHEELER_PERSONAL`?

### `05-integrations.md`

Contains details about external/internal integrations:

* Integration purpose
* Calling component
* Gateway/client
* Endpoint
* Request/response mapping
* Authentication
* Timeout/retry behavior
* Failure handling
* Relevant configuration

### `06-database.md`

Contains MongoDB-related knowledge:

* Collections
* Important entities
* Key fields
* Repository mappings
* Indexes
* Status/state persistence
* Important queries

### `07-kafka-events.md`

Contains event-driven behavior:

* Event IDs
* Topics
* Producers
* Consumers
* Event payloads
* Transformers
* Trigger conditions
* Processing behavior

### `08-error-handling.md`

Contains:

* Error-code taxonomy
* Validation failures
* Integration failures
* Timeout handling
* Retry behavior
* Kafka failures
* Persistence failures
* Business failures

### `09-configuration.md`

Contains important runtime configuration:

* Environment variables
* Application properties
* Integration URLs/configuration
* Feature flags
* High-impact toggles
* Configuration that changes execution behavior

### `10-troubleshooting.md`

Contains developer-focused investigation playbooks.

Each troubleshooting entry should ideally connect:

Symptom
   ↓
Possible Cause
   ↓
Relevant API / Flow
   ↓
Relevant Class / Method
   ↓
Logs / Events / Database
   ↓
Likely Resolution


### `11-glossary.md`

Contains:

* Business abbreviations
* Internal terminology
* Journey names
* Assessment terminology
* System names
* Technical terminology specific to the service

### `flows/`

Contains detailed documentation for individual business journeys.

Current detailed flows include:

flows/
├── perfios-flow.md
├── cap-flow.md
└── income-assessment-flow.md


These documents should contain deeper sequence-level information than the general request-flow documentation.

---

## 7. Source of Truth

The knowledge base combines **curated documentation, source code, configuration, and integration definitions**.

When determining actual implementation behavior, use the following priority:

Current production-oriented code
          ↓
Current configuration
          ↓
Integration/event definitions
          ↓
Curated documentation
          ↓
README / general repository documentation


The README should be treated as supporting context rather than the final authority for implementation-specific behavior.

If documentation and implementation disagree, the current repository implementation should be treated as authoritative and the knowledge-base documentation should be updated accordingly.

---

## 8. Versioning Guidance

The service contains multiple execution versions.

For questions about current behavior:

1. Inspect the V3 implementation first.
2. Follow the controller/application-service routing to determine which version is actually executed.
3. Inspect V2 only when required for comparison, backward compatibility, or an explicitly V2 flow.
4. Do not assume that behavior from V2 applies to V3.

The knowledge base should explicitly identify version-specific behavior whenever the same business operation behaves differently across versions.

---

## 9. RAG Grounding Guidelines

This knowledge base is intended to be consumed by a RAG pipeline.

Therefore, documentation should favor **specific, retrievable engineering facts** over generic explanations.

### Prefer

IncomeAssessmentApplicationServiceV3.kt
    -> methodName()
    -> ZenithOrchestratorGateway
    -> Mongo repository


over:

The application service communicates with various
downstream systems.


### Prefer

Endpoint:
POST /some-endpoint

Controller:
SomeController.someMethod()

Service:
IncomeAssessmentApplicationServiceV3.someMethod()


over a generic description of REST APIs.

### Important grounding rules

* Include exact class names.
* Include exact method names where useful.
* Include repository paths for important implementation anchors.
* Include endpoint names.
* Include event IDs and topic names.
* Include important configuration keys.
* Include journey/status names exactly as they appear in code.
* Distinguish V2 and V3 behavior.
* Avoid unsupported assumptions.
* Do not document behavior merely because it is common in similar systems.
* When behavior is uncertain, mark it for verification rather than presenting it as fact.

---

## 10. Example Questions This Knowledge Base Should Answer

The knowledge base should enable developers to answer questions such as:

### Business Logic

> What is the business handler for `FOUR_WHEELER_PERSONAL`?

The answer should identify the relevant handler/implementation and explain how the journey reaches it.

### API Contract

> What API contract is currently used for `/initiation-application` with CAP?

The answer should identify the controller, request/response models, downstream interaction, and relevant implementation.

### Request Flow

> What is the overall flow from the Income Assessment UI home page to the backend?

The answer should trace the request through the relevant APIs and backend components.

### External Integration

> Where does the request flow after `/generate-link` is called for Perfios Bank Statement assessment?

The answer should identify the relevant application/business service, Perfios gateway/client, external endpoint, and subsequent processing.

### Debugging

> The income assessment is stuck in a particular status. Where should I investigate?

The answer should identify the relevant state transition, implementation class/method, database state, events, and integration involved.

### Code Navigation

> Where is the logic for Zenith/AA-Orch communication?

The answer should point to the relevant gateway and associated service/configuration.

---

## 11. Documentation Principles

The purpose of this knowledge base is not to reproduce the entire repository.

It should document the information that is most useful for **understanding, navigating, debugging, and modifying the service**.

### Do

* Document business-specific behavior.
* Link business behavior to actual implementation.
* Use exact class, method, endpoint, event, and configuration names.
* Explain important request and event flows.
* Document why a component is involved when that is known.
* Keep journey-specific details in dedicated flow documents.
* Keep frequently changing implementation details grounded in code.

### Avoid

* Generic explanations of Kotlin, Spring, MongoDB, Kafka, REST, etc.
* Copying entire source files into Markdown.
* Creating a document for every class.
* Guessing undocumented business behavior.
* Duplicating the same detailed flow across multiple documents.
* Treating old implementations as current without verifying routing/version.

---

## 12. Maintaining the Knowledge Base

The knowledge base should evolve alongside the service.

When a significant feature or flow changes, update the relevant documentation rather than adding disconnected notes.

Typical change mapping:

API change
    -> 03-api-contracts.md

Business-rule change
    -> 04-business-logic.md

Integration change
    -> 05-integrations.md

Database change
    -> 06-database.md

Kafka/event change
    -> 07-kafka-events.md

Error-handling change
    -> 08-error-handling.md

Configuration change
    -> 09-configuration.md

New/changed debugging scenario
    -> 10-troubleshooting.md


For significant end-to-end changes, also update the relevant file under:

flows/


---

## 13. Quick Navigation

When investigating a developer question, start with the document corresponding to the question:

| Developer Question                           | Start Here              |
| -------------------------------------------- | ----------------------- |
| What does Income Assessment do?              | `00-overview.md`        |
| How is the service structured?               | `01-architecture.md`    |
| What happens after an API is called?         | `02-request-flows.md`   |
| What is the API contract?                    | `03-api-contracts.md`   |
| Which business logic/handler executes?       | `04-business-logic.md`  |
| How does Perfios/Zenith/CAP/etc. work?       | `05-integrations.md`    |
| Where is data stored?                        | `06-database.md`        |
| Which events are involved?                   | `07-kafka-events.md`    |
| Why did a request fail?                      | `08-error-handling.md`  |
| Which configuration controls this behavior?  | `09-configuration.md`   |
| How do I debug this issue?                   | `10-troubleshooting.md` |
| What does this internal term mean?           | `11-glossary.md`        |
| How does a specific journey work end-to-end? | `flows/`                |

---

## 14. Current Focus

The initial knowledge base focuses on the **Income Assessment service itself** and its currently implemented behavior.

The immediate goal is to make common developer questions answerable through a combination of:

Curated Business Knowledge
        +
Actual Kotlin Source Code
        +
Configuration
        +
Integration/Event Definitions
        ↓
Service-aware RAG Retrieval
        ↓
Grounded Developer Answer


The knowledge base should therefore remain **implementation-aware, business-focused, and traceable to repository evidence**.

---

## 15. Source citations by primary section

### Sections 1-4: service overview, integrations, mental model, execution model

**Source citations**
- `README.md:3-37`
- `build.gradle:207-269`
- `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/Application.kt:8-15`
- `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/revamp/service/impl/IncomeAssessmentApplicationServiceV3.kt:147-185`

### Section 5: primary code anchors

**Source citations**
- `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/controller/IncomeAssessmentApplicationController.kt:35-395`
- `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/zenithorch/gateway/ZenithOrchestratorGateway.kt:54-69`
- `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/repository/IncomeAssessmentRepository.kt:26-66`
- `src/main/resources/application.yaml:53-203`

### Sections 6-14: knowledge-base structure, source-of-truth rules, version guidance, RAG usage, maintenance, navigation

**Source citations**
- `income-assessment-knowledge/01-architecture.md:1-465`
- `income-assessment-knowledge/02-request-flows.md:1-117`
- `income-assessment-knowledge/03-api-contracts.md:1-1230`
- `income-assessment-knowledge/04-business-logic.md:1-115`
- `income-assessment-knowledge/05-integrations.md:1-84`
- `income-assessment-knowledge/06-database.md:1-103`
- `income-assessment-knowledge/07-kafka-events.md:1-73`
- `income-assessment-knowledge/08-error-handling.md:1-110`
- `income-assessment-knowledge/09-configuration.md:1-103`
- `income-assessment-knowledge/10-troubleshooting.md:1-103`
- `income-assessment-knowledge/11-glossary.md:1-27`
- `income-assessment-knowledge/flows/perfios-flow.md:1-72`
- `income-assessment-knowledge/flows/cap-flow.md:1-65`
- `income-assessment-knowledge/flows/income-assessment-flow.md:1-87`

