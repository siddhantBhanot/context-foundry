# Integration Code Snippets

## Purpose

This document contains implementation-level code anchors for the major external integrations used by Income Assessment (IA).

Use this document when the question is about:

* Which method calls an external system?
* Which gateway/client is used?
* Which configured endpoint is invoked?
* Is the call encrypted or direct?
* What request/response wrapper is used?
* Which headers or ESB metadata are passed?
* Which identifier is used to correlate the request?
* Where should debugging start when an integration call fails?

This document is intentionally **code-centric**.

For business meaning and end-to-end flow, use:

* `05-integrations.md`
* `flows/perfios-flow.md`
* `flows/zenith-flow.md`
* `flows/cap-flow.md`
* `flows/itr-flow.md`
* `08-error-handling.md`
* `10-troubleshooting.md`

For the surrounding orchestration, use:

* `code/orchestration-snippets.md`

---

# 1. Integration Architecture Pattern

The supplied Perfios and Zenith snippets show a common encrypted ESB integration pattern:


IA Service / Gateway
        |
        v
esbClientV2
        |
        v
postEncryptedV2(...)
        |
        +--> configured URI
        +--> encrypted request body
        +--> ESB headers
        +--> HTTP headers
        |
        v
ESB / Integration Layer
        |
        v
External Vendor / Integration Service


Typical code shape:

kotlin
esbClientV2.postEncryptedV2(
    uri = configuredUrl,
    body = requestBody,
    esbHeaders = ...,
    responseType = ...,
    httpHeaders = ...
)


Important distinction:

> The configured IA endpoint path shown in these snippets is the endpoint exposed to the IA application's ESB client. It should not automatically be interpreted as the final vendor URL.

For direct integrations such as CAP and Document Service, the code instead uses `WebClient` or a `webClientWrapper`.

---

# 2. Perfios Integration

## 2.1 Perfios Integration Map

The supplied snippets cover the following Perfios operations:


Generate Link
     |
     v
Start Transaction
     |
     v
Upload Statement
     |
     v
Complete Transaction
     |
     v
Transaction Status / Callback
     |
     v
Retrieve Insight / Transaction Report


Not every assessment medium necessarily executes every operation.

For example, the Scan/Upload journey has explicit upload and complete-transaction operations, while generate-link is a separate journey-link operation.

---

# 3. Perfios Start Transaction

## 3.1 Entry Point

The service-level entry method is:

kotlin
override fun startTransaction(
    token: String,
    assessmentMedium: String,
    institutionId: String?,
    isBSSelected: Boolean?
): Mono<IncomeAssessmentResponse>


The method receives:

* `token`
* `assessmentMedium`
* `institutionId`
* `isBSSelected`

The supplied code explicitly logs the received `assessmentMedium`.

kotlin
Mono.just(true).logOnSuccess(logger) {
    infoV(version, "Assessment Medium received in request param: $assessmentMedium")
}


The code also contains a TODO indicating that validation of `assessmentMedium` may be relevant:


Do we need assessmentMedium in input - if yes, should we validate its ScanUpload/Statement


Do not treat this TODO as an implemented business rule.

---

## 3.2 Internal Orchestration

The service delegates into:

kotlin
private fun proceedForStartTransaction(
    assessmentApplicationDao: IncomeAssessmentApplicationDao,
    institutionId: String?
): Mono<IncomeAssessmentResponse>


The application DAO is therefore available before the actual Perfios integration call.

The supplied snippet shows logging based on:


incomeAssessmentId
partnerId


The remaining orchestration is not included in the supplied snippet.

---

## 3.3 Perfios ESB Call

The actual Perfios integration is performed by:

kotlin
private fun perfiosStartTransaction(
    perfiosStartTransactionRequest: PerfiosStartTransactionRequest,
    applicationReferenceId: String? = null
): Mono<PerfiosStartTransactionSuccessResponse>


The call is made through:

kotlin
esbClientV2.postEncryptedV2(...)


Implementation shape:

kotlin
return esbClientV2
    .postEncryptedV2(
        uri = bankStatementConfig.startTransactionUrl,
        body = mapPerfiosStartTransactionRequest(perfiosStartTransactionRequest),
        httpHeaders = getHeadersForStartTransaction(applicationReferenceId),
        responseType = PerfiosStartTransactionEsbResponse::class.java,
        esbHeaders = EsbHeadersV2(
            serviceRequestId =
                bankStatementConfig.serviceRequestIdForPerfiosUpload
        )
    )


### Important implementation details

| Item                   | Value                                                   |
| ---------------------- | ------------------------------------------------------- |
| Client                 | `esbClientV2`                                           |
| Method                 | `postEncryptedV2`                                       |
| Endpoint config        | `bankStatementConfig.startTransactionUrl`               |
| Endpoint path          | `/perfios/start-transaction/enc/post-start-transaction` |
| Request                | `PerfiosStartTransactionRequest`                        |
| Request mapping        | `mapPerfiosStartTransactionRequest(...)`                |
| Response wrapper       | `PerfiosStartTransactionEsbResponse`                    |
| Return type            | `PerfiosStartTransactionSuccessResponse`                |
| HTTP headers           | `getHeadersForStartTransaction(applicationReferenceId)` |
| ESB service request ID | `bankStatementConfig.serviceRequestIdForPerfiosUpload`  |

### RAG anchor

**`CODE-INT-PERFIOS-001` — Start Transaction**

Use when retrieving:

* Perfios start transaction implementation
* `/perfios/start-transaction/enc/post-start-transaction`
* `startTransactionUrl`
* `PerfiosStartTransactionRequest`
* `applicationReferenceId` headers
* Perfios encrypted ESB calls

---

## 3.4 Debugging Start Transaction

When Start Transaction fails, inspect in this order:


startTransaction(...)
        |
        v
proceedForStartTransaction(...)
        |
        v
perfiosStartTransaction(...)
        |
        v
mapPerfiosStartTransactionRequest(...)
        |
        v
getHeadersForStartTransaction(applicationReferenceId)
        |
        v
startTransactionUrl
        |
        v
esbClientV2.postEncryptedV2(...)


Check:

1. `assessmentMedium`
2. `institutionId`
3. `isBSSelected`
4. `applicationReferenceId`
5. request mapping
6. `bankStatementConfig.startTransactionUrl`
7. `serviceRequestIdForPerfiosUpload`
8. ESB response type
9. raw ESB/vendor response if parsing fails

### Important invariant

> Successful Start Transaction means the Perfios transaction initiation call succeeded. It does not by itself prove that the user's IA journey completed or that IA reached `INCOME_ASSESSMENT_SUCCESS`.

---

# 4. Perfios Upload Statement

## 4.1 Service Entry Point

The service method is:

kotlin
override fun uploadStatement(
    uploadStatementRequest: UploadStatementRequest,
    productCode: String?,
    shouldUploadToOmniDocs: Boolean,
    incomeAssessmentApplicationDao: IncomeAssessmentApplicationDao?,
    statement: FinacleStatementUploadRequest?,
    fromFinacle: Boolean
): Mono<IncomeAssessmentResponse>


The method receives both IA/business-flow information and the statement payload.

Relevant parameters include:

* `uploadStatementRequest`
* `productCode`
* `shouldUploadToOmniDocs`
* `incomeAssessmentApplicationDao`
* `statement`
* `fromFinacle`

---

## 4.2 Statement Serialization

The supplied code first serializes the statement:

kotlin
val file = FileUtils.saveObjectAsJsonFile(
    statement,
    "statement.json"
)

val fileDetailJson =
    FileUtils.convertFileToFileDetails(file)


The result is then used to construct:

kotlin
PerfiosUploadStatementEsbRequest.from(...)


Therefore, the supplied code proves that the upload request construction involves converting the statement into a file/file-detail representation.

The exact fields passed to `PerfiosUploadStatementEsbRequest.from(...)` are not included in the snippet and should not be inferred.

---

## 4.3 Perfios Upload Gateway

The lower-level upload method is:

kotlin
override fun uploadStatement(
    uploadStatementEsbRequest: PerfiosUploadStatementEsbRequest
): Mono<UploadStatementSuccessResponse>


It calls:

kotlin
esbClientV2.postEncryptedV2(...)


Implementation:

kotlin
return esbClientV2
    .postEncryptedV2(
        uri = bankStatementConfig.uploadTransactionUrl,
        body = uploadStatementEsbRequest,
        httpHeaders = mapOf(
            TARGET to PERFIOS_SCAN_AND_UPLOAD
        ),
        responseType = PerfiosUploadStatementEsbResponse::class.java,
        esbHeaders = EsbHeadersV2(
            serviceRequestId =
                bankStatementConfig.serviceRequestIdForPerfiosUpload
        ),
        logMasker = LogUtils.emptyLogMasker
    )


### Important implementation details

