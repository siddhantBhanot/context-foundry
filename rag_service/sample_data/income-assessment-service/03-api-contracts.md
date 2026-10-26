---

service: income-assessment-service
document_type: api-contracts
topic: http-api-contracts
source: repository-code-and-models
language: kotlin
framework: spring-webflux
-------------------------

# API Contracts

This document is the **developer-facing API reference** for `income-assessment-service`.

It answers:

* Which API should I call for a particular IA operation?
* What HTTP method and path does it use?
* What headers, query parameters, and request body are required?
* What response model does it return?
* What important side effects occur behind the API?
* What API/event should be expected next?
* Which controller/model should I inspect in the repository?

The request/response examples in this document are **contextual examples derived from repository models and controller signatures**. They are not a replacement for generated OpenAPI schemas or the Kotlin source of truth.

If an example conflicts with the current implementation, the current Kotlin code and configuration take precedence.

---

# 1. API map

The service exposes APIs across several functional areas:

| Area               | Base path                                            | Primary purpose                                                 |
| ------------------ | ---------------------------------------------------- | --------------------------------------------------------------- |
| Core IA journey    | `/income-assessment-service/v1`                      | Initiation, processing, validation, status and result retrieval |
| Scan/upload        | `/income-assessment-service/v1/scan-upload`          | Statement upload journey                                        |
| IA scan/upload     | `/income-assessment-service/v1/scan-and-upload-ia`   | IA-specific scan/upload journey                                 |
| Bank statement     | `/income-assessment-service/v1/bank-statement`       | Statement details, upload and fraud information                 |
| ITR V1             | `/income-assessment-service/v1/itr-statements`       | ITR transaction and status operations                           |
| ITR V2             | `/income-assessment-service/v2/itr-statements`       | Newer ITR processing flow                                       |
| Consolidation      | `/income-assessment-service/v1/consolidate-document` | Consolidate multiple statement transactions                     |
| BSA                | `/income-assessment-service/v1/bsa`                  | BSA initiation                                                  |
| Callbacks          | `/income-assessment-service/v1/status/*`             | Vendor callback entry points                                    |
| FinFort online ITR | `/income-assessment-service/v1/itr/online`           | Online ITR consent flow                                         |
| Multi-bank         | `/income-assessment-service/v1/multi-bank`           | Multi-bank results and fraud analysis                           |
| Configuration      | `/income-assessment-service/v1`                      | Journey/configuration lookup APIs                               |

---

# 2. Contract conventions

### Base paths

Endpoints are shown relative to their controller base path.

For example:


POST /income-assessment-service/v1/initiate-application


may be documented as:


POST /initiate-application


inside the Core IA section.

### Authentication

Only document an `Authorization` header where the controller/configuration indicates that it is relevant.

Do not assume that every API has the same authentication requirement.

### Request bodies

Request body examples use the corresponding Kotlin request model where available.

Examples are intentionally representative rather than exhaustive.

### Response models

Where the controller returns a sealed/generic response such as `IncomeAssessmentResponse`, document the important known response shape instead of inventing a single universal schema.

### Sensitive data

Examples should use synthetic values only.

Never add real customer PANs, mobile numbers, account numbers, JWTs, vendor credentials, or production URLs to this knowledge base.

---

# 3. Core IA journey APIs

Base path:


/income-assessment-service/v1


These APIs represent the main application lifecycle.

---

## 3.1 Initiate application

### `POST /initiate-application`

Also exposed through:


POST /enc/initiate-application


### Purpose

Creates or initializes the IA application context used by subsequent IA processing.

### Request

Header:


partnerId: <PARTNER_ID>


Request model:


IncomeAssessmentApplicationRequest


Important request fields include:

* `assessmentMedium`
* `productCode`
* customer information
* `occupation`
* `applicationReferenceId`
* `bankName`
* `bankStatementDuration`
* `journeyMode`
* multi-bank/retry flags
* communication address

Example:

json
{
  "assessmentMedium": "NONE",
  "productCode": "PERSONAL",
  "customerName": "Rohit Kumar",
  "emailId": "rohit.kumar@example.com",
  "mobileNumber": "9000000000",
  "pan": "ABCDE1234F",
  "occupation": {
    "type": "SALARIED",
    "employerName": "Example Corp"
  },
  "applicationReferenceId": "PLA000000000031",
  "bankName": "Core Banking Partner",
  "bankStatementDuration": 6,
  "journeyMode": "D2C",
  "isMultiBank": false,
  "isRetryable": true
}


