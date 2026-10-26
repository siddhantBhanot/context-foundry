# Orchestration Code Context

## Purpose

This file documents the implementation-level orchestration of the Income Assessment (IA) application lifecycle.

It connects the high-level IA flow to the actual controller, version-resolution, facade, service, configuration, persistence, and callback code.

Use this file when investigating:

* How an IA application is initiated
* How `/validate` determines the next UI action
* How IA version routing works
* How the assessment medium is selected
* How `/generate-link` chooses between Perfios and Zenith
* How callbacks enter IA
* How Zenith vs Perfios report retrieval is selected
* How reports are persisted to OmniDocs
* Where business validation happens
* Which class/method should be debugged for a particular orchestration issue

This is an **implementation/evidence layer**.

For business meaning and state-machine semantics, refer to:

* `04-business-logic.md`
* `flows/income-assessment-flow.md`
* `flows/perfios-flow.md`
* `flows/zenith-flow.md`
* `10-troubleshooting.md`

---

# 1. Canonical IA Orchestration

The IA application lifecycle is not implemented as one monolithic controller flow.

The request generally passes through the following layers:


HTTP API
   ↓
Controller
   ↓
KeyData / request context
   ↓
CommonVersionResolver
   ↓
ServiceFacade
   ↓
Version-specific IA Service
   ↓
Business orchestration
   ↓
Config / DAO / Gateway / Kafka
   ↓
External system / persisted state / next event


The important implementation anchors observed in the repository snippets are:


IncomeAssessmentApplicationController
        ↓
CommonVersionResolver
        ↓
IncomeAssessmentApplicationServiceFacade
        ↓
ServiceFacade<T>
        ↓
IncomeAssessmentApplicationServiceRevamp
        ↓
Version-specific implementation


The same orchestration pattern is reused across APIs such as:


/initiate-application
/validate
/generate-link


---

# 2. Primary IA Application Entry Point

## CODE-ORCH-001 — IncomeAssessmentApplicationController

**Class**


IncomeAssessmentApplicationController


**Base path**


/income-assessment-service/v1


The controller has the following important dependencies:

kotlin
@RestController
@RequestMapping("/income-assessment-service/v1")
@Validated
class IncomeAssessmentApplicationController(
    val incomeAssessmentApplicationServiceFacade: IncomeAssessmentApplicationServiceFacade,
    val configFetcher: ConfigFetcher,
    val versionResolver: CommonVersionResolver,
) { ... }


### Important dependencies

| Dependency                                 | Responsibility                                                 |
| ------------------------------------------ | -------------------------------------------------------------- |
| `IncomeAssessmentApplicationServiceFacade` | Routes the operation to the appropriate service implementation |
| `ConfigFetcher`                            | Provides runtime configuration / feature-toggle information    |
| `CommonVersionResolver`                    | Resolves the IA version/bucket used for service routing        |

---

# 3. Initiate Application

## CODE-ORCH-002 — `/initiate-application`

**Endpoint**


POST /income-assessment-service/v1/initiate-application
POST /income-assessment-service/v1/enc/initiate-application


**Controller method**


IncomeAssessmentApplicationController.initiateApplication(...)


Observed signature:

kotlin
@PostMapping("/initiate-application", "/enc/initiate-application")
fun initiateApplication(
    @Valid
    @RequestBody applicationRequest: IncomeAssessmentApplicationRequest,
    @RequestHeader partnerId: String
): Mono<com.contextfoundry.lending.incomeassesmentservice.controller.IncomeAssessmentResponse> {
    ...
}


### Input

The API receives:


IncomeAssessmentApplicationRequest
partnerId


### High-level execution


POST /initiate-application
        ↓
IncomeAssessmentApplicationController
        ↓
IncomeAssessmentApplicationServiceFacade
        ↓
version-specific IA service
        ↓
application initiation


The exact controller implementation is partially omitted in the supplied snippet, so the precise invocation sequence inside `initiateApplication(...)` should be populated once the complete method is available.

### Debugging value

If IA initiation behaves differently for two requests, begin by checking:

1. request payload
2. `partnerId`
3. application identifiers
4. version resolution
5. selected service implementation
6. configuration used by that implementation

### Related context

* `flows/income-assessment-flow.md`
* `04-business-logic.md`
* `09-configuration.md`

---

# 4. Version Resolution Architecture

## CODE-ORCH-003 — CommonVersionResolver

**Class**


CommonVersionResolver


Observed dependencies:

kotlin
@Component
class CommonVersionResolver(
    val configFetcher: ConfigFetcher,
    val authServiceClient: AuthServiceClient,
    val keyResolver: KeyResolver,
    val incomeAssessmentApplicationAccessor: IncomeAssessmentApplicationAccessor,
    val incomeAssessmentRepository: IncomeAssessmentRepository,
    val configurationRepository: ConfigurationRepository
) { ... }


### Responsibility

`CommonVersionResolver` is a central routing component used to determine the IA version/bucket for a request.

It has access to:

* runtime configuration
* authentication information
* key resolution
* application access
* application repository
* configuration repository

The exact resolution logic should be captured from the complete class when available.

---

# 5. Service Facade

## CODE-ORCH-004 — IncomeAssessmentApplicationServiceFacade

**Class**


IncomeAssessmentApplicationServiceFacade


Observed implementation:

kotlin
@Service
class IncomeAssessmentApplicationServiceFacade(
    versionResolver: CommonVersionResolver,
    factory: IncomeAssessmentApplicationServiceFactory
) : ServiceFacade<IncomeAssessmentApplicationServiceRevamp>(versionResolver, factory) { ... }


### Architecture


IncomeAssessmentApplicationServiceFacade
              ↓
ServiceFacade<IncomeAssessmentApplicationServiceRevamp>
              ↓
