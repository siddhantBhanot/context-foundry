---

service: income-assessment-service
document_type: request-flows
topic: runtime-request-flows
source: repository-code-and-config
language: kotlin
framework: spring-webflux
-------------------------

# Request Flows

This document is the **master map of request execution paths** in `income-assessment-service`.

Use it to answer questions such as:

* What happens after `POST /income-assessment-service/v1/initiate-application`?
* How does the service decide which implementation/version to execute?
* What happens when `/generate-link` is called?
* How does a Perfios callback update an IA application?
* When is the Zenith / AA-Orchestrator BSA path used?
* Which application state and configuration values control the next step?
* Which component should be inspected when a request or callback is stuck?

Detailed vendor-specific flows are documented separately under `flows/`.

---

## 1. Runtime request execution model

Most API-driven requests pass through the same high-level execution boundary:


HTTP Request
    ↓
REST Controller
    ↓
Build KeyData / request context
    ↓
CommonVersionResolver.primeBucket(...)
    ↓
Version-aware ServiceFacade
    ↓
RevampServiceFactory.getStrategy(version)
    ↓
Versioned service implementation
    ↓
Mongo / External Gateway / Kafka / Callback / Scheduler
    ↓
Application state update
    ↓
HTTP response or asynchronous continuation


The controller does **not** directly select the final business implementation.

Version and routing decisions happen through the resolver/facade/factory chain. Therefore, when debugging an endpoint, do not stop at the controller. Trace:


Controller
→ KeyData
→ CommonVersionResolver
→ ServiceFacade
→ RevampServiceFactory
→ Versioned Service


The primary current implementation anchor is:


src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/revamp/service/impl/IncomeAssessmentApplicationServiceV3.kt


V2 or older implementations should be inspected only when the resolved version or a regression requires them.

---

## 2. Core lifecycle

An IA application is a **stateful, multi-step orchestration flow**, rather than a simple request/response CRUD operation.

A typical lifecycle can be understood as:


Create / Resume Application
        ↓
Resolve Assessment Medium + Version
        ↓
Choose Processing Path
        ↓
Initiate Vendor / Statement / BSA / ITR Processing
        ↓
Persist Transaction + Application State
        ↓
Wait for Callback / Polling / Async Event
        ↓
Process Result
        ↓
Apply Validation / Business Rules
        ↓
Update Application State
        ↓
Publish Lifecycle Event
        ↓
Expose Status / Income / Document Details


The exact path depends on request context, configuration, resolved IA version, assessment medium, and the current application state.

---

# 3. Common API execution path

For the main IA APIs, the request enters through a controller and is routed into the version-aware service layer.

### Common execution sequence

1. Controller receives the request.
2. Controller constructs the relevant `KeyData`.
3. `CommonVersionResolver.primeBucket(...)` resolves the applicable version bucket.
4. The request is delegated to a version-aware facade.
5. `ServiceFacade.executeWithVersion(...)` resolves the implementation.
6. `RevampServiceFactory.getStrategy(version)` returns the appropriate strategy.
7. The versioned service performs business orchestration.
8. The service reads/writes MongoDB and/or invokes downstream systems.
9. The response is returned, or the request creates an asynchronous continuation.

### Important controllers


src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/controller/


Relevant controllers include:

* `IncomeAssessmentApplicationController`
* `IncomeAssessmentApplicationControllerV2`
* `InitiateBsaController`
* `PerfiosCallbackController`
* `ZenithCallbackController`

### Important routing components


src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/revamp/versionresolvers/CommonVersionResolver.kt
src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/revamp/facade/ServiceFacade.kt
src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/revamp/facade/IncomeAssessmentApplicationServiceFacade.kt
src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/revamp/service/factory/RevampServiceFactory.kt


---

# 4. Application initiation flow

Primary endpoint:


POST /income-assessment-service/v1/initiate-application


High-level flow:


Caller
  ↓
IncomeAssessmentApplicationController
  ↓
Build KeyData
  ↓
Resolve version bucket
  ↓
IncomeAssessmentApplicationServiceFacade
  ↓
Resolved versioned implementation
  ↓
Create / initialize IA application
  ↓
Persist IncomeAssessmentApplicationDao
  ↓
