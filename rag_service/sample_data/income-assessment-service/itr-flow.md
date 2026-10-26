# ITR Flow

This document describes the ITR (Income Tax Return) journey in the Income Assessment (IA) Service, including:

* ITR triggered automatically after BSA for applicable Maximus products.
* ITR triggered independently through CAP.
* ITR via Perfios.
* ITR via FinFort.
* Multiple assessment-medium selection.
* ITR document/report retrieval and processing.
* Insight report validation.
* OmniDocs document persistence.
* Final IA status update.

The ITR flow shares several processing stages with the BSA journey but has its own vendor integrations, document-processing logic, validation rules, and terminal-state handling.

---

## 1. ITR Flow in One View

There are two primary ways ITR can be initiated in IA:


                    ┌─────────────────────┐
                    │       ITR Flow      │
                    └──────────┬──────────┘
                               │
              ┌────────────────┴────────────────┐
              │                                 │
              ▼                                 ▼
      Maximus Products                    CAP Products
              │                                 │
        BSA completed                         Direct ITR
              │                                 │
              ▼                                 ▼
 BANK_STATEMENT_ASSESSMENT_COMPLETED    /initiate-application
              │                           assessMentMode=ITR
              ▼                                 │
        ITR Triggered                           │
              │                                 │
              └────────────────┬────────────────┘
                               ▼
                    ITR Assessment Medium
                               │
                  ┌────────────┴────────────┐
                  │                         │
                  ▼                         ▼
              Perfios                    FinFort
                  │                         │
                  └────────────┬────────────┘
                               ▼
                       Fetch/Process Result
                               │
                               ▼
                     Insight Report Retrieval
                               │
                  ┌────────────┴────────────┐
                  │                         │
                  ▼                         ▼
             Excel Report              JSON Report
                  │                         │
                  ▼                         ▼
             OmniDocs              Business Validation
                                            │
                                            ▼
                                      Final IA Status


The main architectural distinction is:

> **Maximus products trigger ITR after BSA completion, while CAP products can trigger ITR directly without performing BSA.**

---

# 2. ITR Triggering Models

## 2.1 Maximus Products — ITR After BSA

For applicable Maximus products, ITR is triggered after the BSA journey completes.

The request contains the `isItrSkipped` flag.


isItrSkipped = false


indicates that ITR needs to be triggered.

The BSA journey may have been completed through either:

* Perfios
* Zenith / AA-Orchestrator

After successful BSA completion, IA updates the application status in MongoDB to:


BANK_STATEMENT_ASSESSMENT_COMPLETED


This status acts as the transition point into the ITR journey.

The high-level sequence is:


Maximus
   ↓
IA
   ↓
BSA
   ↓
Perfios / Zenith
   ↓
BSA completed
   ↓
BANK_STATEMENT_ASSESSMENT_COMPLETED
   ↓
Check isItrSkipped
   ↓
ITR triggered


Important:

> ITR triggering is dependent on the configured/product-specific ITR requirement. `isItrSkipped = false` indicates that ITR should not be skipped.

---

## 2.2 CAP Products — Direct ITR

For products integrated through CAP, ITR can be initiated independently without performing BSA first.

CAP invokes IA through the primary IA initiation endpoint:


POST /income-assessment-service/v1/initiate-application


The request specifies:


assessMentMode = "ITR"


IA uses this assessment mode to determine that the requested journey is ITR.

Therefore:


CAP
 ↓
/initiate-application
 ↓
assessMentMode = ITR
 ↓
IA
 ↓
ITR Flow


There is no requirement for:


BSA
 ↓
BANK_STATEMENT_ASSESSMENT_COMPLETED


before ITR starts in this scenario.

The remainder of the ITR processing is substantially the same as the applicable Maximus ITR path.

---

# 3. Maximus ITR Decision Flow

For Maximus products, the ITR decision occurs after BSA processing.


BSA completed
      │
      ▼
BANK_STATEMENT_ASSESSMENT_COMPLETED
      │
      ▼
Is ITR skipped?
      │
      ├───────────────┐
      │               │
    false            true
      │               │
      ▼               ▼
Trigger ITR       Do not trigger ITR


When:


isItrSkipped = false


the ITR journey proceeds.

The exact ITR medium selection then depends on the assessment-medium configuration.

---

# 4. ITR Assessment Medium Selection

