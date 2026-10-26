# Kafka Events

## Kafka Architecture Overview

Kafka is a core part of the Income Assessment (IA) service's asynchronous workflow.

The service uses Kafka for:

* propagating IA lifecycle events
* receiving callbacks and notifications from external journeys
* triggering asynchronous processing
* synchronizing state across downstream systems
* recording operational and user-journey events
* initiating secondary workflows such as ITR assessment and verification flows

The Kafka flow should be understood as:


Producer / External System
        ↓
      Topic
        ↓
Consumer + Consumer Group
        ↓
Filter / Transformer
        ↓
Business Logic
        ↓
MongoDB / External API
        ↓
Internal Kafka Event
        ↓
Downstream Consumer


Kafka events therefore represent **workflow signals**, not necessarily the final business state.

A Kafka event being published successfully does not by itself mean that:

* the consumer processed it successfully
* MongoDB was updated
* the downstream API succeeded
* the overall IA journey reached the expected status

Similarly, a MongoDB status update does not guarantee that the corresponding Kafka event was successfully published or consumed.

**Source citations**

* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/kafka/event/IncomeAssessmentApplicationEvent.kt:24-137`
* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/kafka/producer/IncomeAssessmentApplicationEventProducer.kt:13-30`
* `src/main/resources/application.yaml:353-533`

---

## Core Kafka Components

### `IncomeAssessmentApplicationEvent`

`IncomeAssessmentApplicationEvent` is the central event-definition class.

It contains the canonical event IDs used throughout the service.

When debugging an event-driven flow, prefer the exact event ID defined here instead of relying only on business terminology.

Examples:


IncomeAssessmentSuccess
IncomeAssessmentFailed
PerfiosCallbackReceived
ZenithCallbackReceived
RawStatementFetched
RetryCountUpdate
IncomeAssessmentLoaderTimeout


**Source**

* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/kafka/event/IncomeAssessmentApplicationEvent.kt:24-137`

### `IncomeAssessmentApplicationEventProducer`

`IncomeAssessmentApplicationEventProducer` is the common publishing abstraction used by the service.

It is the primary code anchor for understanding:

* how events are published
* what event identifier is supplied
* how event payloads are passed
* whether publishing errors propagate or are handled by the caller

When an RCA mentions **"event not published"**, **"Kafka publish failed"**, or **"event missing"**, inspect the producer and its callers before investigating the consumer.

**Source**

* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/kafka/producer/IncomeAssessmentApplicationEventProducer.kt:13-30`

---

# Event Taxonomy

Kafka events can be grouped by their role in the IA workflow.

## 1. Outcome Events

These represent business outcomes or major IA state transitions.

Examples:


IncomeAssessmentSuccess
IncomeAssessmentFailed
IncomeAssessmentRejected
IncomeAssessmentReferred
PolicyNormsNotMet


These events should be correlated with the application's MongoDB `status`.

Important distinction:

> Event name and database status are related, but they are not interchangeable.

For example, an `IncomeAssessmentFailed` event indicates that a failure event was emitted. The MongoDB record must still be checked to determine the persisted application state.

---

## 2. Journey / UI Events

These represent user progression through the IA journey.

Examples:


InitAPIExecuted
UserRedirectedToPerfios
UserRedirectedToZenith
UserLandedFromPerfios
LinkGenerationCompleted
RetryPopUpRendered
AutoRedirectToAA
IncomeAssessmentLoaderTimeout


These events are particularly useful for reconstructing **what the customer actually did**.

For incident analysis, journey events should be correlated with:

* application status
* vendor transaction ID
* retry count
* timestamps
* callback events

This is important when determining whether the user:

* reached the vendor
* returned from the vendor
* abandoned the journey
* retried the journey
* timed out on the UI

---

## 3. Callback and Notification Events

These represent asynchronous responses from external systems.

Examples:


PerfiosCallbackReceived
PerfiosCallbackNotReceived
ZenithCallbackReceived
ZenithCallbackNotReceived
ZenithNotificationReceived
FinFortCallbackNotReceived


Callback events are often the boundary between an external system and the IA state machine.

Typical flow:


External Vendor
      ↓
Callback / Notification
      ↓
Kafka
      ↓