Return initiation response


The initiation request establishes the application context used by subsequent IA operations.

Important information associated with the application includes values such as:

* partner/product
* assessment medium
* journey information
* application/reference identifiers
* current IA status
* vendor transaction identifiers
* retry/attempt information
* downstream transaction context

The persisted application should therefore be treated as the primary state anchor for subsequent asynchronous processing.

### Source anchors


src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/controller/IncomeAssessmentApplicationController.kt
src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/repository/IncomeAssessmentRepository.kt
src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/domain/IncomeAssessmentApplication.kt
src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/revamp/service/impl/IncomeAssessmentApplicationServiceV3.kt


---

# 5. Statement / Perfios flow

The standard statement-processing path is centered around the statement/Perfios orchestration implemented by the versioned service.

Important V3 operations include:


generateLink(...)
startProcess(...)
uploadStatement(...)
completeTransaction(...)


A simplified flow is:


IA Application
    ↓
Generate / initiate vendor transaction
    ↓
Generate link or start processing
    ↓
User / upstream system interacts with vendor
    ↓
Statement/document data is uploaded when required
    ↓
Perfios transaction progresses
    ↓
Perfios callback / timeout event
    ↓
IA application is located
    ↓
State / attempt / timestamp updated
    ↓
Result/report processing
    ↓
Validation / business rules
    ↓
Final application state


The exact branch depends on the assessment medium and runtime configuration.

### Important implementation anchor


src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/revamp/service/impl/IncomeAssessmentApplicationServiceV3.kt


### Callback anchor


src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/kafka/consumer/PerfiosCallbackReceivedConsumer.kt


### Detailed flow

See:


flows/perfios-flow.md


---

# 6. Zenith / AA-Orchestrator BSA flow

The service also supports a BSA path through Zenith / AA-Orchestrator.

The public IA endpoint is:


POST /income-assessment-service/v1/bsa/initiate


The controller delegates the request into the same version-aware orchestration model.

High-level flow:


Caller
  ↓
InitiateBsaController
  ↓
Build request context / KeyData
  ↓
Version-aware service
  ↓
Determine applicable BSA route
  ↓
ZenithOrchestratorGateway
  ↓
AA-Orchestrator
  ↓
BSA processing
  ↓
Callback / async event
  ↓
IA application state update


The configured downstream endpoint is:


platform.gateway.initiateBsaEnc
→ /aa-orch/fiu/api/v1/initiateBSA


The actual route taken depends on journey configuration and runtime feature toggles.

Relevant configuration includes toggles such as:


enableZenithOrchAPI
enableFinaclePdf


Do not treat these toggles as isolated switches. Their effect must be understood together with the partner/product configuration and assessment journey.

### Source anchors


src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/controller/InitiateBsaController.kt
src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/revamp/service/impl/IncomeAssessmentApplicationServiceV3.kt
src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/utils/ConfigFetcher.kt
src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/zenithorch/gateway/ZenithOrchestratorGateway.kt
src/main/resources/application.yaml


### Detailed flow

See:


flows/income-assessment-flow.md


---

# 7. Finacle-assisted statement path

Some journeys can use Finacle as part of the statement-processing flow.

At a high level:


IA request
   ↓
Determine journey/configuration
   ↓
Fetch or obtain statement/PDF information from Finacle
   ↓
Evaluate configured processing route
   ├── Classic statement/upload path
   └── Zenith / AA-Orchestrator BSA path


The branch is controlled by runtime configuration and feature toggles.

Relevant implementation/configuration anchors include:


src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/revamp/service/impl/IncomeAssessmentApplicationServiceV3.kt
src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/utils/ConfigFetcher.kt
src/main/resources/application.yaml


When debugging this path, inspect the resolved partner/product configuration rather than assuming that every Finacle-assisted request follows the same downstream route.

---

# 8. Callback and asynchronous processing

IA processing is not completed entirely within the original HTTP request.

Vendor callbacks and internal events continue the application lifecycle asynchronously.

Important callback/event paths include:


Perfios callback
Zenith callback
FinFort callback
ITR-related events
Notification events
Other IA lifecycle events


A common callback-consumer pattern is:


Kafka Event
   ↓
