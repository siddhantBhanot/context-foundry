# Perfios Flow

## 1. Purpose

This document describes the **Perfios-specific Income Assessment journey**, from transaction initiation through user redirection, vendor processing, callback/status handling, report retrieval, business validation, and final IA state propagation.

Use it to answer:

* How does IA interact with Perfios?
* What happens after `generateLink` or `startProcess`?
* How is a Perfios transaction created and completed?
* How does the callback reach IA?
* What happens when the callback is delayed or missing?
* How are Perfios reports retrieved?
* Where are business rules evaluated?
* Which identifiers are required to trace a Perfios journey?
* Where can the Perfios flow fail?

This document focuses on the **Perfios journey**. General IA state semantics belong in `business-logic.md`, generic external integration behavior in `integrations.md`, Kafka mechanics in `kafka-events.md`, and incident investigation in `troubleshooting.md`.

---

# 2. Perfios Journey at a Glance

The typical Perfios flow is:

id="n8k0qv"
IA Application
↓
Generate Link / Start Process
↓
Start Perfios Transaction
↓
User Redirected to Perfios
↓
User Uploads / Provides Statement
↓
Perfios Transaction Processing
↓
Complete Transaction
↓
Callback / Status Processing
↓
Fetch Report / Statement Data
↓
Business Validation
↓
IA Status Update
↓
Kafka Event / Downstream Propagation


The exact sequence is implementation- and configuration-dependent.

Some flows may use status polling or retry processing when a callback is delayed or unavailable.

---

# 3. High-Level Architecture

The Perfios journey crosses several IA layers:

id="3f1x4e"
Controller
↓
Version Resolution
↓
ServiceFacade
↓
IncomeAssessmentApplicationServiceV3
↓
Perfios Gateway / Client
↓
Perfios
↓
Callback / Status
↓
Kafka Consumer / Callback Service
↓
MongoDB + Report Retrieval
↓
Business Validation
↓
Final Status + Event


The important point is that the Perfios journey is **not synchronous from the application's perspective**.

Starting a Perfios transaction is only the beginning of the journey.

---

# 4. Stage 1 — IA Application Initiation

The journey starts with the IA application being created or reused.

Typical entry point:

id="0w1gqk"
POST /income-assessment-service/v1/initiate-application


The request passes through the normal IA orchestration path:

id="l2r0bw"
Controller
↓
CommonVersionResolver
↓
ServiceFacade
↓
Versioned IA Service


The service establishes the IA application context before starting the Perfios-specific flow.

Important identifiers include:

id="d3y3xq"
incomeAssessmentId
applicationReferenceId
commonClientTransactionId
partnerId
productCode


---

# 5. Stage 2 — Generate Link / Start Process

The Perfios journey can be entered through operations such as:

id="q2d4cj"
GET /income-assessment-service/v1/generate-link


and:

id="k5qv5b"
GET /income-assessment-service/v1/start-process


Relevant service methods include:

id="s7o4g8"
generateLink(...)
startProcess(...)


The purpose of this stage is to prepare/start the vendor journey.

Conceptually:

id="3j8v4x"
IA Application
↓
Resolve journey/configuration
↓
Start Perfios flow
↓
Generate vendor journey/link
↓
Return information required for user redirection


### Important distinction

id="v9n6w4"
Link generated
≠
Perfios journey completed


and:

id="d6c7tv"
Perfios transaction created
≠
Income Assessment succeeded


---

# 6. Stage 3 — Start Perfios Transaction

The IA service invokes the Perfios transaction-start operation through the relevant gateway/client.

The transaction ID returned by Perfios becomes an important correlation identifier.

Typical identifier:

id="y6p3dr"
perfiosTransactionId


The relationship should be treated as:

id="7n5w5j"
IA Application
↓
Perfios Transaction


An application can have multiple Perfios transaction attempts.

Therefore:

id="0a7t5m"
applicationReferenceId


alone is not sufficient to identify a specific vendor attempt.

---

# 7. Stage 4 — User Redirected to Perfios

After successful transaction/link creation, the user is redirected from IA to Perfios.

A representative event is:

id="6p9x1k"
UserRedirectedToPerfios


This represents a transition from:

id="w6s5la"
IA-controlled UI
↓
Perfios-controlled user journey


At this point, IA may be waiting for an external completion signal.

### Important debugging distinction

If the user never completes the Perfios journey:

id="8j4xpk"
transaction initiation may succeed
but callback/completion may never occur


A successful transaction-start API therefore does not prove that the customer completed the journey.

---

# 8. Stage 5 — Statement / Document Upload

During the Perfios journey, statement/document information is uploaded or provided to the vendor.

Relevant service operation:

id="8k1d5q"
uploadStatement(...)


