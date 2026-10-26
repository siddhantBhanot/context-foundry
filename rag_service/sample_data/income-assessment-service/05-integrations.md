# Integrations

## 1. Integration Overview

The Income Assessment (IA) Service is an orchestration layer that communicates with multiple internal and external systems during the IA lifecycle.

Integrations are primarily used for:

* starting vendor journeys
* generating redirect links
* uploading documents
* retrieving bank statements/raw data
* retrieving assessment reports
* initiating BSA
* synchronizing consent/status
* validating authentication/context
* generating or persisting documents
* supporting ITR flows
* retrieving customer/product/master-data context

The major integrations are:

| System                          | Primary responsibility                     | Typical IA usage                                                        |
| ------------------------------- | ------------------------------------------ | ----------------------------------------------------------------------- |
| **Perfios**                     | Income assessment / ITR vendor processing  | Start transaction, upload, status, callback, report retrieval           |
| **Zenith / AA-Orchestrator**    | Account Aggregator orchestration and BSA   | Generate AA journey/link, retrieve raw statements/reports, initiate BSA |
| **Document Service / OmniDocs** | Document storage and retrieval             | Upload and retrieve IA/ITR artifacts                                    |
| **Auth Service**                | Authentication and user/context resolution | Token validation and claims                                             |
| **CAP Service**                 | Consent/status synchronization             | Update consent/IA-related status                                        |
| **DG Service**                  | Document generation                        | Generate documents in selected flows                                    |
| **FinFort**                     | Online ITR journey                         | ITR consent/link and related processing                                 |
| **Loan Orchestrators**          | Loan/product orchestration                 | Application/product context and downstream workflow                     |
| **Customer Service**            | Customer information                       | Customer/application context                                            |
| **Master Data Services**        | Reference/product data                     | Product and business context                                            |

**Source citations**

* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/revamp/service/impl/IncomeAssessmentApplicationServiceV3.kt:149-178`
* `src/main/resources/application.yaml:53-203`
* `src/main/resources/application.yaml:229-350`

---

# 2. Integration Map

A simplified view of the major external interactions is:


                         ┌──────────────┐
                         │     IA       │
                         │   Service    │
                         └──────┬───────┘
                                │
          ┌─────────────────────┼────────────────────────┐
          │                     │                        │
          ▼                     ▼                        ▼
      Perfios             Zenith / AA              Document Service
          │                Orchestrator                   │
          │                     │                        │
          ▼                     ▼                        ▼
   Vendor IA / ITR       AA / BSA Journey          Documents/Artifacts


          ┌─────────────────────┼────────────────────────┐
          │                     │                        │
          ▼                     ▼                        ▼
       CAP Service          Auth Service              FinFort
          │                     │                        │
          ▼                     ▼                        ▼
    Consent/status       Token/context               ITR Flow
       sync               resolution


                         ┌──────────────┐
                         │ Downstream   │
                         │ Orchestrators│
                         └──────────────┘


IA should be treated as the **orchestrator**, while the external systems own their respective domain operations.

---

# 3. Perfios Integration

## Purpose

Perfios is used for vendor-side income-assessment and ITR processing.

Typical operations include:

* starting a transaction
* generating/receiving a redirect URL
* uploading documents/data
* checking transaction status
* retrieving reports
* processing vendor callbacks
* ITR-related vendor operations

A typical Perfios journey is:


IA
 ↓
Start Transaction
 ↓
Perfios returns vendor/transaction information
 ↓
IA redirects user to Perfios
 ↓
User completes vendor journey
 ↓
Perfios callback
 ↓
IA processes callback
 ↓
Fetch report/status/data
 ↓
Update IA state
 ↓
Publish downstream event


### Important debugging distinction

A successful `/start-transaction` response means only that **vendor transaction initiation succeeded**.

It does not prove that:

* the user completed the vendor journey
* Perfios successfully processed the user's data
* IA received the callback
* the report was retrieved
* MongoDB state was updated
* the Kafka event was published
* downstream processing succeeded

When investigating a Perfios issue, trace the complete transaction lifecycle rather than only the initial API call.

### Relevant integration configuration

Perfios configuration is under:


platform.perfios.*


This includes:

* Perfios URLs
* endpoint paths
* retry configuration
* request metadata
* vendor integration settings

**Source citations**

* `src/main/resources/application.yaml:194-203`
* `src/main/resources/application.yaml:229-259`

---

# 4. Zenith / AA-Orchestrator Integration

## Purpose

Zenith / AA-Orchestrator supports Account Aggregator (AA) and bank-statement-related flows.

Typical operations include:

* AA journey/link generation
* raw statement retrieval
* report retrieval
* BSA initiation
* related AA orchestration

The Zenith gateway is represented by:

* `ZenithOrchestratorGateway`

### BSA initiation

The configured BSA endpoint is:


/aa-orch/fiu/api/v1/initiateBSA


The IA BSA controller is:

* `InitiateBsaController`

BSA request/response models are defined in:

* `bsa/model/InitiateBsaModels.kt`

### Important debugging distinction

For Zenith issues, distinguish between:

1. IA controller/request handling
2. Zenith gateway invocation
3. request construction
4. endpoint/path resolution
5. HTTP response
6. response parsing
7. business processing after the response

A `404` from Zenith may indicate an incorrect:

* URL
* base path
* endpoint path
* HTTP method
* stub configuration
* environment configuration

rather than a business-rule failure.

**Source citations**

* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/zenithorch/gateway/ZenithOrchestratorGateway.kt:54-120`
* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/controller/InitiateBsaController.kt:21-31`
* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/bsa/model/InitiateBsaModels.kt:82-151`
* `src/main/resources/application.yaml:330-339`