Consumer
   ↓
Extract transaction/reference identifiers
   ↓
Fetch IncomeAssessmentApplicationDao
   ↓
Check current application state
   ↓
Validate whether transition is allowed
   ↓
Update state / timestamps / attempts / vendor references
   ↓
Persist MongoDB changes
   ↓
Publish normalized IA event
   ↓
Downstream processing continues


The application record is therefore the bridge between the original synchronous request and later asynchronous processing.

### Perfios callback


src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/kafka/consumer/PerfiosCallbackReceivedConsumer.kt


### Zenith callback


src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/kafka/consumer/ZenithCallbackReceivedConsumer.kt


### Event producer


src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/kafka/event/IncomeAssessmentApplicationEvent.kt
src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/kafka/producer/IncomeAssessmentApplicationEventProducer.kt


### Kafka configuration


src/main/resources/application.yaml


---

# 9. Status, validation, and result retrieval

After processing has started, upstream callers use status and validation APIs to determine the current state and obtain assessment results.

Important APIs include:


GET /income-assessment-service/v1/validate
GET /income-assessment-service/v1/status
GET /income-assessment-service/v1/application/status
GET /income-assessment-service/v1/income-details


Conceptually:


Caller
  ↓
Status / Validation API
  ↓
Version-aware facade
  ↓
Application / document / assessment data lookup
  ↓
Evaluate current persisted state
  ↓
Return status / validation / income details


These APIs should generally be understood as **read/validation operations over a stateful IA process**, rather than independent business flows.

For debugging, start with:


IncomeAssessmentApplicationDao
        ↓
current status
        ↓
vendor transaction/reference identifiers
        ↓
callback/event history
        ↓
versioned service implementation


---

# 10. Application state as the flow anchor

`IncomeAssessmentApplicationDao` is the central persistence object connecting different stages of an IA journey.

Relevant state/context can include:

* application and assessment identifiers
* partner/product
* assessment medium
* occupation/journey information
* current IA status
* retry/attempt information
* vendor transaction identifiers
* callback information
* document references
* assessment outputs
* Finacle / Zenith / ITR context
* downstream processing information

This means that the same application can move through multiple execution mechanisms:


HTTP request
   ↓
Mongo state
   ↓
Vendor interaction
   ↓
Kafka callback
   ↓
Mongo state update
   ↓
Business processing
   ↓
Kafka event
   ↓
Status/result API


When tracing a real issue, the application record and its identifiers should be used to connect these stages.

---

# 11. Routing and branching controls

The endpoint alone does not determine the complete execution path.

Important routing inputs include:

### Assessment medium

Examples include:


STATEMENT
STATEMENT_SCAN_AND_UPLOAD
ITR_UPLOAD
AA / BSA-related variants


### Partner / product configuration

Partner and product configuration can influence:

* applicable IA version
* processing route
* vendor/integration selection
* feature toggles
* journey-specific behavior

### IA version

The version-routing chain is:


Request context
   ↓
CommonVersionResolver
   ↓
Version bucket
   ↓
VersionBuckets / IA version
   ↓
RevampServiceFactory
   ↓
Versioned implementation


### Current application state

The persisted `IncomeAssessmentApplicationDao` influences whether an operation is allowed and what processing branch should continue.

### Runtime feature toggles

Configuration-driven toggles can alter the downstream path.

Important examples include:


enableZenithOrchAPI
enableFinaclePdf


### Source anchors


src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/revamp/versionresolvers/CommonVersionResolver.kt
src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/utils/ConfigFetcher.kt
src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/domain/IncomeAssessmentApplication.kt


---

# 12. Request flow by developer question

This section intentionally maps common developer questions to the files/flows that should be traced.

