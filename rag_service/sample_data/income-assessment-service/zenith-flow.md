# Zenith Flow

## Intent

Run Income Assessment (IA) through the Zenith / AA-Orchestrator journey when Zenith is enabled for the applicable partner/product configuration.

The Zenith flow is structurally similar to the Perfios flow, but the external journey APIs are selected through configuration. When the Zenith configuration is enabled for a product, IA routes the applicable journey operations to Zenith APIs instead of the corresponding Perfios APIs.

The key debugging question is:

> **Was Zenith actually enabled and selected for this application, and did the Zenith transaction lifecycle progress correctly from journey-link generation through status, report retrieval, validation, and final IA state?**

---

# 1. High-Level Flow

Conceptually:


IA Application
      |
      v
Partner/Product/Context Resolution
      |
      v
Configuration Resolution
      |
      +---- Zenith Disabled ----> Perfios / Existing Journey
      |
      +---- Zenith Enabled -----> Zenith Journey
                                      |
                                      v
                              Get Journey Link
                                      |
                                      v
                              User Redirected
                                      |
                                      v
                         Zenith Journey / AA Flow
                                      |
                                      v
                       Get Journey Transaction Status
                                      |
                                      v
                           Fetch Analytics Report
                                      |
                                      v
                            Business Validation
                                      |
                                      v
                         Update IA Application State
                                      |
                                      v
                         Kafka / Downstream Events
                                      |
                                      v
                             Final IA Outcome


Zenith should therefore be treated as a **journey implementation selected by configuration**, rather than as an entirely separate IA lifecycle.

---

# 2. Zenith vs Perfios Journey

The overall IA lifecycle remains similar:


Initiate IA
    ↓
Resolve configuration
    ↓
Select journey implementation
    ↓
Generate/Get journey link
    ↓
User completes external journey
    ↓
Fetch transaction status
    ↓
Fetch statement/analytics report
    ↓
Run IA business validation
    ↓
Update IA status
    ↓
Publish events / trigger downstream processing


The major difference is the external API used at each stage.

| IA Operation                   | Perfios Path                       | Zenith Path                             |
| ------------------------------ | ---------------------------------- | --------------------------------------- |
| Generate journey link          | `generate-link` / Perfios flow     | Zenith `get-journey-link`               |
| Fetch transaction status       | Perfios status API / callback flow | Zenith `get-journey-transaction-status` |
| Fetch insight/analytics report | Perfios report flow                | Zenith `get-analytics-report`           |
| External journey               | Perfios                            | Zenith / AA-Orchestrator                |
| Final IA processing            | Common IA business flow            | Common IA business flow                 |

The exact API names, paths, gateway methods, and request/response models should always be verified against the current implementation and configuration.

---

# 3. Configuration Determines Whether Zenith Is Used

Zenith is not necessarily used for every IA application.

The first question when debugging a Zenith issue is:

> **Was Zenith enabled for this application's partner/product configuration?**

The flow depends on configuration such as:


Partner
   +
Product
   +
Journey Context
   ↓
PartnerProductConfigurations
   ↓
Zenith-related configuration / toggle
   ↓
Zenith enabled?
   ↓
Select Zenith journey implementation


A common configuration-driven toggle is:


enableZenithOrchAPI


When this is enabled for the applicable partner/product context, IA uses Zenith / AA-Orchestrator APIs for the relevant journey.

When it is disabled, the application follows the existing configured journey path, such as Perfios.

### Important invariant

> **The presence of Zenith code or APIs in the repository does not mean a particular application is using Zenith.**

Always establish:


application
   ↓
partnerId + productCode + context
   ↓
resolved configuration
   ↓
enableZenithOrchAPI
   ↓
actual runtime branch


---

# 4. Configuration Resolution

Before tracing any Zenith API, establish how the application reached the Zenith branch.

Typical conceptual path:


Request
   ↓
Partner/Product Context
   ↓
ConfigFetcher
   ↓
PartnerProductConfigurations
   ↓
Zenith Configuration / Toggle
   ↓
enableZenithOrchAPI = true
   ↓
Zenith API Path


Relevant components include:

