# Code Anchors

## Purpose

This document is the **code-level navigation index** for the Income Assessment (IA) service.

Use it to answer:

* Where is this behavior implemented?
* Which class/method should I inspect first?
* Which gateway/client owns this external call?
* Where is an endpoint invoked?
* Where is configuration resolved?
* Where is application state persisted?
* Where is a Kafka event produced or consumed?
* Which code path controls a particular IA decision?

This document intentionally contains **anchors and retrieval hints rather than implementation dumps**.

For detailed implementation snippets, use:

* `code/orchestration-snippets.md`
* `code/integrations-snippets.md`
* `code/kafka-snippets.md`
* `code/database-snippets.md`
* `code/configuration-snippets.md`

---

# 1. Code Navigation Mental Model

The primary IA execution path is:

```text
Controller
   ↓
KeyData / Request Context
   ↓
CommonVersionResolver
   ↓
ServiceFacade
   ↓
Version-specific IA Service
   ↓
Business Orchestration
   ↓
Config / DAO / Gateway / Kafka
   ↓
External System / MongoDB / Downstream
```

For an external integration:

```text
IA Service
   ↓
Gateway / Client
   ↓
Request Builder / Mapper
   ↓
ESB Client / WebClient
   ↓
Configured Endpoint
   ↓
External System
   ↓
Response Wrapper
   ↓
Business Processing
```

For asynchronous processing:

```text
Producer
   ↓
Kafka Topic
   ↓
Consumer
   ↓
State Guard
   ↓
Business Handler
   ↓
MongoDB / External API
   ↓
Next Event
```

---

# 2. Primary Application Entry Points

## 2.1 Main IA Controller

**Anchor:** `IncomeAssessmentApplicationController`

Look here first for:

* IA REST endpoints
* request-to-service delegation
* authentication/header extraction
* `KeyData` creation
* version resolution
* `IncomeAssessmentApplicationServiceFacade`

Primary base path:

```text
/income-assessment-service/v1
```

High-value endpoints include:

```text
POST /initiate-application
POST /enc/initiate-application
GET  /validate
GET  /status
GET  /income-details
GET  /generate-link
GET  /start-process
GET  /start-transaction
POST /bsa/initiate
```

**Retrieval terms:**

`IncomeAssessmentApplicationController`, `initiate-application`, `generate-link`, `start-process`, `validate`, `status`

---

# 3. Main IA Orchestration

## 3.1 IncomeAssessmentApplicationServiceFacade

**Anchor:** `IncomeAssessmentApplicationServiceFacade`

Look here when tracing:

```text
Controller
   ↓
Facade
   ↓
Version-specific IA Service
```

The facade extends the generic:

```text
ServiceFacade<IncomeAssessmentApplicationServiceRevamp>
```

It is therefore a key version-routing boundary.

---

## 3.2 CommonVersionResolver

**Anchor:** `CommonVersionResolver`

Look here when:

* the same API behaves differently for different partners/products
* a request reaches a different implementation than expected
* debugging IA version routing
* determining the `VersionBucket`
* tracing `primeBucket(...)`

Important pattern:

```text
KeyData
   ↓
primeBucket(...)
   ↓
VersionBucket
   ↓
ServiceFacade
   ↓
Version-specific service
```

**Retrieval terms:**

`CommonVersionResolver`, `primeBucket`, `VersionBuckets`, `VERSION_RESOLVED`, `iaVersion`

---

## 3.3 ServiceFacade.executeWithVersion

**Anchor:** `ServiceFacade.executeWithVersion(...)`

Look here when the question is:

> Why did this request execute a particular version of the service?

Important concepts:

* `VersionContext`
* cached bucket
* `resolveFromBucket(...)`
* facade name
* version-specific service factory

This is the common version-routing mechanism used by IA service facades.

---

# 4. Main IA Service

## 4.1 IncomeAssessmentApplicationServiceRevamp

**Anchor:** `IncomeAssessmentApplicationServiceRevamp`

This is the service contract for versioned IA implementations.

Use it to discover which operations a concrete IA version implements.

---

## 4.2 IncomeAssessmentApplicationServiceV3

**Anchor:** `IncomeAssessmentApplicationServiceV3`

This is a high-value orchestration anchor.

Look here for:

* initiation
* journey selection
* generate-link
* start-process
* start-transaction
* validation
* report retrieval
* callback processing
* state transitions
* external gateway invocation
* document/event side effects

