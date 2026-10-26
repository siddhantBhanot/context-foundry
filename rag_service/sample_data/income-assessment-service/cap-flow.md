# CAP Integration Flow

## Intent

CAP is an **external platform that integrates with the Income Assessment (IA) Service**.

CAP can invoke IA to initiate an Income Assessment journey, similar to other upstream platforms such as Maximus. After IA is initiated, IA owns the Income Assessment lifecycle and routes the journey through the configured external assessment provider, primarily **Perfios or Zenith**.

Once IA reaches the relevant business outcome, IA can synchronize the outcome back to CAP through the CAP consent-status API when CAP synchronization is enabled.

Therefore, the CAP integration has two directions:

 id="caparch1"
                    UPSTREAM
                       │
                       │ Initiate IA
                       ▼
┌──────────────────────────────────────┐
│              IA Service              │
└──────────────────┬───────────────────┘
                   │
            Journey Selection
                   │
            ┌──────┴──────┐
            ▼             ▼
         Perfios        Zenith
            │             │
            └──────┬──────┘
                   │
                   ▼
             IA Processing
                   │
                   ▼
              IA Outcome
                   │
                   │ Status Sync
                   ▼
┌──────────────────────────────────────┐
│                 CAP                  │
└──────────────────────────────────────┘
                       │
                    DOWNSTREAM


### Core architectural principle

> **CAP is an upstream consumer of IA for journey initiation, while IA can also communicate the resulting IA status back to CAP through a separate status-synchronization integration.**

CAP should therefore not be treated as the IA journey itself. The IA journey after initiation is handled by the IA service and its configured Perfios/Zenith flow.

---

# 1. CAP's Role in the IA Architecture

CAP and IA are separate platforms.

CAP can act as the platform from which an IA journey is initiated:

 id="caprole1"
CAP
 │
 │ Initiate IA
 ▼
IA Service
 │
 ├── Configuration / Version Resolution
 │
 ├── Perfios Journey
 │
 └── Zenith Journey


IA subsequently processes the Income Assessment and determines the business outcome.

After that, IA may synchronize the outcome back to CAP:

 id="caprole2"
IA Outcome
    │
    ▼
CAP Status Synchronization
    │
    ▼
CAP


This means CAP has two logical interaction points with IA:

1. **CAP → IA:** initiate the Income Assessment.
2. **IA → CAP:** synchronize the resulting status.

These two interactions should be debugged independently.

---

# 2. IA Entry Point

The IA service has a single primary entry point for starting an Income Assessment:

 id="capentry1"
POST /income-assessment-service/v1/initiate-application


CAP can invoke this API as an upstream client.

Conceptually:

 id="capentry2"
CAP
  ↓
POST /income-assessment-service/v1/initiate-application
  ↓
IA Application
  ↓
Configuration / Version Resolution
  ↓
IA Journey


The fact that CAP initiated the request does not mean that CAP controls the subsequent IA journey.

Once the request enters IA, the IA service determines how the Income Assessment proceeds.

---

# 3. CAP Is Not the Journey Provider

The IA journey after initiation is separate from the CAP integration.

The high-level flow is:

 id="capjourney1"
CAP
  │
  │ /initiate-application
  ▼
IA
  │
  ▼
Configuration
  │
  ├───────────────┐
  ▼               ▼
Perfios          Zenith
  │               │
  └───────┬───────┘
          ▼
     IA Processing
          │
          ▼
      IA Outcome


Therefore:

 id="capjourney2"
CAP
   ≠
Perfios
   ≠
Zenith


CAP is the **upstream platform/client**.

Perfios and Zenith are the **external journey implementations/providers** used by IA after initiation.

---

# 4. CAP-Initiated IA Flow

When CAP initiates IA, the conceptual sequence is:

 id="capflow1"
CAP
 ↓
/initiate-application
 ↓
IA Controller
 ↓
Version / Configuration Resolution
 ↓
Create or Reuse IA Application
 ↓
Determine applicable journey
 ↓
Perfios OR Zenith
 ↓
External Journey
 ↓
IA Processing
 ↓
IA Business Outcome


The actual journey depends on configuration and application context.

For example:

 id="capflow2"
CAP
 ↓
IA /initiate-application
 ↓
Partner/Product/Context
 ↓
Configuration
 ↓
Zenith enabled?
 │
 ├── YES → Zenith Flow
 │
 └── NO  → Existing configured flow
             └── Perfios / applicable journey


See `configurations.md`, `perfios-flow.md`, and `zenith-flow.md` for the detailed journey behavior.

---

# 5. CAP Initiation vs CAP Status Sync

