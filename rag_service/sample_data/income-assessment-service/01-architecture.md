# Income Assessment Service — Architecture

## 1. Purpose

This document describes the runtime architecture of `income-assessment-service` and provides the code-navigation model needed to understand how requests move through the service.

It is primarily intended to answer questions such as:

* Which component receives a request?
* Which layer owns request orchestration?
* How is the implementation version selected?
* Which implementation actually executes a request?
* Where is application state persisted?
* Which operations are synchronous, asynchronous, or scheduled?
* Which classes should be inspected first when debugging a journey?
* How does the service communicate with downstream systems?

The document focuses on **current implementation anchors**, with particular emphasis on the Revamp/versioned execution model.

---

# 2. Architecture in One View

`income-assessment-service` is a Kotlin + Spring Boot + WebFlux application that acts as a **stateful business orchestrator**.

At a high level:


                         +----------------------+
                         |  Upstream Systems    |
                         |  / UI / Services     |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         |   REST Controllers   |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         |     KeyData /        |
                         | Request Context      |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         | CommonVersionResolver|
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         |    ServiceFacade     |
                         | executeWithVersion() |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         | RevampServiceFactory |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         | Versioned Service    |
                         | V3 / other versions |
                         +----------+-----------+
                                    |
               +--------------------+--------------------+
               |                    |                    |
               v                    v                    v
        +-------------+      +-------------+      +-------------+
        | MongoDB     |      | Gateways /   |      | Kafka       |
        | Repositories|      | Clients      |      | Producers   |
        +-------------+      +------+------+      +-------------+
                                    |
                       +------------+-------------+
                       |            |             |
                       v            v             v
                    Perfios    Zenith/AA-Orch   Other
                                             downstream systems


There are also execution paths that do not begin with a REST request:


Kafka Event
    |
    v
Kafka Consumer
    |
    v
Application / Domain Processing
    |
    v
MongoDB / Integration / Kafka Event


and:


Scheduled Job
    |
    v
Scheduler
    |
    v
Application / Domain Processing
    |
    v
MongoDB / Integration / Kafka


Therefore, the complete runtime architecture is not limited to the HTTP request-response path.

---

# 3. Runtime Foundation

The service is implemented as a Spring Boot application using Kotlin and Spring WebFlux.

The runtime/build configuration indicates the use of:

* Kotlin/JVM
* Java 17
* Spring WebFlux
* Spring Security
* Spring Validation
* Reactor
* Reactive MongoDB
* Reactor Kafka
* Scheduling
* ShedLock
* OpenAPI
* Enterprise/internal platform starters

Application bootstrap is handled by:


src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/Application.kt


The application enables infrastructure such as caching and scheduling.

### Architectural implications

#### Reactive execution

Reactive types such as `Mono` and `Flux` appear across controllers, services, repositories, and event consumers.

This means request and event flows should be traced with the reactive chain rather than assuming conventional blocking execution.

#### Scheduling

Schedulers are part of the runtime architecture.

Some application state changes can therefore originate from scheduled processing rather than directly from an HTTP request or Kafka callback.

#### Internal platform infrastructure

The service relies on shared/internal platform components for areas such as:

* MongoDB
* Kafka
* callbacks
* monitoring
* logging
* migrations
* API documentation

The exact behavior of these platform components should be determined from the service configuration and implementation rather than inferred from the dependency name alone.

---

# 4. Main Architectural Layers

The service can be understood through the following logical layers:


Controller
    ↓
Version / Routing
    ↓
Facade
    ↓
Versioned Application Service
    ↓
Domain / Business Processing
    ↓
Repository / Gateway / Event Infrastructure


The repository does not represent these layers as completely isolated modules. In particular, the main application service contains significant orchestration logic and coordinates multiple dependencies.

---

## 4.1 Controller Layer

Controllers define the HTTP-facing API surface.

Primary location:


src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/controller/


Important controllers include:

* `IncomeAssessmentApplicationController`
* `IncomeAssessmentApplicationControllerV2`
* `InitiateBsaController`
* `ZenithCallbackController`
* `PerfiosCallbackController`

`IncomeAssessmentApplicationController` is the primary application controller and exposes operations including:

* application initiation
* validation
* status retrieval
* link generation
* event publication
* duration/configuration/state lookup
* income-details lookup

`InitiateBsaController` provides a specialized entry point for the AA-Orchestrator BSA initiation flow.

### Controller responsibility

Controllers generally perform request-level responsibilities such as:

1. Receive HTTP request.
2. Extract required request/context information.
3. Construct `KeyData` where required.
4. Perform controller-level validation/precondition checks.
5. Prime version context when applicable.
6. Delegate execution to the appropriate facade.

The controller should therefore **not be assumed to contain the main business orchestration logic**.

---

# 5. Versioned Execution Architecture

Version resolution is one of the most important architectural characteristics of this service.

A controller does not necessarily map directly to a single implementation class.

The effective execution path is:


HTTP Request
     ↓
Controller
     ↓
KeyData
     ↓
CommonVersionResolver
     ↓
ServiceFacade
     ↓
RevampServiceFactory
     ↓
Versioned Implementation
     ↓
Business Execution


This indirection allows different versions of application behavior to be selected based on request/application context.

---

## 5.1 KeyData

`KeyData` acts as an important carrier of context used during version resolution and downstream execution.

Depending on the flow, the resolution context can include information such as:

* partner/product context
* authorization/JWT information
* statement ID
* common client transaction ID
* income assessment ID
* application reference ID

When debugging version-related behavior, inspect how `KeyData` is constructed before looking at the final service implementation.

---

## 5.2 CommonVersionResolver

Primary anchor:


src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/
revamp/versionresolvers/CommonVersionResolver.kt


`CommonVersionResolver` determines the version that should execute a request.

Conceptually, resolution happens in two stages:


Request Context
      |
      v
Determine Version Bucket
      |
      v
Determine Facade-specific Version
      |
      v
Selected Version


The bucket/version can depend on request context, partner/product configuration, JWT information, or identifiers associated with an existing income-assessment application.

If version resolution cannot determine a version, the implementation falls back to the configured/default Revamp version.

---

## 5.3 Bucket Priming

Controllers can call:


CommonVersionResolver.primeBucket(...)


before invoking a facade.

The resolved bucket is stored in Reactor context.

Later, `ServiceFacade.executeWithVersion(...)` can reuse this information instead of repeating the initial bucket-resolution step.

Conceptually:


Controller
    |
    +--> primeBucket()
    |
    v
Facade
    |
    +--> executeWithVersion()
            |
            +--> reuse Reactor context


This is important when tracing nested calls because the version context may be established earlier than the actual service invocation.

---

## 5.4 ServiceFacade

Primary anchor:


src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/
revamp/facade/ServiceFacade.kt


The facade layer hides implementation-version selection from callers.

Typical execution:


Caller
  ↓
Facade method
  ↓
executeWithVersion(...)
  ↓
Version resolution
  ↓
Factory
  ↓
Concrete implementation


`IncomeAssessmentApplicationServiceFacade` is the main application-lifecycle facade.

It provides operations including:

* `initiateApplication`
* `generateLink`
* `uploadStatement`
* `validate`
* `startProcess`
* `initiateBsa`
* document/status-related operations

### Architectural role

The facade should be considered an **architectural routing layer**, not merely a pass-through service.

Its key responsibility is to ensure that the caller reaches the correct versioned implementation.

---

## 5.5 RevampServiceFactory

Primary anchor:


src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/
revamp/factory/RevampServiceFactory.kt


The factory maintains a mapping between versions and concrete strategy implementations.

Conceptually:


Version
   |
   v
RevampServiceFactory
   |
   +---- V3
   +---- V4 / other supported versions
   +---- ...


If a requested version is not supported, the factory raises:


UnsupportedRevampVersionException


Therefore, when a request reaches an unexpected implementation, inspect:


CommonVersionResolver
        ↓
ServiceFacade
        ↓
RevampServiceFactory


rather than starting directly from the implementation class.

---

# 6. Versioned Application Service

The primary current implementation anchor is:


src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/
revamp/service/impl/IncomeAssessmentApplicationServiceV3.kt


`IncomeAssessmentApplicationServiceV3` contains substantial application-level orchestration.

Its dependencies include components associated with:

* repositories
* callback processing
* rules/configuration
* gateway facades
* document services
* event publishing
* Mongo operations
* Finacle
* Zenith
* Perfios
* FinFort
* observability

This makes the V3 application service an important **orchestration boundary** for the current execution model.

When investigating the behavior of a V3 application journey, this class is one of the first implementation anchors to inspect.

---

# 7. Persistence Architecture

MongoDB is the primary persistence mechanism for income-assessment application state.

Important persistence components include:


src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/repository/


Key components include:

* `IncomeAssessmentRepository`
* `DocumentRepository`
* `IncomeAssessmentApplicationAccessor`

---

## 7.1 IncomeAssessmentApplicationDao

