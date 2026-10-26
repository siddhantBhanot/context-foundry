# Troubleshooting

## 1. Purpose

This document is the **debugging entry point** for Income Assessment (IA).

Use it when the question is:

* Why did the IA journey fail?
* Why is the application stuck in a particular status?
* Why was a callback not processed?
* Why did the same action behave differently for different requests?
* Why did an external API return an unexpected error?
* Why was a Kafka event missing or ineffective?
* Why was a document not persisted?
* Why did the application move to an unexpected state?
* Which component should be investigated first?

Troubleshooting should identify the failure layer before changing code.

### Primary debugging layers


Request / Controller
    ↓
Version / Configuration Resolution
    ↓
Business Service / State Guard
    ↓
External Integration
    ↓
Kafka Producer / Consumer
    ↓
MongoDB Persistence
    ↓
Downstream Side Effect


A failure in one layer can produce a misleading error in another layer.

Example:


Wrong Zenith URL
    ↓
HTTP 404
    ↓
HTML response
    ↓
JSON deserialization failure
    ↓
UnsupportedMediaTypeException


The JSON/media-type exception is a **secondary symptom**. The endpoint mismatch is the likely root cause.

---

# 2. Debugging Mental Model

IA is a stateful, asynchronous workflow.

Do not debug an incident as a single API call.

Instead trace:


Application
  ↓
Attempt / Vendor Transaction
  ↓
Request
  ↓
External API
  ↓
Callback / Kafka Event
  ↓
State Guard
  ↓
MongoDB Mutation
  ↓
Next Event / External API
  ↓
Downstream Consumer


A successful step does not prove that the complete journey succeeded.

For example:


Perfios transaction created
≠
Perfios journey completed
≠
Callback received
≠
Callback consumed
≠
MongoDB updated
≠
Next Kafka event published
≠
Downstream consumer processed event


Always identify **which boundary was crossed successfully and where the chain stopped**.

---

# 3. Debug-First Information

Before deep code debugging, capture as many of these identifiers as possible:

* `applicationReferenceId`
* `incomeAssessmentId`
* `commonClientTransactionId`
* `serviceRequestId`
* `requestId`
* `partnerId`
* `productCode`
* `eventId`
* vendor transaction ID
* callback timestamp
* retry count / attempt number
* current IA status
* `statusType`
* relevant journey/version information

### Identifier rule

Do not assume these IDs are interchangeable.

In particular:


incomeAssessmentId
≠
applicationReferenceId
≠
commonClientTransactionId
≠
vendor transaction ID


One IA application can have multiple vendor transaction attempts.

Therefore, when debugging callbacks or retries, always correlate the **vendor transaction / attempt** as well as the application-level identifier.

---

# 4. Universal Troubleshooting Workflow

Use this sequence before diving into individual classes.

## Step 1 — Identify the failing operation

Determine exactly what failed:

* API request
* callback
* Kafka event
* MongoDB update
* document persistence
* status transition
* version routing
* external vendor operation
* retry/timeout
* downstream propagation

Avoid starting from a generic exception message.

---

## Step 2 — Identify the application and attempt

Find:


applicationReferenceId
incomeAssessmentId
partnerId
productCode
vendor transaction ID


Check whether the application has multiple attempts.

For vendor-driven journeys, do not assume the latest callback belongs to the latest attempt.

---

## Step 3 — Check persisted state

Inspect the `IncomeAssessmentApplicationDao` / `incomeAssessmentApplications` record.

Check:

* current `status`
* `statusType`
* retry counters
* timestamps
* attempt information
* vendor transaction information
* event-related state
* user decision fields
* relevant journey-specific fields

Ask:

> What state does IA currently believe the application is in?

---

## Step 4 — Identify the intended transition

Determine:


current state
    ↓
expected event/API/callback
    ↓
expected next state


Then inspect the state guard.

A callback or event may be received correctly but intentionally ignored because the current application state does not allow the transition.

---