### Response

Controller-local `IncomeAssessmentResponse` containing an `IncomeAssessmentIdMap`.

Example:

json
{
  "data": {
    "incomeAssessmentId": "ia-example-123"
  }
}


### Flow continuation

The returned IA/application context is subsequently used by APIs such as:


/generate-link
/start-process
/status
/application/status
/income-details


depending on the selected journey.

### Code anchors


src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/controller/IncomeAssessmentApplicationController.kt
src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/request/IncomeAssessmentApplicationRequest.kt


---

## 3.2 Validate journey

### `GET /validate`

### Inputs

Header:


Authorization: <JWT>


Query parameters:


retry
timedOut
accountSelectionCancel


### Response


ValidateResponse


The response tells the caller what action the UI/journey should take next.

Possible actions include concepts such as:


SHOW_IN_PROGRESS_PAGE
REDIRECT_TO_PARTNER


Example:

json
{
  "action": "SHOW_IN_PROGRESS_PAGE",
  "redirectUrl": "https://example.com/income-assessment",
  "redirectionErrorUrl": "https://example.com/error",
  "details": {
    "status": "INCOME_ASSESSMENT_IN_PROGRESS"
  },
  "showBackButton": false
}


### Developer note

This API is primarily a **journey decision/validation API**. Do not treat it as a simple status lookup.

### Code anchors


src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/controller/IncomeAssessmentApplicationController.kt
src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/response/ValidateResponse.kt


---

## 3.3 Back to partner

### `POST /back-to-partner`

### Inputs

Header:


Authorization: <JWT>


### Response


ValidateResponse


The response instructs the caller to return to the originating partner journey.

Example:

json
{
  "action": "REDIRECT_TO_PARTNER",
  "redirectUrl": "https://example.com/return",
  "redirectionErrorUrl": "https://example.com/error",
  "details": {
    "reason": "USER_NAVIGATED_BACK"
  },
  "showBackButton": false
}


### Code anchors


src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/controller/IncomeAssessmentApplicationController.kt
src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/response/ValidateResponse.kt


---

## 3.4 Status

### `GET /status`

Also exposed through:


GET /enc/status


### Inputs

Header:


partnerId: <PARTNER_ID>


Query parameters:


incomeAssessmentId
productCode


### Response


StatusMap


Example:

json
{
  "data": {
    "status": "INCOME_ASSESSMENT_SUCCESS",
    "incomeAssessmentId": "ia-example-123"
  }
}


### Developer note

Use this API when the caller already has the IA identifier and needs the current application status.

For deeper debugging, inspect the persisted application state rather than relying only on the API response.

---

## 3.5 Application status

### `GET /application/status`

### Input source


TransactionTokenClaims


### Response


StatusMap


Example:

json
{
  "status": "INCOME_ASSESSMENT_IN_PROGRESS",
  "incomeAssessmentId": "ia-example-123",
  "applicationReferenceId": "PLA000000000031",
  "statusCode": "IA-000",
  "details": {
    "assessmentMedium": "STATEMENT"
  }
}


### Difference from `/status`

Use `/application/status` when the application context is derived from the transaction token/claims.

Use `/status` when the caller explicitly supplies the IA identifier and product context.

---

## 3.6 Generate link

### `GET /generate-link`

### Inputs

Header:


Authorization: <JWT>


Query parameters:


assessmentMedium
isBSSelected
isRedirectToAA
promoId
manualSelection


### Response

Sealed:


IncomeAssessmentResponse


A common success response is:


SuccessGenerateLinkResponse


Example:

json
{
  "status": "Success",
  "response": {
    "journeyLink": "https://vendor.example.com/journey/example"
  }
}


### Flow continuation

This API can initiate/prepare the external vendor journey.

Trace:


/generate-link
→ versioned service
→ vendor/integration gateway
→ application state
→ external journey
→ callback/event


For detailed Perfios execution, see:


flows/perfios-flow.md


---

## 3.7 Start process

### `GET /start-process`

### Inputs

Header:


Authorization: <JWT>


Query:


assessmentMedium


### Response


IncomeAssessmentResponse


Common success model:


SuccessStartProcessResponse


Example:

json
{
  "status": "Success",
  "response": "<html>redirect form</html>"
}


### Developer note

This is a processing/redirect operation rather than a simple data retrieval API.

Trace the resolved versioned service to understand which downstream path is selected.

---

## 3.8 Redirect to partner

### `GET /redirect-to-partner`

### Inputs

Header:


Authorization: <JWT>


### Response


IncomeAssessmentResponse


Common success model:


SuccessPartnerRedirectResponse


Example:

json
{
  "status": "Success",
  "returnUrl": "https://example.com/final-status"
}


---

## 3.9 Income details

### `GET /income-details`

Also exposed through:


GET /enc/income-details


### Inputs


incomeAssessmentId
productCode
partnerId


### Response


IncomeAssessmentDetailResponse


The response represents the processed income-assessment information associated with the application.

Example:

json
{
  "incomeAssessmentId": "ia-example-123",
  "productCode": "PERSONAL",
  "partnerId": "PARTNER_CORE",
  "customer": {
    "name": "Rohit Kumar"
  },
  "income": {
    "netAmount": 55000,
    "unit": "MONTH"
  }
}


---

## 3.10 Get details

### `GET /get-details`

### Inputs

Header:


Authorization: <JWT>


Query:


incomeAssessmentId
applicationReferenceId


### Response


GetDetailsWithItrResponse


This response can combine IA and ITR-related information.

Example:

json
{
  "incomeAssessmentData": {
    "incomeAssessmentInsightReport": {
      "monthlyIncome": 55000
    },
    "itr": {
      "statementId": "itr-example-1",
      "statementStatus": "VERIFIED",
      "netTaxableIncome": 720000
    }
  }
}


---

## 3.11 Get document

### `GET /get-document`

### Inputs

Header:


Authorization: <JWT>


Query:


applicationReferenceId
source
deliveryMode
incomeAssessmentId


### Response


DocumentDetailResponse


The response can contain document metadata/reference information such as:

* document code
* document status
* document ID
* repository/system
* URI/reference
* filename
* MIME type

### Developer note

This API is document metadata/retrieval orchestration. Follow the document-service integration when debugging document availability.

---

# 4. Journey/configuration APIs

These APIs expose configuration or UI-driving values rather than performing the core assessment itself.

Examples:


GET /get-statement-duration
GET /get-itr-duration
GET /get-perfios-errormessage
GET /get-occupation-type
GET /get-bank-name
GET /get-journey-mode
GET /get-description-box-config
GET /is-sbb-product
GET /get-bank-account-type
GET /toggles
GET /get-ia-configs
GET /get-applicant-details
GET /get-config-value/{featureConfigName}


These APIs are important when investigating **why a particular journey behaves differently for a partner/product**.

---

## 4.1 Toggles

### `GET /toggles`

Example:

json
{
  "enableZenithOrchAPI": true,
  "enableFinaclePdf": false,
  "enablePopUpForRetry": true
}


Important toggles can affect downstream routing.

For example, `enableZenithOrchAPI` and `enableFinaclePdf` are relevant when investigating statement/BSA/Finacle branches.

### Code anchors


src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/controller/IncomeAssessmentApplicationController.kt
src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/utils/ConfigFetcher.kt


---

## 4.2 IA configuration

### `GET /get-ia-configs`

Returns partner/product-specific configuration used by the IA journey.

Example:

json
{
  "partnerId": "PARTNER_CORE",
  "productCode": "PERSONAL",
  "productType": "PERSONAL_LOAN",
  "applicationSource": "MOBILE",
  "isImputedEnabled": true,
  "deferFCUTaskCreation": false,
  "enableNetFetch": true,
  "enableScanAndUpload": true,
  "isBackButtonEnabled": false
}


### Developer note

When two requests with apparently identical APIs behave differently, inspect the partner/product configuration before assuming that the service implementation is different.

---

## 4.3 Feature configuration

### `GET /get-config-value/{featureConfigName}`

Example:

json
{
  "featureGroup": "IncomeAssessment",
  "featureToggleKey": "enableLoaderTimeout",
  "value": true
}


This is useful for tracing configuration-driven behavior.

---

# 5. Resume / Finacle-assisted APIs

## 5.1 Resume BSA

### `POST /bsa-resume`

Request model:


BsaResumeRequest


Example:

json
{
  "type": "PAUSED_FOR_ITR",
  "userDecision": "PROCEED_WITH_ITR"
}


Response:


ResponseEntity<Any>


The exact response is service-driven.

### Developer note

This API represents a **continuation decision** in a partially completed journey.

Trace the current application state before debugging this API.

---

## 5.2 Multi-account Finacle assessment

### `POST /multi-account-finnacle-assessment`

Request model:


MultiAccFinnacleRequest


Response:


ValidateResponse


Example request:

json
{
  "finacleAccountDetails": {
    "foracid": "910010011001",
    "acct_TYPE": "SB",
    "ifsc_CODE": "UTIB0000001",
    "openingDate": "2023-01-01",
    "isSelected": true
  }
}


Example response:

json
{
  "action": "SHOW_BANK_STATEMENT_PROCESSING",
  "details": {
    "source": "FINACLE"
  }
}


### Developer note

When debugging this flow, inspect the Finacle-assisted routing logic and the configuration that determines whether processing subsequently follows the classic statement path or another configured route.

---

# 6. Scan-and-upload APIs

There are two closely related API groups:


/income-assessment-service/v1/scan-upload
/income-assessment-service/v1/scan-and-upload-ia


The second is the IA-specific variant.

---

## 6.1 Start transaction


POST /scan-upload/start-transaction
POST /scan-and-upload-ia/start-transaction


Inputs include:


assessmentMedium


The IA-specific variant can additionally use:


institutionId
isBSSelected


Response:


IncomeAssessmentResponse


Representative response:

json
{
  "status": "Success",
  "response": {
    "txnId": "st-example-123",
    "uploadUrl": "https://example.com/upload"
  }
}


---

## 6.2 Upload statement


POST /scan-upload/upload-statement
POST /scan-and-upload-ia/upload-statement


Request models:


UploadStatementRequest
UploadStatementRequestForIA


Representative request:

json
{
  "applicationReferenceId": "PLA000000000031",
  "perfiosTransactionId": "txn-example-123",
  "fileDetails": {
    "fileName": "salary-statement.pdf",
    "data": "BASE64_ENCODED_FILE_CONTENT",
    "filePassword": null
  }
}


The file payload is represented here only as a placeholder. Do not place actual customer documents into the knowledge base.

---

## 6.3 Complete transaction


POST /scan-upload/complete-transaction
POST /scan-and-upload-ia/complete-transaction


Query:


perfiosTransactionId


Response:


IncomeAssessmentResponse


The completion operation can transition processing into the downstream/callback/result phase.

---

## 6.4 Document index

### `GET /scan-upload/document-index/{transactionId}`

Response:


List<UploadedDocument>


This API exposes uploaded document/index information associated with a transaction.

---

# 7. Bank statement APIs

Base path:


/income-assessment-service/v1/bank-statement


---

## 7.1 Get statement details

### `GET /{statementId}`

Response:


BankStatementDetails


The response can contain:

* statement status
* income details
* customer details
* account details
* vendor transaction ID
* fraud indicators
* salary credit information

Example:

json
{
  "statementStatus": "VERIFIED",
  "incomeDetails": {
    "netIncomeAmount": 55000,
    "unit": "MONTH"
  },
  "accountDetails": {
    "bankName": "Core Banking Partner"
  },
  "vendorTransactionId": "txn-example-987"
}


---

## 7.2 Fraud indicator

### `GET /{statementId}/fraud-indicator`

Response:


FraudIndicator


Example:

json
{
  "statementId": "st-example-123",
  "fraudIndicators": [
    "EQUAL_CREDIT_DEBIT"
  ]
}


---

## 7.3 Upload statement

### `POST /upload`

Request:


BankStatementRequest


Representative request:

json
{
  "clientId": "client-example",
  "loanType": "PERSONAL",
  "returnUrl": "https://example.com/return",
  "correlationData": {
    "incomeAssessmentId": "ia-example-123"
  },
  "occupation": "SALARIED",
  "destination": "STATEMENT",
  "eligibleForBankingSurrogate": false,
  "applicationReferenceId": "PLA000000000031"
}


---

## 7.4 Scan-upload transaction

### `POST /scan-upload/start-transaction`

Request:


ScanAndUploadStartTransactionRequest


This is the bank-statement module's scan/upload entry point and should be distinguished from the top-level IA scan-upload controller.