| Item                   | Value                                                 |
| ---------------------- | ----------------------------------------------------- |
| Client                 | `esbClientV2`                                         |
| Method                 | `postEncryptedV2`                                     |
| Endpoint config        | `bankStatementConfig.uploadTransactionUrl`            |
| Endpoint path          | `/perfios/upload-statement/enc/post-upload-statement` |
| Request                | `PerfiosUploadStatementEsbRequest`                    |
| Response wrapper       | `PerfiosUploadStatementEsbResponse`                   |
| Return type            | `UploadStatementSuccessResponse`                      |
| Target header          | `TARGET = PERFIOS_SCAN_AND_UPLOAD`                    |
| ESB service request ID | `serviceRequestIdForPerfiosUpload`                    |
| Log masker             | `LogUtils.emptyLogMasker`                             |

### RAG anchor

**`CODE-INT-PERFIOS-002` — Upload Statement**

Use for questions involving:

* Perfios statement upload
* `/perfios/upload-statement/enc/post-upload-statement`
* `PerfiosUploadStatementEsbRequest`
* `PERFIOS_SCAN_AND_UPLOAD`
* statement JSON/file conversion
* `serviceRequestIdForPerfiosUpload`

---

## 4.4 Debugging Upload Statement

Trace:


uploadStatement(...)
        |
        v
FileUtils.saveObjectAsJsonFile(...)
        |
        v
FileUtils.convertFileToFileDetails(...)
        |
        v
PerfiosUploadStatementEsbRequest.from(...)
        |
        v
uploadStatement(...)
        |
        v
postEncryptedV2(...)
        |
        v
uploadTransactionUrl


Check:

1. `statement` is available and correctly serialized.
2. `fileDetailJson` is generated correctly.
3. `PerfiosUploadStatementEsbRequest.from(...)` receives expected values.
4. `uploadTransactionUrl` resolves to the expected endpoint.
5. `TARGET` is `PERFIOS_SCAN_AND_UPLOAD`.
6. `serviceRequestIdForPerfiosUpload` is correct.
7. ESB encryption/decryption succeeds.
8. Response can be deserialized into `PerfiosUploadStatementEsbResponse`.

### Important invariant

> Uploading a statement to Perfios is a vendor-integration step. It does not itself establish that the Perfios transaction has completed or that IA validation has succeeded.

---

# 5. Perfios Complete Transaction

## 5.1 Service-Level Method

The service method is:

kotlin
override fun completeTransaction(
    perfiosTransactionId: String
): Mono<IncomeAssessmentResponse>


The transaction ID is explicitly logged:

kotlin
val details =
    mapOf("perfiosTransactionId" to perfiosTransactionId)


The service delegates to:

kotlin
bankStatementUploadGatewayFacade.completeTransaction(
    KeyData.forCommonClientTransactionId(perfiosTransactionId),
    perfiosTransactionId
)


The result is mapped into:

kotlin
SuccessCompleteTransactionResponse(response = it)


---

## 5.2 Gateway-Level Method

The lower-level gateway method is:

kotlin
override fun completeTransaction(
    perfiosTransactionId: String
): Mono<PerfiosCompleteTransactionSuccessResponse>


It constructs:

kotlin
val perfiosCompleteRequest =
    PerfiosCompleteTransactionRequest(
        perfiosTransactionId = perfiosTransactionId
    )


Then calls:

kotlin
esbClientV2.postEncryptedV2(...)


with:

kotlin
uri = bankStatementConfig.completeTransactionUrl


and:

kotlin
body =
    mapPerfiosCompleteTransactionRequest(
        perfiosCompleteRequest
    )


### Important implementation details

| Item                   | Value                                                        |
| ---------------------- | ------------------------------------------------------------ |
| Service method         | `completeTransaction(perfiosTransactionId)`                  |
| Gateway                | `bankStatementUploadGatewayFacade`                           |
| KeyData                | `KeyData.forCommonClientTransactionId(perfiosTransactionId)` |
| Request                | `PerfiosCompleteTransactionRequest`                          |
| Client                 | `esbClientV2`                                                |
| Method                 | `postEncryptedV2`                                            |
| Endpoint config        | `bankStatementConfig.completeTransactionUrl`                 |
| Endpoint path          | `/perfios/complete-transaction/enc/complete-transaction`     |
| Target header          | `PERFIOS_SCAN_AND_UPLOAD`                                    |
| Response wrapper       | `PerfiosCompleteTransactionEsbResponse`                      |
| ESB service request ID | `serviceRequestIdForPerfiosUpload`                           |

### RAG anchor

**`CODE-INT-PERFIOS-003` — Complete Transaction**

Use for:

* Perfios complete transaction
* Scan/Upload completion
* `perfiosTransactionId`
* `KeyData.forCommonClientTransactionId(...)`
* `/perfios/complete-transaction/enc/complete-transaction`

---

## 5.3 Debugging Complete Transaction

Trace:


completeTransaction(perfiosTransactionId)
        |
        v
bankStatementUploadGatewayFacade
        |
        v
KeyData.forCommonClientTransactionId(...)
        |
        v
PerfiosCompleteTransactionRequest
        |
        v
mapPerfiosCompleteTransactionRequest(...)
        |
        v
postEncryptedV2(...)
        |
        v
completeTransactionUrl


Check:

1. `perfiosTransactionId`
2. `KeyData` construction
3. request mapping
4. `completeTransactionUrl`
5. `PERFIOS_SCAN_AND_UPLOAD`
6. `serviceRequestIdForPerfiosUpload`
7. ESB response

### Important invariant

> Complete Transaction is still part of the Perfios/vendor processing flow. It should not automatically be interpreted as final IA success.

---

# 6. Perfios Generate Link

## 6.1 ESB Method

The encrypted generate-link implementation is:

kotlin
private fun generateLinkEsbEncryptedRequest(
    perfiosGenerateLinkRequest: PerfiosGenerateLinkRequest
): Mono<GenerateLinkResponse>


It directly calls:

kotlin
esbClientV2.postEncryptedV2(...)


---

## 6.2 Request Construction

The request body is created through:

kotlin
createGenerateLinkRequest(
    perfiosGenerateLinkRequest,
    bankStatementConfig.generateLinkEncryptedPrivateKey
)


This is important because the generate-link operation uses:


generateLinkEncryptedPrivateKey


as part of request construction.

---

## 6.3 ESB Call

kotlin
return esbClientV2.postEncryptedV2(
    uri = bankStatementConfig.generateLinkUrlEnc,
    body = createGenerateLinkRequest(
        perfiosGenerateLinkRequest,
        bankStatementConfig.generateLinkEncryptedPrivateKey
    ),
    esbHeaders = EsbHeadersV2(
        serviceRequestId =
            bankStatementConfig.serviceRequestId
    ),
    responseType =
        ESBGenerateLinkResponseWrapper::class.java,
    httpHeaders = headers()
)


The response is transformed into:

kotlin
GenerateLinkResponse(
    it.generateLinkResponse.responseBody
)


### Important implementation details

| Item                   | Value                                    |
| ---------------------- | ---------------------------------------- |
| Method                 | `generateLinkEsbEncryptedRequest`        |
| Client                 | `esbClientV2`                            |
| Method                 | `postEncryptedV2`                        |
| Endpoint config        | `bankStatementConfig.generateLinkUrlEnc` |
| Endpoint path          | `/perfios/generatelink/enc/generatelink` |
| Request                | `PerfiosGenerateLinkRequest`             |
| Request builder        | `createGenerateLinkRequest(...)`         |
| Encryption key config  | `generateLinkEncryptedPrivateKey`        |
| Response wrapper       | `ESBGenerateLinkResponseWrapper`         |
| Return type            | `GenerateLinkResponse`                   |
| ESB service request ID | `bankStatementConfig.serviceRequestId`   |
| HTTP headers           | `headers()`                              |

### RAG anchor

**`CODE-INT-PERFIOS-004` — Generate Link**

Use for:

* Perfios journey link
* `/perfios/generatelink/enc/generatelink`
* `generateLinkUrlEnc`
* `generateLinkEncryptedPrivateKey`
* `PerfiosGenerateLinkRequest`
* `ESBGenerateLinkResponseWrapper`

---

## 6.4 Debugging Generate Link

Trace:


PerfiosGenerateLinkRequest
        |
        v
createGenerateLinkRequest(...)
        |
        +--> generateLinkEncryptedPrivateKey
        |
        v
postEncryptedV2(...)
        |
        v
generateLinkUrlEnc
        |
        v
ESBGenerateLinkResponseWrapper
        |
        v
GenerateLinkResponse


Check:

1. request construction
2. `generateLinkEncryptedPrivateKey`
3. `generateLinkUrlEnc`
4. `serviceRequestId`
5. `headers()`
6. response wrapper
7. response body extraction

### Important invariant

> Generate-link success means IA successfully obtained a journey link from the integration path. It does not prove that the user opened, completed, or successfully passed the vendor journey.

---

# 7. Perfios Transaction Status

## 7.1 Service-Level Method

The higher-level method is:

kotlin
override fun fetchTransactionLog(
    statementId: String,
    productCode: String?,
    incomeAssessmentApplicationDao: IncomeAssessmentApplicationDao
): Mono<TransactionLog>