Conceptually:

id="q1w3za"
Perfios Transaction
↓
Statement / Document Upload
↓
Vendor Processing


The exact upload behavior depends on the active Perfios implementation and journey configuration.

Failure at this stage prevents the vendor transaction from reaching successful completion.

---

# 9. Stage 6 — Complete Perfios Transaction

After the required statement/document data is available, the transaction can be completed.

Relevant service operation:

id="4e6x3n"
completeTransaction(...)


Conceptually:

id="v0p8yx"
Start Transaction
↓
Upload Statement
↓
Complete Transaction
↓
Perfios Processing


Completion of the transaction still does not necessarily mean that IA has its final assessment result.

Perfios may need to process the data and subsequently provide the result through callback/status/report mechanisms.

---

# 10. Stage 7 — Callback / Status Processing

The result can reach IA through callback processing and/or status-based recovery.

Representative components include:

id="v9z3qp"
PerfiosCallbackService
PerfiosCallbackReceivedConsumer
PerfiosCallbackNotReceivedConsumer


The conceptual flow is:

id="w8q2y1"
Perfios
↓
Callback / notification
↓
IA callback processing
↓
Kafka event
↓
Perfios callback consumer
↓
Application lookup
↓
State validation
↓
Continue processing


### Important distinction

A callback can fail at multiple boundaries:

id="g2k4sa"
Vendor did not send callback
↓
Callback sent but not received
↓
Received but not published
↓
Published but not consumed
↓
Consumed but state guard rejected
↓
Processed but MongoDB update failed
↓
State updated but next event/API failed


Always identify the first failed boundary.

---

# 11. Stage 8 — Callback and Application Correlation

When a Perfios callback is processed, correlate it using the strongest available identifiers.

Priority should include:

id="d5a4mh"
perfiosTransactionId
incomeAssessmentId
applicationReferenceId
commonClientTransactionId
serviceRequestId


For multi-attempt journeys:

id="f7u5m0"
Application
├── Perfios Transaction 1
└── Perfios Transaction 2


A callback from Transaction 1 may arrive after Transaction 2 has already progressed.

Therefore, callback debugging must include the vendor transaction identity and timing.

---

# 12. Stage 9 — Missing Callback / Timeout Recovery

A missing callback does not immediately prove that Perfios failed.

The investigation should distinguish:

id="6s7r5u"
Callback never sent
Callback delayed
Callback not ingested
Callback event not published
Callback event not consumed
Callback rejected by state guard


When the callback is not received within the expected period, the IA flow may invoke a status API or recovery path.

Conceptually:

id="g5f5xb"
Callback expected
↓
Wait / timeout
↓
Perfios status API
↓
Retry
↓
Vendor result
↓
Continue IA processing


The exact timeout and retry behavior is configuration/code dependent.

---

# 13. Stage 10 — Retry Behavior

Retry-related events or processing can appear during the Perfios lifecycle.

Useful event identifiers include patterns such as:

id="8e5f8a"
Perfios*Retry


When investigating a retry, determine:

1. What operation was retried?
2. Why was it retried?
3. Which Perfios transaction/attempt was involved?
4. How many retries occurred?
5. Did the retry eventually succeed?
6. Did another transaction attempt start before the retry completed?
7. Did a late callback arrive afterward?

### Important rule

Do not assume:

id="j8k4f7"
retry configured
→
all Perfios errors are retryable


Verify the actual retry operator/predicate and exception type.

---

# 14. Stage 11 — Report Retrieval

After Perfios processing completes, IA retrieves the relevant statement/report information.

A representative event is:

id="9f1h3d"
BankStatementReportFetched


Conceptually:

id="r0g3l4"
Perfios Result
↓
Report Retrieval
↓
Statement / Income Data
↓
IA Processing


Report availability and report parsing are separate failure boundaries.

Possible problems include:

* report not yet available
* vendor returned an error
* malformed/invalid response
* unexpected response structure
* parsing/deserialization failure
* incomplete statement data

---

# 15. Stage 12 — Business Validation

Once the required Perfios data is available, IA evaluates configured business rules.

Examples include:

id="c5s2sw"
incomeCreditGapRule
chequeBounceLimitRule
lastNMonthsIncomeRule
numberOfIncomeCreditsRule
statementStatusRule


Conceptually:

id="d9v4se"
Perfios Report
↓
Extract / normalize data
↓
Business Rules
↓
Outcome


Possible outcomes include:

id="x6f0kz"
INCOME_ASSESSMENT_SUCCESS
INCOME_ASSESSMENT_FAILED
INCOME_ASSESSMENT_REJECTED
INCOME_ASSESSMENT_REFERRED
POLICY_NORMS_NOT_MET


### Important distinction

