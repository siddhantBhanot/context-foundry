# Glossary

## Core Business and Technical Terms

* **IA (Income Assessment)**: The Income Assessment service and workflow responsible for collecting, processing, validating, and determining income-assessment outcomes.

* **Assessment Medium**: The mechanism or journey through which financial information is obtained for IA, such as statement upload, scan-and-upload, Account Aggregator (AA), or ITR-related journeys.

* **IA Application**: The persisted Income Assessment workflow record representing an IA journey for a customer/application. The primary application state is stored in the `incomeAssessmentApplications` collection.

* **IA Attempt**: An individual attempt within an IA application, particularly relevant when an external vendor journey is retried. Attempt information can include vendor transaction IDs, callback timestamps, status, and retry context.

* **Perfios**: An external vendor/integration used by IA for statement-based and ITR-related journeys. IA interacts with Perfios through operations such as transaction initiation, journey-link generation, statement upload, transaction completion, transaction-status retrieval, callbacks, and report retrieval.

* **Zenith / AA-Orchestrator**: The external integration path used by IA for Account Aggregator (AA) journey orchestration, including journey-link generation, journey transaction-status retrieval, financial analytics/report retrieval, and BSA-related operations.

* **BSA (Bank Statement Analysis)**: Analysis of bank-statement or Account Aggregator financial data to derive information used during Income Assessment.

* **CAP**: An external platform that can invoke the IA service to initiate an Income Assessment. CAP is an upstream IA consumer/client, similar to other platforms that invoke IA. IA can subsequently synchronize the resulting IA status back to CAP.

* **CAP Initiation**: The CAP → IA interaction in which CAP invokes IA's `/initiate-application` API to start an Income Assessment journey.

* **CAP Sync**: The IA → CAP interaction used to synchronize an IA outcome/status back to CAP. CAP synchronization is configuration-controlled and implemented as a best-effort side effect.

* **CAP `capRefId`**: The CAP-side reference identifier used to correlate the CAP status synchronization request with the corresponding CAP context.

* **CAP `EventStatus`**: The status representation expected by CAP. IA maps its internal IA status to the corresponding CAP `EventStatus` before sending the CAP update-status request.

* **`eventStatus`**: State stored in the IA application representing the status associated with CAP/event synchronization. It is distinct from the primary IA business `status`.

* **Assessment Journey**: The external-data collection and processing path executed after IA initiation. Depending on configuration and application context, this may be a Perfios or Zenith journey.

* **Finacle Flow**: A flow in which account or statement information is obtained from banking-side/Finacle sources before the wider IA processing continues.

* **FinFort**: An external integration used for online ITR-related processing. IA can create a FinFort order, check its status, retrieve associated file details, and download files from S3 as part of the ITR workflow.

* **FinFort Order**: The external order created in FinFort for an ITR journey. IA maintains the corresponding `finFortOrderId` and uses it for subsequent order-status and file-detail operations.

* **`finFortOrderId`**: Identifier of the FinFort order associated with an IA application. It is used to correlate subsequent FinFort status and file operations with the created order.

* **`ffOrderId`**: FinFort order identifier used in flows where the FinFort order is correlated with persisted assessment data. Do not automatically assume it is the same identifier as an IA application or vendor transaction ID.

* **OmniDocs**: The document-storage integration/path used for persisting or retrieving statements, reports, generated documents, or other IA artifacts.

* **OmniDocs Document Reference**: The document identifier returned by OmniDocs after successful document upload and persisted back into IA state when required.

* **Document Service**: The service used by IA for document upload and document persistence/retrieval operations. Examples include OmniDocs V4 upload and document DB persistence.

* **FCU (Fraud Control Unit)**: A downstream/manual verification path that can receive IA outcomes or events for further verification or decisioning.

* **Status**: The primary business state of an IA application, representing where the Income Assessment currently stands or the outcome reached.

* **Status Type**: Additional state classification stored alongside the primary IA status and used to provide more context about the application's state.

* **State Guard**: Business logic that determines whether a particular IA state transition or operation is allowed based on the current application state and other conditions.

* **Partner**: The upstream business/platform context associated with an IA request. Partner information can influence configuration, routing, and behavior.

* **Product**: The product/business context for which IA is being performed. Product configuration can determine journey selection, feature toggles, version routing, and integration behavior.

