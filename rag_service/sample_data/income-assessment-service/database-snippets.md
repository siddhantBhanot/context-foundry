# Database Code Snippets

## Purpose

This file contains implementation-level snippets showing how IA state is read, created, updated, and queried in MongoDB.

Use this file to answer:

* Which DAO/repository is used?
* Which collection is accessed?
* How is an application identified?
* How is IA status updated?
* Which fields are persisted?
* How are multiple attempts represented?
* Why does Mongo state differ from an event/downstream state?

---

# 1. Primary Collection

```text
incomeAssessmentApplications
```

Primary implementation anchors:

```text
IncomeAssessmentApplicationDao
IncomeAssessmentRepository
```

---

# 2. Application Lookup

Capture all important lookup patterns.

```text
[Snippet to be added]
```

Important identifiers:

```text
incomeAssessmentId
applicationReferenceId
commonClientTransactionId
serviceRequestId
partnerId
productCode
```

Important rule:

```text
incomeAssessmentId
≠
applicationReferenceId
≠
perfiosTransactionId
```

Do not assume these identifiers are interchangeable.

---

# 3. Application Creation

```text
[Snippet to be added]
```

Document:

* when application is created
* uniqueness rules
* partner/product constraints
* generated IDs
* initial status
* initial `statusType`

---

# 4. Application Reuse

```text
[Snippet to be added]
```

Capture:

```text
lookup
→ existing application
→ eligibility/reuse condition
→ continue or create
```

---

# 5. Status Update

```text
[Snippet to be added]
```

Capture:

```text
current status
→ guard
→ update
→ timestamp
→ persistence
```

Important:

> A successful database update only proves that this particular persistence operation succeeded. It does not prove that the complete reactive chain, Kafka publication, or downstream synchronization succeeded.

---

# 6. State Guard Persistence

Capture code around:

```text
canUpdateApplicationStatusInDb()
```

```text
[Snippet to be added]
```

Document:

* allowed transitions
* terminal-state protection
* stale/late callback handling
* duplicate event behavior

---

# 7. Vendor Transaction Persistence

## Perfios

```text
perfiosTransactionId
```

```text
[Snippet to be added]
```

Document how vendor transaction IDs are associated with:

```text
IA application
attempt
statement
callback
```

---

## FinFort

```text
ffOrderId
```

```text
[Snippet to be added]
```

Especially relevant to GST.

---

# 8. Attempt Persistence

```text
iaAttempts
```

```text
[Snippet to be added]
```

Capture:

* attempt creation
* retry count
* vendor transaction ID
* callback association
* attempt status
* timestamps

---

# 9. Important Supporting Collections

Capture repository/DAO code for relevant collections such as:

```text
GST collection
incomeAssessmentMigrations
masters / featureToggles
configurations
```

Only document a collection here once repository evidence is available.

---

# 10. Mongo + Kafka Consistency

IA does not necessarily update Mongo and publish Kafka atomically.

Potential sequence:

```text
Mongo update
   ↓
Kafka publish
```

or:

```text
Kafka event
   ↓
Consumer
   ↓
Mongo update
```

Therefore investigate independently:

```text
Was Mongo updated?
Was Kafka event published?
Was Kafka event consumed?
Did downstream processing succeed?
```

---

# 11. Database Snippet Template

````text
### CODE-DB-XXX — <Operation>

**Collection**

`<collection>`

**DAO / Repository**

`<class>`

**Method**

`<method>`

**Purpose**

<what the operation does>

**Lookup fields**

- ...

**Mutation fields**

- ...

**Relevant snippet**

```kotlin
<small snippet>
````

**State impact**

* ...

**Concurrency / guard behavior**

* ...

**Related identifiers**

* ...

**Debugging value**

<why this matters>

**Related context**

* `06-database.md`
* `04-business-logic.md`
* relevant flow

```
```