A business-rule rejection is different from:

id="n3z1hx"
Perfios API failure
network timeout
callback failure
report parsing failure
Kafka failure


The source of the failure must be identified before interpreting the final status.

---

# 16. Stage 13 — IA Status Update

After processing and business validation, the application state is updated.

Conceptually:

id="b7t6vc"
Perfios Result
↓
Business Outcome
↓
State Guard
↓
MongoDB Status Update


The state transition may be affected by:

* current IA status
* attempt identity
* business rules
* vendor error mapping
* journey/version
* configuration

A callback that arrives after a different attempt has already changed the state may therefore be rejected or handled differently.

---

# 17. Stage 14 — Event Publication

After important state transitions, the service may publish an IA event.

Representative event categories include:

id="y1q9x4"
InitAPIExecuted
UserRedirectedToPerfios
PerfiosCallbackReceived
BankStatementReportFetched
IncomeAssessmentSuccess
IncomeAssessmentFailed
PolicyNormsNotMet


Conceptually:

id="s4w8j2"
IA State Change
↓
IncomeAssessmentApplicationEvent
↓
IncomeAssessmentApplicationEventProducer
↓
Kafka Topic
↓
Downstream Consumer


### Important distinction

id="e3p7c1"
Status updated
≠
Event published
≠
Event consumed
≠
Downstream processing completed


A Kafka publication failure can therefore create a mismatch between IA's persisted state and downstream state.

---

# 18. Perfios Event Lifecycle

A simplified event progression is:

id="d1c8r6"
InitAPIExecuted
↓
UserRedirectedToPerfios
↓
Perfios transaction processing
↓
PerfiosCallbackReceived
↓
BankStatementReportFetched
↓
Business validation
↓
Final outcome event


Possible final events include:

id="j3q6m5"
IncomeAssessmentSuccess
IncomeAssessmentFailed
PolicyNormsNotMet
IncomeAssessmentRejected
IncomeAssessmentReferred


Not every journey produces every event.

Event names should be treated as signals within the workflow rather than as proof of final business state.

---

# 19. Perfios Failure Map

## Transaction initiation failure

id="f8q3zn"
Start transaction
↓
Failure


Investigate:

* request payload
* endpoint
* authentication
* vendor response
* error mapping
* retry behavior

---

## Upload failure

id="m7j2cy"
Upload statement
↓
Failure


Investigate:

* document/statement payload
* transaction ID
* upload API response
* file/document metadata
* retry behavior

---

## Complete transaction failure

id="v8t5pp"
Complete transaction
↓
Failure


Investigate:

* transaction state
* vendor response
* retry behavior
* whether transaction was already completed
* downstream callback expectations

---

## Callback failure

Investigate in this order:

id="u4j1sf"
Was callback sent?
↓
Was callback received?
↓
Was callback event published?
↓
Was Kafka event consumed?
↓
Was application found?
↓
Did state guard allow processing?
↓
Did report retrieval succeed?


---

## Report retrieval failure

Investigate:

* report availability
* vendor response
* response structure
* parsing
* transaction ID
* retry behavior
* resulting IA state

---

## Business validation failure

Investigate:

* effective partner/product configuration
* rule configuration
* input statement data
* calculated values
* vendor error mapping
* expected status transition

---

# 20. Multi-Attempt Perfios Scenario

A common asynchronous scenario is:

id="w2f8s3"
Application A
│
├── Perfios Attempt 1
│      ↓
│   Callback delayed
│
└── Perfios Attempt 2
↓
Callback received
↓
Processing succeeds


Later:

id="c9q4b6"
Attempt 1 callback arrives


This can create apparently contradictory logs or status transitions.

### Required investigation fields

id="m0q5y4"
applicationReferenceId
incomeAssessmentId
perfiosTransactionId
attempt
callback timestamp
current status
event ID
retry count


Reconstruct the complete timeline before concluding that IA incorrectly changed state.

---

# 21. Perfios Troubleshooting Decision Tree

id="z7r2kn"
Perfios journey issue
│
├── Cannot start transaction
│      ↓
│   Gateway / endpoint / vendor response
│
├── User cannot complete journey
│      ↓
│   Link / redirect / vendor journey
│
├── Callback missing
│      ↓
│   Vendor → callback → Kafka → consumer
│
├── Callback consumed but no state change
│      ↓
│   Application lookup → attempt → state guard
│
├── Report unavailable
│      ↓
│   Vendor status → report API → parsing
│
├── Unexpected rejection
│      ↓
│   Report data → business rules → config
│
└── IA status correct but downstream wrong
↓
Kafka → consumer → downstream API


---

# 22. Perfios Debugging Checklist

When investigating a Perfios incident, capture:

### Application

