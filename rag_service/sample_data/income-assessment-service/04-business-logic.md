# Business Logic

## 1. Domain Overview

The **Income Assessment (IA) Service** is a stateful workflow service that determines an income-assessment outcome for a user/application.

The final outcome is **not determined by a single API call**. The workflow may involve:

* user/application context
* partner and product configuration
* selected income-assessment medium
* feature toggles
* vendor transaction initiation
* vendor callbacks
* vendor report/statement processing
* bank-statement validation rules
* ITR assessment
* downstream services
* Kafka events
* MongoDB application state
* retries, timeouts, and resume/re-entry logic

### Important mental model

Think of IA as a **state machine + orchestration layer**, rather than a synchronous decision engine.

A typical journey can look like:


User Request
    ↓
Resolve Partner/Product/Configuration
    ↓
Determine Assessment Journey
    ↓
Start Vendor Transaction / Generate Link
    ↓
User Completes Vendor Journey
    ↓
Vendor Callback
    ↓
Fetch / Process Vendor Data
    ↓
Apply Business Rules
    ↓
Update MongoDB State
    ↓
Publish Kafka Event
    ↓
Downstream Processing
    ↓
Final IA Outcome


A journey can diverge from this path because of:

* missing callback
* vendor timeout
* callback arriving late
* user retrying the journey
* downstream API failure
* MongoDB update failure
* Kafka publishing failure
* business-rule failure
* product/partner-specific configuration
* ITR flow requirements

**Source citations**

* `README.md:15-37`
* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/repository/IncomeAssessmentRepository.kt:66-172`
* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/revamp/service/impl/IncomeAssessmentApplicationServiceV3.kt:147-185`

---

# 2. Core Domain Concepts

## 2.1 IncomeAssessmentApplication

`IncomeAssessmentApplication` is the central domain object representing an income-assessment journey.

It contains the current workflow state and exposes guard methods that determine whether an operation or state transition is allowed.

When debugging a journey, inspect this object before assuming that an API failure is caused by the controller or downstream vendor.

Important guard methods include:

* `canUpdateApplicationStatusInDb()`
* `canUpdateApplicationStatusInPerfiosCallback()`
* `canProceedToDocumentsUpload()`
* `canProceedToItrDocumentsUpload(...)`
* `canProceedToItrAssessment()`
* `canProceedForLinkGeneration()`
* `canProceedForStartProcess()`
* `canProceedForStartTransaction()`
* `isTerminalItrStatus()`

These methods answer questions such as:

* Can the current request modify the application's status?
* Can a callback update the application?
* Can the user start another transaction?
* Can the journey move to ITR?
* Can document upload proceed?
* Is the ITR branch already terminal?
* Should a retry/resume operation be allowed?

**Source citation**

* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/domain/IncomeAssessmentApplication.kt:279-332`

---

# 3. Core Status Model

The application's status represents the current point in the IA workflow.

Important statuses include:

| Status                                | Business meaning                                            |
| ------------------------------------- | ----------------------------------------------------------- |
| `DOCUMENTS_NOT_UPLOADED`              | Required IA documents have not yet been uploaded            |
| `INCOME_ASSESSMENT_IN_PROGRESS`       | IA journey has started but final processing is not complete |
| `INCOME_ASSESSMENT_SUCCESS`           | Income assessment completed successfully                    |
| `INCOME_ASSESSMENT_FAILED`            | IA processing failed                                        |
| `POLICY_NORMS_NOT_MET`                | Business/policy validation criteria were not satisfied      |
| `INCOME_ASSESSMENT_REJECTED`          | IA journey resulted in rejection                            |
| `INCOME_ASSESSMENT_REFERRED`          | IA result requires referral/downstream handling             |
| `BANK_STATEMENT_ASSESSMENT_COMPLETED` | Bank-statement assessment stage completed                   |
| `ITR_DOCUMENTS_NOT_UPLOADED`          | ITR documents are required but not uploaded                 |
| `PROCEED_TO_ITR_ASSESSMENT`           | Workflow should continue to ITR assessment                  |
| `FINFORT_STATUS_IN_PROGRESS`          | FinFort-related processing is still in progress             |
| `BSA_PAUSED_PENDING_USER_DECISION`    | BSA flow is paused while waiting for user decision          |

The repository/persistence layer contains additional statuses related to:

* Finacle
* ITR retries
* timeout handling
* intermediate workflow states
* long-running asynchronous branches

**Important:** Do not infer terminal/non-terminal behavior solely from the status name. Check the corresponding guard/transition logic and repository enum.

**Source citations**

* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/domain/Status.kt:3-37`
* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/repository/IncomeAssessmentRepository.kt:274-312`

---

# 4. State Transition Rules / Guards

IA operations are protected by explicit state-transition guards.

The guards are important because an API can technically be invoked while the business workflow does **not permit the requested operation**.

### Key guards

#### `canUpdateApplicationStatusInDb()`

Determines whether the application status is currently allowed to be updated in MongoDB.

Use this when investigating:

* status not changing
* status unexpectedly remaining in progress
* retry not updating state
* callback attempting to overwrite an existing state

#### `canUpdateApplicationStatusInPerfiosCallback()`

Controls whether a Perfios callback is allowed to modify the application's status.

Use this when investigating:

* late Perfios callbacks
* duplicate callbacks
* callbacks arriving after a retry
* callback status not matching the current IA status

#### `canProceedForLinkGeneration()`

Determines whether the current application can generate another vendor/link transaction.

Relevant to:

* repeated IA attempts
* user retries
* transaction re-entry
* duplicate vendor journeys

#### `canProceedForStartProcess()`

Determines whether the workflow can start vendor processing.

#### `canProceedForStartTransaction()`

Determines whether a new vendor transaction can be started.

#### `canProceedToDocumentsUpload()`

Determines whether the workflow can enter document-upload processing.

#### `canProceedToItrDocumentsUpload(...)`

Determines whether the ITR document-upload stage is allowed.

#### `canProceedToItrAssessment()`

Determines whether the workflow can proceed to ITR assessment.

#### `isTerminalItrStatus()`

Determines whether the ITR state is terminal and therefore should not be advanced further.

**Source citation**

* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/domain/IncomeAssessmentApplication.kt:279-332`

