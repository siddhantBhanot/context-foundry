# Income Assessment End-to-End Flow

## 1. Purpose

This document describes the **end-to-end lifecycle of an Income Assessment (IA) journey**.

Use it to answer:

* How does an IA application move from initiation to completion?
* Which API starts each stage?
* Where does version routing happen?
* When is MongoDB state created or updated?
* Where do external vendors participate?
* Where do callbacks and Kafka events enter the flow?
* How are business outcomes determined?
* Where can the journey branch into different assessment mediums?
* How should a production IA journey be traced end-to-end?

This document is the **flow/navigation layer**.

Detailed business rules belong in `business-logic.md`, external API behavior in `integrations.md`, persistence in `database.md`, asynchronous propagation in `kafka-events.md`, failure semantics in `error-handling.md`, and runtime switches in `configurations.md`.

---

# 2. High-Level Lifecycle

The IA journey can be represented as:


Partner / Upstream Request
        ↓
Initiate IA Application
        ↓
Request Context + Version Resolution
        ↓
Create / Reuse IA Application
        ↓
Determine Journey / Assessment Medium
        ↓
Generate Link / Start Process / Direct Flow
        ↓
External Vendor Journey
        ↓
Callback / Status Polling / Event
        ↓
Process Vendor Result
        ↓
Business Validation
        ↓
Update IA State
        ↓
Publish Event / Persist Documents / Sync Downstream
        ↓
Terminal or Next-Step Status


The actual path depends on:

* partner
* product
* request context
* resolved IA version
* configured feature toggles
* selected assessment medium
* vendor response
* callback/event availability
* business validation outcome

Therefore there is **not one universal linear IA path**.

---

# 3. End-to-End Flow

## Stage 1 — IA Application Initiation

An upstream partner or system initiates an IA application through:


POST /income-assessment-service/v1/initiate-application


The controller validates and constructs the request context required by the downstream service layer.

The application then enters the internal orchestration pipeline:


Controller
    ↓
CommonVersionResolver
    ↓
ServiceFacade
    ↓
Resolved versioned service


The service determines whether the IA application should be created or an existing application should be reused.

### Key responsibilities

* validate request context
* identify partner/product
* construct `KeyData`
* resolve IA version
* create/reuse application state
* initialize the IA journey

### Code anchors

* `IncomeAssessmentApplicationController`
* `CommonVersionResolver`
* `ServiceFacade`
* `IncomeAssessmentApplicationServiceV3`
* `IncomeAssessmentRepository`

---

# 4. Stage 2 — Version and Configuration Resolution

Version resolution is an important decision boundary.

The request context is passed through:


id="f5o4yb"
versionResolver.primeBucket(...)


The system resolves the effective IA version using configuration such as:


iaVersion
VersionBuckets


Conceptually:


Request Context
    ↓
KeyData
    ↓
Version Resolver
    ↓
Version Bucket
    ↓
Concrete IA Service Implementation


This means two apparently identical API requests can follow different internal implementations if their effective configuration/context differs.

### Important debugging question

When two requests behave differently:

> Did they resolve to the same IA version and configuration?

### Code anchors

* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/revamp/versionresolvers/CommonVersionResolver.kt:61-223`
* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/revamp/facade/ServiceFacade.kt:38-52`

---

# 5. Stage 3 — Application State Creation / Reuse

The main IA workflow state is persisted in MongoDB.

The primary application record is represented by:


IncomeAssessmentApplicationDao


and accessed through:


IncomeAssessmentRepository


The main collection is:


incomeAssessmentApplications


At this stage, the system establishes the application-level identity and initial workflow state.

Important identifiers may include:


incomeAssessmentId
applicationReferenceId
commonClientTransactionId
partnerId
productCode


Vendor-specific identifiers are introduced later as the journey progresses.

### Important distinction


Application identity
        ≠
Vendor transaction identity


One IA application can have multiple vendor transaction attempts.

---

# 6. Stage 4 — Assessment Medium / Journey Selection

After the IA application is established, the journey can branch into different assessment mechanisms.

Typical paths include:


Statement / bank-statement journey
Scan / upload journey
Account Aggregator / BSA journey
ITR journey


The exact path is configuration- and version-dependent.

Conceptually:


                 ┌── Statement
                 │
IA Application ──┼── Scan / Upload
                 │
                 ├── AA / BSA
                 │
                 └── ITR


The selected path determines:

* external integration
* required user interaction
* callback/event model
* documents involved
* business validations
* subsequent state transitions

