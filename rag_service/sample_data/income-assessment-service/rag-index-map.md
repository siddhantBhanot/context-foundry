# RAG Index Map

This file is the **first-pass retrieval router** for the Income Assessment Service knowledge base.

Its purpose is to map a developer question to the **smallest and most authoritative knowledge-base chunk first**, before broader retrieval or repository/code search is performed.

The retrieval system should answer two separate questions:

1. **What does IA do?** → Flow / business / configuration documentation.
2. **Where and how is it implemented?** → Code anchors / implementation snippets / repository code.

---

# 1. Retrieval Priority

Prefer retrieval in this order:

1. **Specific flow documentation** for journey-specific questions.
2. **Troubleshooting documentation** for incident/debugging questions.
3. **Business logic** for state, guards, and business-rule questions.
4. **Integration documentation** for external system/API behavior.
5. **Configuration documentation** for toggles, versions, endpoints, retries, and error mappings.
6. **Database/Kafka documentation** for persistence and asynchronous propagation.
7. **API contracts** for exact request/response questions.
8. **Code anchors** for implementation location and code navigation.
9. **Implementation snippets** for exact code-level behavior.
10. **Glossary** for terminology and concise definitions.
11. **Architecture** for broad structural questions.

### Important rule

Do not retrieve implementation snippets merely because a question contains a technical term.

First determine the question intent:

```text
"What is X?"
        ↓
Glossary / relevant documentation

"How does X work?"
        ↓
Flow / integration / business documentation

"Where is X implemented?"
        ↓
code-anchors.md

"How exactly does X call Y?"
        ↓
integration-snippets.md / relevant code snippet

"Why did X fail?"
        ↓
troubleshooting.md
        ↓
relevant flow
        ↓
error-handling
        ↓
code/config anchors
```

---

# 2. Retrieval Principles

## 2.1 Prefer the narrowest relevant chunk

Do not retrieve a broad architecture section when a dedicated flow, troubleshooting section, or code anchor directly answers the question.

Examples:

* "How does Zenith work?" → `flows/zenith-flow.md`
* "Why did Zenith BSA return 404?" → `10-troubleshooting.md`
* "What is `enableZenithOrchAPI`?" → `09-configuration.md`
* "What is BSA?" → `11-glossary.md`
* "Where is Perfios start transaction implemented?" → `code-anchors.md`
* "How does Perfios start transaction call ESB?" → `code/integration-snippets.md`

---

## 2.2 Distinguish explanation from implementation

Use:

| User intent                        | Primary source                    |
| ---------------------------------- | --------------------------------- |
| What is it?                        | `11-glossary.md`                  |
| Why does it happen?                | `04-business-logic.md`            |
| What is the overall flow?          | `flows/income-assessment-flow.md` |
| How does a specific journey work?  | Relevant `flows/*` file           |
| How does an external system work?  | `05-integrations.md`              |
| Which configuration controls it?   | `09-configuration.md`             |
| Where is it stored?                | `06-database.md`                  |
| How does Kafka propagate it?       | `07-kafka-events.md`              |
| Why did it fail?                   | `10-troubleshooting.md`           |
| How is the error handled?          | `08-error-handling.md`            |
| Which API contract is involved?    | `03-api-contracts.md`             |
| Where is it implemented?           | `code-anchors.md`                 |
| Show exact implementation behavior | Relevant `code/*-snippets.md`     |

---

## 2.3 Distinguish business flow from integration mechanics

Use:

* `flows/income-assessment-flow.md` → canonical IA lifecycle.
* `flows/perfios-flow.md` → Perfios-specific execution.
* `flows/zenith-flow.md` → Zenith-specific execution.
* `flows/cap-flow.md` → CAP initiation and CAP status synchronization.
* `flows/itr-flow.md` → ITR-specific execution.
* `flows/gst-flow.md` → GST-specific execution.

Use:

* `05-integrations.md` → integration responsibilities and boundaries.
* `code/integration-snippets.md` → exact integration implementation.
* `code-anchors.md` → where to find the relevant implementation.

Do not use generic architecture as the primary source when a dedicated flow applies.

---

# 3. Upstream Platforms vs Journey Providers

The following distinction must be preserved during retrieval:

```text
Upstream Platform / Client
          |
          | initiate IA
          v
Income Assessment Service
          |
          | selects / executes IA journey
          +------> Perfios
          |
          +------> Zenith / AA-Orchestrator
          |
          +------> Other IA processing paths
          |
          | optional post-processing synchronization
          v
CAP status synchronization
```

**CAP is an external upstream platform/client that can initiate IA.**

**Perfios and Zenith are external journey/integration providers used by IA after initiation.**

Therefore:

> CAP must not be retrieved as a synonym for the Perfios/Zenith journey.

---

# 4. CAP Retrieval Routing

CAP questions must be split into two independent interactions.