---

# 5. Document Service / OmniDocs

## Purpose

Document Service / OmniDocs provides persistence and retrieval of uploaded or generated documents used by IA and ITR flows.

Typical operations include:

* document upload
* document retrieval
* document persistence
* storing generated artifacts
* retrieving previously uploaded/generated artifacts

Important configured paths include:


/document-service/v3/documents
/document-service/v4/documents
/document-service/v7/documents


Different API versions may be used by different document workflows.

### Relevant code anchor

* `DocumentServiceClient`

When debugging document-related issues, identify the exact document API version used by the calling flow before assuming that all document operations use the same endpoint.

**Source citations**

* `src/main/resources/application.yaml:53-145`
* `src/main/resources/application.yaml:341-350`
* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/revamp/service/impl/IncomeAssessmentApplicationServiceV3.kt:149-178`

---

# 6. Auth Service / Token Service

## Purpose

Authentication-related services support:

* token validation
* claims extraction
* authentication context
* version/context resolution

Configured groups include:


platform.auth-service.*
platform.token-service.*


Important code anchor:

* `AuthServiceClient`

Authentication/context information can influence which IA journey or implementation path is selected.

Therefore, an authentication/configuration issue can sometimes manifest as an apparently incorrect business flow.

**Source citations**

* `src/main/resources/application.yaml:53-145`
* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/revamp/service/impl/IncomeAssessmentApplicationServiceV3.kt:149-178`

---

# 7. CAP Service

## Purpose

CAP is used for synchronization of consent/status after IA workflow transitions.

Important service:

* `CapSyncService`

Configured endpoint:


/internal/cap/api/initiate/event/update/status


The CAP integration uses direct HTTP/WebClient handling where HTTP control and request behavior are important.

### CAP flow


IA workflow transition
       ↓
CAP sync required
       ↓
CapSyncService
       ↓
CAP update-status API
       ↓
CAP response


CAP synchronization should be treated as a **downstream synchronization operation** rather than the source of truth for the IA application's primary state.

When debugging CAP issues, separately verify:

* IA state before CAP call
* CAP request construction
* CAP HTTP response
* error handling / retry
* IA state after the CAP call

**Source citations**

* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/multibank/service/CapSyncService.kt:43-59`
* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/multibank/service/CapSyncService.kt:63-137`
* `src/main/resources/application.yaml:194-203`

---

# 8. DG Service

## Purpose

DG Service supports document-generation operations in selected IA flows.