---

# 7. Stage 5 — Link Generation / Journey Start

Depending on the selected path, the service may expose or invoke:


GET /income-assessment-service/v1/generate-link


and/or:


GET /income-assessment-service/v1/start-process


These APIs should be understood as **journey progression operations**, not necessarily the final assessment operation.

Typical conceptual flow:


Generate / retrieve link
        ↓
User redirected to external journey
        ↓
User completes required interaction
        ↓
External system processes data
        ↓
IA receives result asynchronously


For vendor-driven journeys, successfully generating a link or initiating a vendor transaction does **not** mean IA has completed.

---

# 8. Stage 6 — Zenith / AA / BSA Flow

The BSA journey can be initiated through:


POST /income-assessment-service/v1/bsa/initiate


The IA service communicates with the Zenith / AA-Orchestrator layer.

A representative downstream endpoint is:


/aa-orch/fiu/api/v1/initiateBSA


Conceptually:


IA
 ↓
BSA initiation
 ↓
Zenith / AA-Orchestrator
 ↓
AA journey
 ↓
User interaction
 ↓
Callback / notification
 ↓
IA Kafka / consumer processing
 ↓
Business processing


The BSA flow may involve:

* AA journey initiation
* account linking / consent
* statement retrieval
* BSA processing
* callback/event handling
* downstream synchronization

The exact sequence depends on the active implementation and configuration.

---

# 9. Stage 7 — Perfios / Statement Flow

The statement-based journey typically follows a vendor-driven asynchronous model.

Conceptually:


IA
 ↓
Start Perfios transaction
 ↓
Vendor transaction created
 ↓
User completes vendor journey
 ↓
Perfios processes statement
 ↓
Callback / status response
 ↓
IA processes result
 ↓
Raw statement / report retrieval
 ↓
Business validation
 ↓
IA status update


Important identifiers include:


applicationReferenceId
incomeAssessmentId
perfiosTransactionId
statementId
serviceRequestId


### Important rule

Creation of a Perfios transaction means:


vendor journey initiated


It does **not** mean:


income assessment completed


Completion depends on subsequent vendor processing and IA state transitions.

---

# 10. Stage 8 — Callback and Event Processing

External systems can advance the IA workflow asynchronously.

The callback path can be represented as:


External Vendor
      ↓
Callback
      ↓
IA ingestion
      ↓
Kafka event
      ↓
Consumer
      ↓
Application lookup
      ↓
State guard
      ↓
Business processing
      ↓
MongoDB update
      ↓
Next event / external API


Representative consumers include:


PerfiosCallbackReceivedConsumer
PerfiosCallbackNotReceivedConsumer
ZenithCallbackReceivedConsumer
ZenithCallbackNotReceivedConsumer


### Critical distinction

Each boundary is independent:


Callback received
≠
Kafka event published
≠
Kafka event consumed
≠
State transition accepted
≠
MongoDB updated
≠
Downstream processing completed


When debugging a callback incident, identify the **first boundary that failed**.

---

# 11. Stage 9 — Callback State Validation

When a callback or event reaches IA, the application state determines whether the callback can update the workflow.

State guard methods include:


canUpdateApplicationStatusInDb()
canUpdateApplicationStatusInPerfiosCallback()
canProceedToDocumentsUpload()
canProceedToItrDocumentsUpload(...)
canProceedToItrAssessment()
canProceedForLinkGeneration()
canProceedForStartProcess()
canProceedForStartTransaction()


Therefore:


Callback received
        ↓
Current state checked
        ↓
Allowed?
   ┌────┴────┐
   │         │
  Yes        No
   ↓         ↓
Process    Ignore / reject / no-op


A callback that produces no status change is not necessarily a Kafka or vendor failure.

The current application state may intentionally prevent the transition.

---

# 12. Stage 10 — Multiple Attempts

An IA application may have multiple vendor transaction attempts.

For example:


Application A
    │
    ├── Vendor Attempt 1
    │      └── Callback delayed
    │
    └── Vendor Attempt 2
           └── Callback received


The application-level identity remains related to the same IA journey, while the vendor transaction identity can differ.

This becomes especially important when callbacks arrive out of order.

### Correct debugging model


Application
    +
Attempt
    +
Vendor Transaction
    +
Callback Timestamp


Do not correlate asynchronous callbacks using only `applicationReferenceId` or `incomeAssessmentId`.

---