When investigating an end-to-end IA issue, this class is often one of the first implementation files to inspect.

---

# 5. `/initiate-application`

**Primary anchor:**

`IncomeAssessmentApplicationController`

**Next anchors:**

* `CommonVersionResolver`
* `IncomeAssessmentApplicationServiceFacade`
* `IncomeAssessmentApplicationServiceV3`
* `IncomeAssessmentApplicationDao`

Trace:

```text
POST /initiate-application
        ↓
Controller
        ↓
KeyData / request context
        ↓
Version resolution
        ↓
ServiceFacade
        ↓
Versioned IA service
        ↓
Create / reuse IA application
        ↓
Journey-specific processing
```

Use when debugging:

* IA initiation failures
* application creation
* partner/product resolution
* assessment medium
* IA version selection

---

# 6. IA Application Persistence

## 6.1 IncomeAssessmentApplicationDao

**Anchor:** `IncomeAssessmentApplicationDao`

Mongo collection:

```text
incomeAssessmentApplications
```

Use this anchor to understand the persisted IA workflow record.

Important fields/identifiers include:

* `incomeAssessmentId`
* `applicationReferenceId`
* `commonClientTransactionId`
* `partnerId`
* `productCode`
* `assessmentMedium`
* `status`
* `statusType`
* `perfiosTransactionId`
* `capRefId`
* `finFortDetails`
* configuration-related values
* retry/attempt information

---

## 6.2 IncomeAssessmentRepository

**Anchor:** `IncomeAssessmentRepository`

Look here when tracing:

* application lookup
* application persistence
* state updates
* correlation by identifiers

High-value lookup methods include:

```text
findByCommonClientTransactionId(...)
findByApplicationReferenceId(...)
```

Important correlation rule confirmed in integration code:

```text
clientTransactionId
    ↓
substringBefore("--")
    ↓
trim()
    ↓
findByCommonClientTransactionId(...)
```

The same normalization pattern is used for Perfios report retrieval and document-related flows.

---

# 7. Validation / UI Decision Flow

## 7.1 `/validate`

**Controller anchor:**

`IncomeAssessmentApplicationController`

**Service anchor:**

`IncomeAssessmentApplicationServiceV3`

The controller primes version resolution before calling:

```text
facade.validate(...)
```

Important request/context inputs include:

* JWT/auth token
* `retry`
* `timedOut`
* `accountSelectionCancel`

The service returns:

```text
ValidateResponse
```

The returned `ACTION` determines the next UI step.

---

## 7.2 getNextAction / determineNextAction

**Anchors:**

* `getNextAction(...)`
* `determineNextAction(...)`

Use these when investigating:

* retry screen
* landing page redirects
* timeout behavior
* policy norm failure redirects
* retry limits
* next UI action

Important configuration inputs include:

* `retryErrorMsgScreen`
* `enableRedirectToLandingPageForPolicyNormNotMetError`
* `allowRedirectToPartnerForError`
* retry state
* retry-limit state

### Important distinction

`/validate` is a **UI/journey decision endpoint**.

It should not be treated as the same thing as the IA business validation that evaluates vendor insight/report data.

---

# 8. Generate Link

## 8.1 Main Anchor

**Controller:** `IncomeAssessmentApplicationController`

**Service:** `IncomeAssessmentApplicationServiceV3`

Look for:

```text
generateLink(...)
```

The method validates/fetches claims and resolves the IA application using the assessment medium.

---

## 8.2 Journey Selection

High-value anchor:

```text
proceedForLinkGeneration(...)
```

Look for the configuration-driven branch:

```text
enableZenithOrchAPI
```

combined with:

```text
assessmentMedium == ACCOUNT_AGGREGATOR
```

Conceptually:

```text
Zenith toggle ON + AA
        ↓
Zenith journey-link flow

otherwise
        ↓
Perfios link-generation flow
```

Use this anchor when answering:

> Why did this request use Zenith instead of Perfios?

---

# 9. Perfios Integration Anchors

Detailed implementation is in:

`code/integrations-snippets.md`

---

## 9.1 Start Transaction

**Primary anchor:**

`perfiosStartTransaction(...)`

**Service entry:**

`startTransaction(...)`

**Gateway/client:**

`esbClientV2`

**Call:**

`postEncryptedV2(...)`

**Configuration:**

`bankStatementConfig.startTransactionUrl`

**Endpoint:**

```text
/perfios/start-transaction/enc/post-start-transaction
```