Important client:

* `DgClient`

DG should be considered a supporting integration rather than the primary IA state owner.

When debugging DG failures, identify:

* which workflow requested document generation
* whether document generation is mandatory for that workflow
* whether failure blocks the primary journey or is handled as a secondary operation
* whether the generated artifact must subsequently be persisted in Document Service

**Source citation**

* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/revamp/service/impl/IncomeAssessmentApplicationServiceV3.kt:149-178`

---

# 9. FinFort Integration

## Purpose

FinFort supports the online ITR consent/link journey.

Important client:

* `FinFortClient`

Typical conceptual flow:


IA
 ↓
Determine ITR path
 ↓
FinFort
 ↓
Online ITR consent/link journey
 ↓
FinFort result/callback/status
 ↓
IA continues ITR workflow


Relevant IA behavior may depend on:

* ITR status
* feature/configuration
* document state
* retry/terminal-state guards

**Source citation**

* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/revamp/service/impl/IncomeAssessmentApplicationServiceV3.kt:149-178`

---

# 10. Loan Orchestrators, Customer and Master Data

These integrations provide contextual information used by IA.

They can supply or influence:

* customer information
* application information
* loan/product context
* partner/product identification
* reference/master data

These integrations are important because IA behavior can be **partner/product-dependent**.

A downstream API failure in one of these systems may therefore prevent IA from resolving the correct business context before the actual income-assessment flow starts.

**Source citations**

* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/revamp/service/impl/IncomeAssessmentApplicationServiceV3.kt:149-178`
* `src/main/resources/application.yaml:53-145`

---

# 11. Endpoint Configuration

Integration URLs and endpoint paths are primarily configured in:


src/main/resources/application.yaml


### Configuration namespaces

| Namespace              | Integration area                                    |
| ---------------------- | --------------------------------------------------- |
| `platform.endpoints.*`     | Internal orchestrators, customer, document, CAP, DG |
| `platform.perfios.*`       | Perfios URLs, paths, retries, metadata              |
| `platform.gateway.*`        | Zenith base URL and endpoint paths                  |
| `platform.auth-service.*`  | Authentication service                              |
| `platform.token-service.*` | Token/authentication support                        |

### Known endpoint examples


Zenith BSA:
/aa-orch/fiu/api/v1/initiateBSA

CAP:
/internal/cap/api/initiate/event/update/status

Document Service:
/document-service/v3/documents
/document-service/v4/documents
/document-service/v7/documents


### Configuration debugging rule

When an integration returns an unexpected `404`, `405`, `415`, or similar HTTP error, verify:


Environment
 ↓
Base URL
 ↓
Configured endpoint path
 ↓
HTTP method
 ↓
Request content type
 ↓
Request body
 ↓
Headers
 ↓
Actual generated request


Do not assume that a business-logic bug is responsible until the actual outbound request is verified.

**Source citations**

* `src/main/resources/application.yaml:53-145`
* `src/main/resources/application.yaml:194-203`
* `src/main/resources/application.yaml:229-259`
* `src/main/resources/application.yaml:330-350`

---

# 12. Integration Client / Gateway Map

The following classes are important anchors when tracing an external call:

| Integration      | Primary code anchor                                                          |
| ---------------- | ---------------------------------------------------------------------------- |
| Zenith / AA      | `ZenithOrchestratorGateway`                                                  |
| Document Service | `DocumentServiceClient`                                                      |
| Auth             | `AuthServiceClient`                                                          |
| FinFort          | `FinFortClient`                                                              |
| DG               | `DgClient`                                                                   |
| CAP              | `CapSyncService`                                                             |
| Perfios          | Bank-statement transaction/upload/report gateway facades + callback consumer |

`IncomeAssessmentApplicationServiceV3` is an important orchestration entry point because it wires multiple integration dependencies directly.

Therefore, for a question such as:

> "Where does IA call service X?"

a good starting path is:


IncomeAssessmentApplicationServiceV3
        ↓
Integration Client/Gateway
        ↓
Configuration
        ↓
Actual HTTP/WebClient/ESB call


**Source citations**

* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/revamp/service/impl/IncomeAssessmentApplicationServiceV3.kt:149-178`
* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/zenithorch/gateway/ZenithOrchestratorGateway.kt:54-69`
* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/multibank/service/CapSyncService.kt:43-59`