# 13. Stage 11 — Timeout / Status Polling

If a vendor callback is not received within the expected period, the service may fall back to status polling or another recovery mechanism.

Conceptually:


Callback expected
      ↓
Timeout
      ↓
Status API
      ↓
Retry
      ↓
Vendor result
      ↓
Business outcome


Possible outcomes include:


Success
Failure
Retry
Terminal failure
Alternate workflow


A late callback may still arrive after timeout processing.

Therefore the incident timeline must include both:


timeout processing
+
late callback processing


---

# 14. Stage 12 — Business Validation

After vendor data becomes available, IA applies business rules to determine the next state.

Examples of configurable rules include:


incomeCreditGapRule
chequeBounceLimitRule
lastNMonthsIncomeRule
numberOfIncomeCreditsRule
statementStatusRule


Conceptually:


Vendor Result
    ↓
Extract / normalize data
    ↓
Business validations
    ↓
Outcome


The outcome may result in:


SUCCESS
REJECTED
REFERRED
FAILED
POLICY_NORMS_NOT_MET


or another intermediate/next-step status.

Business validation should be distinguished from technical integration failure.

---

# 15. Stage 13 — ITR Branch

Some journeys continue into ITR assessment.

A simplified branch is:


Income Assessment
      ↓
Eligible for ITR?
      │
      ├── No → Continue / terminal IA outcome
      │
      └── Yes
           ↓
      ITR documents
           ↓
      ITR assessment
           ↓
      Business outcome


Relevant states include:


ITR_DOCUMENTS_NOT_UPLOADED
PROCEED_TO_ITR_ASSESSMENT


ITR processing can involve:

* document upload
* consent/link generation
* external ITR processing
* callback/status handling
* document persistence
* business validation

The exact branch is version/configuration dependent.

---

# 16. Stage 14 — Document Persistence

Documents may be uploaded to an external document service and/or persisted in IA's own document collection.

Conceptually:


Assessment result
      ↓
Document generation / retrieval
      ↓
Document Service / OmniDocs
      ↓
Document metadata persistence
      ↓
Downstream availability


Document troubleshooting requires checking both:


external document operation
+
local MongoDB persistence


A successful external upload does not prove that the local document record was persisted.

---

# 17. Stage 15 — Final / Near-Terminal Outcomes

High-value IA statuses include:


INCOME_ASSESSMENT_SUCCESS
INCOME_ASSESSMENT_FAILED
INCOME_ASSESSMENT_REJECTED
INCOME_ASSESSMENT_REFERRED
POLICY_NORMS_NOT_MET


Other statuses represent important workflow pauses or intermediate states, for example:


BSA_PAUSED_PENDING_USER_DECISION
ITR_DOCUMENTS_NOT_UPLOADED
PROCEED_TO_ITR_ASSESSMENT


Do not classify a status as terminal based only on its name.

Verify terminal-state behavior in the current domain/status implementation and transition guards.

---

# 18. Stage 16 — Event and Downstream Propagation

After an important IA state transition, the service may:

* update MongoDB
* publish a Kafka event
* synchronize CAP
* invoke another downstream service
* persist documents
* trigger another stage of the IA workflow

Conceptually:


Business Outcome
      ↓
MongoDB state update
      +
Kafka event
      +
Downstream synchronization


These operations are not necessarily atomic.

Therefore:


IA MongoDB = SUCCESS


does not by itself prove:


downstream system = SUCCESS


Similarly:


Kafka event published


does not prove that downstream consumers successfully processed it.

---

# 19. Complete Conceptual Flow

The following is the preferred mental model for the entire service:


                    ┌─────────────────────────┐
                    │ Partner / Upstream      │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │ Initiate IA Application │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │ Context + Version       │
                    │ Resolution              │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │ Create / Reuse IA       │
                    │ Application             │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │ Journey / Medium        │
                    │ Selection               │
                    └──────┬──────┬──────┬───┘
                           │      │      │
                 ┌─────────┘      │      └─────────┐
                 ▼                ▼                ▼
             Statement         Scan/Upload       AA/BSA
                 │                │                │
                 ▼                ▼                ▼
              Vendor           Documents        Zenith /
             Journey                            AA Journey
                 │                │                │
                 └────────────┬───┴────────────────┘
                              │
                              ▼
                     Callback / Event /
                      Status Polling
                              │
                              ▼
                    ┌─────────────────────┐
                    │ State Guard +       │
                    │ Business Processing │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Business Validation │
                    └──────────┬──────────┘
                               │
                 ┌─────────────┼──────────────┐
                 ▼             ▼              ▼
              Success       Referred       Failed /
                 │             │            Rejected
                 │             │              │
                 └─────────────┼──────────────┘
                               │
                               ▼
                    MongoDB + Kafka + APIs
                               │
                               ▼
                       Downstream Systems


