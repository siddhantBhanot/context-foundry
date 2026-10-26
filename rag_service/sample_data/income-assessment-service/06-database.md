# Database

## 1. Database Overview

The Income Assessment (IA) Service uses **MongoDB with reactive Spring Data** as its primary persistence layer.

MongoDB stores both:

* **business/workflow state**
* **supporting data and derived results**
* **configuration/reference data**
* **operational/scheduler state**

The most important database record is the **Income Assessment Application**. It represents the persisted state of an IA journey and should generally be treated as the primary source when investigating:

* application status
* retry state
* vendor transaction linkage
* journey progress
* document state
* user decisions
* event state
* final IA outcome

Supporting collections contain bank-statement data, reports, fraud analysis, documents, configuration, and multi-bank results.

**Source citations**

* `build.gradle:233-233`
* `src/main/resources/application.yaml:149-150`
* `src/main/resources/application.yaml:542-552`

---

# 2. Database Mental Model

A useful conceptual model is:

text id="m8x2c4"
                    Income Assessment Application
                    incomeAssessmentApplications
                              │
             ┌────────────────┼─────────────────┐
             │                │                 │
             ▼                ▼                 ▼
        Documents       Bank Statements      Vendor State
        document        bankStatements       Perfios/etc.
             │                │
             │                ▼
             │         Statement Reports
             │         bankStatementJsonReports
             │
             └──────────────────────────────┐
                                            │
                                            ▼
                                    Fraud / Analysis
                                    fraudIndicators
                                    multiBank*Results


                    Configuration / Reference
                    configurations
                    banks
                    fraudIndicatorsMapping


The collections should **not** automatically be treated as independent sources of truth.

For most journey-state questions:

> Start with `incomeAssessmentApplications`, then follow identifiers to supporting collections.

---

# 3. MongoDB Collections

## 3.1 `incomeAssessmentApplications`

### Purpose

Stores the primary persisted IA application/workflow record.

### Entity

* `IncomeAssessmentApplicationDao`

### Repository

* `IncomeAssessmentRepository`

### Importance

**Highest-priority collection for IA journey debugging.**

Use this collection when investigating:

* current IA status
* status transitions
* retry attempts
* vendor transaction linkage
* application-level state
* user decisions
* event state
* uploaded documents
* assessment outputs
* ITR/FinFort/Finacle references

### Important identifiers

* `incomeAssessmentId`
* `applicationReferenceId`
* `partnerId`
* `productCode`
* `commonClientTransactionId`
* `perfiosTransactionId`
* `statementId`
* `serviceRequestId`

### Important fields

#### Identity / correlation

* `incomeAssessmentId`
* `applicationReferenceId`
* `partnerId`
* `productCode`

#### Journey context

* `assessmentMedium`
* `occupation`
* `journeyMode`
* `customerType`

#### Workflow state

* `status`
* `statusType`
* retry counters
* timestamps

#### Vendor references

* `perfiosTransactionId`
* `statementId`
* `serviceRequestId`
* FinFort references
* Finacle references

#### Assessment outputs

* `incomeDetails`
* `financialStatements`
* report-related fields

#### Side-effect / workflow state

* `uploadedDocuments`
* `eventStatus`
* `userDecision`
* `config`
* `iaAttempts`

### Indexing

The collection has a unique compound index on:

text id="7i4z6c"
(incomeAssessmentId, productCode, partnerId)


`commonClientTransactionId` is also indexed.

**Source citations**

* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/repository/IncomeAssessmentRepository.kt:26-66`
* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/repository/IncomeAssessmentRepository.kt:66-172`
* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/repository/IncomeAssessmentRepository.kt:397-412`

---

# 4. Supporting Business Collections

## 4.1 `document`

### Entity

* `UploadedDocument`

### Repository

* `DocumentRepository`

### Purpose

Stores uploaded/generated document metadata and supporting document state.

Use when investigating:

* document upload
* document availability
* document-related IA/ITR failures
* generated artifacts
* document-service interactions

**Source citation**

* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/repository/DocumentRepository.kt:9-18`

---

## 4.2 `bankStatements`

### Entity

* `BankStatement`

### Repository

* `BankStatementRepository`

### Purpose

Stores bank-statement information used during bank-statement assessment.

Use when investigating:

* statement retrieval
* statement processing
* statement availability
* bank-account/statement-level processing
* BSA-related data

**Source citation**

* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/bankStatement/repository/BankStatementRepository.kt:15-27`

---

## 4.3 `bankStatementJsonReports`

### Entity

* `BankStatementJsonReport`

### Repository

* `BankStatementJsonReportRepository`

### Purpose

Stores JSON/report representations generated from bank-statement processing.

Use when investigating:

* statement report generation
* vendor report processing
* report retrieval
* report parsing
* bank-statement assessment inputs

**Source citation**

* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/bankStatement/repository/BankStatementJsonReportRepository.kt:12-23`

---

## 4.4 `fraudIndicators`

### Entity

* `FraudIndicator`

### Repository

* `FraudIndicatorRepository`

### Purpose

Stores fraud-related indicators identified during assessment.

Use when investigating:

* fraud-rule results
* fraud indicators
* fraud-related assessment outcomes

**Source citation**

* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/bankStatement/repository/FraudIndicatorRepository.kt:9-19`

---

## 4.5 `fraudIndicatorsMapping`

### Repository

* `FraudIndicatorMappingRepository`

### Purpose

Stores mappings associated with fraud indicators.

This collection should be considered a **supporting/reference mapping layer**, not the primary application workflow state.

**Source citation**

* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/bankStatement/repository/FraudIndicatorMappingRepository.kt:10-13`

---

## 4.6 `banks`

### Entity / Repository

* `Bank`
* `BankRepository`

### Purpose

Stores bank/reference information used by bank-statement and FIP-related flows.

Use this collection when investigating:

* bank/FIP mapping
* supported bank information
* bank-specific processing

**Source citation**

* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/FIP/repository/BankRepository.kt:11-18`

---

## 4.7 `configurations`

### Entity / Repository

* `Configuration`
* `ConfigurationRepository`

### Purpose

Stores runtime/business configuration used by rule-driven processing.

This should be checked when investigating behavior that varies by:

* partner
* product
* configuration
* business rule
* journey

**Source citation**

* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/rules/repositories/ConfigurationRepository.kt:10-15`

---

## 4.8 `multiBankIAResults`

### Entity

* `MultiBankIncomeAssessmentResult`

### Purpose

Stores results related to multi-bank income assessment.

Use when investigating:

* multi-bank assessment
* aggregation of multiple bank results
* multi-bank final assessment data

**Source citation**

* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/multibank/model/MultiBankIncomeAssessmentResult.kt:9-15`

---

## 4.9 `multiBankFraudAnalysisResults`

### Entity

* `MultiBankFraudAnalysisResult`

### Repository

* `MultiBankFraudAnalysisResultRepository`

### Purpose

Stores fraud-analysis results for multi-bank assessment flows.

Use when investigating:

* multi-bank fraud analysis
* fraud results
* downstream multi-bank decision inputs

**Source citation**

* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/multibank/repository/MultiBankFraudAnalysisResultRepository.kt:10-20`

---

# 5. Collection Responsibility Map

| Collection                      | Primary responsibility            |    Priority during IA debugging |
| ------------------------------- | --------------------------------- | ------------------------------: |
| `incomeAssessmentApplications`  | IA application/workflow state     |                     **Highest** |
| `document`                      | Uploaded/generated document state |                            High |
| `bankStatements`                | Bank statement data               |                    High for BSA |
| `bankStatementJsonReports`      | Statement/report JSON             |      High for report processing |
| `fraudIndicators`               | Fraud indicators                  |                     Medium/High |
| `fraudIndicatorsMapping`        | Fraud mappings                    |                          Medium |
| `banks`                         | Bank/reference information        |                          Medium |
| `configurations`                | Business/runtime configuration    |       High when behavior varies |
| `multiBankIAResults`            | Multi-bank IA results             |       High for multi-bank flows |
| `multiBankFraudAnalysisResults` | Multi-bank fraud results          | High for multi-bank fraud flows |

---

# 6. Application Record as Workflow State

`IncomeAssessmentApplicationDao` should be treated as the **workflow record for an IA journey**.

The application record combines:

text id="q3n0b1"
Application Identity
        +
Partner/Product Context
        +
Journey Context
        +
Current Status
        +
Retry State
        +
Vendor References
        +
Documents
        +
Assessment Results
        +
User Decision
        +
Event State
        +
Configuration


This makes it the first place to look when a production issue says:

* "IA is stuck"
* "status is incorrect"
* "user cannot proceed"
* "retry happened"
* "callback updated wrong record"
* "vendor transaction mismatch"
* "event was not triggered"
* "IA status and downstream status don't match"

**Source citations**

* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/repository/IncomeAssessmentRepository.kt:66-172`
* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/repository/IncomeAssessmentRepository.kt:397-412`

---

# 7. Correlation Identifiers

Different identifiers represent different levels of the IA journey.

### `incomeAssessmentId`

Represents the IA assessment/application identity.

Often used with:

text id="3tq0yr"
incomeAssessmentId
+
productCode
+
partnerId


This combination is a key application lookup.

### `applicationReferenceId`

Represents the application/business reference and is used in several multi-record lookup scenarios.

It can be combined with:

text id="a9r4cn"
applicationReferenceId
+
productCode
+
partnerId


### `commonClientTransactionId`

Used for transaction-level correlation and is indexed.

Useful when tracing a request across integration/API logs.

### `perfiosTransactionId`

Links the IA application to a Perfios vendor transaction.

Critical for investigating:

* Perfios callbacks
* multiple vendor attempts
* transaction-status calls
* callback/transaction mismatches

### `statementId`

Links the application/processing flow to a bank statement.

Useful for tracing:

* statement retrieval
* statement processing
* report generation

### `serviceRequestId`

Links IA processing to a downstream service request where applicable.

---

# 8. Application-Level vs Transaction-Level Identity

An important database-debugging distinction is:

> **One IA application can have multiple transaction attempts.**

Therefore:

text id="w2z9q4"
One application
    │
    ├── Transaction Attempt 1
    │      └── perfiosTransactionId = X
    │
    ├── Transaction Attempt 2
    │      └── perfiosTransactionId = Y
    │
    └── Current application status


Do not assume:

text
1 application = 1 vendor transaction


This is particularly important for:

* retries
* user re-entry
* missing callbacks
* late callbacks
* duplicate transactions
* status mismatches

When investigating vendor callbacks, correlate the callback's vendor transaction ID with the application record and determine **which attempt generated the callback**.

---

# 9. Query / Lookup Patterns

Repository code uses several important lookup patterns.

## Primary application lookup

text id="5xk6p8"
incomeAssessmentId
+
productCode
+
partnerId


Use this when you have the IA assessment identifier and need the primary application record.

---

## Application-reference lookup

text id="9d5j8a"
applicationReferenceId
+
productCode
+
partnerId


Useful when an application reference may map to multiple IA records or attempts.

---

## Transaction lookup

text id="0v5s1h"
commonClientTransactionId


Useful for transaction-level correlation.

---

## Perfios lookup

text id="5r9q2b"
perfiosTransactionId


Use when starting from:

* Perfios callback
* Perfios transaction logs
* transaction-status API
* vendor transaction ID

---

## Statement lookup

text id="8k2j5v"
statementId


Use when tracing:

* bank statement processing
* statement reports
* BSA-related processing

---

## Combined application lookup

text id="1j4n6c"
incomeAssessmentId
+
applicationReferenceId


Useful when both identifiers are available and the investigation requires additional correlation.

**Source citations**

* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/repository/IncomeAssessmentRepository.kt:27-57`
* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/repository/IncomeAssessmentApplicationAccessor.kt:17-37`

---

# 10. Database Investigation Workflow

For a production issue, use the following order.

## Step 1 — Identify the application

Start with whichever identifier is available:

text id="5u4n8m"
incomeAssessmentId
applicationReferenceId
commonClientTransactionId
perfiosTransactionId
statementId


Then locate the corresponding application record.

---

## Step 2 — Inspect the primary application document

Check:

* `status`
* `statusType`
* retry counters
* timestamps
* `iaAttempts`
* vendor IDs
* `eventStatus`
* `userDecision`
* document references
* assessment output fields

---

## Step 3 — Determine the journey attempt

If multiple vendor transactions or attempts exist:

text id="2m6v9q"
Application
→ iaAttempts
→ vendor transaction IDs
→ callback transaction ID


Identify which attempt is associated with the incident.

---

## Step 4 — Follow supporting collections

Depending on the problem:

### Document issue

text
incomeAssessmentApplications
→ document


### Bank statement issue

text
incomeAssessmentApplications
→ bankStatements
→ bankStatementJsonReports


### Fraud issue

text
incomeAssessmentApplications
→ fraudIndicators
→ fraudIndicatorsMapping


