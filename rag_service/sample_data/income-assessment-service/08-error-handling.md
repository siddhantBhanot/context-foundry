# Error Handling

## Error Handling Overview

The Income Assessment (IA) service uses layered error handling across:


Controller
   ↓
Service / Facade
   ↓
Gateway / External API
   ↓
Kafka Consumer / Producer
   ↓
MongoDB / Persistence


Errors can originate from:

* request validation
* business-rule validation
* application state guards
* external APIs
* network failures
* JSON serialization/deserialization
* Kafka publishing/consumption
* MongoDB operations
* configuration
* timeouts
* retries
* downstream systems

An exception's class or message alone does **not** determine its business impact.

For every error, determine:

1. **Where did it originate?**
2. **Was it transformed into an IA error?**
3. **Was it retried?**
4. **Was the error swallowed or propagated?**
5. **Was MongoDB state changed?**
6. **Was a Kafka event published?**
7. **Did the user-facing journey fail?**
8. **Did only a best-effort side effect fail?**

This distinction is critical for RCA.

---

# Error Taxonomy

Errors should be classified by both **technical origin** and **business impact**.

## 1. Validation Errors

These occur when the request or input does not satisfy expected requirements.

Typical investigation areas:

* request model
* controller validation
* required fields
* supported journey/product combinations
* malformed payloads

These generally fail early and should not be confused with downstream failures.

---

## 2. Business Rule Errors

These occur when the application is technically functioning but business rules prevent progression.

Examples include:


POLICY_NORMS_NOT_MET
INCOME_ASSESSMENT_REJECTED


Business-rule errors are not necessarily system failures.

When investigating them, inspect:


request context
+
partner/product configuration
+
current application state
+
business-rule configuration


---

## 3. State Guard Errors / No-Op Processing

Some operations are intentionally prevented when the application is already in a state where the requested transition is invalid.

Important guard methods include:


canUpdateApplicationStatusInDb()
canUpdateApplicationStatusInPerfiosCallback()
canProceedToDocumentsUpload()
canProceedToItrDocumentsUpload(...)
canProceedToItrAssessment()
canProceedForLinkGeneration()
canProceedForStartProcess()
canProceedForStartTransaction()
isTerminalItrStatus()


A callback that does not update MongoDB is therefore not automatically a failed callback.

It may have been intentionally rejected by the application's state machine.

**Source**

* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/domain/IncomeAssessmentApplication.kt:279-332`

---

# Error Catalogs

The repository has two important application error catalogs.

## `IncomeAssesmentServiceError`

This contains service/platform-facing errors used across multiple layers.

**Source**

* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/errorcodes/IncomeAssesmentServiceError.kt:1-200`

## `IncomeAssessmentApplicationServiceError`

This contains errors associated more directly with IA application/service flows.

**Source**

* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/errorcodes/IncomeAssessmentApplicationServiceError.kt:1-220`

When searching for a specific error code, search both catalogs before assuming that an error belongs to only one layer.

---

# Error Translation Model

External errors are often translated before reaching the business layer.

The conceptual flow is:


External System
      ↓
HTTP / Network / Vendor Error
      ↓
Gateway
      ↓
Vendor-specific error mapping
      ↓
IA error / application error
      ↓
Business decision
      ↓
Status / response / event


Therefore, the error visible at the API or consumer layer may be different from the original downstream error.

For RCA, preserve both:


Original technical error
+
Normalized IA error


The original error explains **what technically failed**.

The normalized error explains **how IA interpreted that failure**.

---

# Configuration-Driven Error Mapping

Error handling is partly configuration-driven.

The service maintains mappings for external/platform systems including:

* Perfios
* Zenith
* Finacle
* Maximus

These mappings can influence:

* IA error code
* business interpretation
* status
* retry behavior
* user-facing outcome

Therefore, do not assume that vendor error handling is entirely hardcoded.

When a vendor error behaves unexpectedly, inspect both:


error-handling code
+
current configuration


**Source citations**

* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/utils/ConfigFetcher.kt:337-366`
* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/utils/ConfigFetcher.kt:722-728`
* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/utils/ConfigFetcher.kt:762-792`
* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/utils/ConfigFetcher.kt:921-975`
* `src/main/resources/application.yaml:33-40`

---

# Reactive Error Handling

The service uses Project Reactor patterns extensively.

Important operators include:


onErrorResume
onErrorMap
switchIfEmpty
retry / retryWhen


These operators have very different semantics.

## `onErrorResume`

Can convert an error into an alternate reactive path.

Important RCA question:

> Was the original exception intentionally swallowed/recovered from?

A log containing an exception does not necessarily mean the request ultimately failed.

---

## `onErrorMap`

Transforms one exception into another.

When debugging, inspect the complete chain to find:


original exception
        ↓
mapped exception
        ↓
final error observed by caller


The final exception may hide the original root cause unless the cause chain is preserved.

---

## `switchIfEmpty`

Handles an empty reactive result.

An empty result is **not the same thing as an exception**.

For example:


Mongo lookup
    ↓
empty result
    ↓
switchIfEmpty(...)


should be investigated separately from:


Mongo lookup
    ↓
exception
    ↓
onErrorResume(...)


---

## Retry Operators

Retries are generally used around selected network-bound or transient operations.

A retry can change the apparent failure timeline:


Initial request
      ↓
Transient failure
      ↓
Retry
      ↓
Retry succeeds


Therefore, the first exception in logs may not be the final outcome.

When investigating retries, identify:

* operation being retried
* retry count
* retry condition
* retry delay
* final exception
* whether the operation is idempotent
* whether partial side effects occurred before retry

---

# Error Propagation vs Error Suppression

One of the most important concepts in this codebase is that not every error is propagated to the user.

A simplified model:


Operation
   ↓
Error
   |
   +── business-critical → propagate / fail journey
   |
   +── state-critical → update/fail state appropriately
   |
   +── downstream-critical → retry / fail depending on operation
   |
   +── best-effort → log and continue


For every `onErrorResume`, determine **why the error is being recovered**.

A common RCA mistake is:

> "There is an exception in the logs, therefore the user journey failed."

That conclusion is unsafe without tracing the reactive chain after the exception.

---

# Error Impact Classification

Use the following classification during RCA.

| Error category                  | Typical impact                             |
| ------------------------------- | ------------------------------------------ |
| Request validation              | Request rejected                           |
| Business rule                   | Business outcome / rejection               |
| State guard                     | Operation intentionally blocked            |
| External API failure            | Journey may fail, retry, or remain pending |
| Network timeout                 | Often retryable                            |
| Kafka publish failure           | Downstream state may become inconsistent   |
| Kafka consumer failure          | Async workflow may stop                    |
| MongoDB failure                 | Persisted state may be missing/stale       |
| Best-effort side-effect failure | User journey may continue                  |
| Configuration error             | Potentially systematic failure             |
| Serialization/parsing failure   | Integration/consumer flow may fail         |

The actual impact must always be determined from the surrounding code.

---

# External API Error Handling

External-system errors generally follow:


WebClient / Gateway
       ↓
HTTP response / network exception
       ↓
Parse response
       ↓
Map vendor error
       ↓
Retry or recover
       ↓
Business decision


Possible failure classes include:

* HTTP 4xx
* HTTP 5xx
* connection reset
* connection timeout
* read timeout
* DNS/connectivity failure
* malformed response
* unexpected content type
* JSON deserialization failure

Do not group all of these under "API failure."

The exact technical failure determines whether retry or configuration investigation is appropriate.

---

# Network Failures and Retry

Transient network exceptions may be retryable.

A representative failure is:


WebClientRequestException
Connection reset by peer


The correct RCA questions are:

1. Which downstream API was being called?
2. Was the failure before or after the request reached the downstream system?
3. Is the operation safe to retry?
4. Is retry configured?
5. Did retry eventually succeed?
6. If retry was absent, should it exist?
7. What application state remained after the failure?

This is particularly important for callback consumers because a transient downstream failure can leave the IA application in an intermediate state.

---

# HTTP Error Handling

For downstream HTTP failures, first classify the response.

## 4xx

Usually indicates:

* incorrect request
* invalid parameters
* authentication/authorization issue
* unsupported operation
* wrong endpoint/method

Investigate request construction and configuration before adding retries.

## 5xx

Usually indicates:

* downstream server failure
* infrastructure issue
* temporary dependency failure

Retry may be appropriate depending on the operation.

## Network exception

Examples:


Connection reset by peer
Connection refused
Timeout


These are different from receiving an HTTP 4xx/5xx response.

The downstream system may never have processed the request.

---

# Important BSA Error Path

The Zenith BSA initiation flow has a specific application error reference:


MLP2096 / MLP-2096


This represents an unexpected failure during AA-Orchestrator BSA initiation.

The BSA response wrapper supports both successful and error payloads.

Therefore, investigate:


BSA request
   ↓
Zenith gateway
   ↓
HTTP response
   ↓
success/error payload
   ↓
IA error mapping
   ↓
controller/service behavior


**Source citations**

* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/zenithorch/gateway/ZenithOrchestratorGateway.kt:16-20`
* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/bsa/model/InitiateBsaModels.kt:87-151`
* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/request/ZenithNotificationReceivedRequest.kt:28-66`