## Step 5 — Check configuration

Determine whether the behavior is configuration-driven.

Inspect:

* `PartnerProductConfigurations`
* `IncomeAssessment`
* `Callback`
* `VersionBuckets`
* `iaVersion`
* feature toggles
* vendor error mappings
* retry configuration
* endpoint configuration
* Kafka topic/group configuration

Do not assume that identical code means identical runtime behavior.

---

## Step 6 — Check external integration

If the flow calls an external system, verify:

* base URL
* endpoint path
* HTTP method
* headers
* content type
* request body
* environment
* authentication/token
* vendor response status
* vendor response body

For HTTP failures, inspect the **raw response before interpreting secondary parsing errors**.

---

## Step 7 — Check Kafka propagation

If the flow is asynchronous, trace:


event produced
    ↓
topic
    ↓
consumer group
    ↓
consumer
    ↓
filter / transformer
    ↓
business handler
    ↓
MongoDB / external API
    ↓
next event


Do not stop at "event was published".

---

## Step 8 — Determine the failure impact

Classify the failure as:

* user-flow blocking
* state synchronization issue
* event propagation issue
* downstream-only issue
* best-effort side-effect failure
* observability-only issue

This prevents treating every logged exception as a failed IA journey.

---

# 5. Zenith BSA — 404 + HTML Media-Type Error

## Symptom

Typical symptoms:


Web request failed
responseCode: 404


for:


/aa-orch/fiu/api/v1/initiateBSA


followed by:


UnsupportedMediaTypeException:
Content type 'text/html;charset=utf-8'
not supported for bodyType=BsaApiErrorResponse


## Interpretation

This combination usually indicates:


Request reached an endpoint
    ↓
Endpoint/path/method mismatch
    ↓
404 response
    ↓
Server/stub returned HTML
    ↓
Gateway attempted JSON error-body deserialization
    ↓
UnsupportedMediaTypeException


The media-type exception should not automatically be treated as the root cause.

## Checks

1. Verify the complete path:


/aa-orch/fiu/api/v1/initiateBSA


2. Verify the HTTP method is `POST`.

3. Verify the configured Zenith base URL.

4. Verify:


platform.gateway.zenithBaseUrl
platform.gateway.initiateBsaEnc


5. Verify the stub/imposter configuration.

6. Verify the stub returns:


Content-Type: application/json


when the client expects `BsaApiErrorResponse`.

7. Compare the actual request URL with the stubbed route.

8. Check whether the response came from the intended environment.

9. Only after endpoint/stub correctness is established, investigate business validation or gateway parsing behavior.

## Diagnostic rule


404 + HTML
    → check endpoint/stub/environment first

JSON error response
    → then investigate vendor/application error mapping


## Optional hardening

The gateway may be made more tolerant of non-JSON error bodies, but this should not hide endpoint or environment misconfiguration.

### Relevant code anchors

* `src/main/resources/application.yaml:341-349`
* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/controller/InitiateBsaController.kt:21-31`
* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/bsa/model/InitiateBsaModels.kt:82-151`

---

# 6. Same Business Action Behaves Differently Across Routes

## Symptom

The same business action appears to behave differently depending on:

* token
* endpoint
* partner
* product
* request context
* IA version

## Likely causes


Different request context
        ↓
Different KeyData
        ↓
Different version bucket / configuration
        ↓
Different service implementation
        ↓
Different runtime behavior


## Checks

### 1. Verify request context

Confirm that the controller builds the expected `KeyData`.

Check:

* partner
* product
* token-derived context
* endpoint
* request metadata

### 2. Verify version resolution

Confirm that the request path is wrapped in:


versionResolver.primeBucket(...)


### 3. Check version logs

Look for:


VERSION_RESOLVED


and identify the resolved IA version.

### 4. Inspect configuration

Check:


iaVersion
VersionBuckets


for the relevant partner/product/context.

### 5. Identify the actual implementation

Trace:


Controller
    ↓
ServiceFacade
    ↓