---

# 5. Decision Inputs

Business behavior depends on multiple inputs. The same endpoint can therefore produce different outcomes for different partner/product combinations.

Primary decision inputs are:

1. **Partner**
2. **Product**
3. **Application/request context**
4. **Selected assessment medium**
5. **Current application status**
6. **Partner/product configuration**
7. **Feature toggles**
8. **Vendor callback payload**
9. **Vendor API response**
10. **Bank-statement validation results**
11. **ITR/document state**
12. **Previous transaction/retry state**

### Partner/Product Configuration

Configuration is retrieved through:

* `allPartnerProductConfigurations()`

Partner/product configuration can influence:

* journey behavior
* vendor selection
* validation behavior
* feature availability
* downstream processing
* flow-specific decisions

**Source citation**

* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/revamp/versionresolvers/CommonVersionResolver.kt:61-104`

### Request Context / KeyData

Request context is resolved into `KeyData`.

`KeyData` should be considered an important input when determining why the same API behaves differently for different requests.

**Source citation**

* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/controller/IncomeAssessmentApplicationController.kt:51-72`

### Feature Toggles

Journey-specific feature toggles are resolved using:

* `getJourneyWiseToggleName(...)`
* `fetchFeatureToggleFromIAConfig(...)`

Feature-toggle evaluation can change which business path is executed.

**Source citation**

* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/utils/ConfigFetcher.kt:676-712`

---

# 6. Configuration-Driven Business Rules

Bank-statement assessment is **rule-driven and configuration-dependent**.

Current/default rule families configured in `application.yaml` include:

* `incomeCreditGapRule`
* `chequeBounceLimitRule`
* `lastNMonthsIncomeRule`
* `numberOfIncomeCreditsRule`
* `statementStatusRule`

These rules determine whether bank-statement data satisfies the configured business criteria.

The README may contain older/default business terminology, including:

* salary-credit validation
* cheque-bounce validation

### Source-of-truth rule

When business terminology in the README differs from the current implementation/configuration:

> **Prefer the repository implementation and current configuration as the source of truth.**

Do not assume that an old README rule name maps exactly to the current implementation.

**Source citations**

* `src/main/resources/application.yaml:560-569`
* `README.md:46-55`

---

# 7. Vendor Transaction and Callback Model

Some IA journeys are asynchronous and involve a vendor transaction.

A simplified vendor flow is:


IA
 ↓
Start Transaction
 ↓
Generate/Receive Vendor Redirect URL
 ↓
User redirected to Vendor
 ↓
User completes vendor journey
 ↓
Vendor Callback
 ↓
IA Callback Consumer
 ↓
Fetch/Process Vendor Result
 ↓
Update Application State
 ↓
Publish Event


The vendor callback is therefore a **critical state-transition event**, not merely a notification.

When debugging vendor journeys, always correlate:

* application reference ID
* vendor transaction ID / vendor ID
* current IA status
* transaction attempt number
* callback arrival time
* callback payload
* downstream API calls
* retry count
* final MongoDB status
* Kafka event status

---

# 8. Retry, Timeout, and Late Callback Behavior

The IA workflow supports retries and asynchronous processing.

A user/application can therefore have **multiple transaction attempts** associated with the same application.

Important debugging scenario:


Attempt 1
  ↓
Vendor transaction started
  ↓
User leaves / callback delayed / callback missing
  ↓
IA remains IN_PROGRESS or eventually times out
  ↓
User retries

Attempt 2
  ↓
New vendor transaction
  ↓
User completes journey
  ↓
Callback received
  ↓
IA progresses successfully

Later:
Attempt 1 callback arrives


A late callback from an earlier attempt must be evaluated against the application's **current state and callback transition guards**.

This is why the chronological sequence of events matters when investigating:

* duplicate transactions
* status reverting unexpectedly
* `INCOME_ASSESSMENT_FAILED`
* stale callbacks
* retries being exhausted
* application stuck in `INCOME_ASSESSMENT_IN_PROGRESS`

### Debugging principle

Do not analyze an IA issue using only the final application status.

Reconstruct:


Application
→ Attempt 1
→ Vendor transaction
→ Callback / timeout
→ Retry
→ Attempt 2
→ Callback
→ DB update
→ Kafka event
→ Downstream consumer


The **order of events** can explain behavior that is otherwise inconsistent when looking only at the final MongoDB document.

---

# 9. Event + Database Consistency Pattern

A recurring orchestration pattern is:


1. Call downstream vendor/service
2. Update application/supporting-document state in MongoDB
3. Publish domain/observability event
4. Handle selected side-effect failures without breaking the primary user journey


This pattern is visible in:

* Perfios callback processing
* Zenith callback processing
* CAP synchronization

Relevant implementation behavior includes selective use of:

* `onErrorResume`
* asynchronous Kafka publishing
* MongoDB state updates
* downstream API calls

### Important distinction

Not every failure in this sequence has the same business impact.

For example:


Primary business operation succeeds
        ↓
MongoDB update succeeds
        ↓
Kafka publish fails
        ↓
User journey may still be allowed to continue


versus:


Primary vendor/API operation fails
        ↓
Business state cannot be established
        ↓
Journey may need to fail/retry


Therefore, when debugging an exception, determine whether the failing operation is:

* **business-critical**
* **state-critical**
* **event/observability side effect**
* **best-effort downstream processing**

Do not assume every logged exception should result in an IA failure.

**Source citations**

* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/kafka/consumer/PerfiosCallbackReceivedConsumer.kt:80-159`
* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/kafka/consumer/ZenithCallbackReceivedConsumer.kt:76-135`
* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/multibank/service/CapSyncService.kt:189-244`

---

# 10. Kafka Event Semantics

Kafka events are used to communicate IA state/results to downstream consumers.

Typical pattern:


IA business processing
      ↓
MongoDB state update
      ↓
Kafka event
      ↓
Downstream consumer
      ↓
Further business processing


When investigating a workflow stuck after a successful callback, check **both**:

1. whether MongoDB state was updated
2. whether the expected Kafka event was successfully published and consumed

A successful callback does not necessarily mean the complete workflow succeeded.

Potential failure points include:

* callback received but vendor report fetch failed
* report processing succeeded but DB update failed
* DB update succeeded but Kafka publishing failed
* Kafka event published but downstream consumer failed
* downstream consumer received an unexpected status

---

# 11. Callback Debugging Checklist

For callback-related incidents, retrieve and correlate the following information:

### Application

* `applicationReferenceId`
* current IA status
* previous IA status
* partner
* product
* assessment medium

### Vendor transaction

* vendor ID / vendor transaction ID
* transaction attempt
* transaction creation time
* callback time
* transaction status

### IA processing

* callback consumer execution
* vendor report/status API calls
* retry count
* timeout configuration
* guard-method result
* MongoDB update result

### Kafka

* event name
* event payload/status
* publish success/failure
* consumer processing
* downstream consumer result

### Recommended event timeline


T0  IA request
T1  Transaction created
T2  Redirect URL generated
T3  User enters vendor
T4  Vendor processing
T5  Callback expected
T6  Callback received / timeout
T7  Vendor result fetched
T8  IA status updated
T9  Kafka event published
T10 Downstream event consumed
T11 Final status


This timeline should be preferred over analyzing isolated logs.

---

# 12. Common Business Failure Patterns

## 12.1 Missing Vendor Callback


IA → Vendor
     ↓
User completes / abandons vendor journey
     ↓
Callback not received
     ↓
IA waits / retries status
     ↓
Timeout or failure