Callback Consumer
      ↓
Application Lookup
      ↓
State Guard
      ↓
MongoDB Update
      ↓
Internal Event / Downstream Action


Therefore, when a callback-related incident occurs, investigate the complete chain rather than only the callback payload.

---

## 4. Vendor / Processing Events

These events describe successful completion of specific processing steps.

Examples:


FinacleStatementFetchedSuccessfully
PerfiosStartTransactionSucceeded
PerfiosUploadTransactionSucceeded
PerfiosCompleteTransactionSucceeded
FinacleFlowCompletedSuccessfully


These are useful for identifying **the last successfully completed asynchronous step**.

They should not automatically be interpreted as final IA success.

---

## 5. Raw Statement and Document Events

Examples:


RawStatementFetched
RawStatementUploadedToOmniDocs
RawStatementFinacleUploadedToOmniDocs
RawStatementUploadedToDocumentDB


These events help trace document/report movement between:


Vendor / AA
    ↓
IA Service
    ↓
Document Storage
    ↓
Downstream Consumer


A successful raw-statement event indicates completion of that particular step, not necessarily completion of the overall IA journey.

---

## 6. Retry and UX Events

Examples:


RetryCountUpdate
RetryPopUpRendered
AutoRedirectToAA
IncomeAssessmentLoaderTimeout


These events are especially valuable during production RCA because they provide evidence of retry and timeout behavior.

For retry-related incidents, correlate:


retry event
    +
application retry counter
    +
vendor transaction ID
    +
application status
    +
callback timestamp


---

# Event → Topic → Consumer Model

The Kafka architecture should be reasoned about as a chain rather than as isolated events.

For any event, identify:

1. **Event ID**
2. **Topic**
3. **Producer**
4. **Consumer**
5. **Consumer group**
6. **Filter configuration**
7. **Transformer configuration**
8. **Business handler**
9. **MongoDB mutation**
10. **Downstream API/event**
11. **Retry / error behavior**

Conceptually:


Event ID
   ↓
Topic
   ↓
Consumer Group
   ↓
Consumer
   ↓
Filter
   ↓
Transformer
   ↓
Business Handler
   ↓
DB / External API
   ↓
Next Event


This chain is the preferred retrieval path for Kafka-related debugging.

**Source**

* `src/main/resources/application.yaml:353-533`

---

# Topic and Consumer Configuration

Kafka configuration is primarily defined under:


platform.kafka.*


Configuration can determine:

* topic names
* consumer groups
* event filtering
* retry behavior
* transformer/config-file mappings
* consumer-specific settings

The application configuration should therefore be treated as the source of truth when determining **where an event is expected to be consumed**.

Do not infer a topic or consumer group from the Java/Kotlin class name alone.

**Source**

* `src/main/resources/application.yaml:353-533`

---

# Consumer Landscape

Representative consumers include:

* `PerfiosNotificationReceivedConsumer`
* `PerfiosCallbackReceivedConsumer`
* `PerfiosCallbackNotReceivedConsumer`
* `ZenithNotificationReceivedConsumer`
* `ZenithCallbackReceivedConsumer`
* `ZenithCallbackNotReceivedConsumer`
* `BackOfficeNotificationReceivedConsumer`
* `FcuVerificationResetConsumer`
* `InitiateItrAssessmentConsumer`
* `FinFortCallbackNotReceivedConsumer`

Consumers are not merely event listeners.

A typical consumer can:

1. receive an event
2. deserialize/filter the event
3. identify the IA application
4. fetch the application from MongoDB
5. validate whether the current state allows processing
6. call an external service
7. update MongoDB
8. publish another event
9. handle selected errors without failing the overall journey

Therefore:

> **Consumer received ≠ consumer successfully completed business processing.**

**Source citations**

* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/kafka/consumer/PerfiosCallbackReceivedConsumer.kt:33-161`
* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/kafka/consumer/ZenithCallbackReceivedConsumer.kt:30-137`
* `src/main/resources/application.yaml:397-525`

---

# Consumer Filtering and Transformation

Some consumers use configuration-driven filtering and transformation.

The configuration can connect:


Kafka Topic
    ↓
Filter Configuration
    ↓
Event Matching
    ↓