IA can support multiple ITR assessment mediums.

When multiple applicable mediums are enabled, the user is presented with a landing page from which they can select the desired ITR route.

Example options:


ITR Assessment Options

1. Direct ITR via FinFort
2. Offline ITR via Perfios


The user selects the required medium and IA continues through that corresponding integration.

Conceptually:


                    ITR Triggered
                          │
                          ▼
              Multiple mediums enabled?
                    │             │
                   Yes            No
                    │             │
                    ▼             ▼
             ITR Landing Page   Default ITR
                    │             │
             ┌──────┴──────┐      │
             ▼             ▼      ▼
          FinFort        Perfios Perfios


When multiple assessment mediums are **not** enabled, the default ITR route is Perfios and the user is routed directly to the vendor journey.

Important:

> **ITR medium selection is configuration-driven and may differ by product/partner context.**

---

# 5. Perfios ITR Flow

The default ITR route is Perfios when no alternative assessment-medium selection is required.

The high-level flow is:


ITR Triggered
     ↓
Generate / obtain Perfios ITR journey
     ↓
User redirected to Perfios
     ↓
User completes required ITR steps
     ↓
IA fetches transaction status
     ↓
Perfios status = SUCCESS
     ↓
Fetch Insight Report
     ↓
Excel + JSON
     ↓
Excel → OmniDocs
JSON → IA validation
     ↓
Final IA status


---

## 5.1 User ITR Journey

After IA generates the required Perfios journey/link, the user is routed to the Perfios vendor platform.

The user completes the required ITR steps on the vendor side.

Generating the vendor link does **not** mean the ITR journey is complete.

The lifecycle must distinguish:


Link generated
      ≠
User redirected
      ≠
User completed journey
      ≠
Vendor transaction successful
      ≠
Insight report retrieved
      ≠
IA validation successful


Each stage is a separate integration/state boundary.

---

## 5.2 Fetch ITR Transaction Status

After the user completes the vendor journey, IA fetches the transaction status from Perfios.

Conceptually:


Perfios
   ↓
Transaction Status
   ↓
IA


IA should proceed to report retrieval only after the vendor transaction reaches the expected successful state.

If the vendor transaction is unsuccessful, IA follows the applicable error/retry/failure path instead of treating the ITR journey as completed.

---

# 6. Perfios Insight Report Processing

After receiving a successful Perfios transaction status, IA fetches the ITR Insight Report.

The report is retrieved in two representations:


Perfios Insight Report
        │
        ├───────────────┐
        ▼               ▼
      Excel            JSON
        │               │
        ▼               ▼
    OmniDocs       IA Validation


### Excel report

The Excel representation is uploaded to OmniDocs for document persistence.


Perfios
   ↓
Excel Insight Report
   ↓
OmniDocs


### JSON report

The JSON representation is used by IA for business validation.


Perfios
   ↓
JSON Insight Report
   ↓
IA
   ↓
ITR validation rules
   ↓
Business outcome


The Excel upload and JSON validation should therefore be treated as separate processing boundaries.

A successful report fetch does not automatically mean that IA has reached its final successful status.

---

# 7. ITR Business Validation

The JSON insight report is processed by IA to perform the applicable ITR validation rules.

Conceptually:


JSON Insight Report
        ↓
Parse / transform
        ↓
ITR business validation
        ↓
Validation result
        ↓
IA state transition


The validation outcome determines the subsequent IA status.

Therefore:


Vendor SUCCESS
      ≠
IA SUCCESS


Vendor success only confirms successful completion of the relevant vendor transaction. IA still needs to retrieve/process the report and execute its own business validation.

---

# 8. FinFort ITR Flow

The FinFort flow differs from the Perfios flow primarily in how ITR documents are made available.

FinFort provides IA with S3 URLs where the required ITR documents are uploaded.

The high-level flow is:


ITR triggered
      ↓
FinFort
      ↓
FinFort uploads documents to S3
      ↓
FinFort provides S3 document URLs
      ↓
IA fetches documents from S3
      ↓
IA processes documents
      ↓
ITR validation / processing
      ↓
Final IA status


Unlike the Perfios flow, IA does not primarily rely on fetching the same type of vendor Insight Report lifecycle described above.

The important integration boundary is:


FinFort
   ↓
S3 URLs
   ↓
IA document retrieval
   ↓
Document processing