* **PartnerProductConfiguration**: Configuration associated with a particular partner/product combination that controls IA behavior, including feature toggles and journey-specific settings.

* **`capSyncEnabled`**: Configuration flag determining whether IA should synchronize the IA outcome/status back to CAP for the current application context.

* **`enableZenithOrchAPI`**: Configuration toggle controlling whether the applicable IA flow uses the Zenith / AA-Orchestrator integration.

* **IA Version**: The implementation version of the IA service selected for a request through the configured version-resolution mechanism.

* **Version Bucket**: A logical configuration bucket used by the version resolver before selecting the appropriate IA implementation/facade version.

* **`CommonVersionResolver`**: Component responsible for resolving the applicable IA version based on request/application context and configuration.

* **`ConfigFetcher`**: Component used to resolve dynamic configuration used by IA at runtime.

---

## External Integration and API Terms

* **ESB**: Enterprise Service Bus integration layer used by IA for several external/vendor operations. In the supplied implementation, encrypted requests are commonly sent through `esbClientV2.postEncryptedV2(...)`.

* **ESB Client (`esbClientV2`)**: Client abstraction used by IA to invoke encrypted ESB-backed integrations. It handles the common request mechanism while the integration-specific gateway/service constructs the request body, URI, and headers.

* **Gateway**: Integration-layer component responsible for communicating with an external system or integration boundary. Gateways typically construct requests, invoke the relevant client, and map external responses into IA models.

* **External Vendor Transaction**: A transaction created with an external provider such as Perfios or Zenith for a particular IA attempt.

* **Vendor Transaction ID**: The transaction identifier generated by an external journey provider such as Perfios or Zenith. It identifies a particular external journey attempt and should not be confused with the IA application identifier.

* **Journey Link**: A URL or redirect link generated by an external journey provider that allows the customer/user to continue the external assessment journey.

* **Transaction Status**: The status returned by an external provider for a vendor transaction. It represents vendor-side transaction progress and should not automatically be treated as the final IA business status.

* **Analytics Report**: Financial analytics/report data retrieved from the Zenith / AA-Orchestrator path after the external AA journey progresses to the applicable stage.

* **Insight Report**: Report data retrieved from an external provider and subsequently used by IA for processing, validation, persistence, or downstream actions.

* **Raw Statement**: The original/raw financial statement data retrieved from an external vendor or integration before or alongside report-level processing.

---

## Callback and Asynchronous Processing Terms

* **Callback**: An asynchronous notification from an external system such as Perfios or Zenith indicating that an external journey or processing operation has progressed or completed.

* **Callback Timeout**: A condition in which the expected external callback is not received within the configured/allowed time window, potentially causing IA to fall back to status polling, retry logic, or a failure path.

* **Late Callback**: A callback received after IA has already timed out, retried, failed, or started another attempt. Late callbacks must be correlated to the correct IA application and external transaction/attempt.

* **Callback Identifier**: Identifier supplied with or derived from a callback and used to correlate the callback with the corresponding IA transaction/application. Callback validation may include format checks controlled by configuration.

* **Transaction Status Polling**: A recovery or progress-check mechanism in which IA explicitly calls a vendor transaction-status API when the expected callback is unavailable or when status needs to be verified.

* **Retry Attempt**: A subsequent execution of an IA/vendor journey after a previous attempt fails, times out, or is otherwise eligible for retry.

* **Multiple Callback Processing**: Configuration-controlled behavior that allows IA to process multiple callbacks associated with a journey when applicable.

---

## Identifier and Correlation Terms

* **`incomeAssessmentId`**: Identifier associated with the IA application/workflow.

* **`applicationReferenceId`**: Application/business reference used to correlate an IA request with the originating application context.

* **`commonClientTransactionId`**: Client-side/common transaction identifier used for correlation across parts of the request and downstream workflow.

* **`serviceRequestId`**: Service/request-level correlation identifier used for tracing an IA operation across service boundaries.

* **`capRefId`**: CAP reference identifier used when correlating IA status synchronization with the originating CAP context.

* **`perfiosTransactionId`**: Perfios-side transaction identifier representing a particular Perfios journey/attempt.

* **`vendorTransactionId`**: Generic term for an external provider transaction identifier. Depending on the journey, this may correspond to a Perfios or Zenith transaction identifier.