**Important identifiers:**

* `applicationReferenceId`
* `assessmentMedium`
* `institutionId`
* `isBSSelected`

**Retrieval terms:**

`perfiosStartTransaction`, `startTransactionUrl`, `PerfiosStartTransactionRequest`

**Anchor ID:**

`CODE-INT-PERFIOS-001`

---

## 9.2 Upload Statement

**Primary anchors:**

* `uploadStatement(...)`
* `PerfiosUploadStatementEsbRequest.from(...)`

**Client:**

`esbClientV2.postEncryptedV2(...)`

**Configuration:**

`bankStatementConfig.uploadTransactionUrl`

**Endpoint:**

```text
/perfios/upload-statement/enc/post-upload-statement
```

Important implementation details:

* statement is converted to JSON/file details
* `PerfiosUploadStatementEsbRequest` is constructed
* target header is `PERFIOS_SCAN_AND_UPLOAD`
* `serviceRequestIdForPerfiosUpload` is used

**Anchor ID:**

`CODE-INT-PERFIOS-002`

---

## 9.3 Complete Transaction

**Primary anchors:**

* `completeTransaction(...)`
* `bankStatementUploadGatewayFacade.completeTransaction(...)`

**Client:**

`esbClientV2.postEncryptedV2(...)`

**Configuration:**

`bankStatementConfig.completeTransactionUrl`

**Endpoint:**

```text
/perfios/complete-transaction/enc/complete-transaction
```

Important identifier:

`perfiosTransactionId`

Important context construction:

`KeyData.forCommonClientTransactionId(perfiosTransactionId)`

**Anchor ID:**

`CODE-INT-PERFIOS-003`

---

## 9.4 Generate Link

**Primary anchor:**

`generateLinkEsbEncryptedRequest(...)`

**Client:**

`esbClientV2.postEncryptedV2(...)`

**Configuration:**

`bankStatementConfig.generateLinkUrlEnc`

**Endpoint:**

```text
/perfios/generatelink/enc/generatelink
```

Important request construction:

`createGenerateLinkRequest(...)`

Important configuration:

`generateLinkEncryptedPrivateKey`

**Anchor ID:**

`CODE-INT-PERFIOS-004`

---

## 9.5 Transaction Status

**Primary anchors:**

* `fetchTransactionLog(...)`
* `makeTransactionStatusRequest(...)`

Before the external call, configuration is resolved using:

```text
allPartnerProductConfigurations()
```

with:

```text
partnerId
+
ProductCode.toBaseProductCodeName(productCode)
```

Callback configuration is also resolved using the assessment medium.

**Client:**

`esbClientV2.postEncryptedV2(...)`

**Configuration:**

`bankStatementConfig.transactionStatusUrlEnc`

**Endpoint:**

```text
/perfios/transaction-status/enc/get-transaction-status
```

Important inputs:

* `statementId`
* `productCode`
* `occupation`
* PAN header

**Anchor ID:**

`CODE-INT-PERFIOS-005`

---

## 9.6 Perfios Insight / Transaction Report

**Primary anchors:**

* `fetchJsonPerfiosReport(...)`
* `retrieveBankStatementReportV2(...)`

Application lookup:

```text
findByCommonClientTransactionId(...)
```

with:

```text
clientTransactionId.substringBefore("--").trim()
```

External call:

`esbClientV2.postEncryptedV2(...)`

**Configuration:**

`transactionReportConfig.url`

**Endpoint:**

```text
/perfios/retrieve-transaction-report/enc/get-transaction-report
```

Important request inputs:

* `perfiosTransactionId`
* `clientTransactionId`
* `reportType`
* vendor ID
* `isSbbEnableProduct`

Important ESB metadata:

* service request version
* service request ID
* channel ID

Important request headers include:

* Platform service request ID
* request UUID
* target header
* `x-stub-pan`

**Anchor IDs:**

* `CODE-INT-PERFIOS-006A` — correlation/application lookup
* `CODE-INT-PERFIOS-006B` — report retrieval

---

# 10. Perfios Callback Anchors

## 10.1 Callback Controller

**Anchor:** `NewPerfiosCallbackController`

Routes include:

```text
POST /status/perfios
POST /enc/status/perfios
```

Look here first when debugging:

* Perfios callback not received
* callback rejected
* callback identifier validation
* callback request parsing

---

## 10.2 Callback Identifier Validation

**Anchor:**