---

# 13. Integration Implementation Patterns

The service uses multiple integration patterns depending on the downstream system.

## 13.1 ESB-backed / encrypted flows

Selected Perfios and Zenith interactions use encrypted ESB-backed request/response processing.

When debugging these integrations, investigate both:

* application-level request/response handling
* encryption/decryption or ESB transport behavior

A downstream business error may be hidden behind an integration/transport error.

**Source citation**

* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/zenithorch/gateway/ZenithOrchestratorGateway.kt:73-120`

---

## 13.2 Direct WebClient flows

Some integrations use direct `WebClient` calls where explicit control over HTTP behavior is required.

Examples include:

* CAP status updates
* Zenith BSA initiation

For these flows, HTTP-level details are important:

* method
* URL
* headers
* content type
* request body
* response status
* response content type
* response parsing

**Source citations**

* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/multibank/service/CapSyncService.kt:63-137`
* `src/main/resources/application.yaml:330-339`

---

## 13.3 Retry-enabled integrations

Network-heavy integrations may use Reactor retry operators.

When an API call fails, determine:

1. Is retry configured?
2. Which exception types trigger retry?
3. How many attempts are made?
4. What is the retry delay?
5. What happens after retry exhaustion?
6. Does the business workflow fail, remain in progress, or continue?

Do not assume that the presence of a retry operator means every failure will be retried.

**Source citation**

* `src/main/resources/application.yaml:330-339`

---

# 14. Error Handling and Business Impact

An integration exception does not automatically mean the IA journey has failed.

Classify the downstream operation first.

### Business-critical integration

Failure may directly prevent IA from progressing.

Examples:


Vendor transaction initiation
Vendor report retrieval
Required document operation
Required downstream assessment API


### State synchronization integration

Failure may create a discrepancy between systems.

Example:


IA state updated
      ↓
CAP synchronization fails
      ↓
IA and CAP may contain different states


### Event / best-effort integration

Failure may be intentionally absorbed so that the primary user flow continues.

Therefore, when analyzing an exception, determine:


Did the external call fail?
        ↓
Was it retried?
        ↓
Was the error propagated?
        ↓
Was IA state updated?
        ↓
Was an event published?
        ↓
Did downstream processing continue?


This distinction is essential for RCA.

---

# 15. Integration Failure Debugging Workflow

For any external API failure, use the following sequence.

## Step 1 — Identify the integration

Determine whether the failing dependency is:

* Perfios
* Zenith / AA
* Document Service
* Auth
* CAP
* DG
* FinFort
* Customer
* Loan Orchestrator
* Master Data
* another downstream service

## Step 2 — Find the client/gateway

Locate the corresponding:

* client
* gateway
* service
* callback consumer

## Step 3 — Find configuration

Check the relevant `application.yaml` namespace.

Verify:

* base URL
* endpoint path
* timeout
* retry settings
* required metadata

## Step 4 — Verify the actual request

Compare:


Expected
vs
Actual

HTTP method
URL
Path
Headers
Content-Type
Request body
Authentication


## Step 5 — Analyze the response

Check:

* HTTP status
* response body
* response content type
* parsing behavior
* downstream error code

## Step 6 — Check retry behavior

Determine:

* whether retry occurred
* number of attempts
* final attempt result
* whether retry exhaustion changed IA state

## Step 7 — Check business-state impact

Inspect:

* MongoDB application status
* transaction status
* document state
* Kafka event
* downstream consumer state

## Step 8 — Reconstruct the complete timeline


IA request
 ↓
Client/Gateway
 ↓
Outbound request
 ↓
External service
 ↓
Response/error
 ↓
Retry
 ↓
DB state update
 ↓
Kafka/event
 ↓
Downstream processing
 ↓
Final IA state


---

# 16. Common Integration Failure Patterns