## 4.1 CAP Initiation

```text
CAP
 ↓
POST /income-assessment-service/v1/initiate-application
 ↓
IA lifecycle
 ↓
Perfios / Zenith / other IA path
```

Primary retrieval:

```text
flows/cap-flow.md
        ↓
flows/income-assessment-flow.md
        ↓
03-api-contracts.md
        ↓
code-anchors.md
```

Implementation questions:

```text
"Where is CAP initiation handled?"
        ↓
code-anchors.md
        ↓
orchestration-snippets.md
```

---

## 4.2 CAP Status Synchronization

```text
IA outcome
 ↓
capSyncEnabled
 ↓
CapSyncService
 ↓
IA status → CAP EventStatus
 ↓
CAP PATCH update-status API
```

Primary retrieval:

```text
flows/cap-flow.md
        ↓
09-configuration.md
        ↓
05-integrations.md
        ↓
08-error-handling.md
```

Implementation questions:

```text
"Where is CAP PATCH implemented?"
        ↓
code-anchors.md
        ↓
integration-snippets.md
```

High-value terms:

* `CapSyncService`
* `CapSyncServiceFacade`
* `capSyncEnabled`
* `capRefId`
* `EventStatus`
* `eventStatus`
* `callCapServiceUpdateStatus`
* `syncCapConsentStatus`
* HTTP `PATCH`
* CAP update-status API
* best-effort synchronization

---

# 5. Main IA Lifecycle Retrieval

For:

* overall IA flow
* application initiation
* journey selection
* version routing
* state progression
* terminal outcomes

retrieve:

```text
flows/income-assessment-flow.md
        ↓
01-architecture.md
        ↓
04-business-logic.md
        ↓
09-configuration.md
        ↓
code-anchors.md
```

For implementation tracing:

```text
IncomeAssessmentApplicationController
        ↓
CommonVersionResolver
        ↓
IncomeAssessmentApplicationServiceFacade
        ↓
ServiceFacade.executeWithVersion(...)
        ↓
IncomeAssessmentApplicationServiceRevamp
        ↓
IncomeAssessmentApplicationServiceV3
```

Primary code anchors:

* `IncomeAssessmentApplicationController`
* `CommonVersionResolver`
* `IncomeAssessmentApplicationServiceFacade`
* `ServiceFacade.executeWithVersion`
* `IncomeAssessmentApplicationServiceRevamp`
* `IncomeAssessmentApplicationServiceV3`

---

# 6. Initiation Questions

For:

* `/initiate-application`
* who invokes IA
* application creation
* partner/product context
* request context
* version selection
* initial state

retrieve:

```text
flows/income-assessment-flow.md
        ↓
01-architecture.md
        ↓
03-api-contracts.md
        ↓
09-configuration.md
        ↓
code-anchors.md
        ↓
orchestration-snippets.md
```

For exact implementation:

```text
IncomeAssessmentApplicationController
        ↓
CommonVersionResolver
        ↓
IncomeAssessmentApplicationServiceFacade
        ↓
IncomeAssessmentApplicationServiceRevamp
        ↓
IncomeAssessmentApplicationServiceV3
```

---

# 7. Version Routing Retrieval

For:

* `iaVersion`
* version bucket
* same request taking different code paths
* version-specific implementation
* facade resolution

retrieve:

```text
09-configuration.md
        ↓
01-architecture.md
        ↓
code-anchors.md
        ↓
orchestration-snippets.md
```

Core chain:

```text
Request
 ↓
KeyData
 ↓
CommonVersionResolver.primeBucket(...)
 ↓
Version Bucket
 ↓
VersionContext
 ↓
ServiceFacade.executeWithVersion(...)
 ↓
versionResolver.resolveFromBucket(...)
 ↓
Version-specific service
```

High-value code anchors:

* `CommonVersionResolver`
* `ServiceFacade.executeWithVersion`
* `VersionContext.getBucket`
* `versionResolver.resolveFromBucket`
* `IncomeAssessmentApplicationServiceFacade`

---

# 8. `/validate` Retrieval

For:

* what `/validate` does
* why the UI receives a particular action
* retry behavior
* loader timeout
* next page/action
* policy-norm redirect

retrieve:

```text
code-anchors.md
        ↓
orchestration-snippets.md
        ↓
09-configuration.md
        ↓
04-business-logic.md
```

Important implementation concepts:

* `primeBucket(...)`
* `validate(...)`
* `getNextAction(...)`
* `determineNextAction(...)`
* `retry`
* `timedOut`
* `accountSelectionCancel`
* `retryErrorMsgScreen`
* `isRetryLimitReached`

---

# 9. Journey-Link Retrieval

For:

* generate-link
* redirect link
* why Zenith was selected
* why Perfios was selected

retrieve:

```text
relevant flow
        ↓
09-configuration.md
        ↓
code-anchors.md
        ↓
orchestration-snippets.md
```