* `ConfigFetcher`
* `PartnerProductConfigurations`
* `CommonVersionResolver`
* `IncomeAssessmentApplicationServiceV3`
* Zenith-specific service/gateway classes
* `application.yaml`

For configuration debugging, inspect:

1. `partnerId`
2. `productCode`
3. journey/medium/context
4. resolved configuration
5. `enableZenithOrchAPI`
6. IA version
7. concrete service implementation selected
8. Zenith endpoint configuration

---

# 5. Application Initiation

The Zenith journey still starts from the normal IA application lifecycle.

Typical entry point:


POST /income-assessment-service/v1/initiate-application


Conceptually:


Partner Request
      ↓
Controller
      ↓
Version Resolution
      ↓
Configuration Resolution
      ↓
Create / Reuse IA Application
      ↓
Determine Journey
      ↓
Zenith enabled?
      ↓
Zenith Journey


The application record is persisted in:


incomeAssessmentApplications


Important identifiers to capture:


incomeAssessmentId
applicationReferenceId
commonClientTransactionId
serviceRequestId
partnerId
productCode


Do not assume these identifiers are interchangeable.

---

# 6. Zenith Journey Link

For Zenith-enabled journeys, the link-generation step uses the Zenith journey API rather than the equivalent Perfios API.

Conceptually:


IA Application
      ↓
Zenith enabled
      ↓
Get Journey Link
      ↓
Zenith / AA-Orchestrator
      ↓
Journey URL
      ↓
User Redirect


The Zenith operation is conceptually:


get-journey-link


This replaces the corresponding Perfios journey-link generation operation for the configured Zenith path.

### Important distinction

Successful `get-journey-link` means:

> Zenith successfully generated a journey link.

It does **not** mean:

> The user completed the Zenith journey.

Therefore:


get-journey-link success
        ≠
Zenith journey success


---

# 7. User Redirect / External Journey

After receiving the journey link:


IA
 ↓
Zenith get-journey-link
 ↓
Journey URL
 ↓
User redirected to Zenith
 ↓
User completes AA / statement journey


At this point, IA may be waiting for the external journey to progress.

A successful redirect should not automatically be interpreted as successful income assessment.

The following are separate milestones:


Link generated
      ↓
User redirected
      ↓
User started/completed external journey
      ↓
Zenith transaction reached required status
      ↓
Analytics report available
      ↓
IA validation completed


---

# 8. Zenith Transaction Status

After the external journey progresses, IA needs to determine the transaction state.

For Zenith, this is handled through:


get-journey-transaction-status


Conceptually:


IA Application
      ↓
Zenith Transaction
      ↓
get-journey-transaction-status
      ↓
Zenith Status
      ↓
Interpret Zenith Response
      ↓
Continue / Retry / Fail / Fetch Report


This stage is critical because:

> **A successful API response does not necessarily mean the IA journey succeeded.**

The Zenith response must be interpreted according to the current business logic.

Possible conceptual outcomes include:


Journey still in progress
        ↓
Retry / wait

Journey completed
        ↓
Fetch analytics report

Journey failed
        ↓
Map error / update IA state

Unexpected response
        ↓
Error handling / RCA


The exact Zenith statuses and their mappings should be taken from the current Zenith response models and business logic rather than inferred from API names.

---

# 9. Analytics Report

Once the Zenith journey reaches the appropriate state, IA fetches the analytics/insight report.

The Zenith operation is:


get-analytics-report


Conceptually:


Zenith Transaction
      ↓
Transaction Status = Ready
      ↓
get-analytics-report
      ↓
Analytics / Insight Report
      ↓
Parse / Persist
      ↓
Business Validation


### Important distinction

These are separate failure boundaries:


Transaction status API
        ↓
Report availability
        ↓
Report retrieval
        ↓
Report parsing
        ↓
Business validation


Therefore, if the Zenith transaction status is successful but IA remains stuck, do not immediately assume that the Zenith status API failed.

Check whether:

* the analytics report was requested
* Zenith returned the report
* the response was successfully parsed
* the report was persisted
* business validation executed
* the IA state transition succeeded
* the next Kafka event was published

---

# 10. Analytics Report → IA Business Validation

The Zenith report ultimately feeds the common IA business-processing layer.

Conceptually:


Zenith Analytics Report
        ↓
Income / Statement Data
        ↓
IA Business Rules
        ↓
Business Outcome
        ↓
IA Status


Relevant business rules may include:

* `incomeCreditGapRule`
* `chequeBounceLimitRule`
* `lastNMonthsIncomeRule`
* `numberOfIncomeCreditsRule`
* `statementStatusRule`

The important architectural distinction is:

> **Zenith provides the external journey and data; IA remains responsible for interpreting the data and determining the IA business outcome.**

Therefore a Zenith API success does not necessarily result in:


INCOME_ASSESSMENT_SUCCESS


The report can be successfully retrieved and still result in:


INCOME_ASSESSMENT_FAILED
INCOME_ASSESSMENT_REJECTED
INCOME_ASSESSMENT_REFERRED
POLICY_NORMS_NOT_MET


depending on the configured business rules and state.

---

# 11. IA Status Update

After Zenith data is processed, IA updates the application state.

The state is persisted in:


incomeAssessmentApplications


Conceptually:


Zenith Result
     ↓
Report Processing
     ↓
Business Validation
     ↓
State Guard
     ↓
MongoDB
     ↓
IA Status


Before concluding that a status update failed, inspect:

1. current application status
2. previous status
3. status type
4. business validation result
5. state guard
6. attempt information
7. callback/status timestamps
8. Zenith transaction identifier
9. persisted report/analytics data

A valid state guard can intentionally prevent a transition.

Therefore:


"Status did not change"


does not automatically mean:


"Database update failed"


---

# 12. Kafka and Downstream Propagation

After Zenith processing, IA may publish events for downstream consumers.

Conceptually:


Zenith Processing
      ↓
IA State Update
      ↓
Kafka Event
      ↓
Consumer
      ↓
Downstream API / DB
      ↓
Next State


The following are independent success boundaries:


Zenith API success
        ≠
IA processing success
        ≠
Mongo update success
        ≠
Kafka publish success
        ≠
Kafka consumer success
        ≠
Downstream API success


For example:


get-analytics-report
       ↓ success

IA validation
       ↓ success

Mongo status update
       ↓ success

Kafka publish
       ↓ FAILED

Downstream consumer
       ↓ never receives event


In such a case, the Zenith integration itself may have worked correctly even though the overall workflow did not complete.

---

# 13. Zenith API Integration Map

The Zenith journey can be thought of as a sequence of external operations:


┌─────────────────────────────┐
│ IA Application              │
└──────────────┬──────────────┘
               ↓
      Configuration Check
               ↓
      Zenith Enabled?
               ↓
┌─────────────────────────────┐
│ get-journey-link             │
└──────────────┬──────────────┘
               ↓
        User Redirect
               ↓
┌─────────────────────────────┐
│ Zenith / AA Journey         │
└──────────────┬──────────────┘
               ↓
┌─────────────────────────────┐
│ get-journey-transaction-   │
│ status                      │
└──────────────┬──────────────┘
               ↓
       Transaction Ready
               ↓
┌─────────────────────────────┐
│ get-analytics-report        │
└──────────────┬──────────────┘
               ↓
      Analytics / Insight
               ↓
┌─────────────────────────────┐
│ IA Business Validation      │
└──────────────┬──────────────┘
               ↓
        IA Status Update
               ↓
       Kafka / Downstream


---

# 14. Zenith Configuration and Endpoint Resolution

Zenith API behavior depends on endpoint configuration.

Relevant static configuration is under:


platform.gateway.*


Important configuration concepts include:


platform.gateway.zenithBaseUrl
platform.gateway.initiateBsaEnc


The exact endpoint/property names should always be verified against the current `application.yaml`.

For the Zenith BSA integration, an important endpoint is:


/aa-orch/fiu/api/v1/initiateBSA


When investigating an HTTP failure, verify:


Base URL
   +
Configured path
   +
HTTP method
   +
Headers
   +
Content-Type
   +
Request body
   +
Environment
   +
Stub/mock configuration


Do not immediately assume that a 404/405/415 is a Zenith business failure.

---

# 15. Zenith BSA Flow

The BSA initiation flow is related to the Zenith journey but should be treated as a distinct integration boundary.