## 16.1 404 Not Found

Usually investigate:

* incorrect base URL
* incorrect endpoint path
* environment configuration
* missing gateway prefix
* wrong stub path
* wrong service version

Do not immediately classify a `404` as a business failure.

---

## 16.2 405 Method Not Allowed

Investigate:

* configured HTTP method
* gateway implementation
* controller contract
* downstream API contract
* mountebank/stub method

---

## 16.3 415 Unsupported Media Type

Investigate:

* `Content-Type`
* request body encoding
* JSON vs form-data
* stub expectations
* downstream API contract

---

## 16.4 HTML Error Returned Where JSON Is Expected

A common integration-test/stub failure pattern is:


IA request
 ↓
Stub does not match request
 ↓
Stub/server returns HTML 404
 ↓
IA expects JSON error body
 ↓
JSON parsing fails
 ↓
Original integration error becomes harder to diagnose


This is particularly relevant for Zenith BSA initiation.

When using mountebank or similar stubs, ensure the stub matches:

* exact HTTP method
* exact path
* expected headers/content type
* request structure

**Source citations**

* `src/main/resources/application.yaml:341-349`
* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/controller/InitiateBsaController.kt:21-31`
* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/bsa/model/InitiateBsaModels.kt:82-151`

---

# 17. Integration Testing / Mountebank Guidance

For integration tests using mountebank or similar HTTP stubs, the stub contract must match the application's outbound request.

At minimum verify:


HTTP method
+
URL/path
+
headers
+
Content-Type
+
request body


A mismatch can cause the stub to return a generic `404` or HTML response.

This can create a **secondary parsing exception** that hides the original integration mismatch.

### Debugging order

When a test fails with a JSON parsing error:


1. Check raw HTTP status
2. Check raw response Content-Type
3. Check raw response body
4. Verify stub path
5. Verify HTTP method
6. Verify request headers
7. Verify request body
8. Only then inspect JSON parsing


---

# 18. Integration Observability / Correlation

Integration troubleshooting depends heavily on correlating requests across systems.

Where available, use:

* `applicationReferenceId`
* vendor transaction ID
* vendor ID
* request ID
* correlation ID
* transaction attempt
* timestamp
* event ID

For asynchronous integrations, timestamps are especially important.

A useful investigation timeline is:


T0  IA request
T1  External transaction initiated
T2  Redirect/link generated
T3  User/vendor processing
T4  Callback received
T5  External report/status API called
T6  Retry, if any
T7  MongoDB update
T8  Kafka event publish
T9  Downstream consumer
T10 Final application state


Always correlate the **transaction attempt** with the callback/event being investigated.

---

# 19. Integration Source-of-Truth Hierarchy

When determining how an integration works, use this priority:

1. **Current client/gateway implementation**
2. **Current `application.yaml` configuration**
3. **Controller/request/response models**
4. **Callback consumers**
5. **Integration tests/stubs**
6. **README/documentation**

If documentation disagrees with the actual endpoint configured in `application.yaml` or implemented by the gateway, treat the current code/configuration as authoritative.

---

# 20. High-Value RAG Terms / Synonyms

### Perfios

* Perfios
* Perfios API
* Perfios integration
* Perfios transaction
* start transaction
* vendor transaction
* Perfios callback
* Perfios report
* Perfios status
* statement upload
* ITR journey
* vendor ID

### Zenith

* Zenith
* AA-Orchestrator
* AA orchestrator
* Zenith gateway
* AA journey
* account aggregator
* AA link
* raw statement
* raw report
* BSA
* initiate BSA
* BSA initiation

### Document Service

* Document Service
* OmniDocs
* document upload
* document retrieval
* document persistence
* artifact
* generated document

### CAP

* CAP
* CAP sync
* CapSyncService
* consent sync
* status sync
* update status

### Auth

* Auth Service
* token service
* token validation
* claims
* authentication context

### Integration failures

* downstream failure
* external API failure
* integration failure
* API timeout
* connection reset
* connection refused
* 404
* 405
* 415
* HTTP error
* response parsing error
* JSON parsing error
* HTML response
* retry
* retry exhausted
* timeout
* endpoint mismatch
* stub mismatch
* mountebank