The actual implementation can contain additional branches, retries, callbacks, document flows, and version-specific behavior.

---

# 20. API-to-Lifecycle Map

| API                                                       | Primary lifecycle responsibility   |
| --------------------------------------------------------- | ---------------------------------- |
| `POST /income-assessment-service/v1/initiate-application` | Create/start IA application        |
| `GET /income-assessment-service/v1/generate-link`         | Generate or retrieve journey link  |
| `GET /income-assessment-service/v1/start-process`         | Start/progress IA processing       |
| `GET /income-assessment-service/v1/validate`              | Validate IA/business conditions    |
| `GET /income-assessment-service/v1/status`                | Retrieve current IA state          |
| `GET /income-assessment-service/v1/income-details`        | Retrieve income assessment details |
| `POST /income-assessment-service/v1/bsa/initiate`         | Initiate BSA journey               |

These APIs are entry points into a larger asynchronous workflow rather than isolated operations.

---

# 21. Component-to-Flow Map

| Flow stage              | Primary components                                               |
| ----------------------- | ---------------------------------------------------------------- |
| Request entry           | `IncomeAssessmentApplicationController`                          |
| BSA entry               | `InitiateBsaController`                                          |
| Version resolution      | `CommonVersionResolver`                                          |
| Version dispatch        | `ServiceFacade`                                                  |
| Main orchestration      | `IncomeAssessmentApplicationServiceV3`                           |
| Application persistence | `IncomeAssessmentRepository`                                     |
| Configuration           | `ConfigFetcher`                                                  |
| Application state       | `IncomeAssessmentApplication` / `IncomeAssessmentApplicationDao` |
| Kafka event model       | `IncomeAssessmentApplicationEvent`                               |
| Kafka publication       | `IncomeAssessmentApplicationEventProducer`                       |
| Perfios callback        | `PerfiosCallbackReceivedConsumer`                                |
| Zenith callback         | `ZenithCallbackReceivedConsumer`                                 |
| Zenith integration      | `ZenithOrchestratorGateway`                                      |
| CAP synchronization     | `CapSyncService`                                                 |
| Document operations     | `DocumentServiceClient` / `DocumentRepository`                   |
| Authentication/token    | `AuthServiceClient`                                              |

---

# 22. End-to-End Debugging Timeline

For a production incident, reconstruct the journey chronologically.


T0  Application initiated
 ↓
T1  Version resolved
 ↓
T2  Application created/reused
 ↓
T3  Journey/link generated
 ↓
T4  Vendor transaction created
 ↓
T5  User completed vendor journey
 ↓
T6  Callback/event generated
 ↓
T7  Callback/event received
 ↓
T8  Kafka consumer processed
 ↓
T9  State guard evaluated
 ↓
T10 External result fetched
 ↓
T11 Business validation executed
 ↓
T12 MongoDB updated
 ↓
T13 Kafka/downstream event published
 ↓
T14 Downstream consumer/API processed
 ↓
T15 Final IA state


Not every journey contains every step.

The investigation should identify the **first missing or unexpected step**.

---

# 23. End-to-End Failure Boundaries

The IA journey can fail at multiple independent boundaries:


Request validation
        ↓
Version/config resolution
        ↓
Application persistence
        ↓
Vendor initiation
        ↓
User/vendor journey
        ↓
Callback delivery
        ↓
Kafka publication
        ↓
Kafka consumption
        ↓
State guard
        ↓
External result retrieval
        ↓
Business validation
        ↓
MongoDB persistence
        ↓
Downstream event/API
        ↓
Downstream processing


For RCA, always identify:

1. expected step
2. actual step
3. first divergence
4. root cause
5. downstream impact

---

# 24. Observability Requirements

A useful end-to-end trace should correlate:


applicationReferenceId
incomeAssessmentId
commonClientTransactionId
serviceRequestId
requestId
partnerId
productCode
eventId
vendor transaction ID
attempt
timestamps


For asynchronous flows, timestamps are especially important.

A final status without the event/API timeline is often insufficient to determine the root cause.

---

# 25. Source-of-Truth Hierarchy