These are two different interactions.

### CAP → IA

CAP invokes IA:

 id="capsync1"
CAP
 ↓
/initiate-application
 ↓
IA


This starts the IA lifecycle.

### IA → CAP

IA synchronizes the outcome:

 id="capsync2"
IA
 ↓
CAP status synchronization
 ↓
CAP update-status API
 ↓
CAP


The two flows should not be conflated.

A problem with CAP initiation is an **IA entry/integration problem**.

A problem with CAP status synchronization is a **post-processing synchronization problem**.

---

# 6. CAP Status Synchronization

After IA reaches the relevant outcome, IA can synchronize the status to CAP.

The internal IA entry point for this operation is:

 id="capstatus1"
CapSyncService.syncCapConsentStatus(...)


There is also a facade wrapper:

 id="capstatus2"
CapSyncServiceFacade.syncCapConsentStatus(...)


These are **internal IA service methods**, not external IA entry points.

Relevant implementation areas:

 id="capstatus3"
src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/multibank/service/CapSyncService.kt

src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/revamp/facade/impl/CapSyncServiceFacade.kt


---

# 7. CAP Status Sync Sequence

The conceptual status synchronization flow is:

 id="capstatus4"
IA reaches relevant outcome
          ↓
Check capSyncEnabled
          ↓
CAP sync enabled?
      │
      ├── NO → Skip synchronization
      │
      └── YES
           ↓
      Map IA status
           ↓
      Build CAP request
           ↓
      PATCH CAP update-status API
           ↓
      CAP response
           ↓
      Update eventStatus in IA


The implementation reads:

 id="capstatus5"
capSyncEnabled


from:

 id="capstatus6"
incomeAssessmentApplication.config


When enabled, IA maps its internal status to the corresponding CAP `EventStatus` and constructs the CAP update request.

---

# 8. CAP Sync Configuration

CAP status synchronization is controlled by configuration.

Conceptually:

 id="capconfig1"
IA Application
      ↓
incomeAssessmentApplication.config
      ↓
capSyncEnabled
      ↓
CAP synchronization


Therefore, when CAP does not receive a status update, first determine whether synchronization was enabled for that application.

Important distinction:

 id="capconfig2"
capSyncEnabled = false
        ≠
CAP integration failure


It means the synchronization path was not enabled for that application context.

---

# 9. IA Status → CAP EventStatus

IA does not necessarily send its internal status directly to CAP.

Instead:

 id="capmapping1"
IA Status
   ↓
getEventStatusByStatus(...)
   ↓
CAP EventStatus


Examples:

| IA Status                    | CAP EventStatus |
| ---------------------------- | --------------- |
| `INCOME_ASSESSMENT_SUCCESS`  | `COMPLETED`     |
| `POLICY_NORMS_NOT_MET`       | `REJECTED`      |
| `INCOME_ASSESSMENT_REJECTED` | `REJECTED`      |
| `INCOME_ASSESSMENT_FAILED`   | `FAILED`        |

The complete mapping must be verified against the current implementation.

### Debugging implication

If CAP receives an unexpected status, investigate:

 id="capmapping2"
IA status
   ↓
getEventStatusByStatus(...)
   ↓
mapped EventStatus
   ↓
CAP request


before concluding that CAP changed the status incorrectly.

---

# 10. CAP Update Request

The request sent to CAP is constructed using:

 id="caprequest1"
CapConsentStatusUpdateRequest(
    capRefId,
    status,
    reason
)


Conceptually:

 id="caprequest2"
IA Application
     │
     ├── capRefId
     ├── mapped CAP status
     └── reason
     │
     ▼
CapConsentStatusUpdateRequest
     │
     ▼
CAP Update Status API


The important CAP correlation identifier is:

 id="caprequest3"
capRefId


Other useful identifiers when tracing the request include:

 id="caprequest4"
capRefId
applicationReferenceId
incomeAssessmentId
commonClientTransactionId
serviceRequestId


These identifiers represent different layers of the workflow and should not be treated as interchangeable.

---

# 11. CAP Update Status API

IA calls the CAP update-status API using `PATCH`.

The endpoint is configuration-driven.

Relevant configuration includes:

 id="capendpoint1"
platform.endpoints.cap-service.base-url


and:

 id="capendpoint2"
platform.endpoints.cap-service.interactions.update-status-uri.path


Authentication/token configuration is associated with:

 id="capendpoint3"
platform.services.access-token


Conceptually:

 id="capendpoint4"
IA
 ↓
CapSyncService
 ↓
Build CapConsentStatusUpdateRequest
 ↓