CommonVersionResolver
    ↓
resolved version
    ↓
concrete service implementation


### Relevant code anchors

* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/controller/IncomeAssessmentApplicationController.kt:51-72`
* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/revamp/facade/ServiceFacade.kt:38-52`
* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/revamp/versionresolvers/CommonVersionResolver.kt:61-223`

---

# 7. Callback Not Processed

A "callback not processed" incident can originate at several different points.

Do not immediately conclude that the vendor failed to send the callback.

## Callback decision tree


Was callback sent?
    │
    ├── No
    │    └── Investigate vendor / timeout / callback generation
    │
    └── Yes
         ↓
Was callback received by IA?
         │
         ├── No
         │    └── Investigate network / endpoint / callback ingestion
         │
         └── Yes
              ↓
Was callback event published?
              │
              ├── No
              │    └── Investigate callback processing / producer
              │
              └── Yes
                   ↓
Was Kafka event consumed?
                   │
                   ├── No
                   │    └── Investigate topic / consumer group / routing
                   │
                   └── Yes
                        ↓
Was callback accepted by state guard?
                        │
                        ├── No
                        │    └── Investigate current state / attempt correlation
                        │
                        └── Yes
                             ↓
Was MongoDB updated?
                             │
                             ├── No
                             │    └── Investigate persistence/error handling
                             │
                             └── Yes
                                  ↓
Was downstream event/API successful?
                                  │
                                  ├── No
                                  │    └── Investigate downstream failure
                                  │
                                  └── Yes
                                       ↓
                                  Callback flow completed


## Checks

### Callback ingestion

Confirm:

* callback endpoint was invoked, or
* callback event was generated.

### Kafka routing

Inspect:


platform.kafka.*


and identify:

* topic
* consumer group
* event type
* filter
* transformer

### Consumer

Identify the responsible consumer.

Examples:


PerfiosCallbackReceivedConsumer
ZenithCallbackReceivedConsumer


### State guard

Verify that the current application state permits the callback-driven update.

A callback can be received and consumed but intentionally produce no state change.

### Attempt correlation

For vendor journeys, verify:


application
    +
vendor transaction
    +
attempt


A late callback from an earlier attempt must not automatically be interpreted as the latest attempt's callback.

### Relevant code anchors

* `src/main/resources/application.yaml:429-500`
* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/kafka/consumer/PerfiosCallbackReceivedConsumer.kt:75-161`
* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/kafka/consumer/ZenithCallbackReceivedConsumer.kt:72-137`
* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/domain/IncomeAssessmentApplication.kt:279-283`

---

# 8. Missing or Incorrect Status Transition

## Symptom

The application:

* remains in an old status
* moves to an unexpected status
* does not move after a callback
* cannot be re-initiated
* appears stuck despite an apparently successful external operation

## Investigation model


Current MongoDB status
        ↓
Expected event/API
        ↓
State guard
        ↓
Business rule
        ↓
Vendor error mapping
        ↓
Status mutation
        ↓
Next event


## Checks

### 1. Inspect current state

Read the persisted `IncomeAssessmentApplicationDao`.

Do not infer current state only from logs.

### 2. Inspect state guards

Look for methods such as:


canUpdateApplicationStatusInDb()
canUpdateApplicationStatusInPerfiosCallback()
canProceedToDocumentsUpload()
canProceedToItrDocumentsUpload(...)
canProceedToItrAssessment()
canProceedForLinkGeneration()
canProceedForStartProcess()
canProceedForStartTransaction()


### 3. Check business rules

Determine whether the transition was blocked by a business condition rather than a technical exception.

### 4. Check vendor error mapping

Inspect configuration-backed mappings.

An external error may intentionally map to:


FAILED
REJECTED
REFERRED


or another business state.

### 5. Check terminal state

A terminal state may intentionally prevent further processing or re-initiation.

### Relevant code anchors

* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/domain/IncomeAssessmentApplication.kt:279-332`
* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/repository/IncomeAssessmentRepository.kt:66-172`
* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/utils/ConfigFetcher.kt:337-366`

---

# 9. Application State and Downstream State Do Not Match

## Symptom

MongoDB shows one state while:

* FCU
* CAP
* another downstream service
* Kafka consumers
* external vendor state

shows another.

## Important rule

MongoDB state and downstream state are **not one atomic transaction**.

Possible flow:


MongoDB update
    ↓
Kafka publish fails
    ↓
Downstream never receives event


or:


Kafka event published
    ↓
Consumer receives event
    ↓
Downstream API fails
    ↓
MongoDB remains in previous state


## Checks

Trace both sides independently:


IA MongoDB
    +
Kafka event
    +
consumer processing
    +
downstream API
    +
downstream state


Do not assume:


MongoDB state = downstream state


unless the propagation chain has been verified.

---

# 10. Kafka Event Exists but Business State Did Not Change

## Symptom

Logs show that a Kafka event was published or consumed, but the expected status/update did not occur.

## Checks

Follow the full chain:


Producer
  ↓
Topic
  ↓
Consumer Group
  ↓
Consumer
  ↓
Filter / Transformer
  ↓
State Guard
  ↓
Business Handler
  ↓
MongoDB / External API


Investigate:

1. Was the event published successfully?
2. Was it published to the expected topic?
3. Was it consumed by the expected consumer group?
4. Did filtering/transforming modify or reject the event?
5. Did the consumer find the correct application?
6. Did the state guard allow processing?
7. Did the downstream API succeed?
8. Did MongoDB update?
9. Was the next event published?

### Important distinction


Event published
≠
Event consumed
≠
Business processing succeeded


---

# 11. Kafka Event Missing

## Symptom

A downstream action did not occur because an expected event appears absent.

## Checks

### Producer side

Verify:

* producer method was reached
* event object was constructed
* event ID exists
* serialization succeeded
* `send()` was invoked
* Kafka broker accepted the message

### Topic routing

Verify:

* configured topic
* event-to-topic mapping
* environment
* producer configuration

### Payload

Check whether the event exceeded configured Kafka message limits.

Important failure:


RecordTooLargeException


When this occurs, investigate:

* event payload size
* producer limits
* topic/broker limits
* consumer limits
* whether large report/raw-statement data is embedded in the event

### Business impact

Determine whether Kafka publication is:

* user-flow critical
* state synchronization critical
* downstream-only
* best-effort

A failed best-effort event must not automatically be interpreted as a failed IA journey.

---

# 12. Late Callback / Multiple Attempt Troubleshooting

## Symptom

A user retries a vendor journey and callbacks from different attempts arrive out of order.

Example:


Attempt 1
    ↓
Vendor transaction created
    ↓
Callback delayed
    ↓
User retries

Attempt 2
    ↓
Vendor transaction created
    ↓
Callback received
    ↓
IA processes Attempt 2

Later:
Attempt 1 callback arrives


## Risk

If callbacks are correlated only by application-level identity, a late callback may affect the wrong logical attempt or produce an apparently contradictory state transition.

## Checks

Compare:


applicationReferenceId
incomeAssessmentId
vendor transaction ID
attempt number / attempt metadata
callback timestamp
current MongoDB status


Then determine:

1. Which attempt generated the callback?
2. Which attempt is currently active?
3. What state was the application in when the callback was processed?
4. Did the state guard allow or reject the update?
5. Did the callback trigger a new downstream event?
6. Did a timeout/failure for another attempt happen before or after the callback?

### Debugging principle

Always correlate the **callback to the vendor transaction/attempt**, not only to the application.

---

# 13. OmniDocs / Document Persistence Gap

## Symptom

The expected document:

* was uploaded externally but not persisted locally
* exists in IA flow but not in the `document` collection
* is missing from downstream processing
* is created only for some routes

## Checks

### 1. Identify active service path

Trace document upload from the currently selected service implementation.

Do not assume every version follows the same document flow.

### 2. Check configuration

Inspect controlling flags, especially those related to:

* Finacle
* Zenith
* raw statements
* document persistence
* IA failure handling

### 3. Check external document API

Verify:

* endpoint
* request
* response
* document identifier

### 4. Check MongoDB

Inspect the `document` collection using the appropriate correlation identifiers.

### Relevant code anchors

* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/revamp/service/impl/IncomeAssessmentApplicationServiceV3.kt:164-177`
* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/utils/ConfigFetcher.kt:687-712`
* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/repository/DocumentRepository.kt:9-18`