Before the transaction-status call, the code resolves configuration.

It loads:

kotlin
configFetcher.allPartnerProductConfigurations()


and selects the configuration matching:

kotlin
it.partnerId ==
    incomeAssessmentApplicationDao.partnerId


and:

kotlin
it.productCode ==
    ProductCode.toBaseProductCodeName(productCode)


The method then combines this with:

kotlin
configFetcher.callbackConfigForProducts(
    incomeAssessmentApplicationDao.assessmentMedium,
    ...
)


The exact remainder of this orchestration is not included in the supplied snippet.

### Important implication

The transaction-status operation is not simply:


statementId -> vendor API


The shown code first resolves partner/product and callback-related configuration.

---

## 7.2 Transaction Status ESB Call

The lower-level method is:

kotlin
private fun makeTransactionStatusRequest(
    statementId: String,
    productCode: String? = null,
    pan: String? = null,
    occupation: OccupationDetails? = null
): Mono<TransactionStatusEsbResponse>


It calls:

kotlin
esbClientV2.postEncryptedV2(...)


with:

kotlin
uri = bankStatementConfig.transactionStatusUrlEnc


and:

kotlin
body =
    createTransactionStatusRequest(
        statementId,
        productCode,
        occupation
    )


The response is mapped to only the transaction status:

kotlin
TransactionStatusEsbResponse(
    TransactionStatusResponse(
        res.getTransactionStatusResponse
            .responseBody.status
    )
)


### Important implementation details

| Item                   | Value                                                    |
| ---------------------- | -------------------------------------------------------- |
| Method                 | `makeTransactionStatusRequest`                           |
| Client                 | `esbClientV2`                                            |
| Method                 | `postEncryptedV2`                                        |
| Endpoint config        | `bankStatementConfig.transactionStatusUrlEnc`            |
| Endpoint path          | `/perfios/transaction-status/enc/get-transaction-status` |
| Request builder        | `createTransactionStatusRequest(...)`                    |
| Inputs                 | `statementId`, `productCode`, `occupation`               |
| PAN                    | passed through `headers(pan)`                            |
| ESB service request ID | `bankStatementConfig.serviceRequestId`                   |
| Response wrapper       | `TransactionStatusEncResponseWrapper`                    |
| Returned field shown   | `responseBody.status`                                    |

### RAG anchor

**`CODE-INT-PERFIOS-005` — Transaction Status**

Use for:

* Perfios transaction status
* `/perfios/transaction-status/enc/get-transaction-status`
* `statementId`
* partner/product configuration lookup
* callback configuration
* `ProductCode.toBaseProductCodeName(...)`
* PAN headers
* `TransactionStatusEncResponseWrapper`

---

## 7.3 Debugging Transaction Status

Trace two separate layers:


fetchTransactionLog(...)
        |
        +--> allPartnerProductConfigurations()
        |       |
        |       +--> partnerId
        |       +--> base productCode
        |
        +--> callbackConfigForProducts(...)
        |
        v
makeTransactionStatusRequest(...)
        |
        v
createTransactionStatusRequest(...)
        |
        v
postEncryptedV2(...)
        |
        v
transactionStatusUrlEnc


Check:

1. `statementId`
2. `incomeAssessmentApplicationDao.partnerId`
3. incoming `productCode`
4. result of `ProductCode.toBaseProductCodeName(productCode)`
5. matching `PartnerProductConfiguration`
6. callback configuration for `assessmentMedium`
7. `occupation`
8. PAN header
9. `transactionStatusUrlEnc`
10. `serviceRequestId`
11. ESB response status

### Important invariant

> Transaction-status tells IA what the vendor transaction status API returned. It is not equivalent to the final IA business status.

---

# 8. Perfios Insight / Transaction Report

## 8.1 Application Correlation Before Report Retrieval

The service method is:

kotlin
override fun fetchJsonPerfiosReport(
    perfiosTransactionId: String,
    clientTransactionId: String,
    occupation: Occupation?,
    isSbbEnableProduct: Boolean?
): Mono<RetrieveReportEsbResponse>


Before retrieving the report, the code finds the IA application using:

kotlin
incomeAssessmentRepository
    .findByCommonClientTransactionId(
        clientTransactionId
            .substringBefore("--")
            .trim()
    )


If no application is found:

kotlin
Mono.error(
    IllegalStateException(
        "Application not found for clientTransactionId=$clientTransactionId"
    )
)


This is a significant correlation rule.

---

## 8.2 Client Transaction ID Normalization

The code explicitly normalizes:

kotlin
clientTransactionId
    .substringBefore("--")
    .trim()


The same normalization appears in:

kotlin
retrieveBankStatementReportV2(...)


through:

kotlin
val txnIdPrefix =
    clientTransactionId
        .substringBefore("--")
        .trim()


Therefore:


clientTransactionId
        |
        v
substringBefore("--")
        |
        v
trim()
        |
        v
repository lookup


### RAG anchor

**`CODE-INT-PERFIOS-006A` — Client Transaction Correlation**

Use when investigating:

* application not found
* report retrieval using `clientTransactionId`
* `clientTransactionId` containing `--`
* `findByCommonClientTransactionId(...)`

### Important invariant

> A report retrieval failure caused by failure to find the IA application is a different failure boundary from a Perfios report API failure.

---

# 9. Perfios Retrieve Transaction Report

## 9.1 Report Retrieval Method

The lower-level method is:

kotlin
fun retrieveBankStatementReportV2(
    perfiosTransactionId: String,
    clientTransactionId: String,
    reportType: String,
    isSbbEnableProduct: Boolean? = false,
    clazz: Class<*>
): Mono<Any>


It first derives:

kotlin
val txnIdPrefix =
    clientTransactionId
        .substringBefore("--")
        .trim()


Then:

kotlin
incomeAssessmentRepository
    .findByCommonClientTransactionId(txnIdPrefix)


The external report API is only called inside the `flatMap` after the application is found.

This establishes the following order:


clientTransactionId
        |
        v
normalize ID
        |
        v
find IA application
        |
        +-- empty --> Illegal/empty application path
        |
        v
build report request
        |
        v
Perfios report API


---

## 9.2 Report Request

The encrypted request body is created through:

kotlin
createTransactionReportRequestWrapper(
    RetrieveReportEsbRequest.EncryptedRequest(
        perfiosTransactionId = perfiosTransactionId,
        transactionId = clientTransactionId,
        reportType = reportType,
        vendorId =
            if (isSbbEnableProduct == true)
                PerfiosGenerateLinkRequest.Request.VENDOR_ID_SBB
            else
                PerfiosGenerateLinkRequest.Request.VENDOR_ID
    )
)


Important request fields:

* `perfiosTransactionId`
* `clientTransactionId`
* `reportType`
* vendor ID

The vendor ID changes when:

kotlin
isSbbEnableProduct == true


### Vendor ID rule shown by the code


isSbbEnableProduct == true
        |
        v
VENDOR_ID_SBB

otherwise
        |
        v
VENDOR_ID


Do not infer the actual string values of these constants unless they are defined elsewhere in the repository.

---

## 9.3 ESB Headers

The report request uses:

kotlin
EsbHeadersV2(
    serviceRequestVersion =
        getServiceVersion(
            if (isSbbEnableProduct == true)
                PerfiosGenerateLinkRequest.Request.VENDOR_ID_SBB
            else
                PerfiosGenerateLinkRequest.Request.VENDOR_ID
        ),
    serviceRequestId =
        transactionReportConfig.serviceRequestId,
    channelId =
        transactionReportConfig.channelId
)


Therefore, report retrieval has three explicitly configured ESB metadata values:

* service request version
* service request ID
* channel ID

The service request version is derived from the selected vendor ID.

---

## 9.4 HTTP Headers

The request also passes:

kotlin
httpHeaders = mapOf(
    BankStatementService.X_AXIS_SERVICE_REQUEST_ID_HEADER_NAME
        to bankStatementConfig.serviceRequestId,

    EsbRequestHeaders.REQUEST_UUID_HEADER_NAME
        to UUID.randomUUID().toString(),

    BankStatementService.TARGET_HEADER_NAME
        to BankStatementService.TARGET_HEADER_VALUE,

    "x-stub-pan"
        to (application.pan ?: "")
)


Important debugging identifiers/headers:


X-Service-Request-ID
Request UUID
Target header
x-stub-pan


The request UUID is generated for each report request.

---

## 9.5 Report Response

The response type is:

kotlin
TransactionReportResponseWrapper::class.java


The returned value is:

kotlin
it.getTransactionReportResponse as Any


The exact report response fields beyond this wrapper are not included in the supplied snippet.

---

## 9.6 Endpoint

Configured endpoint:


/perfios/retrieve-transaction-report/enc/get-transaction-report


### Important implementation details