### Multi-bank issue

text
incomeAssessmentApplications
→ multiBankIAResults
→ multiBankFraudAnalysisResults


### Configuration issue

text
incomeAssessmentApplications
→ configurations


---

## Step 5 — Correlate with external systems

Use persisted IDs such as:

* `perfiosTransactionId`
* `statementId`
* `serviceRequestId`
* `commonClientTransactionId`

to correlate MongoDB records with external API logs and callbacks.

---

## Step 6 — Compare database state with events

For asynchronous workflows compare:

text id="0h8s3k"
MongoDB application state
        vs
Kafka/event state
        vs
Downstream service state


A mismatch can indicate:

* Kafka publish failure
* Kafka consumer failure
* late callback
* duplicate callback
* downstream processing failure
* state update failure

---

# 11. Status Debugging Using MongoDB

When the reported issue is:

> "IA status is stuck / incorrect"

do not inspect only the `status` field.

Check:

text id="r1x5o2"
status
statusType
retry counters
timestamps
iaAttempts
vendor transaction ID
eventStatus
userDecision


Then correlate with:

text id="7f3m9n"
API logs
↓
vendor transaction
↓
callback
↓
DB update
↓
Kafka event
↓
downstream processing


The final MongoDB status is an important observation, but it does not by itself explain **why** the state was reached.

---

# 12. Status Mismatch Scenarios

## Scenario A — MongoDB status updated, downstream state not updated

text id="w8q2n6"
IA processing
    ↓
MongoDB status = SUCCESS
    ↓
Kafka publish fails
    ↓
Downstream system does not receive SUCCESS


Result:

text
MongoDB = SUCCESS
Downstream = previous state


This is a **state propagation problem**, not necessarily an IA business-logic failure.

---

## Scenario B — Callback arrives for an earlier transaction

text id="p4v8r1"
Application
 ├── Attempt 1 → vendor transaction A
 └── Attempt 2 → vendor transaction B

Current state belongs to Attempt 2

Late callback
 └── vendor transaction A


Investigate the transaction ID before interpreting the callback as a state regression.

---

## Scenario C — Multiple IA records exist

If the same application reference appears across multiple records, do not assume that the most recent record is automatically the correct one.

Compare:

* `incomeAssessmentId`
* `applicationReferenceId`
* `productCode`
* `partnerId`
* timestamps
* vendor transaction IDs
* attempt information
* status

The correct record depends on the workflow and lookup contract.

---

# 13. Reactive MongoDB Access

The service uses reactive Spring Data access.

This means database operations are generally executed through reactive repository/service flows rather than traditional blocking JDBC-style access.

When tracing a database operation, follow:

text id="4c8n2p"
Service
 ↓
Repository / Accessor
 ↓
Reactive Mongo operation
 ↓
Mono / Flux
 ↓
State transformation
 ↓
Subsequent operation


When debugging an issue, inspect where reactive chains:

* transform the result
* short-circuit
* retry
* swallow errors
* update state
* continue to downstream operations

A database call appearing successful in logs does not necessarily mean the entire reactive chain completed successfully.

---

# 14. Database + Event Consistency

MongoDB is one part of a larger distributed workflow.

A typical sequence can be:

text id="9k1p5w"
External API
     ↓
MongoDB update
     ↓
Kafka event
     ↓
Downstream consumer


These steps are not necessarily one atomic transaction.

Therefore, the following states are possible during failures:

text id="8h5r3c"
MongoDB updated
Kafka failed


or:

text id="v3q7m9"
MongoDB updated
Kafka published
Consumer failed


or:

text id="m4j8s2"
External API failed
MongoDB not updated


When performing RCA, determine **which stage completed successfully**.

---

# 15. Operational Collections

MongoDB is also used for operational coordination.

## `incomeAssessmentMigrations`

Used for migration-related coordination/locking.

This collection is not part of the normal IA business-state model.

## ShedLock collections

Used for coordination of scheduled/background jobs.

These should generally be considered operational infrastructure rather than application business data.

## Archiver-related collections

Archiving uses Mongo-backed configuration/collections and may involve separate database/lock configuration.

Do not confuse archiver/scheduler state with the primary IA application state.

**Source citations**

* `src/main/resources/application.yaml:146-150`
* `src/main/resources/application.yaml:37-52`
* `src/main/resources/application.yaml:542-552`

---

# 16. Indexing and Query Considerations