Possible outcomes depend on retry and timeout configuration.

When investigating, distinguish between:

* user abandoning the vendor journey
* vendor not sending callback
* callback sent but not received by IA
* callback received but rejected by state guard
* callback processed but downstream processing failed

---

## 12.2 Late Callback After Retry


Attempt 1 → callback delayed
             ↓
User retries
             ↓
Attempt 2 → callback processed
             ↓
Attempt 1 callback arrives later


This scenario can produce apparently contradictory statuses/events.

Always identify which transaction attempt produced each callback.

---

## 12.3 Vendor Processing Succeeds but Downstream Event Fails


Vendor callback
      ↓
Vendor report fetched
      ↓
IA processing succeeds
      ↓
MongoDB update
      ↓
Kafka publish fails
      ↓
Downstream state does not advance


A Kafka failure can therefore create a discrepancy between **IA's persisted state** and **downstream workflow state**.

---

## 12.4 Downstream API Failure During Callback


Callback received
      ↓
IA calls downstream API
      ↓
API failure / timeout / connection error
      ↓
Callback processing incomplete
      ↓
Application may remain in-progress or transition to failure


Check retry behavior and whether the failed operation is expected to be retried.

---

# 13. ITR Branch

IA can transition from bank-statement assessment into an ITR-based assessment flow.

Relevant statuses include:


BANK_STATEMENT_ASSESSMENT_COMPLETED
        ↓
PROCEED_TO_ITR_ASSESSMENT
        ↓
ITR_DOCUMENTS_NOT_UPLOADED
        ↓
ITR Assessment


ITR behavior is controlled by:

* current application status
* ITR document state
* ITR transition guards
* terminal ITR status checks
* configured retry behavior

When debugging ITR issues, inspect the guard methods in `IncomeAssessmentApplication` rather than relying only on status names.

---

# 14. How to Debug Business-Logic Issues

For any IA business-logic issue, follow this order:

### Step 1 — Identify the application

Find:

* `applicationReferenceId`
* partner
* product
* assessment medium

### Step 2 — Establish current state

Check:

* current MongoDB status
* previous status if available
* document state
* ITR state
* transaction state

### Step 3 — Identify the workflow branch

Determine whether the application is currently in:

* document upload
* vendor transaction
* vendor callback
* bank-statement assessment
* BSA
* ITR
* FinFort
* Finacle
* downstream sync

### Step 4 — Check configuration

Inspect:

* partner/product configuration
* feature toggles
* relevant rule configuration
* timeout/retry configuration

### Step 5 — Check transition guards

Determine whether the relevant `canProceed...()` or `canUpdate...()` method permits the operation.

### Step 6 — Reconstruct event order

Correlate:


API request
→ vendor call
→ callback
→ downstream call
→ MongoDB update
→ Kafka publish
→ Kafka consume
→ final status


### Step 7 — Classify the failure

Determine whether the failure is:

* business-rule failure
* invalid state transition
* vendor failure
* timeout
* retry exhaustion
* database failure
* Kafka/event failure
* downstream API failure
* configuration issue
* user-abandoned flow

### Step 8 — Determine the actual business impact

Do not equate an exception with journey failure.

Determine whether the exception affected:

* user-facing workflow
* persisted IA state
* vendor transaction state
* downstream state
* observability only

---

# 15. Source-of-Truth Hierarchy

When different files appear to describe different business behavior, use the following priority:

1. **Current domain/service implementation**
2. **Current configuration in `application.yaml`**
3. **Persistence/repository enums and transition logic**
4. **Current controllers and consumers**
5. **README/documentation**
6. **Historical documentation/comments**

The README may contain legacy terminology or older rule names. Current code and configuration should take precedence.

---

# 16. High-Value RAG Terms / Synonyms

The following terms refer to related business concepts and should be treated as retrieval aliases where applicable:

### Income Assessment

* IA
* income assessment
* income-assessment
* income assessment journey
* IA journey
* assessment workflow

### Application

* application
* IA application
* income assessment application
* application state
* application status

### Vendor callback

* callback
* vendor callback
* Perfios callback
* Zenith callback
* callback consumer
* asynchronous callback

### Transaction

* vendor transaction
* start transaction
* transaction initiation
* transaction attempt
* retry attempt
* vendor ID
* vendor transaction ID

### State

* status
* application status
* state transition
* transition guard
* lifecycle status
* terminal status
* in-progress state

### Configuration

* partner/product configuration
* product configuration
* partner configuration
* feature toggle
* journey toggle
* IA config
* rule configuration

### Bank Statement Assessment

* BSA
* bank statement assessment
* bank statement validation
* statement rules
* income credit validation
* cheque bounce validation