PATCH CAP update-status API
 ↓
CAP


The actual URL should always be resolved from the current environment configuration.

---

# 12. Successful CAP Synchronization

When the CAP API call succeeds, IA updates the corresponding synchronization state:

 id="capresult1"
CAP API success
      ↓
eventStatus update
      ↓
IA application persistence


This means the IA application can contain both:

 id="capresult2"
status
eventStatus


These represent different concepts.

For example:

 id="capresult3"
status      = INCOME_ASSESSMENT_SUCCESS
eventStatus = COMPLETED


Here:

* `status` represents the IA business outcome.
* `eventStatus` represents the CAP synchronization/event state.

---

# 13. CAP Sync Is Best-Effort

CAP status synchronization is treated as a best-effort side effect.

The important behavior is:

 id="capbest1"
IA Business Processing
        ↓
IA Outcome
        ↓
CAP Sync
        │
        ├── Success
        │      ↓
        │   eventStatus update
        │
        └── Failure
               ↓
        Original IA business result preserved


Therefore:

 id="capbest2"
IA Success
+
CAP Sync Failure
=
IA Success + CAP synchronization issue


It should not automatically become:

 id="capbest3"
IA Failure


This distinction is particularly important during RCA.

A CAP synchronization failure should generally be investigated as a separate integration problem from the underlying IA journey.

---

# 14. Complete CAP ↔ IA Flow

The complete interaction can be visualized as:

 id="capcomplete1"
                 CAP PLATFORM
                      │
                      │ 1. Initiate IA
                      ▼
             /initiate-application
                      │
                      ▼
                IA SERVICE
                      │
                      │ 2. Resolve configuration
                      ▼
                IA Application
                      │
             ┌────────┴────────┐
             │                 │
             ▼                 ▼
          Perfios            Zenith
             │                 │
             └────────┬────────┘
                      │
                      │ 3. External journey
                      ▼
                IA Processing
                      │
                      │ 4. Business validation
                      ▼
                 IA Outcome
                      │
                      │ 5. CAP status sync
                      ▼
              CAP Update API
                      │
                      ▼
                 CAP PLATFORM


The five major boundaries are:

 id="capbound1"
1. CAP → IA initiation
2. IA → Perfios / Zenith routing
3. Perfios / Zenith → IA processing
4. IA → business outcome
5. IA → CAP status synchronization


---

# 15. CAP Initiation Failure

If CAP invokes IA but IA does not start the expected journey, investigate the **incoming IA integration**.

Trace:

 id="capinitfail1"
CAP
 ↓
/initiate-application
 ↓
Request received by IA?
 ↓
Request validation
 ↓
Partner/Product/Context
 ↓
Configuration
 ↓
Version Resolution
 ↓
IA Application creation/reuse
 ↓
Journey selection


Potential areas include:

* invalid request
* authentication/context issue
* partner/product configuration
* version routing
* application creation/reuse
* incorrect journey configuration

Do not start with CAP status synchronization if the IA application was never successfully initiated.

---

# 16. Perfios / Zenith Failure After CAP Initiation

If CAP successfully invokes IA but the IA journey does not complete, investigate the selected journey.

Determine:

 id="capjourneyfail1"
Was IA initiated?
      ↓
Which configuration was resolved?
      ↓
Which journey was selected?
      ↓
Perfios or Zenith?
      ↓
Where did that journey stop?


For Perfios:

 id="capjourneyfail2"
perfios-flow.md


For Zenith:

 id="capjourneyfail3"
zenith-flow.md


CAP itself is not necessarily the source of the failure.

---

# 17. IA Completed but CAP Was Not Updated

If IA reached the expected outcome but CAP did not reflect it, switch the investigation to the synchronization path.

Trace:

 id="capnotupdated1"
IA Outcome
    ↓
capSyncEnabled
    ↓
syncCapConsentStatus(...)
    ↓
getEventStatusByStatus(...)
    ↓
CapConsentStatusUpdateRequest
    ↓
PATCH CAP API
    ↓
CAP Response
    ↓
eventStatus persistence


This separates:

 id="capnotupdated2"
IA journey problem


from:

 id="capnotupdated3"
CAP synchronization problem


---

# 18. CAP Status Mismatch

If CAP shows the wrong status, investigate the entire mapping chain:

 id="capmismatch1"
IA Business Status
       ↓
getEventStatusByStatus(...)
       ↓
CAP EventStatus
       ↓
Request Payload
       ↓
CAP API


Also verify the correct IA application using:

 id="capmismatch2"
capRefId
applicationReferenceId
incomeAssessmentId


A status mismatch can be caused by:

* incorrect application correlation
* unexpected IA status
* status mapping
* incorrect request payload
* CAP API behavior
* stale CAP state

---

# 19. Multiple IA Attempts

The IA application may have multiple external journey attempts.

For example:

 id="capattempt1"
CAP
 ↓
IA Application A
 ↓
Perfios / Zenith Attempt 1
 ↓
Retry
 ↓
Perfios / Zenith Attempt 2
 ↓
IA Outcome
 ↓
CAP Sync


When investigating such cases, distinguish:

 id="capattempt2"
IA application


from:

 id="capattempt3"
vendor transaction / journey attempt


and from:

 id="capattempt4"
CAP reference


A late callback or vendor response from an earlier attempt must not automatically be associated with the latest attempt.

---

# 20. CAP Debugging Decision Tree

 id="capdecision1"
Did CAP invoke /initiate-application?
        |
        +-- NO → CAP/upstream issue
        |
        +-- YES
             |
             v
Did IA receive and accept the request?
             |
             +-- NO → IA entry/integration issue
             |
             +-- YES
                  |
                  v
Was IA application created/reused?
                  |
                  +-- NO → IA persistence/orchestration issue
                  |
                  +-- YES
                       |
                       v
Which journey was selected?
                       |
                  +----+----+
                  |         |
                  v         v
               Perfios    Zenith
                  |         |
                  +----+----+
                       |
                       v
Did the IA journey complete?
                       |
                       +-- NO → Debug selected journey
                       |
                       +-- YES
                            |
                            v
                       IA Outcome
                            |
                            v
                    Is CAP sync enabled?
                            |
                       +----+----+
                       |         |
                       v         v
                      NO        YES
                       |         |
                 Skip sync       v
                           syncCapConsentStatus(...)
                                  |
                                  v
                           Status mapping
                                  |
                                  v
                           CAP API called?
                                  |
                            +-----+-----+
                            |           |
                            v           v
                           NO          YES
                            |           |
                       IA sync path     v
                          issue     CAP response
                                        |
                                  +-----+-----+
                                  |           |
                                  v           v
                                Error       Success
                                  |           |
                                  v           v
                            CAP integration  eventStatus
                               issue         persistence


---

# 21. CAP Incident Investigation Checklist

### Upstream / Initiation

 id="capcheck1"
CAP platform
/initiate-application
request timestamp
request ID
partnerId
productCode
applicationReferenceId


### IA Application

 id="capcheck2"
incomeAssessmentId
applicationReferenceId
commonClientTransactionId
serviceRequestId
current status
statusType
IA version


### Journey

 id="capcheck3"
selected journey
Perfios / Zenith
vendor transaction ID
attempt number
journey timestamps
callback/status timestamps


### CAP Synchronization

 id="capcheck4"
capRefId
capSyncEnabled
IA status
mapped CAP EventStatus
eventStatus
CAP request
CAP response


### API

 id="capcheck5"
CAP base URL
update-status path
HTTP method
request payload
response status
response body
authentication/token behavior
environment


---

# 22. Common CAP Failure Patterns

## CAP invokes IA but IA journey does not start

Investigate:

 id="capfailure1"
CAP request
 ↓
IA /initiate-application
 ↓
Request validation
 ↓
Configuration
 ↓
Version resolution
 ↓
Application creation


---

## CAP invokes IA successfully but IA journey fails

Investigate the selected journey:

 id="capfailure2"
CAP
 ↓
IA
 ↓
Perfios / Zenith
 ↓
Journey failure


Use the corresponding journey context document.

---

## IA succeeds but CAP status is not updated

Investigate:

 id="capfailure3"
IA Outcome
 ↓
capSyncEnabled
 ↓
syncCapConsentStatus(...)
 ↓
CAP API


---

## CAP receives an unexpected status

Investigate:

 id="capfailure4"
IA status
 ↓
getEventStatusByStatus(...)
 ↓
CAP EventStatus
 ↓
CAP request


---

## CAP API fails but IA succeeds

Treat these as separate outcomes:

 id="capfailure5"
IA = successful
CAP sync = failed


The CAP failure should not automatically be treated as an IA business failure.

---

# 23. Source-of-Truth Hierarchy

For CAP integration behavior, prefer:

1. `CapSyncService.kt`
2. `CapSyncServiceFacade.kt`
3. CAP request/response models
4. CAP gateway/client implementation
5. `application.yaml`
6. IA application/entity/DAO behavior
7. tests/stubs
8. README or historical documentation

For the **CAP → IA initiation side**, the IA controller/service/version-routing implementation is the source of truth.