* **`statementId`**: Identifier associated with a statement-processing operation. It can also be used as a reference when persisting document data.

* **`serviceRequestIdForPerfiosUpload`**: Configuration/request identifier used for the Perfios upload-related ESB operations.

* **Correlation Identifier**: Any identifier used to connect an application, request, external transaction, event, callback, or downstream operation during debugging. Common identifiers include `incomeAssessmentId`, `applicationReferenceId`, `commonClientTransactionId`, `serviceRequestId`, `capRefId`, `statementId`, and vendor transaction IDs.

* **Identifier Normalization**: Transformation applied before lookup or correlation when a transaction identifier can contain additional suffix information. For example, some Perfios report and application lookups use the portion before `"--"`.

---

## Document and Persistence Terms

* **Document Upload**: Operation that transfers a statement/report/document from IA to the Document Service/OmniDocs.

* **OmniDocs V4 Upload**: Document Service operation used by IA to upload documents through `/document-service/v4/documents`.

* **Document DB Persistence**: Persistence of document metadata/content through the Document Service document endpoint. The supplied implementation uses `/document-service/v2/document`.

* **Document Reference ID**: Identifier returned or persisted to reference a document stored outside the primary IA application record.

* **`IAS_DOCUMENT_IDENTIFIER_KEY`**: Reference-map key used when document information is persisted with the associated statement identifier.

* **Base64 Document Data**: Representation used by the document persistence flow when document content is encoded before being sent to the Document Service.

---

## Kafka and Event Terms

* **Kafka Event**: An asynchronous workflow signal published by IA to communicate a state change, processing result, callback, retry, or downstream action to another component or service.

* **Kafka Consumer**: Component that receives and processes an IA Kafka event. Consumer receipt does not necessarily mean that the associated business operation or database update succeeded.

* **Kafka Producer**: Component responsible for publishing IA events to Kafka.

* **Event Publication**: The act of publishing an IA event to Kafka. Successful publication does not guarantee successful consumer processing or downstream completion.

* **Downstream Synchronization**: Communication from IA to another system after IA processing, such as CAP status synchronization or other downstream event/API processing.

* **Best-Effort Side Effect**: An operation whose failure should not automatically change or invalidate the primary business result. CAP status synchronization is an example.

---

## Business and State Terms

* **Business Rule**: Rule applied to financial/assessment data to determine the IA business outcome, such as income-credit, cheque-bounce, statement-status, or required-history rules.

* **Terminal State**: An IA state from which the normal workflow should not continue through the same transition path. Terminal-state behavior is enforced through business/state guards.

* **Business Validation**: Processing performed after financial/report data is retrieved to determine whether the data satisfies the configured IA business rules.

* **Policy Norms**: Business-policy conditions that can result in outcomes such as `POLICY_NORMS_NOT_MET`.

* **Next Action**: UI/workflow instruction returned by IA to determine what the user or calling client should do next. The `/validate` flow can derive the next action from the current application state, configuration, retry state, and journey context.

* **Retry Screen**: UI path shown when an IA journey can be retried. Its behavior is controlled by configuration such as `retryErrorMsgScreen`.

* **Loader Timeout**: UI/workflow timeout behavior used when an external journey callback is not received within the configured period. Configuration such as `iaLoaderTimeoutEnabled` and `iaLoaderTimeoutDuration` controls this behavior.

---

## Common IA Status Examples

Important IA workflow/business statuses include:

```text
DOCUMENTS_NOT_UPLOADED
INCOME_ASSESSMENT_IN_PROGRESS
INCOME_ASSESSMENT_SUCCESS
INCOME_ASSESSMENT_FAILED
INCOME_ASSESSMENT_REJECTED
INCOME_ASSESSMENT_REFERRED
POLICY_NORMS_NOT_MET
BANK_STATEMENT_ASSESSMENT_COMPLETED
ITR_DOCUMENTS_NOT_UPLOADED
PROCEED_TO_ITR_ASSESSMENT
BSA_PAUSED_PENDING_USER_DECISION
FINFORT_STATUS_IN_PROGRESS
```

These represent IA workflow/business states and should not automatically be interpreted as CAP `EventStatus` values.

---

## Configuration and Versioning Terms