Core decision:

```text
enableZenithOrchAPI
        +
assessmentMedium == ACCOUNT_AGGREGATOR
        ↓
Zenith journey-link generation
```

Otherwise the applicable path uses the Perfios link-generation implementation.

---

# 10. Perfios Retrieval Route

For Perfios lifecycle questions:

```text
flows/perfios-flow.md
        ↓
05-integrations.md
        ↓
04-business-logic.md
        ↓
07-kafka-events.md
        ↓
06-database.md
```

For implementation questions:

```text
code-anchors.md
        ↓
integration-snippets.md
        ↓
orchestration-snippets.md
```

### High-value Perfios operations

* start transaction
* generate link
* upload statement
* complete transaction
* transaction status
* callback
* callback timeout
* report retrieval
* raw statement retrieval
* report validation
* OmniDocs upload

### Perfios code anchors

* `startTransaction(...)`
* `perfiosStartTransaction(...)`
* `uploadStatement(...)`
* `completeTransaction(...)`
* `generateLinkEsbEncryptedRequest(...)`
* `fetchTransactionLog(...)`
* `makeTransactionStatusRequest(...)`
* `fetchJsonPerfiosReport(...)`
* `retrieveBankStatementReportV2(...)`

### Perfios endpoints represented by supplied implementation

```text
/perfios/start-transaction/enc/post-start-transaction

/perfios/upload-statement/enc/post-upload-statement

/perfios/complete-transaction/enc/complete-transaction

/perfios/generatelink/enc/generatelink

/perfios/transaction-status/enc/get-transaction-status

/perfios/retrieve-transaction-report/enc/get-transaction-report
```

---

# 11. Perfios Transaction Retrieval

For questions involving:

* `perfiosTransactionId`
* transaction-status
* vendor transaction attempts
* retry
* polling
* callback timeout

retrieve:

```text
flows/perfios-flow.md
        ↓
06-database.md
        ↓
10-troubleshooting.md
        ↓
code-anchors.md
        ↓
integration-snippets.md
```

Important implementation detail:

Perfios transaction-status configuration is resolved using partner/product configuration and callback configuration before constructing the request.

Do not assume:

```text
perfiosTransactionId == incomeAssessmentId
```

They represent different levels of the workflow.

---

# 12. Perfios Report Retrieval

For:

* JSON report
* insight report
* report retrieval
* raw report
* transaction report
* report lookup failures

retrieve:

```text
flows/perfios-flow.md
        ↓
05-integrations.md
        ↓
code-anchors.md
        ↓
integration-snippets.md
```

Important implementation path:

```text
clientTransactionId
 ↓
normalize identifier
 ↓
lookup IA application
 ↓
build report request
 ↓
Perfios ESB
 ↓
TransactionReportResponseWrapper
 ↓
report data
 ↓
IA processing / validation
```

Important identifier rule:

Some Perfios lookups normalize `clientTransactionId` using:

```text
substringBefore("--").trim()
```

Do not assume the complete callback/client transaction string is always the Mongo lookup key.

---

# 13. Zenith Retrieval Route

For Zenith/AA journey questions:

```text
flows/zenith-flow.md
        ↓
09-configuration.md
        ↓
05-integrations.md
        ↓
04-business-logic.md
        ↓
07-kafka-events.md
```

For implementation questions:

```text
code-anchors.md
        ↓
integration-snippets.md
        ↓
orchestration-snippets.md
```

High-value operations:

* journey-link generation
* journey transaction-status
* analytics report
* BSA initiation

Important code anchors:

* `zenithOrchJourneyLinkESBRequest(...)`
* `zenithOrchEncryptedJorneyLinkESBRequest(...)`
* `fetchZenithTransactionLog(...)`
* `fetchZenithTransactionStatus(...)`
* `fetchStatementsOrReportsViaZenith(...)`
* `retrieveReportFromEsbViaZenith(...)`
* `ZenithOrchestratorGateway`

Endpoints:

```text
/jarvis/aa-journey-link/enc/get-journey-link

/jarvis/aa-journey-status/enc/get-journey-transaction-status

/jarvis/aa-financial-analytics-report/enc/get-analytics-report
```

---

# 14. Zenith BSA Retrieval

For:

* `initiateBSA`
* Zenith BSA
* `/aa-orch/fiu/api/v1/initiateBSA`
* 404
* HTML response
* BSA initiation failure

retrieve:

```text
10-troubleshooting.md
        ↓
flows/zenith-flow.md
        ↓
05-integrations.md
        ↓
09-configuration.md
        ↓
08-error-handling.md
        ↓
code-anchors.md
```

Implementation anchors:

* `InitiateBsaController`
* `InitiateBsaModels`
* `ZenithOrchestratorGateway`
* `initiateBSA`
* `platform.gateway.zenithBaseUrl`
* `platform.gateway.initiateBsaEnc`