---

# 8. ITR APIs

ITR processing is exposed through both V1 and V2 APIs.

---

## 8.1 ITR V1

Base path:


/income-assessment-service/v1/itr-statements


### `POST /start-transaction`

Request:


ItrStartTransactionRequest


Example:

json
{
  "pan": "ABCDE1234F",
  "returnUrl": "https://example.com/return",
  "productCode": "PERSONAL"
}


### `GET /{statementId}`

Response:


Itr


The ITR model can contain:

* statement status
* vendor transaction ID
* ITR assessment information
* fraud indicators
* assessment attempt information
* taxable income
* uploaded document information

### `PATCH /{statementId}`

Request:


UpdateStatusRequest


Example:

json
{
  "status": "DOCUMENT_UPLOADED"
}


---

## 8.2 ITR V2

Base path:


/income-assessment-service/v2/itr-statements


### `POST /start-transaction`

Response:


IncomeAssessmentResponse


### `POST /fetch-status-and-retrieve-report`

Response:


IncomeAssessmentResponse


### `GET /{statementId}`

Response:


Itr


### `PATCH /{statementId}`

Request:


UpdateStatusRequest


### Developer note

Do not assume V1 and V2 have identical behavior because their response models overlap.

When tracing an ITR issue, first identify which controller/base path was actually invoked.

---

# 9. IA document-consolidation APIs

Base path:


/income-assessment-service/v1/consolidate-document


These APIs orchestrate consolidation of multiple statement transactions.

---

## 9.1 Initiate consolidation

### `POST /initiate`

Request body:


List<String>


The values represent transaction IDs.

Example:

json
[
  "txn-1",
  "txn-2"
]


Response:


IAConsolidateInitiateResponse


---

## 9.2 Process

### `POST /process`

Request body:


String


The string represents the consolidation client transaction ID.

---

## 9.3 Document status

### `POST /document-status`

Request body:


String


Example:

json
"cons-123"


Response:


IAConsolidateStatusResponse


The response can contain report-generation state and service-level processing information.

---

## 9.4 Download report

### `POST /download-report`

Request body:


String


Response:


IAConsolidateDownloadResponse


This can contain consolidated customer, statement and account-analysis information.

---

## 9.5 Fetch report

### `POST /fetch-report`

Request body:


String


Response:


Report bytes / binary response


This endpoint should be treated differently from `/download-report`: `/download-report` exposes the structured report response, while `/fetch-report` returns report content.

---

# 10. BSA API

Base path:


/income-assessment-service/v1/bsa


## `POST /initiate`

Request:


InitiateBsaApiRequest


Representative request:

json
{
  "fileDetails": {
    "fileName": "salary-statement.pdf",
    "data": "BASE64_ENCODED_FILE_CONTENT",
    "filePassword": null
  },
  "assessmentMedium": "STATEMENT",
  "isBSSelected": true,
  "isRedirectToAA": false
}


Response:


InitiateBsaResponse


Example:

json
{
  "status": "SUCCESS",
  "data": {
    "serviceRequestId": "SR-example-123"
  }
}


### Flow continuation

The API can lead into:


IA
→ BSA initiation
→ Zenith / AA-Orchestrator
→ asynchronous processing
→ Zenith callback
→ IA state update


For execution tracing, see:


flows/income-assessment-flow.md


---

# 11. Callback APIs

Callbacks are external/event-driven entry points into IA processing.

A callback response generally acknowledges receipt; the actual business processing can continue asynchronously.

---

## 11.1 Perfios callback

### `POST /status/perfios`

Also exposed through:


POST /enc/status/perfios


Request:


NewPerfiosNotificationReceivedRequest


Representative request:

json
{
  "perfiosTransactionId": "txn-example-123",
  "clientTransactionId": "CLIENT|PL|example--1",
  "status": "COMPLETED",
  "errorMessage": null,
  "errorCode": "E_NO_ERROR"
}


Response:


AcknowledgementResponse


Example:

json
{
  "data": {
    "acknowledge": true
  }
}


### Processing path


Perfios callback
→ callback controller
→ callback/event processing
→ application lookup
→ state validation
→ Mongo update
→ downstream event/processing


See:


flows/perfios-flow.md


---

## 11.2 Zenith callback

### `POST /status/zenith-callback`

Request:


ZenithNotificationReceivedRequest