`validateRequest(callbackIdentifier)`

The shown implementation validates:

* whitespace conditions
* `Constants.clientTransactionIdRegx`

A feature toggle can modify this behavior:

```text
ignoreInvalidClientTransactionIdException
```

**Important retrieval term:**

`clientTransactionIdRegx`

---

## 10.3 Callback Consumers

High-value anchors:

```text
PerfiosNotificationReceivedConsumer
PerfiosCallbackReceivedConsumer
PerfiosCallbackNotReceivedConsumer
```

Use these when tracing:

```text
vendor callback
    ↓
Kafka event
    ↓
consumer
    ↓
IA state processing
```

---

# 11. Zenith Integration Anchors

Detailed implementation is in:

`code/integrations-snippets.md`

---

## 11.1 Zenith Journey Link

**Primary anchors:**

* `zenithOrchJourneyLinkESBRequest(...)`
* `zenithOrchEncryptedJorneyLinkESBRequest(...)`

**Client:**

`esbClientV2.postEncryptedV2(...)`

**Configuration:**

`zenithOrchestratorConfig.journeyLinkUrlEnc`

**Endpoint:**

```text
/jarvis/aa-journey-link/enc/get-journey-link
```

Important dependency:

`zenithEsbConfigFactory.resolveEsbHeaders()`

**Anchor ID:**

`CODE-INT-ZENITH-001`

---

## 11.2 Zenith Transaction Status

**IA-level anchor:**

`fetchZenithTransactionLog(...)`

**Gateway/client anchor:**

`fetchZenithTransactionStatus(...)`

**Client:**

`esbClientV2.postEncryptedV2(...)`

**Configuration:**

`zenithOrchestratorConfig.transactionStatusUrlEnc`

**Endpoint:**

```text
/jarvis/aa-journey-status/enc/get-journey-transaction-status
```

Important request:

`GetJourneyTransactionStatusRequest`

Important identifier:

`serviceRequestId`

**Anchor ID:**

`CODE-INT-ZENITH-002`

---

## 11.3 Zenith Analytics Report

**Primary anchors:**

* `fetchStatementsOrReportsViaZenith(...)`
* `retrieveReportFromEsbViaZenith(...)`

**Client:**

`esbClientV2.postEncryptedV2(...)`

**Configuration:**

`zenithOrchestratorConfig.analyticsReportUrlEnc`

**Endpoint:**

```text
/jarvis/aa-financial-analytics-report/enc/get-analytics-report
```

Important request inputs:

* `serviceRequestId`
* `reportType`

Response processing:

```text
analyticsData.byteArray
        ↓
Base64 decoder
        ↓
ByteArray
```

**Anchor ID:**

`CODE-INT-ZENITH-003`

---

# 12. Zenith BSA Initiation

**Controller anchor:**

`InitiateBsaController`

**Models:**

`InitiateBsaModels`

**Gateway:**

`ZenithOrchestratorGateway`

Important endpoint:

```text
/aa-orch/fiu/api/v1/initiateBSA
```

Important configuration:

```text
platform.gateway.zenithBaseUrl
platform.gateway.initiateBsaEnc
```

Use this anchor when investigating:

* BSA initiation
* Zenith 404/405/415
* AA-Orchestrator connectivity
* BSA initiation error `MLP2096`

---

# 13. Document Service Anchors

## 13.1 OmniDocs V4 Upload

**Anchor:**

`uploadStatementInOmniDocsV4(...)`

**Client:**

`webClientWrapper.post(...)`

**Path identifier:**

`upload-omni-document-v4`

**Endpoint:**

```text
POST /document-service/v4/documents
```

Important request:

`DocumentListWithReferenceIds`

Important response:

`UploadedDocumentResponse`

**Anchor ID:**

`CODE-INT-DOC-001`

---

## 13.2 Document Persistence

**Anchor:**

`saveDocument(...)`

**Client:**

`webClientWrapper.put(...)`

**Path identifier:**

`put-document`

**Endpoint:**

```text
PUT /document-service/v2/document
```

Important transformations:

```text
statementId
    ↓
substringBefore("--")
    ↓
trim()
    ↓
IAS_DOCUMENT_IDENTIFIER_KEY
```

and:

```text
ByteArray
    ↓
Base64
    ↓
DocumentDetailsWithReferenceIds
```

**Anchor ID:**

`CODE-INT-DOC-002`

---

# 14. CAP Integration Anchors