The central persisted application entity is:


IncomeAssessmentApplicationDao


It represents the long-lived state of an income-assessment application.

The persisted state includes information such as:

* `incomeAssessmentId`
* `applicationReferenceId`
* `partnerId`
* `productCode`
* assessment medium
* occupation
* journey mode
* current status
* retry/attempt information
* downstream transaction references
* callback timestamps
* document references
* rule outputs
* Finacle/Zenith/ITR-related context
* user decision information

The exact fields and persistence behavior are documented in:


06-database.md


### Architectural implication

The service is not a stateless request proxy.

It coordinates a **long-running business process whose state is persisted over time**.

A journey may therefore look like:


Initial API request
       ↓
Create/update application
       ↓
External processing
       ↓
Callback/event
       ↓
Update application state
       ↓
Continue processing
       ↓
Final assessment state


For debugging a journey, the persisted application record is often one of the most important objects to inspect.

---

# 8. Integration Architecture

The application-service layer communicates with downstream systems through gateway/client abstractions.

Important integration anchors include:


ZenithOrchestratorGateway
DocumentServiceClient
AuthServiceClient
FinFortClient
DgClient


There are also bank-statement-related gateway/facade components responsible for operations such as transaction initiation, uploads, and report processing.

Configuration contains endpoint groups associated with systems such as:

* personal/auto/home orchestrators
* customer services
* Document Service
* CAP
* DG
* ESB
* Perfios
* Zenith
* authentication/token services
* master-data services

The service therefore acts as both:

1. a **business-process orchestrator**, and
2. an **integration hub**.

Detailed integration behavior belongs in:


05-integrations.md


---

# 9. Synchronous Request Architecture

The typical HTTP execution path is:


HTTP Request
    ↓
Controller
    ↓
KeyData / Request Context
    ↓
Version Bucket Priming
    ↓
Facade
    ↓
Version Resolution
    ↓
Versioned Service
    ↓
Business Processing
    ↓
Mongo / Downstream APIs / Kafka
    ↓
Response


Examples of important endpoints include:


POST /income-assessment-service/v1/initiate-application

GET /income-assessment-service/v1/generate-link

GET /income-assessment-service/v1/validate

GET /income-assessment-service/v1/status

POST /income-assessment-service/v1/bsa/initiate


The exact API contract belongs in:


03-api-contracts.md


The important architectural point is that these APIs can initiate or continue **stateful, multi-step journeys**.

They should therefore not be treated as simple CRUD endpoints.

---

# 10. Asynchronous Architecture

Kafka is an important part of the runtime architecture.

The service contains consumers for callback and event-driven processing.

Examples include consumers handling:

* Perfios callback received
* Perfios callback timeout/not received
* Zenith callback received
* Zenith callback timeout/not received
* FinFort callback received/not received
* back-office notifications
* FCU verification reset
* ITR assessment initiation

---

## 10.1 Typical Callback Processing

A callback consumer generally follows a pattern similar to:


Kafka Event
    ↓
Consumer
    ↓
Identify Income Assessment Application
    ↓
Fetch Mongo Application State
    ↓
Validate Current State / Transition
    ↓
Update Status / Metadata
    ↓
Continue Business Processing
    ↓
Publish Internal Event


This pattern is particularly important for external-provider journeys where the initial API request and final assessment result happen at different points in time.

---

## 10.2 Event Producer

`IncomeAssessmentApplicationEventProducer` is used by application orchestration and callback-processing components to publish lifecycle events.

Therefore:


HTTP flow
   └──> business processing
            └──> event publication

Kafka callback
   └──> state update
            └──> event publication


The complete event model, topic mapping, and event identifiers are documented in:


07-kafka-events.md


---

# 11. Scheduler Architecture

Not all processing starts from an HTTP request or Kafka event.

The service also contains scheduled jobs.

Current scheduler anchors include:


src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/
FIP/service/AAFipSyncScheduler.kt


and:


src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/
itr/scheduler/ItrTransactionStatusScheduler.kt


Examples include:


AAFipSyncScheduler.syncFipsToMasterData()

ItrTransactionStatusScheduler.run()


ShedLock is used for distributed coordination of scheduled processing.

The architectural model is therefore:


                +--> HTTP Request
                |
Income          +--> Kafka Event
Assessment      |
Processing      +--> Scheduled Job
                |
                v
        Application Processing
                |
       +--------+--------+
       |        |        |
       v        v        v
    Mongo    External   Kafka
             Systems


---

# 12. Security and Request Context