| Item                   | Value                                                             |
| ---------------------- | ----------------------------------------------------------------- |
| Method                 | `retrieveBankStatementReportV2`                                   |
| Client                 | `esbClientV2`                                                     |
| Method                 | `postEncryptedV2`                                                 |
| Endpoint               | `/perfios/retrieve-transaction-report/enc/get-transaction-report` |
| Request                | `RetrieveReportEsbRequest.EncryptedRequest`                       |
| Request wrapper        | `createTransactionReportRequestWrapper(...)`                      |
| Response               | `TransactionReportResponseWrapper`                                |
| Transaction ID         | `perfiosTransactionId`                                            |
| Client transaction ID  | `clientTransactionId`                                             |
| Report type            | `reportType`                                                      |
| Vendor selection       | `isSbbEnableProduct`                                              |
| ESB service version    | derived using `getServiceVersion(...)`                            |
| ESB service request ID | `transactionReportConfig.serviceRequestId`                        |
| ESB channel ID         | `transactionReportConfig.channelId`                               |
| Request UUID           | generated with `UUID.randomUUID()`                                |
| PAN header             | `x-stub-pan` from application PAN                                 |

### RAG anchor

**`CODE-INT-PERFIOS-006B` — Retrieve Transaction Report**

Use for:

* Perfios insight report retrieval
* `/perfios/retrieve-transaction-report/enc/get-transaction-report`
* `RetrieveReportEsbRequest`
* `reportType`
* SBB vendor selection
* `transactionReportConfig`
* application lookup before vendor call

---

# 10. Perfios Integration Flow — Code-Level View

For a typical Scan/Upload path, the supplied snippets establish the following possible sequence:


Generate Link
    |
    | /perfios/generatelink/enc/generatelink
    v
User/Vendor Journey
    |
    v
Start Transaction
    |
    | /perfios/start-transaction/enc/post-start-transaction
    v
Perfios Transaction
    |
    v
Upload Statement
    |
    | /perfios/upload-statement/enc/post-upload-statement
    v
Complete Transaction
    |
    | /perfios/complete-transaction/enc/complete-transaction
    v
Perfios Processing
    |
    +----------------------+
    |                      |
    v                      v
Callback              Transaction Status
    |                      |
    +----------+-----------+
               |
               v
Retrieve Transaction Report
               |
               | /perfios/retrieve-transaction-report/enc/get-transaction-report
               v
Business Validation
               |
               v
IA State / Events / Downstream


This diagram represents the integration stages evidenced by the supplied snippets. It should **not** be interpreted as proof that every assessment journey executes every stage in exactly this order.

---

# 11. Zenith Integration

## 11.1 Zenith Integration Map

The supplied Zenith snippets cover:


Journey Link
     |
     v
External AA / Zenith Journey
     |
     v
Journey Transaction Status
     |
     v
Analytics / Insight Report


Zenith calls shown here also use the encrypted ESB client:

kotlin
esbClientV2.postEncryptedV2(...)


---

# 12. Zenith Journey Link

## 12.1 Gateway Entry Point

The gateway method is:

kotlin
fun zenithOrchJourneyLinkESBRequest(
    clientId: String,
    zenithOrchGetJourneyLinkRequest:
        ZenithOrchGetJourneyLinkRequest
): Mono<JourneyLinkResponse>


The method first resolves ESB headers:

kotlin
zenithEsbConfigFactory
    .resolveEsbHeaders()


and then delegates to:

kotlin
zenithOrchEncryptedJorneyLinkESBRequest(
    zenithOrchGetJourneyLinkRequest,
    esbHeaders
)


---

## 12.2 Encrypted Journey-Link Request

The lower-level method is:

kotlin
private fun zenithOrchEncryptedJorneyLinkESBRequest(
    zenithOrchGetJourneyLinkRequest:
        ZenithOrchGetJourneyLinkRequest,
    esbHeaders:
        com.contextfoundry.lending.esbclient.model.v2.EsbHeadersV2
): Mono<JourneyLinkResponse>


It calls:

kotlin
esbClientV2.postEncryptedV2(...)


with:

kotlin
uri =
    zenithOrchestratorConfig.journeyLinkUrlEnc


and:

kotlin
body =
    createJourneyLinkRequest(
        zenithOrchGetJourneyLinkRequest
    )


The response is mapped from:

kotlin
ESBJourneyLinkResponseWrapper


to:

kotlin
JourneyLinkResponse(
    it.getJourneyLinkResponse.responseBody
)


---

## 12.3 Endpoint


/jarvis/aa-journey-link/enc/get-journey-link


### Important implementation details

| Item               | Value                                          |
| ------------------ | ---------------------------------------------- |
| Entry method       | `zenithOrchJourneyLinkESBRequest`              |
| Header resolution  | `zenithEsbConfigFactory.resolveEsbHeaders()`   |
| Lower-level method | `zenithOrchEncryptedJorneyLinkESBRequest`      |
| Client             | `esbClientV2`                                  |
| Method             | `postEncryptedV2`                              |
| Endpoint config    | `zenithOrchestratorConfig.journeyLinkUrlEnc`   |
| Endpoint           | `/jarvis/aa-journey-link/enc/get-journey-link` |
| Request            | `ZenithOrchGetJourneyLinkRequest`              |
| Request builder    | `createJourneyLinkRequest(...)`                |
| Response wrapper   | `ESBJourneyLinkResponseWrapper`                |
| Return type        | `JourneyLinkResponse`                          |
| HTTP headers       | `buildHttpHeaders()`                           |
| ESB headers        | resolved through `zenithEsbConfigFactory`      |

### RAG anchor

**`CODE-INT-ZENITH-001` — Journey Link**

Use for:

* Zenith journey link
* `/jarvis/aa-journey-link/enc/get-journey-link`
* `journeyLinkUrlEnc`
* `ZenithOrchGetJourneyLinkRequest`
* `zenithEsbConfigFactory`
* Zenith encrypted ESB calls

---

# 13. Zenith Transaction Status

## 13.1 IA Gateway Delegation

The IA-facing method is:

kotlin
override fun fetchZenithTransactionLog(
    vendorTransactionId: String,
    productCode: String?,
    incomeAssessmentApplicationDao:
        IncomeAssessmentApplicationDao
): Mono<ZenithTransactionStatusResponseBody>


It delegates to:

kotlin
zenithOrchestratorGateway.fetchTransactionLog(
    vendorTransactionId,
    productCode,
    incomeAssessmentApplicationDao
)


The supplied snippet does not show the complete `fetchTransactionLog(...)` implementation.

---

## 13.2 Zenith ESB Transaction Status

The lower-level method is:

kotlin
fun fetchZenithTransactionStatus(
    serviceRequestId: String,
    pan: String? = ""
): Mono<ZenithTransactionStatusResponseBody>


It creates:

kotlin
val requestBody =
    GetJourneyTransactionStatusRequest(
        serviceRequestId = serviceRequestId
    )


It then resolves ESB headers:

kotlin
zenithEsbConfigFactory.resolveEsbHeaders()


and calls:

kotlin
esbClientV2.postEncryptedV2(...)


with:

kotlin
uri =
    zenithOrchestratorConfig.transactionStatusUrlEnc


The response is mapped to:

kotlin
apiResponse
    .getJourneyTransactionStatusResponse
    .responseBody


---

## 13.3 Endpoint


/jarvis/aa-journey-status/enc/get-journey-transaction-status


### Important implementation details

| Item            | Value                                                          |
| --------------- | -------------------------------------------------------------- |
| Method          | `fetchZenithTransactionStatus`                                 |
| Client          | `esbClientV2`                                                  |
| Method          | `postEncryptedV2`                                              |
| Endpoint config | `zenithOrchestratorConfig.transactionStatusUrlEnc`             |
| Endpoint        | `/jarvis/aa-journey-status/enc/get-journey-transaction-status` |
| Request         | `GetJourneyTransactionStatusRequest`                           |
| Request field   | `serviceRequestId`                                             |
| Response        | `ZenithTransactionStatusBody`                                  |
| Returned value  | `getJourneyTransactionStatusResponse.responseBody`             |
| ESB headers     | `zenithEsbConfigFactory.resolveEsbHeaders()`                   |
| HTTP headers    | `buildHttpHeaders("application/json", true)`                   |
| PAN             | supplied to method as `pan`                                    |

### RAG anchor

**`CODE-INT-ZENITH-002` — Transaction Status**

Use for:

* Zenith transaction status
* `/jarvis/aa-journey-status/enc/get-journey-transaction-status`
* `GetJourneyTransactionStatusRequest`
* `serviceRequestId`
* `fetchZenithTransactionLog`
* `ZenithTransactionStatusResponseBody`

---

# 14. Zenith Insight / Analytics Report

## 14.1 IA-Level Delegation

The IA service method is:

kotlin
private fun fetchStatementsOrReportsViaZenith(
    perfiosTransactionId: String,
    serviceRequestId: String?,
    reportType: ZenithReportType,
    contentTypeAccepted: String
): Mono<ByteArray>


Despite the parameter name:


perfiosTransactionId


the supplied method delegates to the Zenith gateway:

kotlin
zenithOrchestratorGateway
    .retrieveReportFromEsbViaZenith(
        serviceRequestId,
        reportType,
        contentTypeAccepted
    )


The transaction ID is shown in logging, but is not passed to the gateway in the supplied call.

Do not infer that `perfiosTransactionId` is sent to Zenith from this snippet.

---

## 14.2 Zenith Analytics Report Gateway

The lower-level method is:

kotlin
fun retrieveReportFromEsbViaZenith(
    serviceRequestId: String?,
    reportType: ZenithReportType,
    contentTypeAccepted: String
): Mono<ByteArray>


The request body is built using:

kotlin
buildEncryptedRequestBodyForAnalyticsReport(
    serviceRequestId = serviceRequestId,
    reportType = reportType
)


ESB headers are resolved dynamically:

kotlin
zenithEsbConfigFactory.resolveEsbHeaders()


The external call is:

kotlin
esbClientV2.postEncryptedV2(...)


---

## 14.3 Response Processing

The response type is:

kotlin
ESBAnalyticsReportResponseWrapper::class.java


The analytics data is extracted as a Base64 string:

kotlin
val base64String =
    it.getAnalyticsReportResponse
        .responseBody
        .analyticsData
        .byteArray


It is then decoded:

kotlin
Base64.getDecoder().decode(base64String)


Therefore, the supplied code proves:


Zenith analytics response
        |
        v
analyticsData.byteArray
        |
        v
Base64 string
        |
        v
Base64 decoder
        |
        v
ByteArray


---

## 14.4 Endpoint


/jarvis/aa-financial-analytics-report/enc/get-analytics-report


### Important implementation details

| Item             | Value                                                            |
| ---------------- | ---------------------------------------------------------------- |
| IA method        | `fetchStatementsOrReportsViaZenith`                              |
| Gateway          | `zenithOrchestratorGateway`                                      |
| Gateway method   | `retrieveReportFromEsbViaZenith`                                 |
| Client           | `esbClientV2`                                                    |
| Method           | `postEncryptedV2`                                                |
| Endpoint config  | `zenithOrchestratorConfig.analyticsReportUrlEnc`                 |
| Endpoint         | `/jarvis/aa-financial-analytics-report/enc/get-analytics-report` |
| Request builder  | `buildEncryptedRequestBodyForAnalyticsReport(...)`               |
| Request fields   | `serviceRequestId`, `reportType`                                 |
| Response wrapper | `ESBAnalyticsReportResponseWrapper`                              |
| Output           | `ByteArray`                                                      |
| Decode           | Base64                                                           |
| HTTP headers     | `buildHttpHeaders(contentTypeAccepted, true)`                    |
| ESB headers      | resolved through `zenithEsbConfigFactory`                        |

### RAG anchor

**`CODE-INT-ZENITH-003` — Analytics Report**

Use for:

* Zenith insight report
* Zenith analytics report
* `/jarvis/aa-financial-analytics-report/enc/get-analytics-report`
* `retrieveReportFromEsbViaZenith`
* `ZenithReportType`
* Base64 analytics response
* `serviceRequestId`

---

# 15. Document Service / OmniDocs Integration

Unlike Perfios and Zenith, the supplied Document Service snippets use a direct `webClientWrapper`.

---

# 16. Upload Statement to OmniDocs

## 16.1 Method

The method is:

kotlin
fun uploadStatementInOmniDocsV4(
    uploadDocumentRequest: DocumentListWithReferenceIds
): Mono<UploadedDocumentResponse>


The call is:

kotlin
webClientWrapper.post(
    serviceName = documentService,
    pathIdentifier = "upload-omni-document-v4",
    body = uploadDocumentRequest,
    returnType = UploadedDocumentResponse::class.java,
    headers = mapOf(
        "Authorization" to documentServiceToken
    )
)


The code logs failures against:

kotlin
uploadDocumentRequest.referenceIds


---

## 16.2 Endpoint Configuration

yaml
upload-omni-document-v4:
  name: Document
  path: /document-service/v4/documents
  method: POST


### Important implementation details

| Item            | Value                            |
| --------------- | -------------------------------- |
| Method          | `uploadStatementInOmniDocsV4`    |
| Client          | `webClientWrapper`               |
| Service         | `documentService`                |
| Path identifier | `upload-omni-document-v4`        |
| HTTP method     | POST                             |
| Endpoint        | `/document-service/v4/documents` |
| Request         | `DocumentListWithReferenceIds`   |
| Response        | `UploadedDocumentResponse`       |
| Authorization   | `documentServiceToken`           |

### RAG anchor

**`CODE-INT-DOC-001` — OmniDocs V4 Upload**

Use for:

* OmniDocs upload
* `/document-service/v4/documents`
* `uploadStatementInOmniDocsV4`
* `DocumentListWithReferenceIds`
* document-service token
* `upload-omni-document-v4`

---

## 16.3 Debugging OmniDocs Upload

Trace:


uploadStatementInOmniDocsV4(...)
        |
        v
webClientWrapper.post(...)
        |
        +--> serviceName = documentService
        +--> pathIdentifier = upload-omni-document-v4
        +--> Authorization = documentServiceToken
        |
        v
POST /document-service/v4/documents


Check:

1. `uploadDocumentRequest`
2. `referenceIds`
3. `documentService`
4. `documentServiceToken`
5. path identifier
6. resolved path
7. HTTP method
8. response deserialization

The supplied code also shows an `onErrorResume` after logging, but the exact recovery behavior is truncated and should not be inferred.

---

# 17. Upload Statement to Document DB

## 17.1 Method

The method is:

kotlin
fun saveDocument(
    statementId: String,
    documentType: String,
    data: ByteArray
): Mono<DocumentResponse>


It constructs:

kotlin
DocumentDetailsWithReferenceIds(
    mapOf(
        IAS_DOCUMENT_IDENTIFIER_KEY
            to statementId
                .substringBefore("--")
                .trim()
    ),
    documentType,
    Base64.getEncoder().encodeToString(data)
)


Three important transformations occur:

1. `statementId` is normalized using `substringBefore("--").trim()`.
2. The normalized ID becomes the IA document reference.
3. The binary `data` is Base64 encoded.

---

## 17.2 Document Service Call

The method then calls:

kotlin
webClientWrapper.put(
    serviceName = documentService,
    pathIdentifier = "put-document",
    body = documentDetails,
    returnType = DocumentResponse::class.java,
    headers = mapOf(
        "Authorization" to documentServiceToken
    )
)


### Endpoint Configuration

yaml
put-document:
  name: Document
  path: /document-service/v2/document
  method: PUT


### Important implementation details

| Item            | Value                             |
| --------------- | --------------------------------- |
| Method          | `saveDocument`                    |
| Client          | `webClientWrapper`                |
| HTTP method     | PUT                               |
| Path identifier | `put-document`                    |
| Endpoint        | `/document-service/v2/document`   |
| Request         | `DocumentDetailsWithReferenceIds` |
| Response        | `DocumentResponse`                |
| Reference ID    | normalized `statementId`          |
| Document data   | Base64 encoded                    |
| Authorization   | `documentServiceToken`            |

### RAG anchor

**`CODE-INT-DOC-002` — Document DB Upload**

Use for:

* `saveDocument`
* `/document-service/v2/document`
* document persistence
* `statementId` normalization
* `IAS_DOCUMENT_IDENTIFIER_KEY`
* Base64 document data

---

## 17.3 OmniDocs vs Document DB

Do not merge these two operations during retrieval.

They are separate integration calls:


Statement
   |
   +----------------------+
   |                      |
   v                      v
OmniDocs V4           Document Service V2
POST                  PUT
/v4/documents         /v2/document


The code uses different methods, endpoints, request models, and response models.

When debugging document failures, first determine **which document boundary failed**.

---

# 18. CAP Integration

CAP is an external upstream platform that can initiate an IA journey and can receive IA status synchronization.

The snippets here specifically show the **IA → CAP status synchronization** implementation.

For CAP initiation semantics, use:

* `flows/cap-flow.md`
* `05-integrations.md`
* `code/orchestration-snippets.md`

---

# 19. CAP Sync Service Architecture

The facade is:

kotlin
@Service
class CapSyncServiceFacade(
    versionResolver: CommonVersionResolver,
    factory: CapSyncServiceFactory
) : ServiceFacade<CapSyncServiceRevamp>(versionResolver, factory)


The facade exposes:

kotlin
fun <T : Any> syncCapConsentStatus(
    keyData: KeyData,
    incomeAssessmentApplication:
        IncomeAssessmentApplicationDao,
    result: T
): Mono<T> =
    executeWithVersion(keyData) {
        it.syncCapConsentStatus(
            incomeAssessmentApplication,
            result
        )
    }


This means CAP sync participates in the same version-resolution/facade pattern used elsewhere in IA.

---

# 20. CAP Sync Service Contract

The interface defines:

kotlin
interface CapSyncServiceRevamp : RevampService {