For the **IA → CAP synchronization side**, `CapSyncService` and the CAP gateway/configuration are the primary sources of truth.

---

# 24. Cross-Document Retrieval Map

| Question                                               | Primary Context                             |
| ------------------------------------------------------ | ------------------------------------------- |
| How does CAP interact with IA?                         | `cap-flow.md`                               |
| How does CAP initiate IA?                              | `cap-flow.md` + `income-assessment-flow.md` |
| Which IA journey runs after CAP initiation?            | `configurations.md`                         |
| How does Perfios execute after CAP initiation?         | `perfios-flow.md`                           |
| How does Zenith execute after CAP initiation?          | `zenith-flow.md`                            |
| How is IA status determined?                           | `business-logic.md`                         |
| How is IA status synchronized to CAP?                  | `cap-flow.md`                               |
| Where is IA state stored?                              | `database.md`                               |
| Why did CAP sync fail?                                 | `error-handling.md` + `cap-flow.md`         |
| Why did an async event/downstream flow stop?           | `kafka-events.md`                           |
| Where should a CAP-related incident be debugged first? | `troubleshooting.md`                        |

---

# 25. RAG Retrieval Guidance

This document should retrieve strongly for:


CAP flow
CAP integration
CAP invokes IA
CAP initiate
CAP /initiate-application
CAP upstream
CAP platform
CAP client
CAP status sync
CAP consent status
CAP update-status
CAP sync
capSyncEnabled
capRefId
eventStatus
CapSyncService
syncCapConsentStatus
CapConsentStatusUpdateRequest
CAP status mismatch
CAP not updated
CAP API failure
CAP integration failure


For questions about the complete lifecycle:


CAP
→ IA
→ Perfios/Zenith
→ IA Outcome
→ CAP Sync


retrieve:


cap-flow.md
+
income-assessment-flow.md
+
perfios-flow.md / zenith-flow.md


For questions about whether CAP or another upstream platform invokes IA:


cap-flow.md
+
income-assessment-flow.md


For CAP status synchronization problems:


cap-flow.md
+
database.md
+
error-handling.md


For CAP initiation followed by a journey failure:


cap-flow.md
+
configurations.md
+
perfios-flow.md / zenith-flow.md
+
troubleshooting.md


---

# 26. Core CAP Integration Invariants

1. **CAP is a separate external platform that can invoke IA.**
2. **CAP is an upstream IA consumer/client, similar to other platforms such as Maximus.**
3. **`/initiate-application` is the IA entry point used to start the Income Assessment.**
4. **CAP does not itself execute the Perfios or Zenith journey.**
5. **After IA initiation, the IA service determines the applicable journey.**
6. **Perfios and Zenith are journey implementations/providers used by IA.**
7. **CAP → IA initiation and IA → CAP status synchronization are separate interactions.**
8. **CAP status synchronization occurs after relevant IA processing/outcome determination.**
9. **`capSyncEnabled` controls whether IA synchronizes the outcome to CAP.**
10. **IA status and CAP `EventStatus` are different concepts.**
11. **IA status is mapped to CAP `EventStatus` before the CAP update call.**
12. **`capRefId` is the primary CAP correlation identifier.**
13. **CAP synchronization is best-effort and should not redefine the underlying IA business outcome.**
14. **CAP API failure does not automatically mean IA failed.**
15. **A CAP initiation failure and a CAP status-sync failure are different failure domains.**
16. **Application identity, vendor transaction identity, and CAP reference identity must be correlated separately.**
17. **The current implementation and resolved configuration are the source of truth.**

---

# 27. Preferred Mental Model

For any CAP-related issue, trace the interaction in this order:


Which external platform initiated IA?
        ↓
Was it CAP?
        ↓
Was /initiate-application called?
        ↓
Did IA accept the request?
        ↓
Which application was created/reused?
        ↓
Which partner/product/context?
        ↓
Which IA version?
        ↓
Which journey was selected?
        ↓
Perfios or Zenith?
        ↓
Did the external journey complete?
        ↓
What IA business outcome was determined?
        ↓
Was CAP synchronization enabled?
        ↓
Was syncCapConsentStatus(...) invoked?
        ↓
What IA status was mapped to CAP EventStatus?
        ↓
What capRefId was used?
        ↓
Was the CAP update-status API called?
        ↓
What did CAP return?
        ↓
Was eventStatus persisted?
        ↓
Does CAP reflect the expected outcome?


The key RCA question is:

> **Did the problem occur while CAP was initiating the IA journey, during the Perfios/Zenith IA journey itself, or after IA completed when its outcome was being synchronized back to CAP?**