---

# Important Integration Error Pattern: HTML Instead of JSON

A particularly useful debugging pattern occurs when a downstream endpoint returns an unexpected content type.

Example:


Expected:
application/json

Received:
text/html


A common cause is a wrong endpoint, method, gateway route, environment, or stub.

The failure chain can look like:


Wrong endpoint
     ↓
HTTP 404
     ↓
HTML error page
     ↓
JSON model deserialization attempted
     ↓
UnsupportedMediaTypeException / parsing failure


The parsing exception is therefore potentially a **secondary error**.

Correct investigation order:

1. inspect HTTP status
2. inspect raw response body
3. inspect response content type
4. verify base URL
5. verify endpoint path
6. verify HTTP method
7. verify headers/content type
8. verify request body
9. verify environment/stub
10. only then modify parsing logic

**Source citations**

* `src/main/resources/application.yaml:341-349`
* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/controller/InitiateBsaController.kt:21-31`
* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/bsa/model/InitiateBsaModels.kt:82-151`

---

# Kafka Error Handling

Kafka introduces a separate failure domain.

A typical asynchronous flow is:


Business operation
      ↓
Kafka Producer
      ↓
Topic
      ↓
Consumer Group
      ↓
Consumer
      ↓
DB / External API
      ↓
Next Event


A failure can occur at any stage.

## Producer failure

Examples:

* serialization failure
* broker connectivity
* topic configuration
* oversized record
* producer timeout

## Consumer failure

Examples:

* deserialization failure
* filter mismatch
* transformer failure
* MongoDB failure
* downstream API failure
* business/state guard rejection

## Downstream failure after consumption

The Kafka event may have been successfully consumed while the actual business operation fails afterward.

Therefore:

> Kafka delivery success does not mean business processing success.

---

# Important Kafka Error: `RecordTooLargeException`

One important production failure class is:


org.apache.kafka.common.errors.RecordTooLargeException


This indicates that the Kafka record exceeds the applicable message-size limit.

Investigation should cover:


event payload size
+
producer configuration
+
topic configuration
+
broker limits
+
consumer limits


Also determine whether the event contained unexpectedly large:

* report JSON
* raw statements
* documents
* nested payloads

The business impact depends on what happens after the failed publication.

A common failure pattern is:


Primary operation succeeds
        ↓
MongoDB updated
        ↓