    fun callCapServiceUpdateStatus(
        capRequest: CapConsentStatusUpdateRequest
    ): Mono<CapSyncApiResponse>

    fun getEventStatusByStatus(
        status: IncomeAssessmentApplicationStatus
    ): EventStatus?

    fun <T : Any> syncCapConsentStatus(
        incomeAssessmentApplication:
            IncomeAssessmentApplicationDao,
        result: T
    ): Mono<T>
}


Three responsibilities are visible:

1. Build/call CAP status update.
2. Map IA status to CAP `EventStatus`.
3. Synchronize CAP status while preserving the original result type.

---

# 21. CAP Direct PATCH Call

The supplied direct implementation is:

kotlin
private fun callCapServiceUpdateStatusDirect(
    capRequest: CapConsentStatusUpdateRequest
): Mono<CapSyncApiResponse>


It first checks:

kotlin
if (
    capRequest.capRefId.isNullOrBlank() ||
    capRequest.status == null
)


If either value is missing, it returns:

kotlin
CapSyncApiResponse(
    CapSyncApiResponseData(
        capRefId = capRequest.capRefId
    )
)


Otherwise it performs a direct WebClient PATCH request:

kotlin
webClient
    .method(HttpMethod.PATCH)
    .uri("$capBaseUrl$capUpdateStatusUrl")
    .header(
        HttpHeaders.AUTHORIZATION,
        "Bearer $authToken"
    )
    .bodyValue(capRequest)
    .retrieve()
    .bodyToMono(
        CapSyncApiResponse::class.java
    )


### Endpoint

The supplied endpoint path is:


/internal/cap/api/initiate/event/update/status


The complete URL is constructed from:


capBaseUrl + capUpdateStatusUrl


### Important implementation details

| Item                    | Value                                            |
| ----------------------- | ------------------------------------------------ |
| Client                  | Direct `WebClient`                               |
| HTTP method             | PATCH                                            |
| Endpoint path           | `/internal/cap/api/initiate/event/update/status` |
| Request                 | `CapConsentStatusUpdateRequest`                  |
| Authorization           | `Bearer <authToken>`                             |
| Response                | `CapSyncApiResponse`                             |
| Required request values | `capRefId`, `status`                             |

### RAG anchor

**`CODE-INT-CAP-001` — CAP Update Status**

Use for:

* CAP status synchronization
* CAP PATCH request
* `/internal/cap/api/initiate/event/update/status`
* `CapConsentStatusUpdateRequest`
* CAP authorization
* CAP response handling

---

# 22. CAP Sync Feature Flag

The implementation evaluates:

kotlin
val capSyncEnabled =
    (
        incomeAssessmentApplication
            .config
            ?.get("capSyncEnabled") as? Boolean
    ) ?: false


The value is logged:


CAP sync feature flag evaluated to $capSyncEnabled


The relevant configuration key is:


capSyncEnabled


The supplied snippet does not include the complete remainder of `syncCapConsentStatus(...)`, so do not assume the exact `if` branch or fallback behavior from this snippet alone.

### RAG anchor

**`CODE-INT-CAP-002` — CAP Sync Toggle**

Use for:

* `capSyncEnabled`
* CAP sync enablement
* CAP configuration debugging
* why CAP status synchronization did/did not execute

---

# 23. CAP Status Mapping

The service contract exposes:

kotlin
fun getEventStatusByStatus(
    status: IncomeAssessmentApplicationStatus
): EventStatus?


This is important because IA status and CAP event status are separate concepts.

The flow is:


IA IncomeAssessmentApplicationStatus
                |
                v
getEventStatusByStatus(...)
                |
                v
CAP EventStatus
                |
                v
CapConsentStatusUpdateRequest
                |
                v
CAP PATCH API


For exact status mappings, use the implementation of:

kotlin
getEventStatusByStatus(...)


rather than inferring mappings from the interface alone.

---

# 24. FinFort Integration

The supplied snippets show the online ITR integration with FinFort.

The integration is exposed under:


/income-assessment-service/v1/itr/online


and is conditionally enabled using:

kotlin
@ConditionalOnProperty(
    prefix = "platform.finfort.feature",
    name = ["enabled"],
    havingValue = "true",
    matchIfMissing = false
)


Therefore:


platform.finfort.feature.enabled = true


is required for the shown `FinFortController` to be active.

---

# 25. FinFort Controller

The controller is:

kotlin
@RestController
@RequestMapping(
    "/income-assessment-service/v1/itr/online"
)
@ConditionalOnProperty(
    prefix = "platform.finfort.feature",
    name = ["enabled"],
    havingValue = "true",
    matchIfMissing = false
)
class FinFortController(...)


Dependencies shown include:

* `FinFortServiceFacade`
* `ConfigFetcher`
* `AuthServiceClient`
* `CommonVersionResolver`

This places FinFort behind its own service facade and configuration/versioning infrastructure.

### RAG anchor

**`CODE-INT-FINFORT-001` — FinFort Controller**

Use for:

* online ITR FinFort API
* `/income-assessment-service/v1/itr/online`
* `platform.finfort.feature.enabled`
* `FinFortServiceFacade`

---

# 26. FinFort Consent Link / Create Order

## 26.1 Consent-Link Endpoint

The controller exposes:

kotlin
@PostMapping("/consent-link")
fun getConsentLink(
    @RequestHeader(
        name = HttpHeaders.AUTHORIZATION
    )
    authorizationJwtToken: String
): Mono<ResponseEntity<Any>>


The JWT is first validated through:

kotlin
authServiceClient.validateAndFetchClaims(
    authorizationJwtToken
)


This establishes:


HTTP Authorization JWT
        |
        v
AuthServiceClient
        |
        v
validated claims
        |
        v
FinFort flow


---

## 26.2 Create Order

The service constructs an internal transaction ID:

kotlin
val internalTransactionId =
    ItrStatementIdGenerator.generate()


It then builds the FinFort create-order request:

kotlin
buildOrderRequest(application)


The application is converted to:

kotlin
KeyData.forPartnerConfiguration(
    applicationDao = application
)


Then the FinFort authentication flow obtains a decoded token:

kotlin
finFortAuthServiceFacade
    .decodedToken(
        keyData,
        application
    )


Finally, the client executes:

kotlin
client.execute(
    requestBody,
    application.applicationReferenceId!!,
    CreateOrderResponse::class.java,
    encodedToken,
    application.customerId
)


### Important identifiers

The create-order call uses:

* `application.applicationReferenceId`
* `application.customerId`
* FinFort encoded/decoded authentication token
* internally generated ITR statement transaction ID

### RAG anchor

**`CODE-INT-FINFORT-002` — Create Order**

Use for:

* FinFort consent/order creation
* `ItrStatementIdGenerator`
* `buildOrderRequest`
* `applicationReferenceId`
* `customerId`
* FinFort authentication

---

# 27. FinFort Common Client Execution

The common client method is:

kotlin
fun <ReqParam, ResData> execute(
    baseRequest: BaseRequest<ReqParam>,
    applicationRefId: String,
    dataType: Class<ResData>,
    token: String? = null,
    customerId: String?
): Mono<BaseResponse<*>>


It first selects a WebClient:

kotlin
val client = getAppropriateWebClient()


and creates a Jackson mapper:

kotlin
val mapper = jacksonObjectMapper()


---

## 27.1 Environment-Specific Encryption

The code defines:

kotlin
val isProd =
    setOf(
        "prod",
        "sandbox",
        "sandboxnew",
        "uat"
    ).any {
        it.equals(
            activeProfile.trim(),
            ignoreCase = true
        )
    }


Therefore the shown behavior is:


prod / sandbox / sandboxnew / uat
        |
        v
encrypt request body

other environments
        |
        v
send BaseRequest as plain JSON


For the encrypted environments:

kotlin
val requestJson =
    mapper.writeValueAsString(baseRequest)

val encryptedPayload =
    aes256EncryptionUtility.encrypt(requestJson)
        ?: return Mono.error(
            IllegalStateException(
                "Failed to encrypt FinFort request payload ..."
            )
        )


For non-encrypted environments:

kotlin
baseRequest


is used directly.

### RAG anchor

**`CODE-INT-FINFORT-003` — FinFort Client Encryption**

Use for:

* FinFort request encryption
* environment-specific behavior
* `aes256EncryptionUtility`
* prod/sandbox/UAT behavior
* lower-environment / Mountebank behavior

### Important invariant

> FinFort request serialization/encryption behavior is environment-dependent in the supplied implementation.

---

# 28. FinFort Transaction Status

## 28.1 Application Lookup

The method is:

kotlin
override fun checkOrderStatus(
    applicationReferenceId: String
): Mono<CheckOrderStatusResponse>


It first finds the IA application:

kotlin
incomeAssessmentRepository
    .findByApplicationReferenceId(
        applicationReferenceId
    )


Only after the application is found does it build the FinFort request.

---

## 28.2 Request Construction

The request is:

kotlin
BaseRequest(
    CHECK_ORDER_STATUS,
    CheckOrderStatusRequest(
        it.finFortDetails?.finFortOrderId ?: ""
    )
)