For HTTP failures, verify:

```text
HTTP status
 ↓
Base URL
 ↓
Exact path
 ↓
HTTP method
 ↓
Headers
 ↓
Content-Type
 ↓
Request body
 ↓
Environment
 ↓
Stub/mock
```

---

# 15. Document / OmniDocs Retrieval

For:

* document upload
* OmniDocs
* statement upload to documents
* report upload
* document reference
* document persistence

retrieve:

```text
05-integrations.md
        ↓
code-anchors.md
        ↓
integration-snippets.md
        ↓
06-database.md
```

Important implementation anchors:

* `uploadStatementInOmniDocsV4(...)`
* Document Service `webClientWrapper.post`
* `upload-omni-document-v4`
* `/document-service/v4/documents`

For document DB persistence:

* `saveDocument(...)`
* `put-document`
* `/document-service/v2/document`
* `DocumentDetailsWithReferenceIds`
* `IAS_DOCUMENT_IDENTIFIER_KEY`

Important distinction:

```text
Document Service / OmniDocs
        ≠
IA MongoDB application state
```

Successful document storage does not guarantee successful IA state persistence.

---

# 16. FinFort / ITR Retrieval

For ITR questions:

```text
flows/itr-flow.md
        ↓
05-integrations.md
        ↓
code-anchors.md
        ↓
integration-snippets.md
        ↓
06-database.md
```

For FinFort-specific questions:

```text
code-anchors.md
        ↓
FinFortController
        ↓
integration-snippets.md
```

High-value FinFort operations:

* consent link
* order creation
* order status
* file details
* S3 file download

Implementation anchors:

* `FinFortController`
* `getConsentLink(...)`
* `createOrder(...)`
* `checkOrderStatus(...)`
* `getFileDetails(...)`
* `fetchFileFromS3(...)`
* `ItrStatementIdGenerator.generate()`
* `finFortOrderId`
* `FinFortAuthServiceFacade`
* `client.execute(...)`

Do not invent FinFort external endpoint paths unless they are present in the repository/code context.

---

# 17. GST Retrieval

For GST questions:

```text
flows/gst-flow.md
        ↓
05-integrations.md
        ↓
06-database.md
        ↓
code-anchors.md
```

High-value terms:

* `assessmentMode = GST`
* CAP portal
* FinFort
* GSTIN
* `ffOrderId`
* callback
* Insight Report
* OmniDocs
* GST collection

Important distinction:

```text
CAP
 ↓
/initiate-application
 ↓
assessmentMode = GST
 ↓
FinFort
 ↓
GST processing
 ↓
callback
 ↓
Insight Reports / documents
```

Do not collapse CAP initiation with FinFort execution.

---

# 18. State and Status Retrieval

For:

* status stuck
* status reverted
* status not updated
* guard prevented transition
* terminal status
* callback state
* business outcome

retrieve:

```text
04-business-logic.md
        ↓
06-database.md
        ↓
07-kafka-events.md
        ↓
10-troubleshooting.md
        ↓
code-anchors.md
```

Important guards:

* `canUpdateApplicationStatusInDb()`
* `canUpdateApplicationStatusInPerfiosCallback()`
* `canProceedToDocumentsUpload(...)`
* `canProceedToItrDocumentsUpload(...)`
* `canProceedToItrAssessment()`
* `canProceedForLinkGeneration()`
* `canProceedForStartProcess()`
* `canProceedForStartTransaction()`
* `isTerminalItrStatus()`

---

# 19. Callback Retrieval Route

For callback-related incidents:

```text
10-troubleshooting.md
        ↓
04-business-logic.md
        ↓
07-kafka-events.md
        ↓
06-database.md
        ↓
08-error-handling.md
        ↓
code-anchors.md
```

Debug sequence:

```text
Did vendor send callback?
        ↓
Did IA receive callback?
        ↓
Was callback accepted?
        ↓
Was callback event published?
        ↓
Did Kafka consumer receive it?
        ↓
Did filtering/transformation allow processing?
        ↓
Did state guard allow processing?
        ↓
Was MongoDB updated?
        ↓
Did next API/event execute?
        ↓
Did downstream processing succeed?
```

Important invariant:

> Callback received does not mean callback processed.

---

# 20. Multi-Attempt / Late Callback Retrieval

When a case contains:

* retries
* repeated user attempts
* multiple vendor transactions
* contradictory callback history
* late callback
* status reverting after retry

retrieve:

```text
06-database.md
        ↓
04-business-logic.md
        ↓
10-troubleshooting.md
        ↓
07-kafka-events.md
        ↓
relevant flow
        ↓
code-anchors.md
```

Always correlate:

* `incomeAssessmentId`
* `applicationReferenceId`
* `commonClientTransactionId`
* `serviceRequestId`
* vendor transaction ID
* attempt metadata
* callback timestamp
* retry count
* current status
* `statusType`
* event ID