---

# 9. Perfios vs FinFort

| Area                        | Perfios                                   | FinFort                             |
| --------------------------- | ----------------------------------------- | ----------------------------------- |
| ITR journey                 | User completes journey on vendor platform | FinFort provides document locations |
| Completion signal           | Vendor transaction status                 | FinFort/S3 document availability    |
| Result source               | Insight Report                            | Documents from S3                   |
| Report processing           | Excel + JSON                              | Retrieved documents                 |
| Document persistence        | Excel uploaded to OmniDocs                | Documents fetched and processed     |
| Business validation         | JSON Insight Report                       | Processed ITR documents/data        |
| Primary integration concern | Transaction + report retrieval            | S3 document retrieval + processing  |

The key distinction is:

> **Perfios is transaction/report driven, while FinFort is document-location driven through S3 URLs.**

---

# 10. Maximus vs CAP ITR Flow

The core ITR processing after triggering is similar, but the trigger point differs.

### Maximus


Maximus
   ↓
BSA
   ↓
Perfios / Zenith
   ↓
BANK_STATEMENT_ASSESSMENT_COMPLETED
   ↓
isItrSkipped = false
   ↓
ITR


### CAP


CAP
   ↓
/initiate-application
   ↓
assessMentMode = ITR
   ↓
ITR


Therefore:

| Dimension             | Maximus                                      | CAP                            |
| --------------------- | -------------------------------------------- | ------------------------------ |
| ITR trigger           | After BSA                                    | Direct                         |
| BSA required first    | Yes                                          | No                             |
| Trigger signal        | `isItrSkipped = false` after BSA completion  | `assessMentMode = "ITR"`       |
| BSA completion state  | `BANK_STATEMENT_ASSESSMENT_COMPLETED`        | Not required                   |
| ITR processing        | Perfios / FinFort depending on configuration | Same applicable ITR processing |
| User medium selection | Configuration-dependent                      | Configuration-dependent        |

---

# 11. ITR State and Persistence

ITR processing updates the IA application state stored in MongoDB.

Important state transition points include:


BSA
 ↓
BANK_STATEMENT_ASSESSMENT_COMPLETED
 ↓
ITR triggered
 ↓
ITR vendor/document processing
 ↓
Insight report/document processing
 ↓
Business validation
 ↓
Final IA status


For debugging, inspect:

* `incomeAssessmentId`
* `applicationReferenceId`
* `commonClientTransactionId`
* ITR/vendor transaction identifiers
* current `status`
* `statusType`
* ITR attempt metadata
* timestamps
* report/document processing state
* retry information

Do not assume a vendor transaction identifier is the same as the IA application identifier.

---

# 12. ITR Failure Boundaries

ITR failures can occur at multiple independent stages.


ITR Trigger
    │
    ├── Configuration / medium selection failure
    │
    ├── Link / journey generation failure
    │
    ├── Vendor journey failure
    │
    ├── Vendor transaction status failure
    │
    ├── Insight report retrieval failure
    │
    ├── Excel upload / OmniDocs failure
    │
    ├── JSON parsing / transformation failure
    │
    ├── Business validation failure
    │
    ├── MongoDB state update failure
    │
    └── Kafka / downstream propagation failure


These failures should not automatically be treated as the same business outcome.

For example:


Perfios transaction SUCCESS
        +
Insight report retrieval FAILED


is materially different from:


Perfios transaction FAILED


Similarly:


IA status updated successfully
        +
Kafka publication FAILED


means the IA state and downstream propagation may diverge.

---

# 13. ITR Debugging Decision Tree

When debugging an ITR incident, first determine how ITR was triggered.


How was ITR triggered?
        │
        ├───────────────┐
        ▼               ▼
     Maximus           CAP
        │               │
   After BSA        Direct ITR
        │               │
        ▼               ▼
BSA completed?    assessMentMode=ITR?
        │               │
        ▼               ▼
BANK_STATEMENT_     ITR initiated?
ASSESSMENT_              │
COMPLETED                 │
        │                 │
        └────────┬────────┘
                 ▼
        Assessment medium?
          │             │
          ▼             ▼
       Perfios       FinFort
          │             │
          ▼             ▼
   Vendor status     S3 URLs
          │             │
          ▼             ▼
   Insight report   Documents
          │             │
          └──────┬──────┘
                 ▼
          Business validation
                 │
                 ▼
           Final IA status


