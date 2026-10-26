# Kafka Code Snippets

## Purpose

This file contains implementation-level evidence for IA's asynchronous event flow.

Use it to answer:

* Where is an event produced?
* Which topic is used?
* Which consumer processes it?
* Which consumer group handles it?
* What happens after the event is consumed?
* Which state guard runs?
* Which Mongo document is updated?
* Which external API is called?
* Which next event is produced?
* Why did an event exist but the business state not change?

---

# 1. Canonical Kafka Execution Model

```text
Producer
   ↓
Kafka Topic
   ↓
Consumer Group
   ↓
Consumer
   ↓
Filter / Transformer
   ↓
Business Handler
   ↓
Mongo / External API
   ↓
Next Event
```

Important:

```text
Event published
≠
Event consumed
≠
Business processing succeeded
≠
Mongo state updated
≠
Downstream API succeeded
```

---

# 2. Event Producer

## IncomeAssessmentApplicationEventProducer

```text
IncomeAssessmentApplicationEventProducer
```

```text
[Producer snippet to be added]
```

Capture:

* event ID
* payload
* topic
* partition/key
* headers
* serialization
* error handling

---

# 3. Consumer Landscape

Known consumers:

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

---

# 4. Perfios Callback Consumer

## CODE-KAFKA-PERFIOS-XXX

```text
[Snippet to be added]
```

Expected investigation path:

```text
Perfios callback event
      ↓
Consumer
      ↓
Application lookup
      ↓
Attempt/vendor transaction correlation
      ↓
State guard
      ↓
Report/status processing
      ↓
Mongo update
      ↓
Next event
```

---

# 5. Perfios Callback Not Received

```text
[Snippet to be added]
```

Capture:

* callback timeout
* status API invocation
* retry count
* retry interval
* terminal failure
* user retry behavior

---

# 6. Zenith Callback / Status Events

```text
[Snippet to be added]
```

Document:

```text
Event
→ consumer
→ status/report retrieval
→ validation
→ Mongo
→ next event
```

---

# 7. ITR Events

## Initiate ITR Assessment

```text
InitiateItrAssessmentConsumer
```

```text
[Snippet to be added]
```

Capture:

* triggering event
* ITR eligibility/state guard
* document requirements
* assessment invocation
* next event/state

---

# 8. FinFort Events

## Callback Not Received

```text
FinFortCallbackNotReceivedConsumer
```

```text
[Snippet to be added]
```

Especially important for:

```text
GST
ffOrderId
callback timeout
multiple GST assessments
```

---

# 9. Event → State Mapping

For every important event, document:

```text
Event ID
↓
Consumer
↓
Current state requirement
↓
Business action
↓
Mongo mutation
↓
Resulting state
↓
Next event
```

Template:

````text
### CODE-KAFKA-XXX — <Event Name>

**Event ID**

`<event>`

**Topic**

`<topic>`

**Consumer**

`<consumer>`

**Handler**

`<method>`

**Snippet**

```kotlin
<small snippet>
````

**Input state**

<expected state>

**State guard**

<guard>

**DB mutation**

<mutation>

**External side effect**

<API>

**Next event**

<event>

**Failure behavior**

<retry / ignore / fail / fallback>

````

---

# 10. Kafka Failure Patterns

## RecordTooLargeException

```text
[Producer configuration/code snippet to be added]
````

Investigate:

```text
Payload size
→ producer limit
→ topic/broker limit
→ consumer limit
```

Important business question:

> Does failure to publish the event prevent the primary IA state transition?

---

# 11. Duplicate / Late Events

Capture code showing:

```text
event deduplication
state guards
attempt correlation
terminal-state checks
```

```text
[Snippet to be added]
```

This is especially important for:

```text
multiple vendor attempts
late Perfios callback
multiple GST callbacks
retry flows
```

---

# 12. Kafka Debugging Template

When debugging an event:

```text
1. Identify event ID
2. Identify topic
3. Identify producer
4. Verify publication
5. Identify consumer group
6. Verify consumption
7. Identify handler
8. Check application/attempt lookup
9. Check state guard
10. Check DB mutation
11. Check external API
12. Check next event
```

The **first missing expected step** is usually more valuable than the final error log.