For understanding the actual flow, prefer:

1. current controller/service implementation
2. current version-resolution implementation
3. current state/domain model
4. current repository/DAO
5. current Kafka producer/consumer implementation
6. current integration gateway/client
7. current configuration
8. tests/stubs
9. README or historical documentation

The flow described here is a navigation model and should not override the current implementation.

---

# 26. Related Documents

### Business semantics

`business-logic.md`

Use for:

* status meanings
* transition rules
* business guards
* terminal states
* validation logic

### External systems

`integrations.md`

Use for:

* Perfios
* Zenith
* CAP
* Document Service
* FinFort
* Auth/Token
* external APIs

### Persistence

`database.md`

Use for:

* collections
* identifiers
* MongoDB queries
* persisted application state

### Asynchronous processing

`kafka-events.md`

Use for:

* event taxonomy
* topics
* consumer groups
* consumer behavior
* producer failures
* event propagation

### Failure semantics

`error-handling.md`

Use for:

* exception mapping
* retries
* state guards
* external failures
* Kafka failures
* RCA interpretation

### Runtime behavior

`configurations.md`

Use for:

* feature toggles
* version routing
* partner/product configuration
* retry configuration
* vendor error mappings
* endpoint configuration

### Incident investigation

`troubleshooting.md`

Use for:

* where to start
* diagnostic decision trees
* failure boundaries
* incident timeline reconstruction

---

# 27. RAG Retrieval Guidance

Retrieve this document for questions such as:

* "Explain the complete IA flow"
* "What happens after initiate application?"
* "What happens after generate link?"
* "How does the Perfios journey flow?"
* "How does the Zenith BSA flow work?"
* "Where does the callback enter the flow?"
* "What happens after a callback?"
* "How does IA reach SUCCESS?"
* "What are the IA lifecycle stages?"
* "Which APIs are involved in IA?"
* "Where does version resolution happen?"
* "Where is the application created?"
* "Where does Kafka fit into the IA flow?"
* "Where does document processing happen?"
* "How does the ITR branch work?"
* "What happens when a vendor callback is delayed?"
* "How do multiple attempts fit into the flow?"

### Retrieval strategy

For a **high-level flow question**, retrieve this document first.

For a **specific stage**, combine it with the corresponding domain document:


End-to-end flow
    ↓
Identify stage
    ↓
Retrieve specialized document
    ↓
Trace implementation


Examples:


"How does callback processing work?"
→ income-assessment-flow.md
→ kafka-events.md
→ business-logic.md
→ error-handling.md

"Why is Zenith BSA failing?"
→ income-assessment-flow.md
→ integrations.md
→ troubleshooting.md
→ error-handling.md

"Why is the application stuck?"
→ income-assessment-flow.md
→ business-logic.md
→ database.md
→ kafka-events.md
→ troubleshooting.md


---

# 28. Core Flow Invariants

1. IA is a **stateful workflow**, not a single API call.
2. Initiating an application does not mean the assessment is complete.
3. Generating a vendor link does not mean the vendor journey is complete.
4. Creating a vendor transaction does not mean IA succeeded.
5. A callback being received does not guarantee a state transition.
6. A Kafka event being published does not guarantee consumer processing.
7. A MongoDB update does not guarantee downstream synchronization.
8. One IA application can have multiple vendor transaction attempts.
9. Callback correlation must account for vendor transaction/attempt identity.
10. Version and configuration resolution can change the runtime path.
11. Business validation and technical integration failure are separate concepts.
12. Final state should be interpreted together with the event/API timeline.
13. The first unexpected boundary in the timeline is usually more useful for RCA than the final visible exception.
14. This document explains **flow and handoffs**; detailed behavior belongs to the specialized context documents.

---

# 29. Preferred Mental Model

When asked to explain or debug an IA journey, think:


WHO initiated?
    ↓
WHICH application?
    ↓
WHICH partner/product/context?
    ↓
WHICH IA version?
    ↓
WHICH journey/medium?
    ↓
WHICH vendor transaction/attempt?
    ↓
WHICH API/event/callback?
    ↓
WHICH consumer/service processed it?
    ↓
WHICH state guard applied?
    ↓
WHICH business validation ran?
    ↓
WHAT was persisted?
    ↓
WHAT event/API was triggered next?
    ↓
WHAT downstream system processed it?
    ↓
WHAT is the final IA state?


The most important troubleshooting question is:

> **At which step did the actual journey first diverge from the expected flow?**