Invariant:

> One IA application can contain multiple vendor transaction attempts.

A late callback must be associated with the correct attempt, not merely the application.

---

# 21. Kafka Retrieval Route

For Kafka questions:

```text
07-kafka-events.md
        ↓
10-troubleshooting.md
        ↓
06-database.md
        ↓
08-error-handling.md
        ↓
code-anchors.md
        ↓
kafka-snippets.md
```

Trace:

```text
Producer
 ↓
Event object
 ↓
Serialization
 ↓
Topic
 ↓
Consumer group
 ↓
Consumer
 ↓
Filter / transformer
 ↓
Business handler
 ↓
State guard
 ↓
MongoDB / external API
 ↓
Next event
```

Important implementation anchors:

* `IncomeAssessmentApplicationEvent`
* `IncomeAssessmentApplicationEventProducer`
* relevant consumer
* event ID
* topic configuration
* consumer group
* event filter/transformer

Invariant:

> Kafka publication success does not mean consumer processing success, MongoDB mutation success, downstream API success, or final IA success.

---

# 22. Database Retrieval Route

For persistence questions:

```text
06-database.md
        ↓
04-business-logic.md
        ↓
07-kafka-events.md
        ↓
code-anchors.md
        ↓
database-snippets.md
```

Highest-priority collection:

```text
incomeAssessmentApplications
```

Important identifiers:

```text
incomeAssessmentId
        ≠
applicationReferenceId
        ≠
commonClientTransactionId
        ≠
vendor transaction ID
```

Do not assume identifiers are interchangeable.

---

# 23. Error Handling Retrieval Route

For:

* exception
* vendor error
* timeout
* retry
* `onErrorResume`
* `onErrorMap`
* error mapping
* suppressed exception
* best-effort behavior

retrieve:

```text
08-error-handling.md
        ↓
10-troubleshooting.md
        ↓
09-configuration.md
        ↓
05-integrations.md
        ↓
code-anchors.md
```

Trace:

```text
External/API/Kafka/Mongo error
        ↓
Gateway / Consumer / Persistence
        ↓
Error mapping
        ↓
IA error
        ↓
Business decision
        ↓
State / Event / Response
        ↓
Downstream impact
```

Check whether an error was:

* propagated
* mapped
* retried
* suppressed
* handled by `onErrorResume`
* transformed by `onErrorMap`
* bypassed by a state guard
* treated as best-effort

---

# 24. External API Failure Retrieval

For `4xx`, `5xx`, network, timeout, parsing, or content-type failures:

```text
10-troubleshooting.md
        ↓
05-integrations.md
        ↓
08-error-handling.md
        ↓
09-configuration.md
        ↓
code-anchors.md
```

For:

### 404

```text
Base URL
 ↓
Exact path
 ↓
HTTP method
 ↓
Headers
 ↓
Content-Type
 ↓
Request body
 ↓
Environment
 ↓
Stub
```

### 405

Verify HTTP method first.

### 415

Verify:

* Content-Type
* request body
* gateway expectations

### HTML instead of JSON

Treat:

```text
HTTP endpoint failure
```

as the primary problem and:

```text
JSON parsing / UnsupportedMediaTypeException
```

as a possible secondary failure.

---

# 25. Configuration Retrieval Route

For:

* toggles
* endpoint configuration
* version routing
* retry configuration
* callback configuration
* error mappings

retrieve:

```text
09-configuration.md
        ↓
01-architecture.md
        ↓
05-integrations.md
        ↓
04-business-logic.md
        ↓
code-anchors.md
```

Conceptual chain:

```text
Request context
 ↓
Partner / Product / Journey context
 ↓
Configuration key
 ↓
ConfigFetcher / configuration source
 ↓
Resolved value
 ↓
Caller interpretation
 ↓
Runtime branch
 ↓
DB / Kafka / external side effect
```

High-value configuration:

* `PartnerProductConfigurations`
* `IncomeAssessment`
* `Callback`
* `VersionBuckets`
* `PerfiosErrorCodeAndConfigMapping`
* `ZenithErrorCodeAndConfigMapping`
* `FinacleErrorCodeAndConfigMapping`
* `MaximusErrorCodeAndConfigMapping`

High-impact toggles:

* `enableZenithOrchAPI`
* `iaVersion`
* `retryErrorMsgScreen`
* `fetchAndSaveRawStatement`
* `fetchAndSaveRawStatementForIAFailed`
* `enablePopUpForRetry`
* `limitMultipleRetryAttempt`
* `autoRedirectScreen`
* `capSyncEnabled`
* `uploadStatementPerfiosIA`
* `enableTransactionReportEncrypted`
* `enablePerfiosGenerateLinkEncrypted`
* `enableMultiplePerfiosCallbacks`
* `iaLoaderTimeoutEnabled`