The service uses request/context information as part of its execution model.

Important observations include:

* Several APIs require an `Authorization` header.
* JWT-derived information can participate in version resolution.
* Some endpoints are configured differently from authenticated application APIs.
* `KeyData` carries context used during routing and downstream execution.

Therefore, when debugging behavior that differs between requests, inspect not only the request payload but also:


Authorization / JWT context
        +
KeyData
        +
Partner/Product context
        +
Application identifiers


A difference in request context can result in a different resolved version or execution path.

---

# 13. V2 vs V3

The repository contains both older and newer execution paths.

`IncomeAssessmentApplicationControllerV2` exposes a narrower API surface, while the Revamp architecture provides the versioned execution model.

For most current application behavior:


Start with V3


Primary anchor:


revamp/service/impl/IncomeAssessmentApplicationServiceV3.kt


Inspect V2 when:

* The endpoint explicitly routes through V2.
* Investigating backward compatibility.
* Debugging a legacy journey.
* Comparing historical behavior.
* A regression appears related to an older implementation.

Do not assume V2 behavior applies to V3.

When in doubt, trace the actual routing chain:


Controller
   ↓
KeyData
   ↓
CommonVersionResolver
   ↓
ServiceFacade
   ↓
RevampServiceFactory
   ↓
Concrete Version


---

# 14. Component Responsibility Matrix

| Component                              | Primary Responsibility                                         |
| -------------------------------------- | -------------------------------------------------------------- |
| Controller                             | Receive HTTP request and delegate execution                    |
| `KeyData`                              | Carry request/application context used for routing             |
| `CommonVersionResolver`                | Resolve version bucket and implementation version              |
| `ServiceFacade`                        | Route execution to the appropriate version                     |
| `RevampServiceFactory`                 | Map resolved version to concrete strategy                      |
| `IncomeAssessmentApplicationServiceV3` | Orchestrate current application journeys                       |
| Repository                             | Read/write persisted application state                         |
| Gateway/Client                         | Communicate with downstream systems                            |
| Kafka Consumer                         | Process asynchronous events/callbacks                          |
| Kafka Producer                         | Publish income-assessment lifecycle events                     |
| Scheduler                              | Execute time-driven/background workflows                       |
| Configuration                          | Control endpoints, routing, integrations, and runtime behavior |

---

# 15. Debugging Navigation

When investigating a request, the recommended order is:

### Step 1 — Find the entry point

Start with:


controller/


Identify the controller and endpoint handling the request.

### Step 2 — Identify request context

Inspect:


KeyData
Authorization/JWT
partner/product information
incomeAssessmentId
applicationReferenceId


### Step 3 — Trace version resolution

Inspect:


CommonVersionResolver
        ↓
ServiceFacade
        ↓
RevampServiceFactory


Determine which implementation version actually executes.

### Step 4 — Trace the implementation

For V3:


IncomeAssessmentApplicationServiceV3


Follow the relevant method and its downstream calls.

### Step 5 — Inspect state

Check:


IncomeAssessmentApplicationDao
IncomeAssessmentRepository


Determine the current persisted status and relevant transaction/reference IDs.

### Step 6 — Inspect integrations

Follow the relevant:


Gateway
Client
Facade


to determine which downstream system was called.

### Step 7 — Check asynchronous processing

If the flow does not complete synchronously, inspect:


Kafka consumer
    ↓
Mongo state update
    ↓
Follow-up processing
    ↓
Kafka producer


### Step 8 — Check scheduled processing

If the expected state transition does not originate from an API or callback, check the relevant scheduler.

---

# 16. Configuration as Part of Architecture

Runtime behavior is not determined exclusively by Kotlin code.

Important configuration is maintained in:


src/main/resources/application.yaml


and supporting configuration resources under:


src/main/resources/configurations/
src/main/resources/transformers/


Configuration can influence:

* downstream endpoints
* authentication
* event/topic configuration
* feature/toggle behavior
* integration behavior
* versioning/routing
* transformation logic

When investigating behavior that appears inconsistent with the code, configuration should be checked alongside the Kotlin implementation.

Detailed configuration information belongs in:


09-configuration.md


---

# 17. Architecture-Level Mental Model