Conceptually:


IA
 ↓
BSA Initiation
 ↓
Zenith / AA-Orchestrator
 ↓
POST /aa-orch/fiu/api/v1/initiateBSA
 ↓
BSA / AA Processing
 ↓
Statements / Analytics
 ↓
IA Processing


Relevant code anchors include:


InitiateBsaController
InitiateBsaModels
ZenithOrchestratorGateway


When the BSA API fails, determine whether the failure occurred at:


Controller validation
      ↓
Request construction
      ↓
Gateway
      ↓
HTTP request
      ↓
Zenith / AA-Orchestrator
      ↓
Response parsing
      ↓
Business handling


---

# 16. Zenith Error Handling

Zenith errors pass through multiple layers.

Conceptually:


Zenith Response
      ↓
HTTP / Network Error
      ↓
Zenith Gateway
      ↓
Error Mapping
      ↓
IA Error
      ↓
Business Decision
      ↓
Status / Event / Response


Configuration-backed Zenith error mappings may influence the final IA behavior.

Relevant configuration group:


ZenithErrorCodeAndConfigMapping


Therefore, when a Zenith error results in an unexpected IA status, inspect both:


Zenith response


and:


Zenith error-code mapping configuration


before concluding that the service has incorrect business logic.

---

# 17. Retry and Timeout Behavior

Zenith operations may be affected by retry configuration and reactive retry operators.

Typical patterns include:


retry
retryWhen
onErrorResume
onErrorMap
switchIfEmpty


The important distinction is:

> **A configured retry does not automatically mean every Zenith error is retryable.**

For a failed Zenith operation, determine:


Did the request fail?
        ↓
Was the error retryable?
        ↓
Was retry configured?
        ↓
Was retry actually triggered?
        ↓
How many attempts occurred?
        ↓
What happened after the final attempt?


For transaction-status operations, also distinguish:


Zenith transaction still processing


from:


Zenith API request failed


These represent different failure modes.

---

# 18. Missing Callback / Status Progression

Zenith journeys can also involve asynchronous progression.

When the expected Zenith result does not reach IA, investigate the full chain:


Zenith generated transaction
        ↓
Zenith journey progressed
        ↓
Expected callback/notification generated?
        ↓
IA received it?
        ↓
Kafka event published?
        ↓
Kafka consumer received it?
        ↓
State guard accepted it?
        ↓
MongoDB updated?
        ↓
get-journey-transaction-status invoked if required?
        ↓
Analytics report fetched?
        ↓
Next event published?


Do not collapse all of these into:

> "Zenith callback was not received."

First establish where the chain stopped.

---

# 19. Multi-Attempt / Retry Scenario

A single IA application may have multiple external journey attempts.

Conceptually:


IA Application A
   |
   +-- Zenith Transaction T1
   |       |
   |       +-- Journey incomplete / delayed
   |
   +-- Retry
           |
           +-- Zenith Transaction T2
                   |
                   +-- Journey completes


A late event or status response associated with `T1` must not automatically be interpreted as the result of `T2`.

Always correlate:


incomeAssessmentId
applicationReferenceId
commonClientTransactionId
serviceRequestId
Zenith transaction ID
attempt number
event ID
timestamp


### Critical invariant

> **Application identity and Zenith transaction identity are different dimensions of the journey.**

Never debug a multi-attempt issue using only `applicationReferenceId`.

---

# 20. Common Zenith Failure Patterns

## 20.1 Zenith APIs not being called

Check:


Partner/Product
      ↓
Resolved configuration
      ↓
enableZenithOrchAPI
      ↓
IA version
      ↓
Concrete service implementation
      ↓
Zenith branch


Possible causes:

* Zenith disabled for the product
* wrong partner/product configuration
* wrong configuration environment
* wrong version bucket
* unexpected journey context
* code path bypassing Zenith branch

---

## 20.2 `get-journey-link` fails

Investigate:


IA request
→ Zenith configuration
→ Base URL
→ Endpoint path
→ HTTP method
→ Request payload
→ Headers
→ Zenith response


For 404/405/415 specifically, verify endpoint and request construction before investigating business rules.

---

## 20.3 Journey link generated but IA remains in progress

Remember:


get-journey-link success