| Developer question                                              | Start here                              | Then trace                                                                 |
| --------------------------------------------------------------- | --------------------------------------- | -------------------------------------------------------------------------- |
| What happens after `/initiate-application`?                     | `IncomeAssessmentApplicationController` | Facade → resolved version → `IncomeAssessmentApplicationServiceV3` → Mongo |
| What happens after `/generate-link`?                            | Controller method                       | Facade → versioned service → vendor gateway → application state            |
| Where does Perfios callback go?                                 | `PerfiosCallbackReceivedConsumer`       | Application lookup → state guard → Mongo update → downstream event         |
| Where does Zenith BSA start?                                    | `InitiateBsaController`                 | Facade/service → `ZenithOrchestratorGateway` → AA-Orchestrator             |
| Why did this request execute V3?                                | `CommonVersionResolver`                 | Version bucket → `ServiceFacade` → `RevampServiceFactory`                  |
| Why did this journey choose Zenith instead of the classic path? | `ConfigFetcher` / V3 flow               | Partner/product config → feature toggles → route decision                  |
| What is the current application state?                          | `IncomeAssessmentApplicationDao`        | Status + transaction IDs + callback/event context                          |
| Where should I debug a stuck callback?                          | Kafka consumer                          | Application lookup → state guard → persistence → next event                |
| How does the UI journey continue after vendor initiation?       | API + vendor flow                       | `generate-link` / `start-process` → callback/event → status APIs           |

This table should be kept aligned with the actual repository as implementation changes.

---

# 13. Debugging flow

For an unknown production/lower-environment issue, use the following tracing strategy:


1. Identify API / Kafka event / scheduler
          ↓
2. Identify application / transaction identifier
          ↓
3. Inspect IncomeAssessmentApplicationDao
          ↓
4. Determine current status + assessment medium
          ↓
5. Determine resolved IA version
          ↓
6. Trace versioned service implementation
          ↓
7. Inspect downstream gateway/client
          ↓
8. Check callback/event path
          ↓
9. Check state transition / retry / timeout logic


### If the issue starts from an HTTP API

Start with:


Controller
→ KeyData
→ CommonVersionResolver
→ ServiceFacade
→ RevampServiceFactory
→ Versioned Service


### If the issue starts from a callback

Start with:


Kafka topic/event
→ Consumer
→ Application lookup
→ State guard
→ Mongo update
→ Next event / processing


### If the issue is about routing

Start with:


Partner/Product
→ ConfigFetcher
→ Feature toggles
→ Assessment medium
→ CommonVersionResolver
→ Versioned implementation


---

# 14. Detailed flow documents

This file is intentionally the **master request-flow map**.

Detailed journey tracing should live in the following documents:


flows/perfios-flow.md
flows/cap-flow.md
flows/income-assessment-flow.md


Use these documents when the question requires step-by-step tracing through a specific integration or business journey.

---

# 15. Source-of-truth rules

For flow-related questions, use the following priority:

1. **Current Kotlin implementation**
2. **Current application/configuration**
3. **Curated Markdown flow documentation**
4. Older implementation/version documentation

If this document conflicts with the current code, the code is the source of truth.

When documenting a flow, prefer concrete implementation anchors such as:


Controller method
→ Service method
→ Gateway/client method
→ Repository method
→ Kafka consumer/producer
→ Configuration key


Avoid documenting only class names when a specific method provides a stronger retrieval anchor.

---

# 16. RAG retrieval guidance

This document should answer **“where does the request go?”**

For best retrieval:

* Keep endpoint names exact.
* Keep Kafka event/topic names exact where known.
* Keep method names such as `generateLink`, `startProcess`, `uploadStatement`, and `completeTransaction`.
* Keep important configuration keys exact.
* Keep component/class names unchanged.
* Preserve the distinction between synchronous HTTP execution and asynchronous callback/event execution.
* Link high-level flow descriptions to the deeper `flows/*.md` documents.
* Prefer short, traceable flow sections over large narrative explanations.

The architecture document explains **what components exist and how they relate**.

This document explains **how a request moves through those components**.

Kotlin source code remains the implementation-level evidence.

---

## Related knowledge

* `00-overview.md` — service purpose, responsibilities, integrations, and boundaries
* `01-architecture.md` — runtime architecture and component relationships
* `03-api-contracts.md` — API request/response contracts
* `04-business-logic.md` — domain/business decision logic
* `05-integrations.md` — downstream integration details
* `10-troubleshooting.md` — symptom-driven debugging and known failure modes
* `flows/perfios-flow.md` — detailed Perfios journey
* `flows/cap-flow.md` — detailed CAP journey
* `flows/income-assessment-flow.md` — detailed IA journey