For most developer questions, the following model is sufficient as the starting point:


                 REQUEST / EVENT
                       |
                       v
              +----------------+
              | Entry Point    |
              | Controller /   |
              | Consumer /     |
              | Scheduler      |
              +-------+--------+
                      |
                      v
              +----------------+
              | Request Context|
              | / KeyData      |
              +-------+--------+
                      |
                      v
              +----------------+
              | Version        |
              | Resolution     |
              +-------+--------+
                      |
                      v
              +----------------+
              | Facade         |
              +-------+--------+
                      |
                      v
              +----------------+
              | Versioned      |
              | Application    |
              | Service        |
              +-------+--------+
                      |
          +-----------+-----------+
          |           |           |
          v           v           v
       MongoDB    Downstream     Kafka
                  Systems
          |           |           |
          +-----------+-----------+
                      |
                      v
                Updated State


The most important architectural idea is:

> **Income Assessment is a versioned, stateful orchestration service.**

A request or event enters through an HTTP controller, Kafka consumer, or scheduler; execution is routed through the version-resolution/facade mechanism; the selected application service coordinates business processing; and the journey persists state while interacting with downstream systems and asynchronous infrastructure.

---

# 18. Primary Code Anchors

| Area                      | Repository Path                                                                                                          |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| Application bootstrap     | `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/Application.kt`                                                 |
| Controllers               | `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/controller/`                                                    |
| Version resolver          | `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/revamp/versionresolvers/CommonVersionResolver.kt`               |
| Facade                    | `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/revamp/facade/ServiceFacade.kt`                                 |
| Application facade        | `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/revamp/facade/impl/IncomeAssessmentApplicationServiceFacade.kt` |
| Version factory           | `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/revamp/factory/RevampServiceFactory.kt`                         |
| V3 application service    | `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/revamp/service/impl/IncomeAssessmentApplicationServiceV3.kt`    |
| Repositories              | `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/repository/`                                                    |
| Kafka consumers           | `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/kafka/consumer/`                                                |
| Zenith gateway            | `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/zenithorch/gateway/ZenithOrchestratorGateway.kt`                |
| Runtime configuration     | `src/main/resources/application.yaml`                                                                                    |
| Configuration definitions | `src/main/resources/configurations/`                                                                                     |
| Transformers              | `src/main/resources/transformers/`                                                                                       |

---

# 19. Related Knowledge Base Documents

Use this document for architecture and code-navigation questions.

For deeper questions, use:

| Question                                        | Document                |
| ----------------------------------------------- | ----------------------- |
| How does a specific request flow end-to-end?    | `02-request-flows.md`   |
| What is the exact API contract?                 | `03-api-contracts.md`   |
| Which business rule/status/handler is involved? | `04-business-logic.md`  |
| How does Perfios/CAP/Zenith/etc. work?          | `05-integrations.md`    |
| Where is application state stored?              | `06-database.md`        |
| Which Kafka events/topics are involved?         | `07-kafka-events.md`    |
| Why did a request fail?                         | `08-error-handling.md`  |
| Which configuration affects behavior?           | `09-configuration.md`   |
| How should a developer investigate an issue?    | `10-troubleshooting.md` |
| What does an internal term mean?                | `11-glossary.md`        |
| How does a specific business journey work?      | `flows/*.md`            |

---

# 20. RAG Retrieval Guidance

This document is the preferred source when a developer asks about:

* service architecture
* component responsibilities
* request routing
* version resolution
* V2/V3 execution
* synchronous vs asynchronous processing
* scheduler architecture
* persistence role
* major integration boundaries
* where to start debugging
* which classes to inspect

For implementation-specific questions, prefer retrieving this architecture document together with the relevant source-code chunks.

For example:


Question:
"Which handler is used for FOUR_WHEELER_PERSONAL?"

Retrieve:
04-business-logic.md
+
relevant Kotlin handler/source code



Question:
"What happens after /generate-link?"

Retrieve:
02-request-flows.md
+
03-api-contracts.md
+
05-integrations.md
+
relevant Kotlin implementation



Question:
"Why did this application execute V3?"

Retrieve:
01-architecture.md
+
CommonVersionResolver.kt
+
ServiceFacade.kt
+
RevampServiceFactory.kt
+
relevant configuration


The architecture document should provide the **structural context**, while source-code chunks provide the **implementation evidence**.

---

# 21. Architecture Source References

The architecture described above is derived primarily from the following repository locations:


src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/Application.kt

src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/controller/

src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/revamp/facade/

src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/revamp/factory/

src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/revamp/versionresolvers/

src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/revamp/service/impl/

src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/repository/

src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/kafka/

src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/zenithorch/

src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/FIP/

src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/itr/

src/main/resources/application.yaml

src/main/resources/configurations/

src/main/resources/transformers/


When implementation and documentation differ, verify behavior against the current repository implementation and configuration.