## 14.1 CAP Sync Facade

**Anchor:**

`CapSyncServiceFacade`

Important method:

`syncCapConsentStatus(...)`

It uses:

```text
executeWithVersion(...)
```

Therefore CAP synchronization participates in IA version resolution.

---

## 14.2 CAP Sync Service

**Anchor:**

`CapSyncServiceRevamp`

Important methods:

```text
callCapServiceUpdateStatus(...)
getEventStatusByStatus(...)
syncCapConsentStatus(...)
```

Use this interface to discover CAP synchronization behavior.

---

## 14.3 CAP Update Status

**Anchor:**

`callCapServiceUpdateStatusDirect(...)`

The supplied implementation uses direct WebClient PATCH.

Endpoint:

```text
/internal/cap/api/initiate/event/update/status
```

Request:

`CapConsentStatusUpdateRequest`

Important fields:

* `capRefId`
* `status`

Authorization:

```text
Bearer <authToken>
```

**Anchor ID:**

`CODE-INT-CAP-001`

---

## 14.4 CAP Sync Toggle

**Anchor:**

`syncCapConsentStatus(...)`

Configuration value:

```text
capSyncEnabled
```

The shown implementation reads it from:

```text
incomeAssessmentApplication.config
```

**Anchor ID:**

`CODE-INT-CAP-002`

---

## 14.5 CAP Status Mapping

**Anchor:**

`getEventStatusByStatus(...)`

This is the key method for:

```text
IA IncomeAssessmentApplicationStatus
        ↓
CAP EventStatus
```

Do not confuse:

```text
IA status
```

with:

```text
CAP EventStatus
```

---

# 15. FinFort Integration Anchors

## 15.1 FinFort Controller

**Anchor:**

`FinFortController`

Base path:

```text
/income-assessment-service/v1/itr/online
```

Activation:

```text
platform.finfort.feature.enabled
```

Use when tracing the online ITR FinFort entry point.

**Anchor ID:**

`CODE-INT-FINFORT-001`

---

## 15.2 FinFort Consent Link

**Controller method:**

`getConsentLink(...)`

Endpoint:

```text
POST /consent-link
```

Authentication begins with:

```text
authServiceClient.validateAndFetchClaims(...)
```

Use when tracing:

```text
JWT
 ↓
claims
 ↓
FinFort ITR flow
```

---

## 15.3 FinFort Create Order

**Anchor:**

`createOrder(...)`

Important calls:

```text
ItrStatementIdGenerator.generate()
buildOrderRequest(application)
KeyData.forPartnerConfiguration(...)
finFortAuthServiceFacade.decodedToken(...)
client.execute(...)
```

Important application fields:

* `applicationReferenceId`
* `customerId`

**Anchor ID:**

`CODE-INT-FINFORT-002`

---

## 15.4 FinFort Client Encryption

**Anchor:**

`execute(...)`

Important method:

`getAppropriateWebClient()`

Environment handling determines whether the request is encrypted.

Encrypted profiles shown:

```text
prod
sandbox
sandboxnew
uat
```

Encrypted path:

```text
BaseRequest
    ↓
Jackson JSON
    ↓
AES-256 encryption
    ↓
HTTP client
```

Lower environments use the `BaseRequest` directly according to the supplied implementation.

**Anchor ID:**

`CODE-INT-FINFORT-003`

---

## 15.5 FinFort Order Status

**Anchor:**

`checkOrderStatus(...)`

Application lookup:

```text
findByApplicationReferenceId(...)
```

FinFort order ID:

```text
application.finFortDetails.finFortOrderId
```

FinFort auth token is Base64-decoded before client execution.

**Anchor ID:**

`CODE-INT-FINFORT-004`

---

## 15.6 FinFort File Details

**Anchor:**

`getFileDetails(...)`

Application lookup:

```text
findByApplicationReferenceId(...)
```

Request uses:

```text
finFortOrderId
```

Response type:

`GetFileDetailsResponse`

**Anchor ID:**

`CODE-INT-FINFORT-005`

---

## 15.7 FinFort File Download

**Anchor:**

`fetchFileFromS3(...)`

Delegates to:

```text
client.downloadFiles(...)
```

Inputs:

* file URL
* file name
* customer ID

The supplied logging indicates this path can participate in `CALLBACK_NOT_RECEIVED` recovery/retry processing.

**Anchor ID:**

`CODE-INT-FINFORT-006`

---