Transformer
    ↓
Consumer Payload


This means a shared topic may carry multiple event types while a particular consumer only processes events matching its configured filter.

When a consumer appears not to react to an event, verify:

* event ID
* topic
* filter configuration
* transformer configuration
* expected payload/schema
* consumer group
* consumer logs

Do not immediately assume the consumer code itself is broken.

**Source**

* `src/main/resources/application.yaml:381-468`

---

# Event Payload and Transformation

There are potentially multiple representations of the same event as it moves through the system:


Published Event
      ↓
Kafka Message
      ↓
Configured Filter
      ↓
Transformer
      ↓
Consumer Model


Therefore, when debugging payload-related failures, inspect the event definition and transformation configuration together.

The event class should be checked first to understand the canonical event structure before relying on a transformed consumer payload.

**Source**

* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/kafka/event/IncomeAssessmentApplicationEvent.kt:24-137`
* `src/main/resources/application.yaml:381-468`

---

# Kafka and MongoDB Consistency

Kafka and MongoDB are separate systems and do not provide one atomic transaction across:


MongoDB update
+
Kafka publish


A workflow can therefore reach states such as:

### Case 1 — DB updated, event publish fails


MongoDB → SUCCESS
Kafka    → publish failed


The application may appear successful in MongoDB while a downstream consumer never receives the expected event.

### Case 2 — Event published, consumer processing fails


Kafka publish → SUCCESS
Consumer      → FAILURE
MongoDB       → not updated / partially updated


### Case 3 — DB and Kafka both succeed, downstream API fails


MongoDB update
      ↓
Kafka event published
      ↓
Consumer executes
      ↓
Downstream API fails


### Case 4 — Duplicate or late event


Attempt 1 → Event A
Attempt 2 → Event B
Attempt 1 callback arrives late


The consumer may receive a valid event whose associated application state has already changed.

This is why Kafka debugging must always be correlated with MongoDB state and application attempt/transaction identifiers.

---

# Event Ordering and Late Events

Kafka event processing should not be assumed to represent a simple chronological business timeline.

In long-running IA journeys:

* external callbacks can arrive late
* users can retry
* multiple vendor transactions can exist for one application
* events can represent different attempts
* downstream processing can complete at different times

Therefore:

> **Event timestamp alone is not sufficient to determine the current business state.**

For callback and retry incidents, correlate:


applicationReferenceId
incomeAssessmentId
perfiosTransactionId / vendor transaction ID
event timestamp
application status
retry count
iaAttempts
consumer processing logs


The current persisted application state and the event's transaction/attempt identity must be evaluated together.

---

# Duplicate Event / Idempotency Considerations

Consumers should be investigated for state guards before assuming that every Kafka delivery results in another business transition.

Important questions during an RCA:

* Does the consumer check the current application status?
* Does it validate the vendor transaction ID?
* Can the same callback be processed more than once?
* What happens if the callback arrives after a retry?
* Does the consumer ignore stale events?
* Is the database update conditional?
* Can processing the same event twice trigger duplicate downstream calls?

The presence of methods such as:


canUpdateApplicationStatusInDb()
canUpdateApplicationStatusInPerfiosCallback()


indicates that application state guards are an important part of callback processing.

**Source**

* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/domain/IncomeAssessmentApplication.kt:279-332`
* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/kafka/consumer/PerfiosCallbackReceivedConsumer.kt:80-159`

---

# Retry and Failure Semantics

Kafka-related failures should be classified by their business impact.

## 1. Consumer processing failure

The event was delivered, but business processing failed.

Investigate:


consumer
→ application lookup
→ state guard
→ downstream API
→ DB update


## 2. Event publication failure

The producer could not publish the event.

Investigate:


producer
→ Kafka broker/topic
→ payload size
→ serialization
→ producer configuration


A producer failure may be critical even when the preceding business operation succeeded.

## 3. Downstream failure after event consumption

The event was consumed successfully, but the consumer's external API call failed.

Investigate:


consumer
→ WebClient/gateway
→ HTTP response / network error
→ retry policy
→ error handling


## 4. Filter / transformation failure

Kafka delivery succeeded, but the consumer did not process the event because:

* event filter did not match
* payload did not match expected schema
* transformation failed
* configuration was incorrect

## 5. Business guard rejection

The consumer received the event but intentionally did not transition the application because the current state did not allow it.

This is different from Kafka delivery failure.

---

# Important Kafka Failure Pattern: Event Publish Failure

A critical RCA pattern is:


Business operation succeeds
        ↓
MongoDB updated
        ↓
Kafka event publication fails
        ↓
Downstream consumer never receives event
        ↓
Distributed workflow becomes inconsistent


One known class of failure is Kafka rejecting an oversized record, for example:


RecordTooLargeException


When this occurs, investigate:

* event payload size
* Kafka producer limits
* broker/topic limits
* whether the event contains an unexpectedly large report/document
* whether the producer error is propagated
* whether user flow is incorrectly coupled to event publication

The key distinction is:

> A Kafka publication failure can be a downstream-consistency failure even when the primary IA operation itself succeeded.

---

# Important Kafka Failure Pattern: Missing Callback

For callback-driven journeys:


External Vendor
      ↓
Callback
      ↓
Kafka
      ↓
Callback Consumer
      ↓
MongoDB


If the callback is never received, investigate:

1. Was the vendor callback generated?
2. Did IA receive it?
3. Was the callback converted into a Kafka event?
4. Was the event published to the expected topic?
5. Did the expected consumer group receive it?
6. Did filtering accept it?
7. Did the consumer process it?
8. Did the consumer state guard allow the transition?
9. Was MongoDB updated?
10. Was the next downstream event published?

This prevents incorrectly labeling every callback incident as a vendor issue.

---

# Important Kafka Failure Pattern: Late Callback After Retry

A particularly important IA scenario is:


Attempt 1
   ↓
Vendor transaction
   ↓
Callback delayed
   ↓
IA retry / timeout
   ↓
Attempt 2
   ↓
New vendor transaction
   ↓
Attempt 2 callback processed
   ↓
Attempt 1 callback arrives later


The late event can be valid but stale relative to the current application state.

For these incidents, never investigate the callback using only:


applicationReferenceId


Also correlate the vendor transaction / attempt identifier.

Required investigation dimensions:


Application
+
Attempt
+
Vendor Transaction
+
Event
+
Current Mongo Status
+
Consumer Processing


---

# Kafka Event vs Business Status

The following concepts should not be treated as equivalent:

| Concept               | Meaning                                         |
| --------------------- | ----------------------------------------------- |
| Kafka event           | Signal that something happened or should happen |
| MongoDB status        | Persisted application state                     |
| Consumer execution    | Processing of an event                          |
| Downstream API result | Result of an external side effect               |
| Final IA outcome      | Business result of the overall journey          |

A common RCA mistake is to assume:


Event exists → business state must be updated


The correct reasoning is:


Event exists
    ↓
Was it delivered?
    ↓
Was it consumed?
    ↓
Did filter match?
    ↓
Did consumer process?
    ↓
Did state guard allow transition?
    ↓
Did DB update succeed?
    ↓
Did downstream event/API succeed?


---

# Kafka Debugging Workflow

When an event-driven issue is reported, use this order.

## Step 1 — Identify the exact event

Start with the canonical event ID from:


IncomeAssessmentApplicationEvent


Do not rely only on a business description such as "success event" or "Perfios callback."

---

## Step 2 — Identify the topic

Use `application.yaml` to determine:


event → topic


---

## Step 3 — Identify the consumer group

Determine which consumer group is expected to process the event.

---

## Step 4 — Identify the consumer

Find the corresponding consumer class and inspect its handler.

---

## Step 5 — Check filtering/transformation

Verify:


topic
→ filter
→ event match
→ transformer
→ payload


---

## Step 6 — Trace the business handler

Determine whether the consumer:

* reads MongoDB
* checks application state
* calls a downstream service
* updates MongoDB
* publishes another event

---

## Step 7 — Correlate MongoDB

Use the relevant identifiers:


incomeAssessmentId
applicationReferenceId
productCode
partnerId
commonClientTransactionId
perfiosTransactionId
statementId
serviceRequestId


Check:

* current status
* statusType
* retry counters
* timestamps
* `iaAttempts`
* `eventStatus`
* vendor transaction identifiers

---

## Step 8 — Trace the next side effect

After consumer execution, determine whether the expected:

* DB update
* external API call
* document operation
* downstream Kafka event

actually occurred.

---

# Kafka RCA Decision Tree

Use this mental model for event-related incidents:


Expected event missing
        |
        +-- Was producer invoked?
        |       |
        |       +-- NO → business code / guard issue
        |       |
        |       +-- YES
        |
        +-- Was Kafka publish successful?
        |       |
        |       +-- NO → producer / Kafka issue
        |       |
        |       +-- YES
        |
        +-- Did expected consumer receive it?
        |       |
        |       +-- NO → topic / group / filter / consumer issue
        |       |
        |       +-- YES
        |
        +-- Did filter / transformation succeed?
        |       |
        |       +-- NO → config / schema / transformer issue
        |       |
        |       +-- YES
        |
        +-- Did business handler execute?
        |       |
        |       +-- NO → consumer logic / guard issue
        |       |
        |       +-- YES
        |
        +-- Did DB/API side effect succeed?
                |
                +-- NO → downstream / persistence issue
                |
                +-- YES → trace next event / consumer


This decision tree should be preferred over starting with random Kafka logs.

---

# Consumer Group and Delivery Debugging

When an event is published but appears unprocessed, distinguish between:

### Producer-side problem


Producer
  ↓
Kafka


Potential causes:

* serialization failure
* oversized message
* broker connectivity
* topic configuration
* producer configuration

### Kafka delivery problem


Kafka
  ↓
Consumer Group


Potential causes:

* wrong topic
* wrong consumer group
* consumer unavailable
* offset/consumption issue
* filtering configuration

### Consumer business problem


Consumer
  ↓
Business Handler


Potential causes:

* invalid payload
* state guard rejection
* Mongo lookup failure
* downstream API failure
* database update failure

This separation is important because "Kafka issue" is often used too broadly in RCAs.

---

# Event Correlation Identifiers

Kafka events should be correlated with application and transaction identifiers wherever available.

High-value identifiers include:


incomeAssessmentId
applicationReferenceId
commonClientTransactionId
perfiosTransactionId
statementId
serviceRequestId


The most important distinction is:


incomeAssessmentId
    ≠
applicationReferenceId
    ≠
perfiosTransactionId


A single IA application can have multiple vendor transaction attempts.

Therefore, when reconstructing event history:


Application
   ├── Attempt 1
   │     ├── Vendor Transaction A
   │     └── Events
   │
   └── Attempt 2
         ├── Vendor Transaction B
         └── Events


Do not combine events from different attempts merely because they share the same application reference.

---

# Kafka + Application State Investigation

For a stuck or inconsistent IA journey, compare:


Kafka event timeline
        vs
MongoDB state timeline
        vs
External API timeline


Example:


T1  Vendor transaction created
T2  PerfiosStartTransactionSucceeded
T3  User redirected
T4  Callback event expected
T5  Callback delayed
T6  Retry / timeout
T7  New transaction created
T8  Second callback processed
T9  First callback arrives late


This timeline can explain apparent contradictions such as:

* event says success but Mongo says failed
* two callbacks exist for one application
* downstream received an event for an older attempt
* application is in progress after a successful vendor operation

---

# Kafka Configuration as Source of Truth

For Kafka routing and consumption, prefer this source hierarchy:

1. **Current consumer/producer implementation**
2. **`IncomeAssessmentApplicationEvent`**
3. **Current `application.yaml` Kafka configuration**
4. **Filter/transformer configuration**
5. **Consumer-specific models**
6. **Tests/stubs**
7. **README or historical documentation**

If documentation conflicts with current Kafka configuration, current code/configuration wins.

---

# Important Kafka Code Anchors

When investigating Kafka behavior, start with:

### Event definitions


src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/kafka/event/IncomeAssessmentApplicationEvent.kt


### Event producer


src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/kafka/producer/IncomeAssessmentApplicationEventProducer.kt


### Callback consumers


src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/kafka/consumer/PerfiosCallbackReceivedConsumer.kt
src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/kafka/consumer/ZenithCallbackReceivedConsumer.kt


### Kafka configuration


src/main/resources/application.yaml


### Business state guards


src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/domain/IncomeAssessmentApplication.kt


These files together provide the primary path for understanding event-driven state transitions.

---

# High-Value Kafka Search Terms

Use exact strings wherever possible during RAG retrieval.

## Event identifiers


IncomeAssessmentSuccess
IncomeAssessmentFailed
IncomeAssessmentRejected
IncomeAssessmentReferred
PolicyNormsNotMet
PerfiosCallbackReceived
PerfiosCallbackNotReceived
ZenithCallbackReceived
ZenithCallbackNotReceived
ZenithNotificationReceived
RawStatementFetched
RetryCountUpdate
IncomeAssessmentLoaderTimeout


## Kafka infrastructure


IncomeAssessmentApplicationEvent
IncomeAssessmentApplicationEventProducer
platform.kafka
consumer group
topic
filter
transformer
retry


## Consumer classes


PerfiosCallbackReceivedConsumer
PerfiosNotificationReceivedConsumer
PerfiosCallbackNotReceivedConsumer
ZenithCallbackReceivedConsumer
ZenithNotificationReceivedConsumer
ZenithCallbackNotReceivedConsumer
InitiateItrAssessmentConsumer
FcuVerificationResetConsumer


## Failure terminology


event not published
Kafka publish failed
RecordTooLargeException
consumer not receiving event
consumer group
event filter
transformer
callback not received
late callback
duplicate callback
stale event
event status mismatch
Kafka retry


---

# RAG Retrieval Guidance

Retrieve Kafka context based on the question being asked.

### If the question is:

**"What Kafka event represents X?"**

Retrieve:


IncomeAssessmentApplicationEvent


### "Which topic consumes X?"

Retrieve:


IncomeAssessmentApplicationEvent
+
application.yaml platform.kafka configuration


### "Why was the event not consumed?"

Retrieve:


application.yaml
+
consumer
+
filter/transformer configuration


### "Why did the event not get published?"

Retrieve:


IncomeAssessmentApplicationEventProducer
+
producer caller
+
Kafka configuration


### "Why is MongoDB status different from the Kafka event?"

Retrieve:


Kafka consumer
+
IncomeAssessmentApplication
+
IncomeAssessmentRepository
+
database.md


### "Why did a callback update the wrong state?"

Retrieve:


callback consumer
+
IncomeAssessmentApplication state guards
+
database.md
+
integration/vendor transaction context


### "Why is the journey stuck after a successful vendor operation?"

Retrieve:


event definition
+
producer
+
consumer
+
MongoDB state
+
downstream event/API


---

# Key Kafka Invariants

The following assumptions should guide debugging:

1. **An event is a workflow signal, not necessarily a final business state.**
2. **Event publication success does not guarantee consumer processing success.**
3. **Consumer receipt does not guarantee business processing success.**
4. **MongoDB state and Kafka state are not updated atomically.**
5. **A single IA application can have multiple vendor transaction attempts.**
6. **Application-level identifiers must be distinguished from vendor transaction identifiers.**
7. **A late callback can be valid but stale relative to the current application state.**
8. **State guards can intentionally prevent an otherwise valid event from changing application state.**
9. **Topic, consumer group, filter, and transformer configuration must be checked before assuming consumer-code failure.**
10. **Producer failures and consumer failures are different failure domains.**
11. **A downstream API failure can occur after successful Kafka delivery.**
12. **Event timestamps must be interpreted together with application attempt and transaction identity.**
13. **Current code and configuration are more authoritative than historical documentation.**
14. **Kafka incidents should be investigated across the complete chain: producer → topic → consumer → business logic → DB/API → next event.**

---

# Preferred Kafka Debugging Mental Model

For any Kafka-related production issue, reason through:


What event?
    ↓
Produced by whom?
    ↓
To which topic?
    ↓
Consumed by which group?
    ↓
Filtered/transformed how?
    ↓
Handled by which consumer?
    ↓
Which application/attempt?
    ↓
What state guard applied?
    ↓
What MongoDB mutation happened?
    ↓
What external API was called?
    ↓
What next event was published?
    ↓
What downstream system consumed it?


This is the canonical reasoning path for Kafka-related RCA in the IA service.