Kafka event publication fails
        ↓
Downstream consumer receives nothing
        ↓
Distributed state becomes inconsistent


Therefore, Kafka publication failure can be a **distributed consistency problem**, not merely an infrastructure error.

---

# Kafka Callback Error Handling

Callback consumers typically:


receive event
    ↓
lookup application
    ↓
check state guard
    ↓
call downstream service / process callback
    ↓
update MongoDB
    ↓
publish next event


Errors can occur at each stage.

When a callback-related incident occurs, distinguish:


callback not received
        ≠
callback received but not consumed
        ≠
callback consumed but rejected by state guard
        ≠
callback processed but DB update failed
        ≠
callback processed but next event failed


These are different RCA categories.

**Source citations**

* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/kafka/consumer/PerfiosCallbackReceivedConsumer.kt:104-160`
* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/kafka/consumer/ZenithCallbackReceivedConsumer.kt:77-136`

---

# Timeout and Callback-Not-Received Handling

Long-running vendor journeys can involve:


Vendor transaction
      ↓
Waiting for callback
      ↓
Callback timeout
      ↓
Status/retry processing
      ↓
Failure or retry


The timeout itself does not prove that the vendor journey failed.

A callback can arrive after the timeout.

Therefore, investigate:

* timeout timestamp
* retry count
* current application status
* vendor transaction ID
* callback timestamp
* callback event
* current attempt
* consumer state guard

A late callback can be valid but stale relative to the current application attempt.

---

# Error Handling in Multi-Attempt Journeys

One application can have multiple IA/vendor attempts.

Example:


Application A
   │
   ├── Attempt 1
   │     └── Vendor Transaction X
   │
   └── Attempt 2
         └── Vendor Transaction Y


Possible sequence:


Attempt 1
   ↓
Callback delayed
   ↓
Retry / timeout
   ↓
Attempt 2
   ↓
Attempt 2 succeeds
   ↓
Attempt 1 callback arrives late


The late callback may encounter a state guard and intentionally avoid updating the application.

Therefore, an error or warning around callback processing should always be correlated with:


incomeAssessmentId
applicationReferenceId
vendor transaction ID
attempt metadata
current MongoDB status
event timestamp


---

# Database Error Handling

MongoDB errors can cause:

* missing state updates
* stale application state
* failed lookups
* partial workflow completion
* incorrect downstream decisions

Important distinction:


Mongo lookup returns empty
        ≠
Mongo lookup throws exception


Also distinguish:


MongoDB update failed
        ≠
MongoDB update succeeded but Kafka publish failed


For a persistence-related incident, inspect:

* repository method
* query criteria
* returned document
* update operation
* reactive error path
* retry/recovery
* subsequent Kafka publication

---

# Best-Effort Side Effects

Some operations are intentionally handled as best-effort.

Typical examples may include:

* event publication
* CAP synchronization
* secondary notifications
* observability/analytics side effects

The presence of:


onErrorResume(...)


around an operation should trigger the question:

> Is this failure intentionally prevented from breaking the primary business flow?

Do not automatically convert such errors into user-facing failures.

**Source citations**

* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/multibank/service/CapSyncService.kt:107-137`
* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/revamp/service/impl/IncomeAssessmentApplicationServiceV3.kt:219-260`

---

# Error Logging and Observability

Important logging helpers include:


logOnError
logOnErrorWithThrowable
errorV
warnV


Useful correlation fields include:


requestId
serviceRequestId
applicationReferenceId
incomeAssessmentId
partnerId
productCode
eventId
retry count
attempt metadata
vendor transaction ID


When searching logs, avoid searching only by exception class.

Prefer a combination such as:


applicationReferenceId
+
incomeAssessmentId
+
eventId
+
error code


For vendor callback incidents, add:


vendor transaction ID


**Source citations**

* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/kafka/consumer/PerfiosCallbackReceivedConsumer.kt:108-157`
* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/kafka/consumer/ZenithCallbackReceivedConsumer.kt:81-133`
* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/repository/IncomeAssessmentRepository.kt:120-166`

---

# Error RCA Workflow

For any production error, use this sequence.

## Step 1 — Identify the failing operation

Examples:


API request
vendor API
Kafka publish
Kafka consume
Mongo lookup
Mongo update
document upload
callback processing


Do not start with the exception alone.

---

## Step 2 — Identify the original exception

Find the earliest meaningful technical failure.

Example:


Connection reset by peer


may be more useful than a later:


MLP-XXXX


or generic:


Internal Server Error


---

## Step 3 — Trace exception transformation

Determine whether the exception was:


caught
mapped
retried
recovered
swallowed
re-thrown


---

## Step 4 — Check retry behavior

Determine:


Was retry configured?
How many attempts?
What condition triggers retry?
Did retry succeed?


---

## Step 5 — Check application state

Inspect MongoDB:


status
statusType
retry counters
timestamps
iaAttempts
eventStatus
vendor transaction IDs


---

## Step 6 — Check Kafka side effects

Determine:


Was an event published?
Was it consumed?
Was filtering successful?
Did the consumer execute?
Was the next event published?


---

## Step 7 — Check downstream side effects

Determine whether external APIs or document operations were executed and whether they succeeded.

---

## Step 8 — Determine business impact

Finally classify the incident:


User-facing failure
State inconsistency
Downstream synchronization failure
Transient/recovered error
Best-effort side-effect failure
Configuration issue
Infrastructure issue


This prevents the RCA from stopping at the first exception found in logs.

---

# Error RCA Decision Tree

Use this as the default reasoning model:


Error observed
      ↓
Where did it originate?
      |
      +-- Controller
      +-- Business logic
      +-- Gateway
      +-- Kafka
      +-- MongoDB
      +-- Configuration
      |
      ↓
Was it transformed?
      |
      +-- YES → identify original + mapped error
      +-- NO
      |
      ↓
Was it retried?
      |
      +-- YES → inspect all attempts + final result
      +-- NO
      |
      ↓
Was it recovered/swallowed?
      |
      +-- YES → trace continuation
      +-- NO → trace propagated failure
      |
      ↓
Did application state change?
      |
      +-- YES → inspect resulting status
      +-- NO → determine why
      |
      ↓
Was Kafka event published?
      |
      +-- YES → trace consumer
      +-- NO → inspect producer failure
      |
      ↓
Did downstream side effect succeed?
      |
      +-- YES → continue workflow trace
      +-- NO → investigate dependency failure


---

# Error Handling Source-of-Truth Hierarchy

When determining how a specific error is handled, prefer:

1. **Current implementation at the failing call site**
2. **Error catalog**
3. **External-system error mapping/configuration**
4. **Retry/error operators surrounding the call**
5. **Controller/service response mapping**
6. **Kafka consumer/producer behavior**
7. **Current `application.yaml`**
8. **Tests/stubs**
9. **README or historical documentation**

The actual call-site behavior is more authoritative than a generic error catalog entry.

---

# High-Value Error Search Terms

## Error catalogs


IncomeAssesmentServiceError
IncomeAssessmentApplicationServiceError


## Reactive handling


onErrorResume
onErrorMap
switchIfEmpty
retry
retryWhen


## Logging


logOnError
logOnErrorWithThrowable
errorV
warnV


## Integration errors


WebClientRequestException
Connection reset by peer
timeout
UnsupportedMediaTypeException
404
405
415
5xx


## Kafka errors


RecordTooLargeException
Kafka publish failed
consumer failure
consumer group
deserialization
transformer
event not published
event not consumed


## Business/state errors


MLP2096
MLP-2096
state guard
callback not received
late callback
retry exhausted
status mismatch


---

# Important Code Anchors

### Error catalogs


src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/errorcodes/IncomeAssesmentServiceError.kt

src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/errorcodes/IncomeAssessmentApplicationServiceError.kt


### Error mapping/configuration


src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/utils/ConfigFetcher.kt
src/main/resources/application.yaml


### Business state guards


src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/domain/IncomeAssessmentApplication.kt


### Reactive service flow


src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/revamp/service/impl/IncomeAssessmentApplicationServiceV3.kt


### Callback error handling


src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/kafka/consumer/PerfiosCallbackReceivedConsumer.kt

src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/kafka/consumer/ZenithCallbackReceivedConsumer.kt


### BSA error path


src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/zenithorch/gateway/ZenithOrchestratorGateway.kt

src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/bsa/model/InitiateBsaModels.kt

src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/controller/InitiateBsaController.kt


### CAP / best-effort error handling


src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/multibank/service/CapSyncService.kt


---

# Key Error-Handling Invariants

1. **An exception in logs does not automatically mean the user journey failed.**
2. **The original technical exception and normalized IA error may be different.**
3. **`onErrorResume` can intentionally prevent an exception from failing the primary flow.**
4. **`onErrorMap` can hide the original exception unless the cause chain is inspected.**
5. **`switchIfEmpty` represents an empty result, not an exception.**
6. **Retry can make the first observed exception non-terminal.**
7. **HTTP errors and network exceptions are different failure classes.**
8. **A parsing exception may be secondary to an incorrect endpoint or content type.**
9. **A vendor error may be translated through configuration rather than hardcoded logic.**
10. **Kafka publication failure and Kafka consumer failure are different failure domains.**
11. **Kafka event publication success does not guarantee downstream processing success.**
12. **A callback can be received successfully but intentionally rejected by a state guard.**
13. **Late callbacks must be correlated with vendor transaction and attempt identity.**
14. **MongoDB state and Kafka state are not updated atomically.**
15. **Best-effort side-effect failures should be distinguished from business-critical failures.**
16. **The final business impact must be determined from the complete reactive/workflow chain, not the first exception.**

---

# RAG Retrieval Guidance

Retrieve context based on the failure question.

### "What does this error code mean?"

Retrieve:


error catalog
+
ConfigFetcher mappings
+
call sites


### "Why is this vendor error mapped to this IA error?"

Retrieve:


vendor gateway
+
ConfigFetcher
+
application.yaml
+
error catalog


### "Why didn't this error fail the journey?"

Retrieve:


failing call site
+
onErrorResume/onErrorMap
+
caller
+
subsequent DB/Kafka operations


### "Why did retry not happen?"

Retrieve:


failing gateway/service
+
retry configuration
+
retry operators
+
exception type


### "Why did callback processing fail?"

Retrieve:


callback consumer
+
state guards
+
MongoDB
+
vendor transaction identity
+
downstream API
+
Kafka events


### "Why is there an UnsupportedMediaTypeException?"

Retrieve:


gateway
+
endpoint configuration
+
HTTP method
+
response content type
+
raw response


### "Why is MongoDB state correct but downstream state wrong?"

Retrieve:


repository
+
Kafka producer
+
event
+
consumer
+
downstream API


### "Why is the user stuck despite the vendor succeeding?"

Retrieve:


vendor integration
+
callback consumer
+
Kafka event
+
MongoDB status
+
retry/timeout behavior
+
downstream side effects


---

# Preferred Error Investigation Mental Model

For every production issue, reason through:


What failed?
    ↓
Where did it fail?
    ↓
What was the original exception?
    ↓
Was it mapped?
    ↓
Was it retried?
    ↓
Was it recovered/swallowed?
    ↓
What happened to MongoDB state?
    ↓
What Kafka event was published?
    ↓
Was it consumed?
    ↓
What downstream operation happened?
    ↓
What was the final business impact?


The canonical RCA principle for this service is:

> **Do not stop at the exception. Trace the exception through the reactive chain and determine its effect on application state, Kafka propagation, downstream systems, and the final user journey.**