# 16. Business Validation Anchors

## 16.1 performValidation

**Anchor:**

`performValidation(...)`

Important inputs shown:

* `IncomeAssessmentApplicationDao`
* retrieved report response
* `CallbackNotification`

The method also:

* copies IFSC from report data into the updated application
* constructs partner configuration `KeyData`

Use this anchor when tracing:

```text
Vendor report
    ↓
IA report processing
    ↓
Business validation
    ↓
IA status
```

---

## 16.2 Business Rule Configuration

High-value code/config terms:

```text
incomeCreditGapRule
chequeBounceLimitRule
lastNMonthsIncomeRule
numberOfIncomeCreditsRule
statementStatusRule
```

Use these together with:

`ConfigFetcher`

and:

`PartnerProductConfigurations`

---

# 17. State Guard Anchors

These methods are critical when a callback/event appears to be successfully received but the expected state does not change.

Search for:

```text
canUpdateApplicationStatusInDb()
canUpdateApplicationStatusInPerfiosCallback()
canProceedToDocumentsUpload()
canProceedToItrDocumentsUpload(...)
canProceedToItrAssessment()
canProceedForLinkGeneration()
canProceedForStartProcess()
canProceedForStartTransaction()
isTerminalItrStatus()
```

These methods answer:

> Is this state transition allowed from the application's current state?

When a callback/event is present but no state change occurs, inspect the relevant state guard before assuming Kafka or vendor failure.

---

# 18. Kafka Anchors

Detailed implementation is in:

`code/kafka-snippets.md`

## 18.1 Producer

**Anchor:**

`IncomeAssessmentApplicationEventProducer`

Use when tracing:

```text
business operation
    ↓
event construction
    ↓
Kafka publication
```

---

## 18.2 Event Model

**Anchor:**

`IncomeAssessmentApplicationEvent`

Use to determine:

* event ID
* event payload
* correlation information
* event type

---

## 18.3 High-Value Consumers

Search for:

```text
PerfiosNotificationReceivedConsumer
PerfiosCallbackReceivedConsumer
PerfiosCallbackNotReceivedConsumer

ZenithNotificationReceivedConsumer
ZenithCallbackReceivedConsumer
ZenithCallbackNotReceivedConsumer

BackOfficeNotificationReceivedConsumer
FcuVerificationResetConsumer
InitiateItrAssessmentConsumer
FinFortCallbackNotReceivedConsumer
```

Use consumer anchors when tracing:

```text
Kafka event
    ↓
consumer
    ↓
state guard
    ↓
external call / Mongo update
    ↓
next event
```

---

# 19. Configuration Anchors

Detailed configuration implementation is in:

`code/configuration-snippets.md`

High-value anchors:

```text
ConfigFetcher
CommonVersionResolver
PartnerProductConfigurations
ConfigurationRepository
application.yaml
```

---

## 19.1 Version Configuration

Search:

```text
iaVersion
VersionBuckets
primeBucket
resolveFromBucket
```

---

## 19.2 Journey Selection

Search:

```text
enableZenithOrchAPI
assessmentMedium
ACCOUNT_AGGREGATOR
```

---

## 19.3 Retry / Timeout

Search:

```text
retryErrorMsgScreen
iaLoaderTimeoutEnabled
iaLoaderTimeoutDuration
enablePopUpForRetry
retryPopUpHoldTime
limitMultipleRetryAttempt
maxAllowedRetryAttempt
```

---

## 19.4 Vendor Error Mapping

Search:

```text
PerfiosErrorCodeAndConfigMapping
ZenithErrorCodeAndConfigMapping
FinacleErrorCodeAndConfigMapping
MaximusErrorCodeAndConfigMapping
```

---

# 20. Reactive Error / Retry Anchors

When debugging a failure that appears to disappear, transform, or retry unexpectedly, search for:

```text
onErrorResume
onErrorMap
switchIfEmpty
retry
retryWhen
```

These operators can determine whether:

* the error propagates
* the error is mapped
* a fallback is returned
* the operation retries
* the reactive chain terminates
* downstream processing continues

---

# 21. Integration Client Anchors

When debugging external calls, first identify which abstraction is being used.

### Encrypted ESB

```text
esbClientV2
postEncryptedV2
```

Primarily used in supplied snippets for:

* Perfios
* Zenith

### Direct HTTP

```text
WebClient
webClientWrapper
```

Used in supplied snippets for:

* CAP
* Document Service