Representative request:

json
{
  "serviceRequestId": "SR-example-123",
  "requestReferenceId": "CLIENT|PL|example--1",
  "status": "COMPLETED",
  "subStatus": "ANALYTICS_COMPLETED",
  "tspInfo": {
    "tsp": "AA",
    "tspReferenceId": "TSP-example"
  },
  "bsaInfo": {
    "bsa": "COMPLETED",
    "bsaReferenceId": "BSA-example"
  },
  "errorMsg": null,
  "errorCode": null
}


Response:


AcknowledgementResponse


---

## 11.3 FinFort callback

### `POST /status/finfort`

Request:


FinFortCallbackReceivedRequest


The callback contains FinFort order/reference/status information.

Response:


AcknowledgementResponse


### Developer note

For callback debugging, identify the external reference ID first and then trace it into the application record and consumer/business-processing path.

---

# 12. FinFort online ITR

Base path:


/income-assessment-service/v1/itr/online


## `POST /consent-link`

Header:


Authorization: <JWT>


Response can contain either a consent-link response or a fallback error response.

Success example:

json
{
  "consentUrl": "https://example.com/consent/example",
  "shouldRedirect": true,
  "shouldSendSms": false,
  "waitForCallback": true
}


Failure/fallback example:

json
{
  "status": "ERROR",
  "errorCode": "ONLINE_ITR_FINFORT_FAILED",
  "errorMessage": "Unable to retrieve ITR details online.",
  "fallbackMediums": [
    {
      "mediumType": "OFFLINE_ITR_PERFIOS",
      "action": "PROCEED_TO_ITR_UPLOAD",
      "endPoint": "/income-assessment-service/v2/itr-statements/start-transaction"
    }
  ]
}


### Developer note

This API is particularly important for understanding **fallback journey selection** when online ITR processing is unavailable.

---

# 13. Fraud-indicator APIs

## IA fraud-indicator mapping

### `GET /fraud-indicators-mapping`

Returns the configured mapping between fraud indicators and their interpretation/severity.

Example:

json
[
  {
    "fraudIndicator": "EQUAL_CREDIT_DEBIT",
    "severity": "HIGH",
    "message": "Suspicious equal credit/debit pattern"
  }
]


---

## Multi-bank fraud-indicator mapping

### `GET /multi-bank/fraud-indicators-mapping`

Returns mappings used by the multi-bank journey.

Example:

json
[
  {
    "fraudIndicator": "MULTI_ACCOUNT_CIRCULAR_FLOW",
    "severity": "HIGH"
  }
]


---

# 14. Multi-bank result APIs

Base path:


/income-assessment-service/v1/multi-bank


## Fraud analysis result

### `GET /{incomeAssessmentId}/fraud-analysis-result`

Response:


MultiBankFraudAnalysisResult


The response associates accounts with detected fraud indicators.

---

## Income assessment result

### `GET /{incomeAssessmentId}/income-assessment-result`

Response:


MultiBankIncomeAssessmentResult


The result can contain customer information, account analysis, statement details and derived income information.

### Developer note

These APIs are result retrieval endpoints. For investigating incorrect results, trace backwards from the result model into the repository and processing flow rather than treating the API as the origin of the calculation.

---

# 15. Legacy APIs

## `POST /start-transaction`

Base path:


/income-assessment-service/v1


Request:


IncomeAssessmentRequest


Response:


ResponseEntity<Any>


The controller returns an HTTP redirect (`302 FOUND`) with a `Location` header.

Representative request:

json
{
  "pan": "ABCDE1234F",
  "returnUrl": "https://example.com/return",
  "loanAmount": "50000",
  "loanType": "PERSONAL",
  "loanDuration": "60",
  "correlationData": {
    "applicationReferenceId": "PLA000000000031"
  },
  "employerName": "Example Corp",
  "occupation": "SALARIED"
}


### Developer note

This is a legacy entry point.

For new debugging, first determine whether the caller still uses this endpoint or the newer `initiate-application` / `generate-link` flow.

---

# 16. V2 description configuration

## `GET /v2/get-description-box-config`

Header:


Authorization: <JWT>


Response:


DescriptionBoxConfig


Example:

json
{
  "showDescriptionBox": true,
  "showDisclaimer": true
}


---

# 17. API-to-flow mapping

Use this section when starting from a developer question.