### ITR

* ITR assessment
* ITR documents
* ITR upload
* ITR retry
* ITR status

### Events

* Kafka event
* domain event
* callback event
* event publishing
* event consumer
* downstream event
* event propagation

### Failure / Incident Terms

* stuck
* stuck in progress
* status not updated
* callback missing
* callback delayed
* late callback
* duplicate callback
* retry exhausted
* timeout
* downstream failure
* Kafka failure
* state mismatch
* inconsistent state
* status regression
* failed transition

---

# 17. Key Business Invariants

These invariants are useful when reasoning about incidents:

1. **IA is a stateful workflow.** A single API response does not necessarily represent the final journey outcome.

2. **Current application status matters.** The same API/callback can behave differently depending on the application's existing state.

3. **Transition guards are business rules.** A rejected operation may be an intentional state-protection mechanism rather than an API failure.

4. **Partner/product configuration matters.** Business behavior is not necessarily identical across products or partners.

5. **Callbacks are state transitions.** Vendor callbacks can change the application's workflow state and must be evaluated against current state.

6. **Multiple transaction attempts can exist.** Application-level and transaction-level state should not be treated as the same thing.

7. **Eventual consistency exists.** MongoDB state and downstream Kafka-consumer state can temporarily or permanently diverge when event publishing/consumption fails.

8. **Not every exception is user-flow critical.** Some operations are best-effort side effects.

9. **Retry behavior is business-relevant.** Retry count, timeout, and retry ordering can determine the final IA status.

10. **Event order matters.** A late callback or delayed Kafka event can produce a different outcome from the same events occurring in a different order.

11. **Current code/configuration overrides documentation.** Historical README descriptions should not be treated as authoritative when they conflict with implementation.

---

# 18. Important Classes / Files for Business-Logic Investigation

| Area                      | File                                                          | Why it matters                               |
| ------------------------- | ------------------------------------------------------------- | -------------------------------------------- |
| Domain state              | `domain/IncomeAssessmentApplication.kt`                       | State-transition guards and workflow rules   |
| Status model              | `domain/Status.kt`                                            | Domain lifecycle statuses                    |
| Persistence               | `repository/IncomeAssessmentRepository.kt`                    | Persisted statuses and application state     |
| Main orchestration        | `revamp/service/impl/IncomeAssessmentApplicationServiceV3.kt` | Core IA workflow orchestration               |
| Version/config resolution | `revamp/versionresolvers/CommonVersionResolver.kt`            | Partner/product-specific behavior            |
| Configuration             | `utils/ConfigFetcher.kt`                                      | Feature toggles and runtime configuration    |
| Controller                | `controller/IncomeAssessmentApplicationController.kt`         | Request context and entry points             |
| Perfios callback          | `kafka/consumer/PerfiosCallbackReceivedConsumer.kt`           | Callback processing and state/event flow     |
| Zenith callback           | `kafka/consumer/ZenithCallbackReceivedConsumer.kt`            | Zenith callback processing                   |
| CAP sync                  | `multibank/service/CapSyncService.kt`                         | CAP synchronization and event/error handling |
| Business rules            | `src/main/resources/application.yaml`                         | Current rule/configuration values            |
| Documentation             | `README.md`                                                   | High-level business/domain description       |

---

# 19. RAG Retrieval Guidance

When answering a business-logic question, prioritize retrieval based on the user's intent.

### If the question is about status/state

Retrieve:

* `Status.kt`
* `IncomeAssessmentApplication.kt`
* `IncomeAssessmentRepository.kt`

### If the question is about why a transition was rejected

Retrieve:

* `IncomeAssessmentApplication.kt`
* relevant service implementation
* current application status

Focus on:

* `canProceed...()`
* `canUpdate...()`
* `isTerminal...()`

### If the question is about partner/product-specific behavior

Retrieve:

* `CommonVersionResolver.kt`
* `ConfigFetcher.kt`
* relevant configuration
* controller/request context

### If the question is about Perfios/Zenith callbacks

Retrieve:

* corresponding callback consumer
* `IncomeAssessmentApplication.kt`
* repository/state update logic
* relevant downstream service
* Kafka event logic

### If the question is about rules/validation

Retrieve:

* `application.yaml`
* rule implementation
* README only for business terminology/context

### If the question is about a production incident

Retrieve all relevant components and reconstruct the **event timeline**, rather than answering from a single class or log statement.

The preferred reasoning sequence is:


Application
→ Current Status
→ Transaction Attempt
→ Configuration
→ Guard
→ Vendor/API Result
→ DB Update
→ Kafka Event
→ Downstream Consumer
→ Final State