Therefore the FinFort order ID comes from:


application.finFortDetails.finFortOrderId


If absent, the supplied code uses an empty string.

---

## 28.3 Client Execution

The client receives:

kotlin
client.execute(
    baseRequest = requestBody,
    applicationRefId = applicationReferenceId,
    dataType = CheckOrderStatusResponse::class.java,
    token =
        it.finFortDetails?.finFortAuthToken?.let {
            encoded ->
            String(
                Base64.getDecoder()
                    .decode(encoded)
            )
        },
    customerId = it.customerId
)


The FinFort auth token is therefore Base64-decoded before being passed to `client.execute(...)`.

The result is then cast:

kotlin
val response =
    it.data as CheckOrderStatusResponse


and returned.

### RAG anchor

**`CODE-INT-FINFORT-004` — Check Order Status**

Use for:

* FinFort transaction status
* `checkOrderStatus`
* `finFortOrderId`
* `finFortAuthToken`
* application lookup
* Base64 token decoding

---

# 29. FinFort Get File Details

## 29.1 Application Lookup

The method is:

kotlin
override fun getFileDetails(
    applicationRefId: String
): Mono<BaseResponse<*>>


It first resolves the IA application:

kotlin
incomeAssessmentRepository
    .findByApplicationReferenceId(
        applicationRefId
    )


---

## 29.2 Request

It constructs:

kotlin
BaseRequest(
    GET_FILE_DETAILS_REQUEST,
    GetFileDetailRequest(
        it.finFortDetails?.finFortOrderId ?: "",
        false
    )
)


Therefore the request contains:

* FinFort order ID
* boolean `false`

The supplied snippet does not identify the semantic meaning of that boolean.

---

## 29.3 Client Call

It invokes:

kotlin
client.execute(
    baseRequest = getFileDetailsRequestBody,
    applicationRefId = applicationRefId,
    dataType = GetFileDetailsResponse::class.java,
    token =
        it.finFortDetails?.finFortAuthToken?.let {
            encoded ->
            String(
                Base64.getDecoder()
                    .decode(encoded)
            )
        },
    customerId = it.customerId
)


### RAG anchor

**`CODE-INT-FINFORT-005` — Get File Details**

Use for:

* FinFort file details
* `getFileDetails`
* `finFortOrderId`
* FinFort auth token
* file metadata retrieval

---

# 30. FinFort Download Files

The callback-related file retrieval method is:

kotlin
private fun fetchFileFromS3(
    url: String,
    fileName: String,
    customerId: String? = null
): Mono<ByteArray>


It delegates to:

kotlin
client.downloadFiles(
    url,
    fileName,
    customerId
)


The method logs:


filename
url


and returns the downloaded bytes.

### RAG anchor

**`CODE-INT-FINFORT-006` — Download FinFort Files**

Use for:

* FinFort callback file download
* S3 file retrieval
* `downloadFiles`
* file URL
* file name
* customer ID

### Important observation

The log explicitly says this method can be invoked from:


CALLBACK_NOT_RECEIVED consumer


and that the operation is being marked for retry.

This is evidence that file retrieval participates in a retry/recovery path, although the exact retry mechanism is outside the supplied snippet.

---

# 31. Integration Route Summary

| Integration      | Operation            | Main Method                               | Client             | Endpoint                                                          |
| ---------------- | -------------------- | ----------------------------------------- | ------------------ | ----------------------------------------------------------------- |
| Perfios          | Start transaction    | `perfiosStartTransaction`                 | `esbClientV2`      | `/perfios/start-transaction/enc/post-start-transaction`           |
| Perfios          | Upload statement     | `uploadStatement`                         | `esbClientV2`      | `/perfios/upload-statement/enc/post-upload-statement`             |
| Perfios          | Complete transaction | `completeTransaction`                     | `esbClientV2`      | `/perfios/complete-transaction/enc/complete-transaction`          |
| Perfios          | Generate link        | `generateLinkEsbEncryptedRequest`         | `esbClientV2`      | `/perfios/generatelink/enc/generatelink`                          |
| Perfios          | Transaction status   | `makeTransactionStatusRequest`            | `esbClientV2`      | `/perfios/transaction-status/enc/get-transaction-status`          |
| Perfios          | Insight/report       | `retrieveBankStatementReportV2`           | `esbClientV2`      | `/perfios/retrieve-transaction-report/enc/get-transaction-report` |
| Zenith           | Journey link         | `zenithOrchEncryptedJorneyLinkESBRequest` | `esbClientV2`      | `/jarvis/aa-journey-link/enc/get-journey-link`                    |
| Zenith           | Transaction status   | `fetchZenithTransactionStatus`            | `esbClientV2`      | `/jarvis/aa-journey-status/enc/get-journey-transaction-status`    |
| Zenith           | Analytics report     | `retrieveReportFromEsbViaZenith`          | `esbClientV2`      | `/jarvis/aa-financial-analytics-report/enc/get-analytics-report`  |
| Document Service | OmniDocs upload      | `uploadStatementInOmniDocsV4`             | `webClientWrapper` | `/document-service/v4/documents`                                  |
| Document Service | Document upload      | `saveDocument`                            | `webClientWrapper` | `/document-service/v2/document`                                   |
| CAP              | Status sync          | `callCapServiceUpdateStatusDirect`        | `WebClient`        | `/internal/cap/api/initiate/event/update/status`                  |
| FinFort          | Consent/order        | `createOrder`                             | FinFort client     | Client abstraction                                                |
| FinFort          | Order status         | `checkOrderStatus`                        | FinFort client     | Client abstraction                                                |
| FinFort          | File details         | `getFileDetails`                          | FinFort client     | Client abstraction                                                |
| FinFort          | File download        | `fetchFileFromS3`                         | FinFort client     | S3 URL supplied at runtime                                        |

---

# 32. Client Pattern Classification

The snippets establish three major integration styles.

## Pattern A — Encrypted ESB

Used by:

* Perfios
* Zenith

Typical call:

kotlin
esbClientV2.postEncryptedV2(...)


Debugging focus:


request mapping
    ↓
encryption
    ↓
ESB headers
    ↓
HTTP headers
    ↓
configured URI
    ↓
ESB response wrapper
    ↓
response mapping


---

## Pattern B — Direct WebClient

Used by:

* CAP
* Document Service

Typical call:

kotlin
webClient...


or:

kotlin
webClientWrapper...


Debugging focus:


base URL
    ↓
path
    ↓
HTTP method
    ↓
headers/auth
    ↓
request body
    ↓
response status
    ↓
response parsing


---

## Pattern C — Domain Client Abstraction

Used by:

* FinFort

Typical call:

kotlin
client.execute(...)


or:

kotlin
client.downloadFiles(...)


Debugging requires tracing:


IA service
    ↓
FinFort client
    ↓
getAppropriateWebClient()
    ↓
environment handling
    ↓
encryption/plain JSON
    ↓
actual HTTP request


---

# 33. High-Value Correlation Identifiers

When debugging an integration, identify the identifier used by that integration before looking at logs.

| Identifier                  | Important for                                                             |
| --------------------------- | ------------------------------------------------------------------------- |
| `incomeAssessmentId`        | IA application/workflow                                                   |
| `applicationReferenceId`    | IA ↔ application-level correlation; Perfios start headers; FinFort lookup |
| `commonClientTransactionId` | IA/vendor transaction correlation                                         |
| `clientTransactionId`       | Perfios report/correlation                                                |
| `perfiosTransactionId`      | Perfios transaction operations                                            |
| `statementId`               | Perfios transaction-status/document correlation                           |
| `vendorTransactionId`       | Zenith journey transaction                                                |
| `serviceRequestId`          | ESB/vendor request correlation                                            |
| `partnerId`                 | Partner configuration resolution                                          |
| `productCode`               | Product configuration resolution                                          |
| `capRefId`                  | CAP status synchronization                                                |
| `finFortOrderId`            | FinFort order/status/file operations                                      |
| `customerId`                | FinFort client calls/file retrieval                                       |
| `request UUID`              | Perfios report request                                                    |
| `PAN`                       | Vendor/report/document-related headers in shown flows                     |

---

# 34. Integration Failure Boundary Model

Do not classify every integration failure as the same kind of failure.

A typical flow contains multiple boundaries:


IA Service
   |
   v
Request Construction
   |
   v
Gateway / Client
   |
   v
ESB / HTTP
   |
   v
External Vendor
   |
   v
Response Parsing
   |
   v
IA State Update
   |
   v
Kafka / Document Service / CAP
   |
   v
Downstream State


A failure can occur at any boundary.

Examples:

### Request construction failure


PerfiosUploadStatementEsbRequest.from(...)


### Configuration failure


bankStatementConfig.startTransactionUrl


### ESB transport failure


esbClientV2.postEncryptedV2(...)


### HTTP/API failure


404 / 405 / 415 / 5xx


### Response parsing failure


response wrapper deserialization


### Application correlation failure