---

# 14. ITR Incident Checklist

For an ITR issue, identify the following before drawing an RCA.

### Trigger

* Was the request from Maximus or CAP?
* Was ITR triggered after BSA or directly?
* For Maximus, was `isItrSkipped = false`?
* For CAP, was `assessMentMode = "ITR"`?
* Was BSA completed where required?
* Was the application status `BANK_STATEMENT_ASSESSMENT_COMPLETED`?

### Medium selection

* Which assessment mediums were enabled?
* Was the multiple-medium landing page shown?
* Which medium did the user select?
* If no selection was required, was the default Perfios route used?

### Perfios

* Was the ITR journey/link generated?
* Was the user redirected?
* Did the user complete the vendor journey?
* What was the vendor transaction status?
* Was the Insight Report fetched?
* Was both Excel and JSON retrieved?
* Was Excel uploaded to OmniDocs?
* Was JSON successfully parsed and validated?

### FinFort

* Did FinFort provide the S3 URLs?
* Were the S3 URLs accessible?
* Were the documents successfully downloaded?
* Did document processing succeed?
* Did validation complete?

### IA processing

* Which business validation rules executed?
* What status transition was expected?
* What status was actually persisted?
* Was the state guard satisfied?
* Was the final status updated in MongoDB?

### Downstream

* Was a Kafka event generated?
* Was the event published successfully?
* Was it consumed?
* Did downstream processing succeed?
* Was CAP status synchronization required/enabled?

---

# 15. ITR RCA Mental Model

For any ITR production incident, reconstruct:


WHO triggered ITR?
        ↓
WHY was ITR triggered?
        ↓
WHICH IA application?
        ↓
WHICH BSA/ITR dependency?
        ↓
WHICH assessment medium?
        ↓
WHICH vendor/document attempt?
        ↓
WHICH transaction/document?
        ↓
WHICH status?
        ↓
WHICH report/document?
        ↓
WHICH validation?
        ↓
WHICH IA state transition?
        ↓
WHICH Kafka/downstream propagation?
        ↓
FINAL IA STATE


The key RCA question is:

> **At which step did the actual ITR journey first diverge from the expected flow?**

---

# 16. Code and Configuration Anchors

Exact implementation should be verified against the current repository.

Relevant areas include:

* ITR controller and service classes under `itr/`
* `IncomeAssessmentApplicationServiceV3`
* ITR-specific gateways/clients
* Perfios integration classes
* FinFort integration classes
* `IncomeAssessmentApplicationDao`
* `IncomeAssessmentRepository`
* `ConfigFetcher`
* `PartnerProductConfigurations`
* Kafka event producers/consumers
* OmniDocs/document integration classes
* `application.yaml`

Important configuration areas include:

* ITR assessment-medium configuration
* `isItrSkipped`
* `assessMentMode`
* Perfios ITR endpoints
* FinFort endpoints/S3 configuration
* OmniDocs configuration
* retry configuration
* error-code mappings
* partner/product-specific configuration

Current code and runtime configuration should take precedence over this document when exact behavior differs.

---

# 17. RAG Retrieval Terms

High-value retrieval terms for this flow include:


ITR
ITR flow
ITR journey
ITR assessment
isItrSkipped
assessMentMode
ITR via Perfios
Offline ITR via Perfios
ITR via FinFort
FinFort
S3 URL
ITR documents
Insight Report
ITR Insight Report
Excel report
JSON report
OmniDocs
ITR validation
BANK_STATEMENT_ASSESSMENT_COMPLETED
BSA completed
Maximus ITR
CAP ITR
direct ITR
multiple assessment medium
ITR landing page
Perfios ITR
FinFort ITR
ITR transaction status
ITR report retrieval


---

# 18. Cross-Document Retrieval Map