only proves link generation.

Check:

* user redirect
* Zenith journey progress
* transaction status
* callback/notification
* `get-journey-transaction-status`
* retry/timeout behavior

---

## 20.4 Transaction status succeeds but report is missing

Trace:


get-journey-transaction-status
       ↓
Does Zenith consider transaction ready?
       ↓
get-analytics-report
       ↓
HTTP response
       ↓
Parsing
       ↓
Persistence


Do not assume successful transaction status guarantees report availability.

---

## 20.5 Analytics report fetched but IA status is incorrect

Trace:


Analytics Report
       ↓
Parsing
       ↓
Business Rules
       ↓
Business Outcome
       ↓
State Guard
       ↓
Mongo Update
       ↓
Kafka Event


The problem may be in IA business validation rather than Zenith.

---

## 20.6 Zenith API succeeds but downstream remains stuck

Check:


Zenith API
      ↓
IA processing
      ↓
MongoDB
      ↓
Kafka Producer
      ↓
Kafka Topic
      ↓
Consumer
      ↓
Downstream API


Kafka publication and downstream processing are separate failure boundaries.

---

# 21. Zenith Debugging Decision Tree


Is Zenith expected for this application?
        |
        +-- NO → Check partner/product configuration
        |
        +-- YES
             |
             v
Is enableZenithOrchAPI resolved as enabled?
             |
             +-- NO → Configuration/version/context issue
             |
             +-- YES
                  |
                  v
Was get-journey-link called?
                  |
                  +-- NO → Service/version/branch issue
                  |
                  +-- YES
                       |
                       v
Did get-journey-link succeed?
                       |
                       +-- NO → Endpoint/request/Zenith error
                       |
                       +-- YES
                            |
                            v
Did Zenith journey progress?
                            |
                            +-- NO → User/vendor journey issue
                            |
                            +-- YES
                                 |
                                 v
Did transaction status reach expected state?
                                 |
                                 +-- NO → Status/retry/timeout issue
                                 |
                                 +-- YES
                                      |
                                      v
Was get-analytics-report called?
                                      |
                                      +-- NO → Orchestration/state issue
                                      |
                                      +-- YES
                                           |
                                           v
Was analytics report retrieved and parsed?
                                           |
                                           +-- NO → Zenith/report/parsing issue
                                           |
                                           +-- YES
                                                |
                                                v
Did business validation complete?
                                                |
                                                +-- NO → IA business-processing issue
                                                |
                                                +-- YES
                                                     |
                                                     v
Was IA status persisted?
                                                     |
                                                     +-- NO → State/persistence issue
                                                     |
                                                     +-- YES
                                                          |
                                                          v
Was next Kafka/downstream processing successful?


---

# 22. Zenith Incident Investigation Checklist

When investigating a Zenith issue, capture:

### Application


applicationReferenceId
incomeAssessmentId
commonClientTransactionId
serviceRequestId
partnerId
productCode


### Configuration


enableZenithOrchAPI
iaVersion
VersionBuckets
relevant PartnerProductConfigurations
Zenith endpoint configuration


### Zenith


Zenith transaction ID
journey ID, if available
get-journey-link request/response
get-journey-transaction-status request/response
get-analytics-report request/response
Zenith error code
Zenith response status


### Workflow


current IA status
previous IA status
statusType
attempt number
retry count
callback/notification timestamp
event ID
Kafka topic
consumer group


### Timeline

Always reconstruct:


Application initiated
        ↓
Zenith selected
        ↓
Journey link generated
        ↓
User redirected
        ↓
Zenith transaction created/progressed
        ↓
Transaction status checked
        ↓
Analytics report fetched
        ↓
Business validation
        ↓
IA status update
        ↓
Kafka event
        ↓
Downstream processing


---

# 23. Code Anchors

High-value repository search anchors:


enableZenithOrchAPI
Zenith
ZenithOrchestratorGateway
InitiateBsaController
InitiateBsaModels
getJourneyLink
getJourneyTransactionStatus
getAnalyticsReport
ZenithErrorCodeAndConfigMapping
platform.gateway
IncomeAssessmentApplicationServiceV3
CommonVersionResolver
ConfigFetcher
PartnerProductConfigurations
IncomeAssessmentApplication
IncomeAssessmentApplicationDao
IncomeAssessmentRepository
IncomeAssessmentApplicationEvent
IncomeAssessmentApplicationEventProducer