### Domain Client

```text
client.execute(...)
client.downloadFiles(...)
```

Used in supplied snippets for:

* FinFort

---

# 22. Endpoint Debugging Anchors

For an HTTP integration problem, search for the endpoint configuration rather than only the method name.

High-value configuration anchors:

```text
bankStatementConfig.*
zenithOrchestratorConfig.*
transactionReportConfig.*
capBaseUrl
capUpdateStatusUrl
documentService
```

Typical debugging chain:

```text
Method
 ↓
Config property
 ↓
Resolved URL/path
 ↓
HTTP method
 ↓
Headers
 ↓
Request body
 ↓
Response status
 ↓
Response parsing
```

For 404/405/415 issues, verify:

1. base URL
2. path
3. HTTP method
4. headers
5. content type
6. request body
7. environment
8. stub/mock configuration

before investigating business logic.

---

# 23. Identifier / Correlation Anchors

When searching logs or code, use the correct identifier for the operation.

```text
incomeAssessmentId
applicationReferenceId
commonClientTransactionId
clientTransactionId
perfiosTransactionId
statementId
vendorTransactionId
serviceRequestId
partnerId
productCode
capRefId
finFortOrderId
customerId
```

Important distinction:

```text
incomeAssessmentId
≠
applicationReferenceId
≠
commonClientTransactionId
≠
perfiosTransactionId
```

Never assume these identifiers are interchangeable.

---

# 24. Multi-Attempt Debugging Anchors

When an IA journey is retried, search for:

```text
perfiosTransactionId
commonClientTransactionId
clientTransactionId
statementId
retry
attempt
callback
```

Important model:

```text
One IA application
        |
        +--> Attempt 1
        |       |
        |       +--> vendor transaction A
        |
        +--> Attempt 2
                |
                +--> vendor transaction B
```

A callback arriving late must be correlated to the correct vendor transaction/attempt before evaluating the resulting state transition.

---

# 25. Document/Event/State Boundary Anchors

When an operation appears successful but the overall journey is incorrect, trace these separately:

```text
External API response
        ↓
Mongo state
        ↓
Kafka publication
        ↓
Kafka consumer
        ↓
Document Service
        ↓
CAP / downstream synchronization
```

Do not treat:

```text
API success
```

as proof of:

```text
Mongo success
Kafka success
document upload success
downstream success
final IA success
```

---

# 26. High-Value RCA Entry Points

## Callback Not Received

Search:

```text
PerfiosCallbackNotReceivedConsumer
PerfiosCallbackReceivedConsumer
PerfiosNotificationReceivedConsumer
ZenithCallbackNotReceivedConsumer
ZenithCallbackReceivedConsumer
callbackConfigForProducts
```

Then correlate:

```text
vendor transaction ID
→ callback
→ Kafka event
→ consumer
→ state guard
→ Mongo
→ next event
```

---

## Callback Received but Status Did Not Change

Search:

```text
canUpdateApplicationStatusInPerfiosCallback()
canUpdateApplicationStatusInDb()
```

Then inspect:

```text
current status
statusType
attempt
vendor transaction ID
```

---

## Kafka Event Published but Flow Did Not Progress

Search:

```text
IncomeAssessmentApplicationEventProducer
<relevant>Consumer
state guard
Mongo update
next event
```

Do not stop at Kafka publication.

---

## External API 404/405/415

Search:

```text
<gateway/client method>
<endpoint config>
application.yaml
stub configuration
```

Verify endpoint/method/content type before investigating business logic.

---

## Perfios Report "Application Not Found"

Search:

```text
fetchJsonPerfiosReport
retrieveBankStatementReportV2
findByCommonClientTransactionId
substringBefore("--")
```

Verify:

```text
clientTransactionId
→ normalized prefix
→ Mongo lookup
→ application exists
```

---

## CAP Status Not Updated

Search:

```text
CapSyncServiceFacade
CapSyncServiceRevamp
syncCapConsentStatus
capSyncEnabled
getEventStatusByStatus
callCapServiceUpdateStatusDirect
```

Then verify:

```text
IA status
→ CAP EventStatus
→ capRefId
→ PATCH request
```

---

## FinFort Order/File Issue

Search:

```text
createOrder
checkOrderStatus
getFileDetails
fetchFileFromS3
finFortOrderId
finFortAuthToken
```

Then verify:

```text
applicationReferenceId
→ IA application
→ FinFort order
→ FinFort authentication
→ FinFort API/file
```