* **Feature Toggle**: Configuration that enables or disables a specific IA capability or behavior, generally resolved from the feature-toggle configuration.

* **Partner/Product Configuration**: Runtime configuration associated with a specific partner/product context. It can control journey behavior, retry behavior, callback handling, timeouts, and IA version.

* **`PartnerProductConfigurations`**: Configuration group containing partner/product-specific IA behavior.

* **`iaVersion`**: Configuration value representing the active IA implementation version for the applicable partner/product context.

* **`VersionBuckets`**: Configuration defining the mapping or bucket used to resolve an IA implementation version.

* **`enableZenithOrchAPI`**: Enables the Zenith/AA-Orchestrator path when the applicable application context and assessment medium satisfy the journey conditions.

* **`enablePerfiosGenerateLinkEncrypted`**: Feature toggle controlling the encrypted Perfios generate-link integration path.

* **`uploadStatementPerfiosIA`**: Feature toggle controlling applicable Perfios statement-upload/document behavior.

* **`enableTransactionReportEncrypted`**: Feature toggle controlling the encrypted transaction-report retrieval path.

* **`enableMultiplePerfiosCallbacks`**: Partner/product configuration controlling whether multiple Perfios callbacks can be processed.

* **`iaLoaderTimeoutEnabled`**: Partner/product configuration controlling whether IA applies loader-timeout behavior when an expected callback is not received.

* **`retryErrorMsgScreen`**: Partner/product configuration controlling whether the retry/error-message UI path is enabled.

* **Configuration-Driven Error Mapping**: Mapping between external vendor/integration error codes and IA-specific errors or business behavior. Examples include `PerfiosErrorCodeAndConfigMapping`, `ZenithErrorCodeAndConfigMapping`, and `FinacleErrorCodeAndConfigMapping`.

---

## Important Architectural Distinctions

### CAP vs IA

```text
CAP
 │
 │ /initiate-application
 ▼
IA
```

CAP is an external/upstream platform that invokes IA.

---

### Perfios / Zenith vs CAP

```text
CAP
 │
 ▼
IA
 │
 ├── Perfios
 │
 └── Zenith
```

Perfios and Zenith are journey/integration providers used by IA after initiation.

CAP is the platform that can initiate the IA journey.

---

### CAP Initiation vs CAP Sync

```text
CAP ──────────────→ IA
       Initiation

IA ───────────────→ CAP
       Status Sync
```

These are separate integration directions and should be debugged independently.

---

### IA Status vs CAP EventStatus

```text
IA Business Status
        │
        ▼
  Status Mapping
        │
        ▼
 CAP EventStatus
```

`status` and `eventStatus` should not be treated as the same state.

---

### IA Application vs Vendor Transaction

```text
IA Application
      │
      ├── Vendor Attempt 1
      │      └── Vendor Transaction ID
      │
      ├── Vendor Attempt 2
      │      └── Vendor Transaction ID
      │
      └── Vendor Attempt N
             └── Vendor Transaction ID
```

One IA application can contain multiple external journey attempts.

---

### Vendor Transaction vs IA Business Outcome

A successful vendor transaction/status does not automatically mean:

```text
Vendor Success
      ↓
IA Success
```

The normal conceptual flow is closer to:

```text
Vendor Transaction
      ↓
Report / Financial Data
      ↓
IA Processing
      ↓
Business Validation
      ↓
IA Business Status
```

---

### Journey Link vs Journey Completion

Generating a Perfios or Zenith journey link only proves that the link-generation operation succeeded.

It does **not** prove that:

* the user opened the journey,
* the user completed the journey,
* the vendor processed the data,
* the callback was received,
* the report was retrieved,
* or IA reached a successful business state.

---

### Callback vs Report Retrieval

A callback indicates external processing progress/completion, but it is not necessarily the report itself.

```text
External Journey
      ↓
Callback / Status
      ↓
Report Retrieval
      ↓
Business Processing
      ↓
IA Status
```

A callback can therefore succeed while report retrieval subsequently fails.

---

### Document Service vs IA Database

Document storage and IA application state are separate persistence boundaries.

```text
IA Application
     │
     ├── MongoDB
     │      └── IA workflow state
     │
     └── Document Service / OmniDocs
            └── Document content/reference
```

A successful document upload does not automatically mean the IA MongoDB update succeeded, and vice versa.