---

# 14. External API Failure Troubleshooting

When an external API fails, classify the error before debugging business logic.

## HTTP 4xx

Check:

* URL/path
* HTTP method
* headers
* content type
* request body
* authentication
* environment
* stub/imposter

### Special case: 404


404
→ verify base URL
→ verify path
→ verify method
→ verify environment/stub


### Special case: 405

Usually investigate:


HTTP method mismatch


before business validation.

### Special case: 415

Investigate:


Content-Type
Accept
request body format
server expectations


---

# 15. Network / Timeout Failures

Typical symptoms include:


WebClientRequestException
Connection reset by peer
timeout
connection refused


## Checks

1. Determine which downstream API failed.
2. Check whether the request reached the downstream system.
3. Check retry configuration.
4. Check whether the operation is safe to retry.
5. Determine whether the current code actually applies `retry` / `retryWhen`.
6. Check whether the error was swallowed with `onErrorResume`.
7. Inspect resulting IA status/event behavior.

### Important rule

A configured retry value does not mean every exception is automatically retryable.

Verify:


configuration
+
retry operator
+
retry predicate
+
exception type


---

# 16. Configuration-Driven Failure

When behavior differs without an obvious code change, inspect configuration early.

## Common configuration dimensions


PartnerProductConfigurations
IncomeAssessment
Callback
VersionBuckets
iaVersion
feature toggles
vendor error mappings
retry configuration
endpoint configuration
Kafka topic/group configuration


## Investigation

Trace:


Request context
    ↓
Config key/group
    ↓
ConfigFetcher
    ↓
Resolved value
    ↓
Caller interpretation
    ↓
Runtime branch
    ↓
Observed behavior


Do not stop at finding the configuration key.

The important question is:

> What effective value did this request receive, and how did the caller interpret it?

---

# 17. Error Mapping Troubleshooting

A vendor error does not necessarily map directly to the same IA outcome.

Trace:


External response/error
    ↓
Gateway
    ↓
Vendor-specific error mapping
    ↓
IA error
    ↓
Business decision
    ↓
Status / response / event


Check configuration groups such as:


PerfiosErrorCodeAndConfigMapping
ZenithErrorCodeAndConfigMapping
FinacleErrorCodeAndConfigMapping
MaximusErrorCodeAndConfigMapping


When an unexpected status appears, inspect the mapping before assuming the state transition code is incorrect.

---

# 18. Reactive Chain Troubleshooting

The service uses reactive flows, so the location of an exception in logs does not always represent the final business outcome.

Important operators include:


onErrorResume
onErrorMap
switchIfEmpty
retry
retryWhen
flatMap
then


## Questions to ask

### `onErrorResume`

Was an exception intentionally converted into a fallback/success path?

### `onErrorMap`

Was the original exception translated into an IA-specific exception?

### `switchIfEmpty`

Did an empty result trigger an alternate path?

### `retry` / `retryWhen`

Was the operation actually retried?

### Chained operations

Did the chain continue after the failing operation, or was the failure terminal?

Use the final state and downstream side effects to validate the actual outcome.

---

# 19. Callback Timeout Troubleshooting

When a callback is not received within the configured timeout:


Callback expected
    ↓
Timeout period expires
    ↓
Status API / fallback processing
    ↓
Retries
    ↓
Failure or alternate state


Check:

* callback timeout configuration
* status API invocation
* retry count
* vendor response
* failure-code mapping
* final IA state
* whether a late callback subsequently arrived

A later callback can create a second state transition after timeout processing.

Therefore always inspect the **full timeline**, not only the final exception.

---

# 20. Status Stuck in `INCOME_ASSESSMENT_IN_PROGRESS`

Use this sequence:


1. Find application record
2. Identify active attempt
3. Identify expected callback/event
4. Verify callback/event arrival
5. Verify Kafka consumption
6. Verify state guard
7. Verify vendor response/error
8. Verify MongoDB update
9. Verify next event


Common causes:

* callback not received
* callback event not consumed
* callback rejected by state guard
* vendor API failure
* retry exhaustion
* MongoDB update failure
* next event publication failure
* late callback from another attempt
* configuration/version mismatch

---

# 21. Status Reverted or Appears Contradictory

When a status appears to move backward:

Do not immediately assume a bad status update.

Check the timeline:


T1 → Attempt 1 started
T2 → Attempt 1 timeout/failure
T3 → Attempt 2 started
T4 → Attempt 2 callback
T5 → Attempt 1 late callback


Then correlate every status change with:

* timestamp
* event ID
* vendor transaction ID
* attempt
* consumer
* API call
* state guard

This frequently reveals that apparently contradictory states were produced by **different asynchronous attempts**.

---

# 22. Debugging by Failure Type

| Failure symptom                        | Start investigation at                             |
| -------------------------------------- | -------------------------------------------------- |
| HTTP 404                               | Base URL / path / environment / stub               |
| HTTP 405                               | HTTP method                                        |
| HTTP 415                               | Content-Type / body format                         |
| HTML response for JSON error model     | Endpoint/stub first                                |
| Callback missing                       | Vendor → callback ingestion → Kafka                |
| Callback consumed but no status change | State guard                                        |
| Status unexpectedly changed            | Error mapping + event timeline                     |
| Kafka event missing                    | Producer + topic + payload                         |
| Kafka event consumed but no effect     | Consumer + filter + state guard                    |
| Mongo state wrong                      | Repository/accessor + preceding business operation |
| Downstream state differs               | Kafka propagation + downstream API                 |
| Same route behaves differently         | KeyData + version + config                         |
| Retry not happening                    | Reactive retry operator + predicate + config       |
| Document missing                       | Document client + toggles + Mongo                  |
| `RecordTooLargeException`              | Event payload + Kafka limits                       |
| Timeout / connection reset             | Network + retry + downstream behavior              |

---

# 23. Source-of-Truth Hierarchy

When sources disagree, prefer:

1. current production code / active call site
2. current DAO/entity/model definitions
3. current controller/service/consumer implementation
4. current configuration resolution code
5. `application.yaml` and environment configuration
6. tests and stubs
7. README / historical documentation

For runtime incidents, historical documentation should never override current code/configuration.

---

# 24. High-Value Code Anchors

Use these classes as investigation entry points.

### Request / orchestration


IncomeAssessmentApplicationController
IncomeAssessmentApplicationServiceV3
ServiceFacade


### Version resolution


CommonVersionResolver
ConfigFetcher


### State


IncomeAssessmentApplication
IncomeAssessmentApplicationDao
IncomeAssessmentRepository
IncomeAssessmentApplicationAccessor


### Kafka


IncomeAssessmentApplicationEvent
IncomeAssessmentApplicationEventProducer
PerfiosCallbackReceivedConsumer
PerfiosCallbackNotReceivedConsumer
ZenithCallbackReceivedConsumer
ZenithCallbackNotReceivedConsumer


### Integrations


ZenithOrchestratorGateway
DocumentServiceClient
AuthServiceClient
FinFortClient
CapSyncService


### BSA


InitiateBsaController
InitiateBsaModels


---

# 25. Cross-Document Troubleshooting Map

Use the other context files depending on the failure layer.