id="f5z7n8"
applicationReferenceId
incomeAssessmentId
commonClientTransactionId
partnerId
productCode


### Vendor

id="e4k2g1"
perfiosTransactionId
statementId
serviceRequestId


### Timeline

id="h3m8c5"
transaction creation time
user redirection time
upload time
completion time
callback time
timeout time
status-poll time
report retrieval time
final status time


### Processing

id="s6x2q9"
eventId
Kafka topic
consumer group
consumer
retry count
current IA status
resolved IA version


---

# 23. Key Code Anchors

## Main orchestration

IncomeAssessmentApplicationServiceV3


Relevant operations include:


generateLink(...)
startProcess(...)
uploadStatement(...)
completeTransaction(...)


## Version routing


CommonVersionResolver
ServiceFacade


## Callback processing


PerfiosCallbackService
PerfiosCallbackReceivedConsumer
PerfiosCallbackNotReceivedConsumer


## Persistence


IncomeAssessmentRepository
IncomeAssessmentApplicationDao


## Events


IncomeAssessmentApplicationEvent
IncomeAssessmentApplicationEventProducer


## Integration

Look under:


bankStatement/gateway/


for the Perfios gateway implementations.

---

# 24. Perfios-to-Context-Document Map

| Investigation area              | Primary document     |
| ------------------------------- | -------------------- |
| Overall Perfios sequence        | `perfios-flow.md`    |
| IA state transitions            | `business-logic.md`  |
| Perfios APIs/gateways           | `integrations.md`    |
| Perfios callback events         | `kafka-events.md`    |
| Perfios failures/retries        | `error-handling.md`  |
| Vendor error mappings/toggles   | `configurations.md`  |
| Perfios transaction persistence | `database.md`        |
| Production investigation        | `troubleshooting.md` |

---

# 25. RAG Retrieval Guidance

Retrieve this document for questions such as:

* "Explain the Perfios flow"
* "How does Perfios transaction initiation work?"
* "What happens after generate link?"
* "What happens after start process?"
* "Where is the Perfios transaction created?"
* "Where is the statement uploaded?"
* "Where is the Perfios transaction completed?"
* "How does the Perfios callback flow work?"
* "What happens if Perfios callback is not received?"
* "How does IA retrieve the Perfios report?"
* "Where are Perfios business rules evaluated?"
* "Why is a Perfios status stuck?"
* "How do Perfios retries work?"
* "How do multiple Perfios attempts work?"
* "What IDs should I use to trace a Perfios journey?"
* "Which events are generated during Perfios?"

### Retrieval strategy

For a high-level Perfios question:

id="p6y1r8"
perfios-flow.md


For a specific issue, combine with the relevant specialized context:

id="w3f6s2"
Perfios callback issue
→ perfios-flow.md
→ kafka-events.md
→ troubleshooting.md

Perfios API failure
→ perfios-flow.md
→ integrations.md
→ error-handling.md

Unexpected Perfios outcome
→ perfios-flow.md
→ business-logic.md
→ configurations.md

Perfios state mismatch
→ perfios-flow.md
→ database.md
→ kafka-events.md
→ troubleshooting.md


---

# 26. Core Perfios Flow Invariants

1. Starting a Perfios transaction does not mean IA succeeded.
2. Generating a Perfios link does not mean the user completed the vendor journey.
3. Uploading a statement does not mean the assessment result is available.
4. Completing a Perfios transaction does not necessarily mean IA has received the final result.
5. Callback receipt does not guarantee callback processing.
6. Kafka event publication does not guarantee consumer processing.
7. A consumed callback does not guarantee a state transition.
8. Report retrieval and business validation are separate stages.
9. Vendor errors and business-rule failures are different failure classes.
10. One IA application can have multiple Perfios transaction attempts.
11. Callback correlation must include `perfiosTransactionId` when available.
12. Timeout processing and late callbacks must be analyzed together.
13. Final IA status should be correlated with the event/API timeline.
14. A successful MongoDB state update does not prove downstream event propagation.
15. Configuration and IA version can alter the Perfios execution path.

---

# 27. Preferred Mental Model

When debugging or explaining a Perfios journey, think:


Which IA application?
↓
Which partner/product?
↓
Which IA version?
↓
Which Perfios transaction?
↓
Which attempt?
↓
Was transaction started?
↓
Was user redirected?
↓
Was statement uploaded?
↓
Was transaction completed?
↓
Was callback received?
↓
Was callback event consumed?
↓
Did state guard allow processing?
↓
Was report fetched?
↓
Did business validation pass?
↓
What status was persisted?
↓
What event was published?
↓
Did downstream processing complete?


The most important Perfios RCA question is:

> **At which step did the Perfios transaction lifecycle first diverge from the expected IA flow?**