---

### CAP Sync vs Primary IA Outcome

CAP synchronization is a downstream side effect.

Conceptually:

```text
IA Business Processing
        ↓
IA Status
        ↓
CAP Status Mapping
        ↓
CAP PATCH API
```

Failure of the CAP synchronization call should not automatically redefine the primary IA business outcome.

---

### FinFort Order vs IA Application

```text
IA Application
      │
      └── FinFort Order
             └── finFortOrderId
```

The FinFort order is an external ITR-processing entity associated with an IA application. The FinFort order identifier should not be treated as the IA application identifier.

---

## Common Configuration Groups

Important runtime configuration concepts include:

```text
PartnerProductConfigurations
IncomeAssessment
Callback
VersionBuckets
PerfiosErrorCodeAndConfigMapping
ZenithErrorCodeAndConfigMapping
FinacleErrorCodeAndConfigMapping
MaximusErrorCodeAndConfigMapping
```

Configuration can change runtime behavior without requiring a code change.

---

## RAG Retrieval Guidance

For developer/debugging questions, prefer retrieving glossary terms together with the corresponding flow or implementation document.

| Query intent                                                | Primary terminology                                                             |
| ----------------------------------------------------------- | ------------------------------------------------------------------------------- |
| “What is CAP?”                                              | CAP, CAP Initiation, CAP Sync                                                   |
| “How does CAP start IA?”                                    | CAP Initiation, `/initiate-application`                                         |
| “How does IA update CAP?”                                   | CAP Sync, `capRefId`, `EventStatus`, `capSyncEnabled`                           |
| “What is Perfios transaction ID?”                           | Perfios, Vendor Transaction ID, `perfiosTransactionId`, IA Attempt              |
| “Why is transaction status different from IA status?”       | Transaction Status, Status, Vendor Transaction                                  |
| “What happens after callback?”                              | Callback, Report Retrieval, Business Validation                                 |
| “Why can callback succeed but IA fail?”                     | Callback, Report Retrieval, Business Validation, State Guard                    |
| “What is Zenith?”                                           | Zenith / AA-Orchestrator, Assessment Journey                                    |
| “What is FinFort?”                                          | FinFort, FinFort Order, `finFortOrderId`                                        |
| “Where are documents stored?”                               | Document Service, OmniDocs, Document DB Persistence                             |
| “Why can document upload succeed but state be wrong?”       | Document Service, IA Application, MongoDB                                       |
| “What is a late callback?”                                  | Late Callback, IA Attempt, Vendor Transaction ID                                |
| “What identifies an IA application?”                        | `incomeAssessmentId`, `applicationReferenceId`, `commonClientTransactionId`     |
| “Why is my transaction lookup not finding the application?” | Identifier Normalization, `commonClientTransactionId`, `applicationReferenceId` |
| “How is Zenith selected?”                                   | `enableZenithOrchAPI`, Assessment Medium, PartnerProductConfiguration           |
| “How is IA version selected?”                               | `iaVersion`, Version Bucket, `CommonVersionResolver`                            |
| “Where does external error mapping happen?”                 | Configuration-Driven Error Mapping, Perfios/Zenith/Finacle mappings             |

---

## Source-of-Truth Reminder

For any definition that describes actual runtime behavior, prioritize:

1. Current implementation code
2. Repository/domain models and enums
3. Configuration consumed by that code
4. Integration gateway/client implementation
5. Kafka consumers/producers
6. Tests and stubs
7. README or historical documentation

The glossary provides terminology and architectural distinctions. It should not override the implementation when the code behaves differently.

---

## Source Citations

* `README.md:15-31`
* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/domain/Status.kt:3-44`
* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/repository/IncomeAssessmentRepository.kt:397-412`
* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/revamp/versionresolvers/CommonVersionResolver.kt:53-69`
* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/multibank/service/CapSyncService.kt:189-244`
* `src/main/resources/application.yaml:341-349`
* Perfios integration implementation: start transaction, upload statement, complete transaction, generate link, transaction status, and report retrieval
* Zenith integration implementation: journey link, transaction status, and analytics report retrieval
* Document Service implementation: OmniDocs V4 upload and document persistence
* FinFort integration implementation: consent link, order creation, order status, file details, and S3 file retrieval