---

# 21. Key Integration Invariants

1. **IA is the orchestrator; downstream systems own their respective operations.**

2. **Starting a vendor transaction does not mean the vendor journey completed.**

3. **A successful external API call does not necessarily mean the overall IA journey succeeded.**

4. **MongoDB application state and downstream-system state can diverge.**

5. **Kafka/event success and external API success are separate concerns.**

6. **Retry behavior is integration-specific.** Never assume every external failure is retried.

7. **Endpoint configuration and client implementation must be considered together.**

8. **A downstream HTTP error can be caused by environment/base-path/method/stub configuration rather than business logic.**

9. **A parsing exception can be a secondary error.** Always inspect the raw HTTP response before concluding that response parsing is the root cause.

10. **Multiple vendor transaction attempts may belong to one IA application.** Always correlate callbacks/events with the correct transaction attempt.

11. **Asynchronous callbacks must be analyzed against application state at callback time**, not only against the state that existed when the transaction was initially created.

12. **Current implementation and configuration are more authoritative than historical documentation.**

---

# 22. Important Integration Code Anchors

| Area               | Code anchor                                                   | Primary use                                              |
| ------------------ | ------------------------------------------------------------- | -------------------------------------------------------- |
| Main orchestration | `revamp/service/impl/IncomeAssessmentApplicationServiceV3.kt` | Integration dependency wiring and workflow orchestration |
| Zenith             | `zenithorch/gateway/ZenithOrchestratorGateway.kt`             | Zenith/AA outbound calls                                 |
| BSA entry point    | `controller/InitiateBsaController.kt`                         | BSA request entry point                                  |
| BSA models         | `bsa/model/InitiateBsaModels.kt`                              | BSA request/response contracts                           |
| Document Service   | `DocumentServiceClient`                                       | Document APIs                                            |
| Auth               | `AuthServiceClient`                                           | Authentication/token operations                          |
| FinFort            | `FinFortClient`                                               | Online ITR integration                                   |
| DG                 | `DgClient`                                                    | Document generation                                      |
| CAP                | `multibank/service/CapSyncService.kt`                         | CAP synchronization                                      |
| Perfios callbacks  | `kafka/consumer/PerfiosCallbackReceivedConsumer.kt`           | Vendor callback processing                               |
| Zenith callbacks   | `kafka/consumer/ZenithCallbackReceivedConsumer.kt`            | Zenith callback processing                               |
| Configuration      | `src/main/resources/application.yaml`                         | URLs, endpoint paths, retries and integration settings   |

---

# 23. RAG Retrieval Guidance

When answering an integration question, retrieve information according to the failure/question type.

### "Which service does IA call for X?"

Retrieve:


IncomeAssessmentApplicationServiceV3
→ Relevant client/gateway
→ application.yaml


### "What endpoint does IA call?"

Retrieve:


Client/Gateway implementation
+
application.yaml


Prioritize the **actual configured endpoint** over README descriptions.

### "Why is external API returning 404?"

Retrieve:


Gateway/client
+
application.yaml
+
test/stub configuration


Check:

* base URL
* path
* HTTP method
* environment
* stub mapping

### "Why did response parsing fail?"

Retrieve:


HTTP client implementation
+
error handling
+
request/response model
+
test stub


Check the raw response status/content type before assuming malformed JSON.

### "Why is IA stuck after callback?"

Retrieve:


Callback consumer
→ downstream API call
→ retry logic
→ MongoDB update
→ Kafka event
→ downstream consumer
→ final status


### "Was the external API failure responsible for the IA failure?"

Retrieve both:

1. integration implementation
2. business-state/transition logic

Then determine whether the error was:

* propagated
* retried
* swallowed/best-effort
* converted into a status
* followed by a successful state update

### Preferred integration reasoning path


Business Flow
→ Integration Client/Gateway
→ Configuration
→ Actual HTTP Request
→ External Response
→ Retry/Error Handling
→ DB State
→ Event
→ Downstream State