---

# 27. Recommended Search Strategy

For an unknown issue, do not start with the exception alone.

Use this sequence:

```text
1. Search business operation
        ↓
2. Find controller/service method
        ↓
3. Find gateway/client call
        ↓
4. Find endpoint/config
        ↓
5. Find request/response model
        ↓
6. Find state mutation
        ↓
7. Find Kafka event
        ↓
8. Find downstream consumer
```

Example:

```text
"Perfios transaction status failed"
        ↓
fetchTransactionLog
        ↓
makeTransactionStatusRequest
        ↓
transactionStatusUrlEnc
        ↓
TransactionStatusEncResponseWrapper
        ↓
callback/status processing
        ↓
Mongo state
```

---

# 28. Code Anchor Priority

For RAG retrieval, prioritize anchors in this order:

### Tier 1 — Orchestration

```text
IncomeAssessmentApplicationController
CommonVersionResolver
IncomeAssessmentApplicationServiceFacade
IncomeAssessmentApplicationServiceV3
```

### Tier 2 — State

```text
IncomeAssessmentApplicationDao
IncomeAssessmentRepository
state guard methods
```

### Tier 3 — External integrations

```text
Perfios gateways
ZenithOrchestratorGateway
CapSyncService
FinFort client/service
Document Service client
```

### Tier 4 — Async processing

```text
IncomeAssessmentApplicationEventProducer
Kafka consumers
event models
```

### Tier 5 — Configuration

```text
ConfigFetcher
PartnerProductConfigurations
ConfigurationRepository
application.yaml
```

---

# 29. Cross-Reference to Code Documents

| Question                                | First document                        |
| --------------------------------------- | ------------------------------------- |
| Where does the request enter IA?        | `code/orchestration-snippets.md`      |
| How is IA version resolved?             | `code/orchestration-snippets.md`      |
| How is Perfios called?                  | `code/integrations-snippets.md`       |
| How is Zenith called?                   | `code/integrations-snippets.md`       |
| How is CAP sync called?                 | `code/integrations-snippets.md`       |
| How does FinFort communicate?           | `code/integrations-snippets.md`       |
| How are documents uploaded?             | `code/integrations-snippets.md`       |
| How does an event move through Kafka?   | `code/kafka-snippets.md`              |
| Where is application state stored?      | `code/database-snippets.md`           |
| Which configuration controls this path? | `code/configuration-snippets.md`      |
| Why was a state transition rejected?    | `08-error-handling.md` + state guards |
| Where should I debug this incident?     | `10-troubleshooting.md`               |

---

# 30. Core Code-Level Invariants

1. **Version resolution occurs before execution of the versioned IA service.**
2. **`IncomeAssessmentApplicationServiceV3` is a major IA orchestration anchor.**
3. **`incomeAssessmentApplications` is the primary Mongo state store for the IA workflow.**
4. **`applicationReferenceId`, `commonClientTransactionId`, `perfiosTransactionId`, and `incomeAssessmentId` represent different correlation concepts.**
5. **Perfios and Zenith integrations shown here use encrypted `esbClientV2.postEncryptedV2(...)`.**
6. **CAP status synchronization uses a direct PATCH WebClient implementation in the supplied code.**
7. **Document Service uses separate V4 POST and V2 PUT integration paths.**
8. **FinFort uses an abstraction that changes request encryption behavior by environment.**
9. **`clientTransactionId.substringBefore("--").trim()` is an explicit correlation normalization rule in Perfios report retrieval.**
10. **External integration success is not equivalent to final IA business success.**
11. **Kafka publication success is not equivalent to consumer processing success.**
12. **Mongo persistence and Kafka publication are separate consistency boundaries.**
13. **State guards can reject an otherwise successfully received callback/event.**
14. **Feature toggles and partner/product configuration can change the executed integration path.**
15. **CAP `EventStatus` is distinct from IA `IncomeAssessmentApplicationStatus`.**
16. **A single IA application can have multiple vendor transaction attempts.**
17. **Late callbacks must be correlated to the correct vendor transaction/attempt.**
18. **The first failing boundary is generally more valuable for RCA than the final propagated exception.**

---

# 31. Canonical Code-Level RCA Question

When investigating an incident, the most useful question is:

> **Starting from the exact API/event and application identifier, which code path was expected to execute, which code path actually executed, and at which method or integration boundary did the behavior first diverge?**