| Question                                                 | First retrieval         | Supporting retrieval                                                    |
| -------------------------------------------------------- | ----------------------- | ----------------------------------------------------------------------- |
| How does ITR work end-to-end?                            | `flows/itr-flow.md`     | `flows/income-assessment-flow.md`                                       |
| How is ITR triggered after BSA?                          | `flows/itr-flow.md`     | `04-business-logic.md`, `flows/perfios-flow.md`, `flows/zenith-flow.md` |
| How does CAP directly trigger ITR?                       | `flows/itr-flow.md`     | `flows/cap-flow.md`, `03-api-contracts.md`                              |
| Why didn't ITR trigger after BSA?                        | `10-troubleshooting.md` | `flows/itr-flow.md`, `04-business-logic.md`, `09-configuration.md`      |
| Why was ITR skipped?                                     | `flows/itr-flow.md`     | `09-configuration.md`, `04-business-logic.md`                           |
| Why did user see the ITR landing page?                   | `flows/itr-flow.md`     | `09-configuration.md`                                                   |
| Why did ITR use Perfios instead of FinFort?              | `flows/itr-flow.md`     | `09-configuration.md`                                                   |
| Why did Perfios ITR fail?                                | `flows/itr-flow.md`     | `05-integrations.md`, `08-error-handling.md`, `10-troubleshooting.md`   |
| Why was the Insight Report not retrieved?                | `10-troubleshooting.md` | `flows/itr-flow.md`, `05-integrations.md`                               |
| Why was Excel not uploaded to OmniDocs?                  | `flows/itr-flow.md`     | `05-integrations.md`, `08-error-handling.md`                            |
| Why did ITR validation fail?                             | `04-business-logic.md`  | `flows/itr-flow.md`, `08-error-handling.md`                             |
| Why did FinFort ITR fail?                                | `flows/itr-flow.md`     | `05-integrations.md`, `10-troubleshooting.md`                           |
| Why couldn't IA fetch FinFort documents?                 | `10-troubleshooting.md` | `flows/itr-flow.md`, `05-integrations.md`                               |
| Why is ITR status different from vendor status?          | `flows/itr-flow.md`     | `04-business-logic.md`, `06-database.md`                                |
| Why is Mongo correct but downstream ITR status is wrong? | `06-database.md`        | `07-kafka-events.md`, `10-troubleshooting.md`                           |
| What does `isItrSkipped` mean?                           | `flows/itr-flow.md`     | `11-glossary.md`, `09-configuration.md`                                 |
| What does `assessMentMode=ITR` mean?                     | `flows/itr-flow.md`     | `03-api-contracts.md`, `flows/cap-flow.md`                              |

---

# 19. Core ITR Invariants

1. ITR can be triggered independently through CAP.
2. ITR can also be triggered after BSA for applicable Maximus products.
3. Maximus ITR requires the applicable BSA completion transition before automatic triggering.
4. `isItrSkipped = false` indicates that ITR should be triggered for the applicable Maximus flow.
5. BSA can complete through Perfios or Zenith before Maximus ITR is triggered.
6. `BANK_STATEMENT_ASSESSMENT_COMPLETED` is an important transition point from BSA to ITR.
7. CAP can trigger ITR directly using `/initiate-application` with `assessMentMode = "ITR"`.
8. CAP direct ITR does not require BSA to complete first.
9. Multiple ITR assessment mediums can be enabled depending on configuration.
10. When multiple mediums are enabled, the user can select between the applicable ITR routes.
11. When the applicable multiple-medium selection is not required, the default ITR route is Perfios.
12. Perfios ITR requires vendor journey completion before successful report processing.
13. Vendor transaction success does not automatically mean IA business success.
14. Perfios Insight Report processing has separate Excel and JSON paths.
15. Excel is uploaded to OmniDocs.
16. JSON is used for IA business validation.
17. FinFort provides S3 URLs containing the ITR documents.
18. IA fetches and processes FinFort documents from those S3 URLs.
19. Perfios and FinFort therefore have materially different result/document retrieval mechanisms.
20. Report/document retrieval, validation, MongoDB state update, and downstream event publication are separate failure boundaries.
21. Current code and runtime configuration are authoritative when documentation and implementation differ.

---

## 20. Preferred Mental Model

For ITR questions, think:


Trigger
  ↓
BSA dependency?
  ↓
IA application
  ↓
Assessment-medium configuration
  ↓
Perfios / FinFort
  ↓
Vendor transaction / S3 documents
  ↓
Report / document retrieval
  ↓
OmniDocs persistence
  ↓
JSON/document processing
  ↓
Business validation
  ↓
IA state transition
  ↓
Kafka / downstream propagation
  ↓
Final outcome


The most important question during debugging is:

> **Which ITR trigger path was used, which assessment medium was selected, and at which boundary did the actual flow first diverge from the expected flow?**