Search for the actual method names in the current repository before assuming a class or method boundary.

---

# 24. Zenith-to-Context-Document Map

Use the context documents together:

| Question                                        | Primary Context                      |
| ----------------------------------------------- | ------------------------------------ |
| Is Zenith enabled for this product?             | `configurations.md`                  |
| Which API does Zenith use?                      | `integrations.md`                    |
| What is the complete Zenith lifecycle?          | `zenith-flow.md`                     |
| Where is IA state stored?                       | `database.md`                        |
| Why did IA status change?                       | `business-logic.md`                  |
| Why did Zenith/API fail?                        | `error-handling.md`                  |
| Why did the event/downstream flow stop?         | `kafka-events.md`                    |
| Where should I debug first?                     | `troubleshooting.md`                 |
| How does Zenith fit into complete IA lifecycle? | `income-assessment-flow.md`          |
| How does Perfios compare with Zenith?           | `perfios-flow.md` + `zenith-flow.md` |

---

# 25. RAG Retrieval Guidance

This document should retrieve strongly for questions containing:


Zenith flow
Zenith journey
Zenith API
Zenith enabled
enableZenithOrchAPI
get journey link
get-journey-link
get journey transaction status
get-journey-transaction-status
get analytics report
get-analytics-report
Zenith transaction
Zenith status
Zenith report
Zenith callback
Zenith BSA
AA Orchestrator
Zenith error
Zenith retry
Zenith stuck
Zenith status not updated
Zenith report not fetched
Zenith API not called


For questions about why Zenith is selected, retrieve:


zenith-flow.md
+
configurations.md
+
income-assessment-flow.md


For Zenith API failures:


zenith-flow.md
+
integrations.md
+
error-handling.md


For Zenith status/callback problems:


zenith-flow.md
+
kafka-events.md
+
database.md
+
troubleshooting.md


For incorrect final IA outcomes:


zenith-flow.md
+
business-logic.md
+
database.md
+
error-handling.md


---

# 26. Core Zenith Invariants

1. **Zenith usage is configuration-driven.**
2. **`enableZenithOrchAPI` must be evaluated in the correct partner/product/context.**
3. **Zenith link generation does not mean the external journey completed.**
4. **Zenith transaction status and analytics report retrieval are separate stages.**
5. **A successful Zenith API response does not necessarily mean IA succeeded.**
6. **Zenith provides external journey/data; IA owns business validation and final IA state.**
7. **IA application identity and Zenith transaction identity are different.**
8. **A single IA application may have multiple Zenith transaction attempts.**
9. **Late responses/events must be correlated to the correct transaction/attempt.**
10. **MongoDB state and Kafka/downstream state are not atomic.**
11. **A Zenith integration success does not imply Kafka/downstream success.**
12. **HTTP 404/405/415 should first be investigated as endpoint/request/environment problems.**
13. **Configured retry does not mean every Zenith failure is retryable.**
14. **Error-code mappings can change the business interpretation of Zenith failures without changing integration code.**
15. **The actual repository implementation and resolved configuration are the source of truth over historical documentation.**

---

# 27. Preferred Mental Model

For any Zenith issue, trace:


Which IA application?
        ↓
Which partner/product?
        ↓
Which context/configuration?
        ↓
Was Zenith enabled?
        ↓
Which IA version?
        ↓
Which Zenith API?
        ↓
Was the Zenith transaction created?
        ↓
Which transaction/attempt?
        ↓
Did the journey progress?
        ↓
What did get-journey-transaction-status return?
        ↓
Was get-analytics-report called?
        ↓
Was the report retrieved and parsed?
        ↓
Which IA business rules executed?
        ↓
Which state guard executed?
        ↓
What was persisted in MongoDB?
        ↓
Which Kafka event was published?
        ↓
Which consumer processed it?
        ↓
What downstream action occurred?
        ↓
What was the final IA state?


The key RCA question is:

> **At which step did the Zenith transaction lifecycle first diverge from the expected IA flow?**