IncomeAssessmentApplicationServiceFactory
              ↓
resolved IA service implementation


The facade does not directly contain the entire business flow.

Its important role is to participate in version-aware service routing.

---

# 6. Generic ServiceFacade

## CODE-ORCH-005 — executeWithVersion

**Class**


ServiceFacade<T : RevampService>


Observed structure:

kotlin
abstract class ServiceFacade<T : RevampService>(
    protected val versionResolver: CommonVersionResolver,
    protected val factory: RevampServiceFactory<T>
) {
    private val logger = Logger(ServiceFacade::class.java)
    ...
}


Important method:

kotlin
protected fun <R> executeWithVersion(
    keyData: KeyData,
    action: (T) -> Mono<R>,
): Mono<R> =
    Mono.deferContextual { ctx ->
        val cachedBucketName = VersionContext.getBucket(ctx)
        if (cachedBucketName != null) {
            versionResolver.resolveFromBucket(
                cachedBucketName,
                factory.facadeName
            )
            ...


### Important implementation detail

`executeWithVersion(...)` checks the Reactor context for an already-resolved bucket:


VersionContext.getBucket(ctx)


If a cached bucket exists, the facade can resolve the service using that bucket.

This means version information can be carried through the reactive execution context rather than necessarily being recalculated at every service operation.

### Debugging significance

If a request appears to execute the wrong IA implementation, inspect:


KeyData
   ↓
primeBucket(...)
   ↓
VersionContext
   ↓
cachedBucketName
   ↓
resolveFromBucket(...)
   ↓
factory
   ↓
concrete service


Do not debug the concrete service first without confirming which version was actually selected.

---

# 7. IA Service Abstraction

## CODE-ORCH-006 — IncomeAssessmentApplicationServiceRevamp

The versioned IA implementations conform to:

kotlin
interface IncomeAssessmentApplicationServiceRevamp : RevampService {
    ...
}


This interface represents the service contract consumed by the facade.

Important operations observed in the supplied snippets include:


initiateApplication(...)
validate(...)
generateLink(...)


Additional operations should be added as repository code is provided.

---

# 8. Initiate Application Service

## CODE-ORCH-007 — initiateApplication(...)

Observed service method:

kotlin
override fun initiateApplication(
    request: IncomeAssessmentApplicationRequest,
    partnerId: String
): Mono<String> {
    return getIncomeAssessmentFeatureToggle()
        .logOnSuccess(logger) {
            infoV(
                version,
                "Got IA feature toggle",
                mapOf(
                    "incomeAssessmentId" to
                        (request.incomeAssessmentId ?: "")
                )
            )
        }
    ...
}


### Important implementation evidence

IA initiation reads feature-toggle/configuration information before continuing with the orchestration.

The request's:


incomeAssessmentId


is included in logging associated with the feature-toggle retrieval.

### Conceptual execution


initiateApplication(...)
       ↓
getIncomeAssessmentFeatureToggle()
       ↓
feature/configuration resolution
       ↓
remaining IA initiation orchestration


The remaining method body was not included in the supplied snippet.

Therefore the exact application creation, assessment-medium selection, and downstream invocation should be populated from the complete method rather than inferred here.

---

# 9. IA Application Persistence Model

## CODE-ORCH-008 — IncomeAssessmentApplicationDao

The main IA application state is represented by:

kotlin
@Document(collection = "incomeAssessmentApplications")
@CompoundIndex(
    name = "incomeAssessmentRecordsIdx",
    unique = true,
    def = "{'incomeAssessmentId' : 1, 'productCode' : 1, 'partnerId' : 1}"
)
@TypeAlias("IncomeAssessmentApplication")
data class IncomeAssessmentApplicationDao(
    val assessmentMedium: AssessmentMedium,
    ...
)


### Important persistence facts

MongoDB collection:


incomeAssessmentApplications


Unique compound index:


incomeAssessmentId
productCode
partnerId


### Architectural significance

The IA application record is not merely a response object.

It represents persisted workflow state used by later operations such as:


/validate
/generate-link
callback processing
report processing
status transitions


The `assessmentMedium` is persisted as part of the application model.

### Debugging significance

When investigating a journey-routing issue, inspect the persisted:


assessmentMedium
incomeAssessmentId
productCode
partnerId
status
statusType
vendor transaction identifiers


The exact fields should be expanded as more DAO code is provided.

---

# 10. `/validate` — UI Decision Orchestration

## CODE-ORCH-009 — `/validate`

**Endpoint**


GET /income-assessment-service/v1/validate


The `/validate` operation is an important orchestration boundary because its response contains an **ACTION** that determines what the UI should do next.

The UI uses the returned action to decide which page/flow to display.

---

## Controller

Observed implementation:

kotlin
@GetMapping("/validate")
fun validate(
    @RequestHeader(name = HttpHeaders.AUTHORIZATION)
    authorizationJwtToken: String?,
    @RequestParam retry: Boolean? = false,
    @RequestParam(
        name = "timedOut",
        required = false
    )
    timedOut: Boolean? = false,
    @RequestParam(
        name = "accountSelectionCancel",
        required = false
    )
    accountSelectionCancel: Boolean? = false,
): Mono<ValidateResponse> {
    val keyData = KeyData.forJwtToken(authorizationJwtToken!!)

    return versionResolver.primeBucket(keyData) {
        incomeAssessmentApplicationServiceFacade.validate(
            keyData,
            authorizationJwtToken,
            retry,
            timedOut,
            accountSelectionCancel
        )
    }
}


### Important execution path


GET /validate
      ↓
authorization JWT
      ↓
KeyData.forJwtToken(...)
      ↓
versionResolver.primeBucket(...)
      ↓
IncomeAssessmentApplicationServiceFacade.validate(...)
      ↓
version-specific validate(...)
      ↓
ValidateResponse
      ↓
UI interprets ACTION


---

# 11. `/validate` Version Resolution

## CODE-ORCH-010 — primeBucket(...)

The controller explicitly wraps the `/validate` operation in:

kotlin
versionResolver.primeBucket(keyData) {
    incomeAssessmentApplicationServiceFacade.validate(...)
}


### Significance

The `/validate` operation participates in the same version-routing architecture as the rest of IA.

Therefore, if `/validate` returns an unexpected action, investigate:


JWT
 ↓
KeyData
 ↓
primeBucket
 ↓
resolved version/bucket
 ↓
facade
 ↓
concrete validate implementation
 ↓
configuration/application state
 ↓
determineNextAction


---

# 12. Validate Service

## CODE-ORCH-011 — validate(...)

Observed implementation begins with:

kotlin
override fun validate(
    incomeAssessmentToken: String?,
    retry: Boolean?,
    loaderTimeout: Boolean?,
    accountSelectionCancel: Boolean?
): Mono<ValidateResponse> {
    var productCode = FeatureTogglesScope.GLOBAL.name

    if (incomeAssessmentToken.isNullOrEmpty()) {
        throw InvalidAuthorizationTokenException(IA121)
    }

    ...
}


### Important inputs


incomeAssessmentToken
retry
loaderTimeout
accountSelectionCancel


### Important behavior

The service validates the income-assessment token before continuing.

If the token is missing/empty:


InvalidAuthorizationTokenException(IA121)


is thrown.

### Debugging significance

An unexpected `/validate` result must first be distinguished between:


invalid token
vs
valid token + business/action decision


---

# 13. Validate Next-Action Resolution

## CODE-ORCH-012 — getNextAction(...)

Observed method:

kotlin
private fun getNextAction(
    authToken: String,
    applicationDao: IncomeAssessmentApplicationDao,
    token: IncomeAssessmentToken,
    configs: PartnerProductConfigurations,
    retry: Boolean?,
    loaderTimeout: Boolean?,
    accountSelectionCancel: Boolean?
): Mono<ValidateResponse> {
    val featureToggleName =
        getRetryScreenErrMsgToggleName(applicationDao)

    return Mono.zip(
        fetchFeatureToggleFromIAConfig(
            applicationDao,
            featureToggleName,
            "retryErrorMsgScreen"
        ),
        ...
    )
}


### Important behavior

`getNextAction(...)` combines:


application state
+
token
+
partner/product configuration
+
retry state
+
loader timeout state
+
account-selection cancellation
+
feature toggles


to determine the next response.

### Configuration dependency

One explicitly observed toggle is:


retryErrorMsgScreen


The code first determines the feature-toggle name through:


getRetryScreenErrMsgToggleName(applicationDao)


and then fetches the configured value.

### Debugging significance

If `/validate` returns an unexpected action, inspect the inputs to `getNextAction(...)` rather than looking only at the final response.

---

# 14. Validate Action Determination

## CODE-ORCH-013 — determineNextAction(...)

Observed signature:

kotlin
private fun determineNextAction(
    applicationDao: IncomeAssessmentApplicationDao,
    token: IncomeAssessmentToken,
    showErrorMsg: Boolean,
    enableRedirectToLandingPageForPolicyNormNotMetError: Boolean,
    allowRedirectToPartnerForError: Boolean,
    retry: Boolean?,
    authToken: String,
    isRetryLimitReached: Boolean = false
): Mono<ValidateResponse> {
    ...
}


### Inputs influencing ACTION

The next UI action can depend on:


applicationDao
token
showErrorMsg
enableRedirectToLandingPageForPolicyNormNotMetError
allowRedirectToPartnerForError
retry
authToken
isRetryLimitReached


This makes `/validate` a **decision/orchestration endpoint**, not merely a validation endpoint.

### Important distinction

The endpoint name is `/validate`, but its practical role is:


Current IA state/configuration
        ↓
Determine allowed next action
        ↓
ValidateResponse
        ↓
UI decides next page/flow


---

# 15. `/validate` Downstream UI Decision

The `/validate` response drives the next UI behavior.

Conceptually:


/validate
    ↓
ValidateResponse
    ↓
ACTION
    ├── Landing page
    │      ↓
    │   assessment medium selection
    │
    ├── Finacle flow
    │
    ├── Retry flow
    │
    └── Other configured action


There are also cases where an IA application originating through CAP can trigger certain assessment flows directly without presenting the normal assessment-medium selection UI.

These direct-flow cases should be correlated with the actual branch/code that produces the corresponding `ACTION`.

---

# 16. Assessment Medium Selection

When the UI presents the IA landing page, the user can select an assessment medium.

The selected medium is then passed to:


/generate-link


The important architectural distinction is:


/validate
    ↓
UI action
    ↓
Landing page
    ↓
User selects assessment medium
    ↓
/generate-link


Therefore `/validate` and `/generate-link` are separate orchestration stages.

---

# 17. `/generate-link`

## CODE-ORCH-014 — Generate Link Controller

**Endpoint**


GET /income-assessment-service/v1/generate-link


Observed controller:

kotlin
@GetMapping("/generate-link")
fun generateLink(
    @RequestHeader(name = HttpHeaders.AUTHORIZATION)
    authorizationJwtToken: String,
    @RequestParam(
        defaultValue = "NONE",
        required = false
    )
    assessmentMedium: String,
    @RequestParam(required = false)
    isBSSelected: Boolean?,
    @RequestParam(defaultValue = "false")
    isRedirectToAA: Boolean,
    @RequestParam(defaultValue = "", required = false)
    promoId: String,
    @RequestParam(defaultValue = "false")
    manualSelection: Boolean
): Mono<IncomeAssessmentResponse> {
    val keyData = KeyData.forJwtToken(authorizationJwtToken)

    return versionResolver.primeBucket(keyData) {
        incomeAssessmentApplicationServiceFacade.generateLink(
            keyData,
            authorizationJwtToken,
            assessmentMedium,
            isBSSelected,
            isRedirectToAA,
            promoId,
            manualSelection
        )
    }
}


### Inputs


authorizationJwtToken
assessmentMedium
isBSSelected
isRedirectToAA
promoId
manualSelection


### Execution path


GET /generate-link
      ↓
KeyData.forJwtToken(...)
      ↓
versionResolver.primeBucket(...)
      ↓
facade.generateLink(...)
      ↓
version-specific generateLink(...)


---

# 18. Generate Link Service

## CODE-ORCH-015 — generateLink(...)

Observed implementation:

kotlin
override fun generateLink(
    token: String,
    assessmentMedium: String,
    isBSSelected: Boolean?,
    isRedirectToAA: Boolean,
    promoId: String,
    manualSelection: Boolean
): Mono<IncomeAssessmentResponse> {
    val claims = authServiceClient.validateAndFetchClaims(token)

    return Mono.just(true)
        .logOnSuccess(logger) {
            infoV(
                version,
                "Assessment Medium received in request param: $assessmentMedium"
            )
        }
        .flatMap {
            validateAndGetIaApplicationDao(
                claims,
                assessmentMedium
            )
            ...
        }
}


### Important behavior

Before link generation proceeds:

1. JWT claims are validated/fetched.
2. `assessmentMedium` is logged.
3. The IA application is validated/retrieved through:

   
   validateAndGetIaApplicationDao(...)
   

### Debugging significance

If `/generate-link` behaves incorrectly, verify:


JWT claims
↓
assessmentMedium request parameter
↓
IA application lookup
↓
application.assessmentMedium
↓
configuration
↓
journey selection


---

# 19. Link Generation Decision Point

## CODE-ORCH-016 — proceedForLinkGeneration(...)

Observed method:

kotlin
private fun proceedForLinkGeneration(
    application: IncomeAssessmentApplicationDao,
    promoId: String = ""
): Mono<IncomeAssessmentResponse> {
    val details = logDetails(application)

    return configFetcher.allPartnerProductConfigurations()
        .map { configuration ->
            ...
        }
}


This method is an important configuration-driven orchestration boundary.

It receives the persisted:


IncomeAssessmentApplicationDao


and retrieves partner/product configuration before deciding how link generation proceeds.

---

# 20. Zenith vs Perfios Selection

## CODE-ORCH-017 — enableZenithOrchAPI

A critical branch in link generation is:

kotlin
configFetcher
    .fetchFeatureToggleFromIAConfig(
        application,
        configToggleName,
        "enableZenithOrchAPI"
    )
    .flatMap { toggleValue ->
        val toggleOn = (toggleValue as? Boolean) ?: false

        val txnId = getTransactionId(
            application,
            config,
            toggleOn
        )

        val initialFlow =
            if (
                toggleOn &&
                application.assessmentMedium == ACCOUNT_AGGREGATOR
            ) {
                // Zenith Orch API flow
                handleZenithOrchJourneyLinkGeneration(
                    application,
                    config,
                    txnId,
                    promoId,
                    details
                )
            } else {
                // Perfios API flow
                handleLinkGeneration(
                    application,
                    config,
                    txnId,
                    promoId,
                    details,
                    toggleOn
                )
            }
        ...
    }


### Exact decision rule observed

Zenith path is selected only when:


enableZenithOrchAPI == true
AND
application.assessmentMedium == ACCOUNT_AGGREGATOR


Otherwise the code enters the Perfios path.

Conceptually:


                   enableZenithOrchAPI?
                         |
                 +-------+-------+
                 |               |
               FALSE            TRUE
                 |               |
              Perfios      assessmentMedium?
                                 |
                         +-------+-------+
                         |               |
                    ACCOUNT_AGGREGATOR   Other
                         |               |
                      Zenith            Perfios


### Important debugging invariant


Zenith is not selected solely because the toggle is enabled.


Both conditions matter:


toggleOn
AND
assessmentMedium == ACCOUNT_AGGREGATOR


### Important transaction behavior

The code calculates:


getTransactionId(application, config, toggleOn)


before selecting the journey-specific link-generation path.

The exact transaction-ID implementation should be documented when the method is provided.

---

# 21. Link Generation Architecture

The observed implementation creates two distinct branches:

### Zenith


application
   ↓
enableZenithOrchAPI = true
   ↓
assessmentMedium = ACCOUNT_AGGREGATOR
   ↓
getTransactionId(...)
   ↓
handleZenithOrchJourneyLinkGeneration(...)
   ↓
Zenith journey


### Perfios


application
   ↓
otherwise
   ↓
getTransactionId(...)
   ↓
handleLinkGeneration(...)
   ↓
Perfios journey


This is one of the most important code-level routing decisions in the IA application.

---

# 22. Callback Entry Point

## CODE-ORCH-018 — NewPerfiosCallbackController

Perfios callbacks enter IA through:


POST /income-assessment-service/v1/status/perfios
POST /income-assessment-service/v1/enc/status/perfios


Controller:


NewPerfiosCallbackController


Observed structure:

kotlin
@RestController
@RequestMapping("/income-assessment-service/v1")
@Qualifier("PerfiosCallback")
class NewPerfiosCallbackController(
    @Autowired val featureTogglesFetcher: FeatureTogglesFetcher,
    @Autowired val perfiosCallbackController: PerfiosCallbackController
) {
    val logger = Logger(this::class.java)
    ...
}


### Callback architecture

The controller depends on:


FeatureTogglesFetcher
PerfiosCallbackController


This indicates that callback processing is feature-toggle aware and delegates into callback-specific processing.

---

# 23. Callback Identifier Validation

## CODE-ORCH-019 — validateRequest(...)

Observed validation:

kotlin
private fun validateRequest(
    callbackIdentifier: String
): Boolean {
    return WhiteSpaceValidator().isValid(
        callbackIdentifier,
        null
    ) &&
        Constants.clientTransactionIdRegx
            .toRegex()
            .containsMatchIn(callbackIdentifier)
}


### Validation performed

The callback identifier must satisfy:


non-whitespace validation
AND
clientTransactionId regex validation


### Related toggle

The callback controller checks:


ignoreInvalidClientTransactionIdException


through:


featureTogglesFetcher.fetch(
    FeatureTogglesScope.GLOBAL.name,
    "ignoreInvalidClientTransactionIdException"
)


This toggle therefore affects callback identifier validation behavior.

### Debugging significance

For callback rejection issues, inspect:


callbackIdentifier
↓
WhitespaceValidator
↓
clientTransactionId regex
↓
ignoreInvalidClientTransactionIdException
↓
callback processing


---

# 24. Callback → Report Retrieval Routing

After callback processing, report/statement retrieval can use either Zenith or Perfios depending on the application context and configuration.

One observed branch is:

kotlin
zenithToggle.flatMap { viaZenith ->
    if (
        viaZenith &&
        incomeAssessmentDao.assessmentMedium ==
            AssessmentMedium.ACCOUNT_AGGREGATOR
    ) {
        fetchRawStatementsViaZenith(
            vendorTransactionId,
            ZenithReportType.ZIP,
            CONTENT_TYPE_JSON
        )
        ...
    } else {
        bankStatementReportGatewayFacade
            .retrieveReportInByteArrayFromEsbClientV2(
                keyData,
                perfiosTransactionId =
                    perfiosTransactionIdFoRetrieveReport,
                clientTransactionId =
                    incomeAssessmentDao.commonClientTransactionId.toString(),
                reportType = REPORT_TYPE,
                contentTypeAccepted = CONTENT_TYPE,
                vendorId = VENDOR_ID,
                perfiosNumRetry = perfiosNumRetry,
                pan = incomeAssessmentDao.pan
            )
    }
}


### Exact routing condition

Zenith raw-statement retrieval occurs when:


viaZenith == true
AND
assessmentMedium == ACCOUNT_AGGREGATOR


Otherwise the Perfios report gateway is used.

### Architecture


Callback / processing
       ↓
Zenith toggle?
       |
   +---+---+
   |       |
 FALSE    TRUE
   |       |
Perfios   assessmentMedium?
             |
       +-----+-----+
       |           |
      AA          Other
       |           |
    Zenith       Perfios


This mirrors the same routing principle used during link generation.

---

# 25. Excel Report Retrieval Routing

A similar branch exists for Excel report retrieval:

kotlin
toggleMonoValue.flatMap { toggleOn ->
    if (
        toggleOn &&
        application.assessmentMedium ==
            AssessmentMedium.ACCOUNT_AGGREGATOR
    ) {
        fetchStatementsOrReportsViaZenith(
            perfiosTransactionId,
            serviceRequestId,
            ZenithReportType.XLSX,
            VENDOR_JSON_TYPE
        )
        ...
    } else {
        fetchPerfiosStatementsOrReport(
            perfiosTransactionId,
            clientTransactionId,
            XLS_REPORT_TYPE,
            MS_EXCEL_MEDIA_TYPE,
            isSbbEnableProduct = isSbbEnableProduct,
            pan = application.pan,
            isMultiBank = isMultiBank
        )
        ...
    }
}


### Routing condition

Again:


toggleOn
AND
assessmentMedium == ACCOUNT_AGGREGATOR


→ Zenith

Otherwise:


Perfios


### Important implementation pattern

The Zenith/Perfios decision is therefore not limited to journey-link generation.

It also appears during downstream report retrieval.

---

# 26. OmniDocs Report Persistence

## CODE-ORCH-020 — Save Excel Report to OmniDocs

After retrieving the Excel report, the code invokes:

kotlin
bankStatementReportGatewayFacade.saveExcelReportInOmniDocs(
    keyData,
    incomeAssessmentApplication = incomeAssessmentApplication,
    vendorTransactionId = perfiosTransactionId,
    statementId = clientTransactionId,
    longHandStatementId =
        convertShortToLongHandProductCode(clientTransactionId),
    isSbbEnableProduct = isSbbEnableProduct,
    isMultiBank = isMultiBank
)


The resulting document reference is then persisted:

kotlin
.flatMap {
    incomeAssessmentRepository.save(
        incomeAssessmentApplication.copy(
            omniDocsRefIdReport =
                it.documentList[0].docIndex
        )
    )
}


Finally, an event is published:

kotlin
.flatMap { appAfterOmniDocs ->
    publishDocUploadedEvent(
        appAfterOmniDocs,
        IncomeAssessmentApplicationEvent
            .PERFIOS_EXCEL_UPLOADED_TO_OMNIDOCS_EVENT_ID
    )
    .thenReturn(appAfterOmniDocs)
}


### Exact execution chain


Excel report
    ↓
saveExcelReportInOmniDocs(...)
    ↓
OmniDocs document created
    ↓
documentList[0].docIndex
    ↓
incomeAssessmentRepository.save(...)
    ↓
omniDocsRefIdReport persisted
    ↓
publishDocUploadedEvent(...)
    ↓
PERFIOS_EXCEL_UPLOADED_TO_OMNIDOCS_EVENT_ID


### Important orchestration property

This is a multi-boundary operation:


External report
   ↓
OmniDocs
   ↓
MongoDB
   ↓
Kafka


A failure at any individual boundary can produce a different incident symptom.

For example:


OmniDocs success
+ Mongo failure
→ document exists externally but reference isn't persisted

Mongo success
+ Kafka failure
→ DB shows uploaded document but downstream consumer may not react


---

# 27. JSON Report Retrieval Routing

Another callback-processing branch retrieves the JSON report:

kotlin
return toggleMonoValue.flatMap { toggleOn ->
    val reportMono =
        if (
            toggleOn &&
            incomeAssessmentApplication.assessmentMedium ==
                AssessmentMedium.ACCOUNT_AGGREGATOR
        ) {
            zenithOrchestratorGateway.fetchJsonReportViaZenith(
                notification.vendorTransactionId,
                notification.clientTransactionId,
                ZenithReportType.JSON,
                serviceRequestId
            )
            ...
        } else {
            bankStatementReportGatewayFacade.fetchJsonPerfiosReport(
                keyData,
                notification.vendorTransactionId,
                notification.clientTransactionId,
                occupation,
                isSbbEnableProduct
            )
            ...
        }

    ...
}


### Routing condition

Again:


toggleOn
AND
assessmentMedium == ACCOUNT_AGGREGATOR


→


zenithOrchestratorGateway.fetchJsonReportViaZenith(...)


Otherwise:


bankStatementReportGatewayFacade.fetchJsonPerfiosReport(...)


---

# 28. Report Retrieval Uses Vendor Transaction Identity

The JSON report retrieval code explicitly passes:


notification.vendorTransactionId
notification.clientTransactionId
serviceRequestId


to the Zenith path.

This is important for callback debugging because:


IA application identity
≠
vendor transaction identity
≠
client transaction identity


The correct identifiers must be correlated when tracing a callback/report issue.

Refer to:

* `06-database.md`
* `flows/perfios-flow.md`
* `flows/zenith-flow.md`

for the broader identifier model.

---

# 29. Business Validation After Report Retrieval

## CODE-ORCH-021 — performValidation(...)

Observed method:

kotlin
private fun performValidation(
    it: Tuple2<
        IncomeAssessmentApplicationDao,
        RetrieveReportEsbResponse
    >,
    notification: CallbackNotification
): Mono<IncomeAssessmentPolicyValidationResult> {
    var imputedEnabled1 = false

    val retrieveReportEsbResponse = it.t2

    val updatedIncomeAssessmentApplication =
        it.t1.copy(
            ifsc =
                retrieveReportEsbResponse.response
                    .xns
                    ?.first()
                    ?.ifscCode ?: ""
        )

    val keyData = KeyData.forPartnerConfiguration(
        partnerId =
            updatedIncomeAssessmentApplication.partnerId,
        ...
    )
    ...
}


### Important behavior

The validation flow receives:


IncomeAssessmentApplicationDao
+
RetrieveReportEsbResponse
+
CallbackNotification


It creates an updated application representation containing information extracted from the retrieved report.

Example:


IFSC


is extracted from the report response and copied into the application object.

### Conceptual flow


Retrieved report
      ↓
IncomeAssessmentApplicationDao
      ↓
extract report data
      ↓
update application representation
      ↓
construct KeyData
      ↓
business validation
      ↓
IncomeAssessmentPolicyValidationResult


### Important architectural distinction

Report retrieval and business validation are separate stages:


Vendor report retrieval
        ↓
Report response
        ↓
Business validation


Therefore:


report retrieved successfully


does not by itself mean:


IA assessment succeeded


---

# 30. End-to-End Orchestration Map

Combining the supplied implementation snippets:


                    ┌──────────────────────────┐
                    │        IA Controller      │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │     CommonVersionResolver │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │ ServiceFacade             │
                    │ executeWithVersion(...)   │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │ Version-specific IA       │
                    │ ServiceRevamp             │
                    └────────────┬─────────────┘
                                 │
               ┌─────────────────┼──────────────────┐
               │                 │                  │
               ▼                 ▼                  ▼
        /initiate-application  /validate       /generate-link
               │                 │                  │
               │                 ▼                  │
               │          determineNextAction       │
               │                 │                  │
               │                 ▼                  │
               │          ValidateResponse          │
               │                 │                  │
               │                 ▼                  │
               │             UI ACTION              │
               │                                    │
               │                              assessmentMedium
               │                                    │
               │                                    ▼
               │                              configuration
               │                                    │
               │                         ┌──────────┴──────────┐
               │                         │                     │
               │                         ▼                     ▼
               │                    Zenith + AA            Perfios
               │                         │                     │
               │                         └──────────┬──────────┘
               │                                    │
               │                                    ▼
               │                              Vendor Journey
               │                                    │
               │                                    ▼
               │                               Callback
               │                                    │
               │                                    ▼
               │                         Report Retrieval
               │                                    │
               │                         ┌──────────┴──────────┐
               │                         │                     │
               │                         ▼                     ▼
               │                      Zenith                Perfios
               │                         │                     │
               │                         └──────────┬──────────┘
               │                                    │
               │                                    ▼
               │                            Business Validation
               │                                    │
               │                                    ▼
               │                              State / Events
               │
               ▼
       incomeAssessmentApplications


---

# 31. Critical Routing Conditions

The following conditions are directly evidenced by the supplied code.

## 31.1 Zenith journey link generation


enableZenithOrchAPI == true
AND
assessmentMedium == ACCOUNT_AGGREGATOR


→ Zenith journey-link generation.

Otherwise → Perfios path.

---

## 31.2 Zenith raw statement retrieval


viaZenith == true
AND
assessmentMedium == ACCOUNT_AGGREGATOR


→ `fetchRawStatementsViaZenith(...)`

Otherwise → Perfios gateway.

---

## 31.3 Zenith Excel report retrieval


toggleOn == true
AND
assessmentMedium == ACCOUNT_AGGREGATOR


→ `fetchStatementsOrReportsViaZenith(...)`

Otherwise → Perfios report retrieval.

---

## 31.4 Zenith JSON report retrieval


toggleOn == true
AND
assessmentMedium == ACCOUNT_AGGREGATOR


→ `fetchJsonReportViaZenith(...)`

Otherwise → `fetchJsonPerfiosReport(...)`.

---

# 32. Important Orchestration Invariants

### Invariant 1 — Version resolution happens before version-specific execution

For the supplied `/validate` and `/generate-link` flows:


KeyData
→ primeBucket(...)
→ facade
→ version-specific service


---

### Invariant 2 — `/validate` is a UI decision endpoint

The result of `/validate` is not simply a boolean validation result.

It produces a `ValidateResponse` whose ACTION drives subsequent UI behavior.

---

### Invariant 3 — `/validate` and `/generate-link` are separate stages


/validate
→ determine UI action
→ landing page / flow

/generate-link
→ user-selected assessment medium
→ journey link generation


---

### Invariant 4 — Zenith selection requires both configuration and assessment medium

The observed condition is:


enableZenithOrchAPI
AND
ACCOUNT_AGGREGATOR


A Zenith toggle alone does not establish that the Zenith path will execute.

---

### Invariant 5 — Vendor journey routing and report routing use the same core decision

The Zenith/Perfios distinction appears during:


link generation
raw statement retrieval
Excel report retrieval
JSON report retrieval


This makes the routing condition a high-value debugging anchor.

---

### Invariant 6 — Report retrieval does not equal business success

The observed flow is:


callback
→ report retrieval
→ business validation
→ final state/event


Successful report retrieval is an intermediate step.

---

### Invariant 7 — OmniDocs persistence is separate from Mongo persistence

The Excel report flow demonstrates:


save to OmniDocs
→ retrieve document reference
→ save reference in Mongo
→ publish Kafka event


These are separate failure boundaries.

---

### Invariant 8 — IA application state is persisted in Mongo

The primary application collection is:


incomeAssessmentApplications


with a unique compound index on:


incomeAssessmentId
productCode
partnerId


---

# 33. Debugging Decision Tree

## `/initiate-application` issue


Request received?
    ↓
Controller
    ↓
partnerId correct?
    ↓
Key/context correct?
    ↓
Version resolved?
    ↓
Correct service implementation?
    ↓
Feature toggle/configuration?
    ↓
Application created/reused?
    ↓
Assessment medium/journey selected?


---

## `/validate` returns unexpected ACTION


JWT valid?
    ↓
KeyData created?
    ↓
primeBucket succeeded?
    ↓
Correct IA version?
    ↓
Correct application loaded?
    ↓
retry/timedOut/accountSelectionCancel values?
    ↓
PartnerProductConfigurations?
    ↓
retryErrorMsgScreen?
    ↓
other action-related toggles?
    ↓
isRetryLimitReached?
    ↓
determineNextAction(...)
    ↓
ValidateResponse.ACTION


---

## `/generate-link` chooses wrong vendor


JWT claims valid?
    ↓
assessmentMedium received correctly?
    ↓
validateAndGetIaApplicationDao(...)
    ↓
application.assessmentMedium correct?
    ↓
enableZenithOrchAPI resolved?
    ↓
toggleOn?
    ↓
assessmentMedium == ACCOUNT_AGGREGATOR?
    ↓
getTransactionId(...)
    ↓
Zenith or Perfios branch


---

## Callback/report issue


Callback received?
    ↓
callbackIdentifier valid?
    ↓
ignoreInvalidClientTransactionIdException?
    ↓
Correct application identified?
    ↓
Correct vendor transaction identified?
    ↓
Zenith/Perfios toggle?
    ↓
assessmentMedium?
    ↓
Correct report gateway?
    ↓
Report retrieved?
    ↓
OmniDocs / persistence?
    ↓
Business validation?
    ↓
Kafka / downstream?


---

# 34. High-Value Code Anchors for RAG

| ID              | Anchor                                     | Primary debugging question                               |
| --------------- | ------------------------------------------ | -------------------------------------------------------- |
| `CODE-ORCH-001` | `IncomeAssessmentApplicationController`    | Where does an IA API request enter?                      |
| `CODE-ORCH-002` | `/initiate-application`                    | How is IA initiation started?                            |
| `CODE-ORCH-003` | `CommonVersionResolver`                    | How is the IA version determined?                        |
| `CODE-ORCH-004` | `IncomeAssessmentApplicationServiceFacade` | How does the facade route requests?                      |
| `CODE-ORCH-005` | `ServiceFacade.executeWithVersion(...)`    | How does version-aware execution work?                   |
| `CODE-ORCH-006` | `IncomeAssessmentApplicationServiceRevamp` | What is the versioned IA service contract?               |
| `CODE-ORCH-007` | `initiateApplication(...)`                 | What happens after IA initiation enters the service?     |
| `CODE-ORCH-008` | `IncomeAssessmentApplicationDao`           | Where is application state persisted?                    |
| `CODE-ORCH-009` | `/validate`                                | How does UI decide what to do next?                      |
| `CODE-ORCH-010` | `primeBucket(...)`                         | How does `/validate` select its implementation?          |
| `CODE-ORCH-011` | `validate(...)`                            | What inputs affect validation?                           |
| `CODE-ORCH-012` | `getNextAction(...)`                       | Which configs participate in next-action calculation?    |
| `CODE-ORCH-013` | `determineNextAction(...)`                 | How is the final UI action determined?                   |
| `CODE-ORCH-014` | `/generate-link`                           | How does the user-selected medium reach the service?     |
| `CODE-ORCH-015` | `generateLink(...)`                        | How is the application validated before link generation? |
| `CODE-ORCH-016` | `proceedForLinkGeneration(...)`            | Where does configuration enter journey selection?        |
| `CODE-ORCH-017` | `enableZenithOrchAPI` branch               | What determines Zenith vs Perfios?                       |
| `CODE-ORCH-018` | `NewPerfiosCallbackController`             | Where does the Perfios callback enter?                   |
| `CODE-ORCH-019` | `validateRequest(...)`                     | Why could a callback identifier be rejected?             |
| `CODE-ORCH-020` | OmniDocs save flow                         | How does report retrieval become a persisted document?   |
| `CODE-ORCH-021` | `performValidation(...)`                   | Where does report data enter business validation?        |

---

# 35. RAG Retrieval Map

### Query: "How is IA initiated?"

Retrieve:


CODE-ORCH-001
CODE-ORCH-002
CODE-ORCH-003
CODE-ORCH-004
CODE-ORCH-007


Then supplement with:


flows/income-assessment-flow.md
04-business-logic.md


---

### Query: "Why is `/validate` returning a particular action?"

Retrieve:


CODE-ORCH-009
CODE-ORCH-010
CODE-ORCH-011
CODE-ORCH-012
CODE-ORCH-013


Then supplement with:


10-troubleshooting.md
09-configuration.md
toggles-and-ia-configurations.md


---

### Query: "Why did IA use Perfios instead of Zenith?"

Retrieve:


CODE-ORCH-015
CODE-ORCH-016
CODE-ORCH-017


Then retrieve:


CODE-CONFIG-* 
flows/perfios-flow.md
flows/zenith-flow.md


Key evidence to inspect:


application.assessmentMedium
enableZenithOrchAPI


---

### Query: "Perfios callback came but report was fetched through the wrong path"

Retrieve:


CODE-ORCH-018
CODE-ORCH-019
CODE-ORCH-017


and the report retrieval anchors.

Check:


callback identifier
vendor transaction ID
application.assessmentMedium
Zenith toggle
selected gateway


---

### Query: "Report was retrieved but downstream did not process it"

Retrieve:


CODE-ORCH-020
CODE-ORCH-021


Then retrieve:


07-kafka-events.md
06-database.md
08-error-handling.md


Trace:


report retrieval
→ OmniDocs
→ Mongo
→ Kafka event
→ consumer
→ business processing


---

# 36. Code Evidence vs Business Inference

The following are directly evidenced by the supplied snippets:

* `/initiate-application` is exposed by `IncomeAssessmentApplicationController`.
* `/validate` calls `versionResolver.primeBucket(...)`.
* `/generate-link` calls `versionResolver.primeBucket(...)`.
* `IncomeAssessmentApplicationServiceFacade` extends `ServiceFacade<IncomeAssessmentApplicationServiceRevamp>`.
* `ServiceFacade.executeWithVersion(...)` checks `VersionContext`.
* `/validate` produces `ValidateResponse`.
* `determineNextAction(...)` uses retry/error/action-related inputs.
* `/generate-link` receives `assessmentMedium`.
* `enableZenithOrchAPI` participates in Zenith vs Perfios selection.
* Zenith requires `ACCOUNT_AGGREGATOR` in the supplied branch.
* Perfios is the fallback branch in the supplied code.
* Report retrieval contains equivalent Zenith/Perfios branching.
* Excel report persistence involves OmniDocs → Mongo → Kafka event.
* JSON/report retrieval is followed by a separate `performValidation(...)` stage.
* The main application is persisted in `incomeAssessmentApplications`.

The following should only be added after the corresponding repository code is provided:

* exact application creation method
* exact initial IA status
* exact assessment-medium selection implementation
* complete version-bucket resolution algorithm
* exact service factory implementation
* complete callback delegation chain
* exact `ValidateResponse.ACTION` enum values
* exact direct CAP → GST/ITR branching implementation
* exact transaction-ID generation rules
* exact state transitions during report validation

This distinction is intentional: **RAG context should preserve uncertainty rather than convert assumptions into false implementation facts.**

---

# 37. Recommended Next Code Additions

The highest-value missing snippets for this file are:

1. Complete `IncomeAssessmentApplicationController.initiateApplication(...)`
2. Complete `CommonVersionResolver.primeBucket(...)`
3. `resolveFromBucket(...)`
4. `IncomeAssessmentApplicationServiceFactory`
5. Complete `initiateApplication(...)`
6. Complete `validate(...)`
7. Complete `getNextAction(...)`
8. Complete `determineNextAction(...)`
9. `validateAndGetIaApplicationDao(...)`
10. `getTransactionId(...)`
11. `handleZenithOrchJourneyLinkGeneration(...)`
12. `handleLinkGeneration(...)`
13. Complete `NewPerfiosCallbackController.callPerfios(...)`
14. Callback delegation into `PerfiosCallbackController`
15. Complete `performValidation(...)`

These additions will allow this file to move from a **routing map** into a highly accurate **execution trace**.

---

# 38. Core Orchestration Mental Model

For debugging IA code, use:


WHO
 ↓
API / Event entry point

WHICH APPLICATION
 ↓
incomeAssessmentId / applicationReferenceId / client transaction

WHICH VERSION
 ↓
CommonVersionResolver / VersionContext / Factory

WHICH FLOW
 ↓
assessmentMedium / configuration

WHICH VENDOR
 ↓
Zenith or Perfios

WHICH ATTEMPT
 ↓
vendor transaction ID / attempt metadata

WHICH OPERATION
 ↓
link / callback / report / validation

WHICH STATE
 ↓
Mongo application state + state guard

WHICH SIDE EFFECT
 ↓
OmniDocs / Kafka / downstream API

WHICH FINAL OUTCOME
 ↓
IA status / next event / UI action


The most useful RCA question remains:

> **At which exact orchestration boundary did the actual execution first diverge from the expected path?**