| Question                                              | API / entry point                             | Next trace                                                 |
| ----------------------------------------------------- | --------------------------------------------- | ---------------------------------------------------------- |
| How is an IA application created?                     | `/initiate-application`                       | Controller → facade → versioned service → repository       |
| What happens when the user starts the vendor journey? | `/generate-link` or `/start-process`          | Versioned service → vendor gateway                         |
| Why is a different journey shown?                     | `/validate`                                   | Config/state → validation logic                            |
| Where is current IA status stored?                    | `/status` / `/application/status`             | `IncomeAssessmentApplicationDao`                           |
| Where does Perfios callback go?                       | `/status/perfios`                             | Callback controller → consumer/service → application state |
| Where does Zenith BSA start?                          | `/bsa/initiate`                               | BSA controller → service → `ZenithOrchestratorGateway`     |
| Why was Zenith selected?                              | `/bsa/initiate` / journey APIs                | `ConfigFetcher` → feature toggles → route logic            |
| How are uploaded documents represented?               | `/scan-upload/document-index/{transactionId}` | `DocumentRepository` / document model                      |
| How does ITR processing start?                        | `/itr-statements/start-transaction`           | ITR controller → ITR service                               |
| How does online ITR fall back?                        | `/itr/online/consent-link`                    | FinFort → fallback medium                                  |
| How are multiple statements consolidated?             | `/consolidate-document/*`                     | Consolidation controller → downstream report flow          |
| Where does multi-bank income result come from?        | `/multi-bank/{id}/income-assessment-result`   | Repository → result model                                  |
| Why did an endpoint execute V3?                       | Any version-aware IA API                      | `CommonVersionResolver` → factory → V3                     |

---

# 18. Debugging an API

When an API behaves unexpectedly, use this sequence:


1. Identify exact HTTP method + path
        ↓
2. Identify controller method
        ↓
3. Identify request model
        ↓
4. Identify KeyData / authentication context
        ↓
5. Identify version-routing decision
        ↓
6. Identify facade/service method
        ↓
7. Identify downstream gateway/repository
        ↓
8. Identify application state changes
        ↓
9. Identify asynchronous callback/event if applicable


For example:


GET /generate-link
    ↓
IncomeAssessmentApplicationController
    ↓
KeyData
    ↓
CommonVersionResolver
    ↓
ServiceFacade
    ↓
IncomeAssessmentApplicationServiceV3
    ↓
vendor gateway
    ↓
callback/event
    ↓
IncomeAssessmentApplicationDao


This is often more useful to a developer than the response JSON alone.

---

# 19. Source-of-truth rules

For API contracts, use this priority:

1. **Controller method and annotations**
2. **Kotlin request/response models**
3. **Security/configuration**
4. **Service implementation**
5. **This Markdown document**

The controller establishes the HTTP contract.

The request/response models establish the object structure.

The service implementation establishes important side effects and processing behavior.

This document connects those pieces into a developer-readable contract.

Do not infer required fields solely from sample payloads.

---

# 20. RAG retrieval guidance

API questions are often very specific. Preserve exact technical identifiers because developers are likely to ask using them.

High-value retrieval terms include:

* exact HTTP method
* exact endpoint path
* request class name
* response class name
* controller class name
* service method name
* query parameter names
* header names
* configuration keys
* vendor transaction identifiers
* Kafka callback names

For each important API, prefer chunks that contain:


HTTP method + path
        +
request/response model
        +
purpose
        +
flow continuation
        +
source anchor


This allows a query such as:

> "What does `/generate-link` return?"

to retrieve the contract, while:

> "Where does `/generate-link` go after the controller?"

can retrieve the contract together with `request-flows.md` and Kotlin implementation chunks.

---

# 21. Related knowledge

* `00-overview.md` — service purpose and boundaries
* `01-architecture.md` — runtime component architecture
* `02-request-flows.md` — request execution paths
* `04-business-logic.md` — business decisions and routing logic
* `05-integrations.md` — downstream system contracts and integration behavior
* `06-database.md` — persisted application state
* `07-kafka-events.md` — asynchronous event contracts
* `10-troubleshooting.md` — failure investigation
* `flows/perfios-flow.md` — detailed Perfios flow
* `flows/cap-flow.md` — detailed CAP flow
* `flows/income-assessment-flow.md` — detailed IA journey