---

# 26. API Contract Retrieval

For exact:

* request JSON
* response JSON
* request model
* response model
* HTTP method
* endpoint
* field names
* validation rules

prefer:

```text
03-api-contracts.md
```

Do not use flow documentation as the primary source for exact API contracts.

Then use:

```text
code-anchors.md
```

to verify implementation routing.

---

# 27. Code Navigation Retrieval

Use `code-anchors.md` when the developer asks:

* Where is this implemented?
* Which class handles this?
* Which method calls this API?
* Where is this endpoint constructed?
* Which gateway is responsible?
* Which service decides between Perfios and Zenith?
* Where is this toggle consumed?
* Where is this event published?
* Which consumer handles this event?
* Where is this Mongo collection accessed?
* Which code path handles this callback?

### Code navigation pattern

```text
Developer question
        ↓
code-anchors.md
        ↓
Specific anchor
        ↓
Relevant snippet file
        ↓
Repository implementation
```

---

# 28. Code Snippet Routing

## 28.1 Orchestration

Use:

```text
orchestration-snippets.md
```

for:

* controller → facade
* version resolution
* `ServiceFacade.executeWithVersion`
* `/initiate-application`
* `/validate`
* `/generate-link`
* journey selection
* application DAO access
* service orchestration

---

## 28.2 Integration

Use:

```text
integration-snippets.md
```

for:

* Perfios API calls
* Zenith API calls
* OmniDocs
* Document Service
* CAP
* FinFort
* ESB request construction
* WebClient calls
* external response mapping

---

## 28.3 Kafka

Use:

```text
kafka-snippets.md
```

for:

* event producer
* event ID
* topic
* consumer
* consumer processing
* event filtering
* event transformation

---

## 28.4 Database

Use:

```text
database-snippets.md
```

for:

* repository calls
* DAO persistence
* collection access
* Mongo queries
* identifier lookups
* state updates

---

## 28.5 Configuration

Use:

```text
configuration-snippets.md
```

for:

* configuration access
* toggle resolution
* `ConfigFetcher`
* partner/product configuration
* endpoint configuration
* version configuration
* error mapping configuration

---

# 29. Code Anchor → Snippet Routing

| Question                                     | First anchor                                              | Implementation source       |
| -------------------------------------------- | --------------------------------------------------------- | --------------------------- |
| Where does IA start?                         | `IncomeAssessmentApplicationController`                   | `orchestration-snippets.md` |
| Where is version resolved?                   | `CommonVersionResolver`                                   | `orchestration-snippets.md` |
| How does facade choose implementation?       | `ServiceFacade.executeWithVersion`                        | `orchestration-snippets.md` |
| How does `/validate` decide next action?     | `getNextAction`, `determineNextAction`                    | `orchestration-snippets.md` |
| Where is Perfios start transaction called?   | `startTransaction`, `perfiosStartTransaction`             | `integration-snippets.md`   |
| Where is Perfios statement uploaded?         | `uploadStatement`                                         | `integration-snippets.md`   |
| Where is Perfios transaction completed?      | `completeTransaction`                                     | `integration-snippets.md`   |
| Where is Perfios link generated?             | `generateLinkEsbEncryptedRequest`                         | `integration-snippets.md`   |
| Where is Perfios transaction status fetched? | `fetchTransactionLog`                                     | `integration-snippets.md`   |
| Where is Perfios report fetched?             | `fetchJsonPerfiosReport`, `retrieveBankStatementReportV2` | `integration-snippets.md`   |
| Where is Zenith journey link generated?      | `zenithOrchJourneyLinkESBRequest`                         | `integration-snippets.md`   |
| Where is Zenith transaction status fetched?  | `fetchZenithTransactionStatus`                            | `integration-snippets.md`   |
| Where is Zenith analytics report fetched?    | `retrieveReportFromEsbViaZenith`                          | `integration-snippets.md`   |
| Where is OmniDocs upload performed?          | `uploadStatementInOmniDocsV4`                             | `integration-snippets.md`   |
| Where is document DB persistence performed?  | `saveDocument`                                            | `integration-snippets.md`   |
| Where is CAP PATCH implemented?              | `callCapServiceUpdateStatusDirect`                        | `integration-snippets.md`   |
| Where is CAP sync enabled/disabled?          | `syncCapConsentStatus`                                    | `integration-snippets.md`   |
| Where is FinFort order created?              | `createOrder`                                             | `integration-snippets.md`   |
| Where is FinFort status checked?             | `checkOrderStatus`                                        | `integration-snippets.md`   |
| Where are FinFort files retrieved?           | `getFileDetails`, `fetchFileFromS3`                       | `integration-snippets.md`   |

---

# 30. Callback + Code Retrieval

When debugging a callback, documentation alone may not be sufficient.

Use:

```text
10-troubleshooting.md
        ↓
relevant flow
        ↓
07-kafka-events.md
        ↓
06-database.md
        ↓
code-anchors.md
        ↓
relevant integration/orchestration snippet
```

For Perfios callback:

```text
NewPerfiosCallbackController
        ↓
callback validation
        ↓
Perfios callback service / consumer
        ↓
state guard
        ↓
MongoDB
        ↓
report retrieval
        ↓
business validation
        ↓
Kafka / downstream
```

---

# 31. Identifier Retrieval Route

For questions such as:

* Which ID should I use?
* Why did lookup fail?
* Which ID identifies the vendor attempt?
* Why does callback correlation fail?

retrieve:

```text
06-database.md
        ↓
11-glossary.md
        ↓
code-anchors.md
        ↓
relevant flow
```

Important identifiers:

```text
incomeAssessmentId
applicationReferenceId
commonClientTransactionId
serviceRequestId
statementId
capRefId
perfiosTransactionId
vendorTransactionId
finFortOrderId
```

Never collapse these into a generic "transaction ID".

---

# 32. Cross-Document Retrieval Scenarios

## "Why did my status get stuck?"

```text
10-troubleshooting.md
04-business-logic.md
06-database.md
07-kafka-events.md
relevant flow
code-anchors.md
```

---

## "Why did Perfios callback not complete the journey?"

```text
flows/perfios-flow.md
10-troubleshooting.md
07-kafka-events.md
06-database.md
08-error-handling.md
code-anchors.md
integration-snippets.md
```

---

## "Why did Zenith BSA fail?"

```text
flows/zenith-flow.md
10-troubleshooting.md
05-integrations.md
09-configuration.md
08-error-handling.md
code-anchors.md
```

---

## "Why didn't CAP receive the IA result?"

```text
flows/cap-flow.md
09-configuration.md
08-error-handling.md
05-integrations.md
10-troubleshooting.md
code-anchors.md
integration-snippets.md
```

---

## "Why did CAP initiation fail?"

```text
flows/cap-flow.md
flows/income-assessment-flow.md
03-api-contracts.md
10-troubleshooting.md
code-anchors.md
orchestration-snippets.md
```

---

## "Why did the same application have contradictory vendor results?"

```text
06-database.md
04-business-logic.md
relevant vendor flow
10-troubleshooting.md
07-kafka-events.md
code-anchors.md
```

---

## "Why did report retrieval fail after callback?"

```text
relevant flow
05-integrations.md
10-troubleshooting.md
08-error-handling.md
code-anchors.md
integration-snippets.md
```

---

## "Why did document upload succeed but application state remain wrong?"

```text
05-integrations.md
06-database.md
07-kafka-events.md
10-troubleshooting.md
code-anchors.md
integration-snippets.md
```

---

## "Why is FinFort status stuck?"

```text
flows/itr-flow.md
05-integrations.md
10-troubleshooting.md
06-database.md
code-anchors.md
integration-snippets.md
```

---

# 33. Glossary Retrieval

Use `11-glossary.md` for short terminology questions:

* IA
* IA Application
* IA Attempt
* Assessment Medium
* Perfios
* Zenith / AA-Orchestrator
* BSA
* CAP
* CAP Initiation
* CAP Sync
* `capRefId`
* CAP `EventStatus`
* `eventStatus`
* FinFort
* FinFort Order
* `finFortOrderId`
* OmniDocs
* Document Service
* Callback
* Callback Timeout
* Late Callback
* Vendor Transaction ID
* `perfiosTransactionId`
* `incomeAssessmentId`
* `applicationReferenceId`
* `commonClientTransactionId`
* `serviceRequestId`
* `statementId`
* Partner
* Product
* `PartnerProductConfiguration`
* `capSyncEnabled`
* `enableZenithOrchAPI`
* IA Version
* Version Bucket
* `ConfigFetcher`
* ESB
* Gateway
* Journey Link
* Transaction Status
* Insight Report
* Kafka Event
* State Guard
* Best-Effort Side Effect
* Terminal State

Use glossary retrieval only when the question is definitional.

For behavior questions, retrieve the relevant flow/business/configuration document instead.

---

# 34. Knowledge-Base File Map