findByCommonClientTransactionId(...)


### Downstream document failure


webClientWrapper.post(...)


### CAP synchronization failure


PATCH /internal/cap/api/initiate/event/update/status


Always identify the **first failing boundary** rather than only the final exception.

---

# 35. Common Integration Debugging Checklist

When an external integration fails:

## Step 1 — Identify the operation

Examples:


Start Transaction
Upload Statement
Complete Transaction
Generate Link
Transaction Status
Retrieve Report
Zenith Journey Link
CAP Status Sync
FinFort Order Status


---

## Step 2 — Identify the exact method

Search for the method named in the relevant RAG anchor.

Examples:


perfiosStartTransaction
uploadStatement
completeTransaction
generateLinkEsbEncryptedRequest
makeTransactionStatusRequest
retrieveBankStatementReportV2
fetchZenithTransactionStatus
retrieveReportFromEsbViaZenith
callCapServiceUpdateStatusDirect
checkOrderStatus


---

## Step 3 — Identify the client abstraction

Determine whether the operation uses:


esbClientV2
webClientWrapper
WebClient
FinFort client


This immediately narrows the debugging surface.

---

## Step 4 — Resolve the endpoint

Check the configured value:


bankStatementConfig.*
zenithOrchestratorConfig.*
transactionReportConfig.*
capBaseUrl + capUpdateStatusUrl
document-service path configuration


Never assume the endpoint from the method name.

---

## Step 5 — Check request construction

Look for:


map...
create...
build...
from(...)


Examples:


mapPerfiosStartTransactionRequest
createGenerateLinkRequest
createTransactionStatusRequest
createTransactionReportRequestWrapper
createJourneyLinkRequest
buildEncryptedRequestBodyForAnalyticsReport


---

## Step 6 — Check identifiers

Correlate:


applicationReferenceId
incomeAssessmentId
commonClientTransactionId
clientTransactionId
perfiosTransactionId
statementId
vendorTransactionId
serviceRequestId
finFortOrderId
capRefId


---

## Step 7 — Check headers

Particularly for encrypted ESB calls:


serviceRequestId
serviceRequestVersion
channelId
TARGET
request UUID
PAN-related headers
authorization


---

## Step 8 — Check response handling

Determine whether failure occurred:


before HTTP call
during HTTP call
after HTTP response
during response deserialization
during response mapping


---

## Step 9 — Check downstream processing

A successful integration response does not necessarily mean the IA flow completed.

Continue tracing:


external response
      ↓
business processing
      ↓
Mongo state
      ↓
Kafka event
      ↓
Document/CAP/downstream API


---

# 36. RAG Retrieval Map

Use these retrieval paths for common developer questions.

| Question                                                        | Primary anchor                                  |
| --------------------------------------------------------------- | ----------------------------------------------- |
| How does IA start a Perfios transaction?                        | `CODE-INT-PERFIOS-001`                          |
| Which Perfios endpoint starts a transaction?                    | `CODE-INT-PERFIOS-001`                          |
| How is the Perfios upload request built?                        | `CODE-INT-PERFIOS-002`                          |
| Which target header is used for Perfios upload?                 | `CODE-INT-PERFIOS-002`                          |
| How does Perfios complete transaction?                          | `CODE-INT-PERFIOS-003`                          |
| How is the Perfios journey link generated?                      | `CODE-INT-PERFIOS-004`                          |
| Why is Perfios transaction status not working?                  | `CODE-INT-PERFIOS-005`                          |
| Where is partner/product config resolved before Perfios status? | `CODE-INT-PERFIOS-005`                          |
| How does Perfios report retrieval correlate to IA?              | `CODE-INT-PERFIOS-006A`                         |
| Why does Perfios report retrieval say application not found?    | `CODE-INT-PERFIOS-006A`                         |
| How is Perfios insight report fetched?                          | `CODE-INT-PERFIOS-006B`                         |
| How is SBB handled in Perfios report retrieval?                 | `CODE-INT-PERFIOS-006B`                         |
| How does Zenith generate a journey link?                        | `CODE-INT-ZENITH-001`                           |
| How does Zenith transaction status work?                        | `CODE-INT-ZENITH-002`                           |
| How does Zenith fetch analytics report?                         | `CODE-INT-ZENITH-003`                           |
| Why is Zenith report returned as bytes?                         | `CODE-INT-ZENITH-003`                           |
| How are documents uploaded to OmniDocs?                         | `CODE-INT-DOC-001`                              |
| How are documents stored through Document Service?              | `CODE-INT-DOC-002`                              |
| Why is statementId truncated before document storage?           | `CODE-INT-DOC-002`                              |
| How does IA sync status to CAP?                                 | `CODE-INT-CAP-001`                              |
| Which CAP endpoint receives status updates?                     | `CODE-INT-CAP-001`                              |
| What controls CAP synchronization?                              | `CODE-INT-CAP-002`                              |
| How does FinFort create an order?                               | `CODE-INT-FINFORT-002`                          |
| How is FinFort encryption handled?                              | `CODE-INT-FINFORT-003`                          |
| How is FinFort order status checked?                            | `CODE-INT-FINFORT-004`                          |
| How are FinFort files retrieved?                                | `CODE-INT-FINFORT-005` / `CODE-INT-FINFORT-006` |

---

# 37. Source-of-Truth Hierarchy for Integration Questions

When snippets conflict with documentation, use this priority:

1. **Current gateway/client implementation**
2. **Current service implementation calling the gateway**
3. **Current endpoint/configuration definition**
4. **Request/response model definitions**
5. **Error mapping and retry operators**
6. **Tests/stubs**
7. **Architecture documentation**
8. **README/history**

The endpoint string in this document is based on the supplied code/config snippets.

If the repository contains a newer value, the repository value wins.

---

# 38. Cross-Document Navigation

Use this document together with:


05-integrations.md
    → integration purpose, boundaries, API behavior

flows/perfios-flow.md
    → Perfios end-to-end business/journey flow

flows/zenith-flow.md
    → Zenith end-to-end journey flow

flows/cap-flow.md
    → CAP initiation and status synchronization

flows/itr-flow.md
    → ITR / FinFort flow

08-error-handling.md
    → error classification and propagation

09-configuration.md
    → endpoint/configuration resolution

10-troubleshooting.md
    → incident investigation workflow

code/orchestration-snippets.md
    → controller → version → facade → service orchestration

code/kafka-snippets.md
    → asynchronous event propagation after integration responses

code/database-snippets.md
    → persistence and correlation after integration calls


---

# 39. Core Integration Invariants

These are high-value facts for RAG retrieval and debugging:

1. **Perfios and Zenith calls shown in this document use encrypted `esbClientV2.postEncryptedV2(...)`.**
2. **CAP status synchronization uses a direct PATCH WebClient call in the supplied implementation.**
3. **Document Service calls use `webClientWrapper` with POST/PUT operations.**
4. **FinFort uses a client abstraction with environment-dependent request encryption.**
5. **Perfios Start Transaction success does not mean the IA journey completed.**
6. **Perfios Generate Link success does not mean the user completed the journey.**
7. **Perfios Complete Transaction is still a vendor-processing boundary, not automatically final IA success.**
8. **Perfios transaction status is distinct from final IA business status.**
9. **Perfios report retrieval first correlates the request to an IA application using normalized `clientTransactionId`.**
10. **`clientTransactionId.substringBefore("--").trim()` is an explicit correlation rule in the supplied report/document paths.**
11. **Zenith journey-link success does not mean the Zenith journey completed.**
12. **Zenith transaction-status success does not by itself mean IA business validation succeeded.**
13. **Zenith analytics report retrieval is a separate step from transaction status.**
14. **OmniDocs upload and Document Service persistence are separate integration boundaries.**
15. **CAP `EventStatus` is separate from IA `IncomeAssessmentApplicationStatus`.**
16. **CAP synchronization is controlled by `capSyncEnabled` in the supplied implementation.**
17. **FinFort order status and file-details operations first resolve the IA application using `applicationReferenceId`.**
18. **FinFort authentication tokens stored in the shown application model are Base64-decoded before client execution.**
19. **Integration success does not automatically imply Mongo persistence, Kafka publication, downstream synchronization, or final IA success.**
20. **For RCA, identify the first integration boundary where actual behavior diverged from expected behavior.**

---

# 40. Canonical Integration Debugging Mental Model

When debugging any IA integration, think:


Which IA operation?
        |
        v
Which service method?
        |
        v
Which gateway/client?
        |
        v
Which request builder?
        |
        v
Which identifier?
        |
        v
Which headers / ESB metadata?
        |
        v
Which configured endpoint?
        |
        v
Did the HTTP/ESB call execute?
        |
        v
What was the raw response?
        |
        v
Did response deserialization succeed?
        |
        v
Did business processing succeed?
        |
        v
Did Mongo state update?
        |
        v
Was Kafka event published?
        |
        v
Did downstream processing succeed?


The most important RCA question is:

> **At which boundary did the expected integration behavior first diverge from the actual behavior?**