| Problem                     | Primary document    | Secondary document  |
| --------------------------- | ------------------- | ------------------- |
| Expected status/state       | `business-logic.md` | `database.md`       |
| External API failure        | `integrations.md`   | `error-handling.md` |
| Kafka event missing         | `kafka-events.md`   | `error-handling.md` |
| Callback not processed      | `kafka-events.md`   | `business-logic.md` |
| Wrong status mapping        | `error-handling.md` | `configurations.md` |
| Different behavior by route | `configurations.md` | `business-logic.md` |
| Mongo state issue           | `database.md`       | `business-logic.md` |
| Document persistence        | `integrations.md`   | `database.md`       |
| Retry / timeout             | `error-handling.md` | `configurations.md` |
| Vendor error                | `error-handling.md` | `integrations.md`   |
| Version routing             | `configurations.md` | `business-logic.md` |
| Downstream mismatch         | `kafka-events.md`   | `database.md`       |

---

# 26. RAG Retrieval Guidance

Retrieve this document when the user asks:

* "How do I debug this?"
* "What should I check first?"
* "Where should I start investigation?"
* "Why is this status stuck?"
* "Why was the callback not processed?"
* "Why did the same API behave differently?"
* "Why did Zenith return 404?"
* "Why am I seeing an HTML/media-type error?"
* "Why is Kafka event missing?"
* "Kafka event was consumed but nothing happened"
* "Mongo state and downstream state don't match"
* "Why didn't retry happen?"
* "Why did the status change unexpectedly?"
* "Could this be a configuration issue?"
* "How do I RCA this issue?"

### Retrieval priority

For incident/RCA questions, combine this document with:


Troubleshooting
    +
Business Logic
    +
Error Handling
    +
Integrations
    +
Kafka Events
    +
Database
    +
Configurations


Use the troubleshooting document to determine **where to investigate** and the other documents to determine **what the component is supposed to do**.

---

# 27. Core Troubleshooting Invariants

These assumptions should guide investigation:

1. A successful external API call does not prove the IA journey completed.
2. A callback being received does not prove it was accepted.
3. A Kafka event being published does not prove it was consumed.
4. A Kafka event being consumed does not prove business processing succeeded.
5. A MongoDB update does not prove downstream state was synchronized.
6. A logged exception does not automatically mean the user flow failed.
7. A 404 + HTML response should be investigated as an endpoint/environment/stub problem before a JSON parsing problem.
8. Configuration can change runtime behavior without code changes.
9. `iaVersion` and version-bucket resolution can route requests to different implementations.
10. Vendor error mappings can change business outcomes without changing the caller.
11. Retry configuration does not imply every exception is retryable.
12. Multiple vendor attempts can produce out-of-order callbacks.
13. Application-level identifiers and vendor transaction identifiers must not be conflated.
14. Final MongoDB state alone is insufficient for asynchronous RCA; reconstruct the event/API timeline.
15. The first visible exception is not necessarily the root cause.

---

# 28. Preferred Incident Investigation Format

For a production incident, reconstruct the flow in this order:


Application:
  applicationReferenceId = ?

IA:
  incomeAssessmentId = ?

Context:
  partnerId = ?
  productCode = ?
  IA version = ?

Attempt:
  vendor transaction ID = ?
  attempt = ?

Initial state:
  status = ?

Trigger:
  API / callback / Kafka event = ?

External result:
  HTTP/vendor response = ?

Processing:
  consumer/service = ?

State guard:
  allowed / rejected = ?

Persistence:
  MongoDB update = ?

Event:
  published / not published = ?

Downstream:
  API/event processing = ?

Final state:
  status = ?

Root cause:
  ?

Contributing factors:
  ?

User/business impact:
  ?


This format should be preferred over starting with a stack trace alone.

---

# 29. One-Line Debugging Principle

> **Trace the request/event from its origin to its final state, correlate it to the correct application and attempt, and identify the first boundary where expected behavior diverged.**

This is the primary troubleshooting model for the IA service.