| File                              | Primary question                                                      |
| --------------------------------- | --------------------------------------------------------------------- |
| `01-architecture.md`              | **How is IA structured?**                                             |
| `03-api-contracts.md`             | **What are the exact APIs and payloads?**                             |
| `04-business-logic.md`            | **Why does IA transition between states?**                            |
| `05-integrations.md`              | **How does IA communicate with external systems?**                    |
| `06-database.md`                  | **Where is workflow state stored and how is it identified?**          |
| `07-kafka-events.md`              | **How does asynchronous propagation work?**                           |
| `08-error-handling.md`            | **How are failures translated, retried, suppressed, and propagated?** |
| `09-configuration.md`             | **Which configuration controls runtime behavior?**                    |
| `10-troubleshooting.md`           | **Where and how should an incident be debugged?**                     |
| `11-glossary.md`                  | **What does a domain/technical term mean?**                           |
| `rag-index.md`                    | **Which knowledge should be retrieved first?**                        |
| `code-anchors.md`                 | **Where is the relevant implementation?**                             |
| `orchestration-snippets.md`       | **How is IA orchestration implemented?**                              |
| `integration-snippets.md`         | **How are external integrations implemented?**                        |
| `kafka-snippets.md`               | **How are Kafka events implemented?**                                 |
| `database-snippets.md`            | **How is persistence implemented?**                                   |
| `configuration-snippets.md`       | **How is runtime configuration consumed?**                            |
| `flows/income-assessment-flow.md` | **What is the canonical IA lifecycle?**                               |
| `flows/perfios-flow.md`           | **How does the Perfios journey execute?**                             |
| `flows/zenith-flow.md`            | **How does the Zenith journey execute?**                              |
| `flows/cap-flow.md`               | **How does CAP initiate IA and receive synchronized status?**         |
| `flows/itr-flow.md`               | **How does the ITR journey execute?**                                 |
| `flows/gst-flow.md`               | **How does the GST journey execute?**                                 |

---

# 35. Core Retrieval Invariants

The following concepts must not be collapsed into broader synonyms:

1. `/initiate-application` is the primary IA entry point.
2. CAP is an external upstream platform/client that can initiate IA.
3. CAP is **not** a Perfios/Zenith journey provider.
4. Perfios and Zenith are external journey/integration providers used by IA.
5. CAP initiation and CAP status synchronization are separate interactions.
6. CAP status synchronization occurs from IA back to CAP.
7. `capSyncEnabled` controls whether CAP synchronization is enabled.
8. IA `status` and CAP `EventStatus` are different concepts.
9. `eventStatus` should not automatically be treated as primary IA business status.
10. One IA application can contain multiple vendor transaction attempts.
11. `incomeAssessmentId`, `applicationReferenceId`, `commonClientTransactionId`, `serviceRequestId`, and vendor transaction IDs are distinct identifiers.
12. Callback receipt does not guarantee callback processing.
13. Kafka publication does not guarantee consumer processing.
14. MongoDB persistence and downstream propagation are not atomic.
15. Journey-link generation does not mean the external journey completed.
16. Vendor transaction success does not automatically mean IA business success.
17. Callback success does not automatically mean report retrieval success.
18. Report retrieval success does not automatically mean business validation success.
19. Document upload and IA MongoDB persistence are separate failure boundaries.
20. Configuration can change runtime behavior without a code change.
21. Configured retry does not mean every error is retryable.
22. An exception in logs does not automatically mean the overall journey failed.
23. Best-effort side effects must be distinguished from business-critical state transitions.
24. External HTTP failures should be diagnosed at the HTTP boundary before secondary parsing errors.
25. Current implementation and runtime configuration take precedence over historical documentation.
26. Code anchors identify where behavior lives; snippets explain how the supplied implementation works.
27. Do not invent external endpoint paths when the repository evidence does not provide them.

---

# 36. Preferred RAG Mental Model

For normal developer questions:

```text
Question
 ↓
Intent classification
 ↓
Business / API / Flow / Incident / Implementation
 ↓
Most specific knowledge-base chunk
 ↓
Supporting cross-document chunk(s)
 ↓
Code anchor when implementation is relevant
 ↓
Implementation snippet when exact behavior is required
 ↓
Configuration
 ↓
Runtime state / Kafka / Mongo / external API evidence
 ↓
Answer
```

For incident questions:

```text
Symptom
 ↓
Application identity
 ↓
Attempt identity
 ↓
Expected transition
 ↓
Actual transition
 ↓
First divergent boundary
 ↓
Code/config evidence
 ↓
Root cause
 ↓
State / event / downstream impact
```

For implementation questions:

```text
Question
 ↓
code-anchors.md
 ↓
Specific class/method/gateway/consumer
 ↓
Relevant snippet
 ↓
Current repository implementation
 ↓
Configuration dependency
 ↓
Runtime behavior
```

---

# 37. Final Retrieval Principle

The purpose of this index is **not to retrieve the maximum amount of related documentation**.

The purpose is to retrieve the **smallest authoritative context required to reconstruct the correct IA behavior**.

When multiple documents are needed, retrieve them in dependency order:

```text
Business intent
      ↓
Flow
      ↓
Configuration
      ↓
Integration / Kafka / Database
      ↓
Code anchor
      ↓
Implementation snippet
      ↓
Runtime evidence
```

For RCA:

```text
Expected behavior
      ↓
Actual behavior
      ↓
First divergence
      ↓
Evidence
      ↓
Root cause
```

The RAG system should prefer **precision over breadth**, and **current implementation over historical explanation**.