The primary application collection has a unique compound index:

text id="5c8n2a"
(incomeAssessmentId, productCode, partnerId)


and an index on:

text id="9m2v6k"
commonClientTransactionId


This reflects the importance of these identifiers for application and transaction lookup.

When creating diagnostic queries, prefer the repository's existing lookup contract instead of querying arbitrary fields.

For production investigations, avoid assuming that:

text
applicationReferenceId


alone uniquely identifies an IA record.

Include the relevant:

text
productCode
partnerId


and/or `incomeAssessmentId` where the repository contract expects them.

**Source citation**

* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/repository/IncomeAssessmentRepository.kt:26-66`

---

# 17. Data Relationship Map

A useful conceptual relationship is:

text id="c8v2m5"
incomeAssessmentApplications
        │
        │ incomeAssessmentId / applicationReferenceId
        │
        ├──────────────→ document
        │
        ├──────────────→ bankStatements
        │                    │
        │                    └──→ bankStatementJsonReports
        │
        ├──────────────→ fraudIndicators
        │                    │
        │                    └──→ fraudIndicatorsMapping
        │
        ├──────────────→ multiBankIAResults
        │
        └──────────────→ multiBankFraudAnalysisResults


This diagram is conceptual. Exact field-level relationships should be confirmed from the corresponding entity/repository implementation before writing database queries.

---

# 18. Database Source-of-Truth Hierarchy

When determining how data is stored or retrieved, prefer:

1. **Repository implementation**
2. **DAO/entity definition**
3. **Accessor/service implementation**
4. **Mongo configuration/index definitions**
5. **Integration/business-logic code**
6. **README/documentation**

If documentation conflicts with the repository's actual query method or entity structure, the current repository/entity implementation is authoritative.

---

# 19. High-Value RAG Terms / Synonyms

### Primary application

* incomeAssessmentApplications
* IncomeAssessmentApplicationDao
* IncomeAssessmentApplication
* IA application
* application record
* application document
* IA document
* workflow record
* application state

### MongoDB

* Mongo
* MongoDB
* Mongo collection
* Mongo document
* reactive Mongo
* reactive repository
* Spring Data Mongo
* Mongo query

### Status/state

* status
* application status
* statusType
* workflow state
* state transition
* stuck
* stuck in progress
* status mismatch
* status not updated
* status regression

### Transaction identifiers

* incomeAssessmentId
* applicationReferenceId
* commonClientTransactionId
* perfiosTransactionId
* statementId
* serviceRequestId
* vendor transaction ID
* transaction attempt
* retry attempt

### Supporting data

* bankStatements
* bank statement
* bankStatementJsonReports
* statement report
* fraudIndicators
* fraud indicator
* multiBankIAResults
* multi-bank result
* document
* UploadedDocument

### Operational data

* migration lock
* incomeAssessmentMigrations
* ShedLock
* scheduler
* archiver

### Database failure / debugging

* Mongo query
* repository query
* document not found
* duplicate record
* duplicate application
* stale record
* missing record
* state mismatch
* DB update failed
* Mongo update
* Mongo timeout
* reactive chain
* persistence failure

---

# 20. Key Database Invariants

1. **`incomeAssessmentApplications` is the primary persisted IA workflow record.**

2. **Supporting collections should be interpreted in the context of the corresponding IA application.**

3. **`incomeAssessmentId + productCode + partnerId` is a key application lookup contract and has a unique compound index.**

4. **`applicationReferenceId` should not automatically be assumed to uniquely identify one IA record.**

5. **One IA application can have multiple transaction attempts.**

6. **`perfiosTransactionId` identifies a vendor transaction, not necessarily the entire IA application.**

7. **Application-level identity and vendor transaction-level identity are different concepts.**

8. **MongoDB state and downstream event state are not necessarily updated atomically.**

9. **A successful MongoDB update does not prove successful Kafka propagation.**

10. **A final MongoDB status does not by itself explain the sequence of events that produced that status.**

11. **For callback investigations, always correlate the callback's vendor transaction ID with the persisted application record.**

12. **For production RCA, timestamps and attempt identifiers are essential when multiple transactions exist.**

13. **Operational collections such as migration locks and ShedLock should not be confused with business-state collections.**

14. **Current repository/entity implementation is the authoritative source for database behavior.**

---

# 21. Important Database Code Anchors

| Area                 | Code anchor                                                      | Why it matters                                      |
| -------------------- | ---------------------------------------------------------------- | --------------------------------------------------- |
| Primary application  | `repository/IncomeAssessmentRepository.kt`                       | Application DAO, indexes, queries, persisted state  |
| Application accessor | `repository/IncomeAssessmentApplicationAccessor.kt`              | Higher-level application lookup/access patterns     |
| Application domain   | `domain/IncomeAssessmentApplication.kt`                          | Business state represented by persisted application |
| Documents            | `repository/DocumentRepository.kt`                               | Document persistence/retrieval                      |
| Bank statements      | `bankStatement/repository/BankStatementRepository.kt`            | Statement persistence                               |
| Statement reports    | `bankStatement/repository/BankStatementJsonReportRepository.kt`  | Statement/report persistence                        |
| Fraud                | `bankStatement/repository/FraudIndicatorRepository.kt`           | Fraud indicator persistence                         |
| Fraud mapping        | `bankStatement/repository/FraudIndicatorMappingRepository.kt`    | Fraud mapping persistence                           |
| Banks                | `FIP/repository/BankRepository.kt`                               | Bank/reference data                                 |
| Configuration        | `rules/repositories/ConfigurationRepository.kt`                  | Runtime/business configuration                      |
| Multi-bank IA        | `multibank/model/MultiBankIncomeAssessmentResult.kt`             | Multi-bank assessment result                        |
| Multi-bank fraud     | `multibank/repository/MultiBankFraudAnalysisResultRepository.kt` | Multi-bank fraud results                            |
| Mongo config         | `application.yaml`                                               | Database/collection/operational configuration       |

---

# 22. RAG Retrieval Guidance

Use the following retrieval paths depending on the question.

### "What is the source of truth for IA status?"

Retrieve:

text id="8r3v2n"
IncomeAssessmentRepository
→ IncomeAssessmentApplicationDao
→ persisted status fields


Primary collection:

text
incomeAssessmentApplications


---

### "Find the IA record for this application"

Retrieve:

text id="7m2k9c"
IncomeAssessmentRepository
→ lookup by incomeAssessmentId/productCode/partnerId


If only `applicationReferenceId` is available, inspect the repository lookup contract before assuming uniqueness.

---

### "Why is IA stuck in progress?"

Retrieve:

text id="2v6n8p"
incomeAssessmentApplications
→ status
→ retry counters
→ iaAttempts
→ vendor transaction ID
→ timestamps
→ eventStatus


Then correlate with:

text id="6c1m4x"
vendor callback
→ MongoDB update
→ Kafka event
→ downstream state


---

### "Which Perfios transaction belongs to this IA?"

Retrieve:

text id="4n8j2s"
incomeAssessmentApplications
→ perfiosTransactionId
→ iaAttempts


Then correlate the ID with the Perfios callback/API logs.

---

### "Why are there multiple IA records?"

Retrieve:

text id="1p5r7k"
incomeAssessmentId
applicationReferenceId
productCode
partnerId
timestamps
transaction IDs


Do not assume duplicate records are necessarily erroneous until the repository lookup contract and workflow attempt model are understood.

---

### "Where is bank-statement data stored?"

Retrieve:

text id="5q8m2v"
bankStatements
→ bankStatementJsonReports


Then use the application record to identify the relevant statement/application relationship.

---

### "Why does downstream status differ from MongoDB?"

Retrieve:

text id="9c4k7n"
incomeAssessmentApplications
→ eventStatus
→ Kafka publishing
→ downstream consumer


Determine whether the discrepancy occurred because of:

* event publishing failure
* event consumption failure
* delayed processing
* callback ordering
* downstream failure

---

### "How should I query Mongo for an incident?"

Preferred sequence:


Known identifier
→ repository lookup contract
→ primary application document
→ supporting collection
→ external transaction ID
→ event correlation


Do not begin with broad collection scans when a repository-defined lookup key is available.

---

# 23. Preferred Database Debugging Reasoning Path

For production incidents, use this mental model:

text id="4w9m2k"
Identifier
   ↓
Application Record
   ↓
Current State
   ↓
Attempt / Transaction
   ↓
Supporting Collection
   ↓
External Integration
   ↓
Mongo Update
   ↓
Kafka/Event
   ↓
Downstream State
   ↓
Final Outcome


The database should therefore be treated as a **timeline anchor and persisted-state source**, not as the only source of truth for a distributed IA workflow.
