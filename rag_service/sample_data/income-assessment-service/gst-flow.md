# GST Flow

## 1. Purpose

This document describes the GST-specific assessment flow in Income Assessment (IA), including:

* How GST is initiated
* CAP-specific initiation
* FinFort vendor interaction
* Multiple GST numbers associated with one PAN
* Multiple GST assessment executions
* Callback handling
* Insight report and document retrieval
* OmniDocs upload
* Internal GST collection persistence
* Correlation using `ffOrderId`
* Current absence of GST insight-data validation
* Failure and debugging boundaries

GST is currently applicable **only through the CAP portal** and can be performed independently through **FinFort**.

GST should be treated as a separate assessment journey rather than an extension of the BSA or ITR flow.

---

# 2. GST Architecture in One View

The high-level GST flow is:


CAP Portal
    |
    | POST /initiate-application
    | assessmentMode = "GST"
    v
IA
    |
    | Identify GST assessment
    v
GST / FinFort Flow
    |
    | Initiate vendor process
    v
FinFort
    |
    | User completes GST journey
    v
User redirected back to IA
    |
    | Wait for callback(s)
    v
IA Callback Processing
    |
    | Fetch Insight Reports + Documents
    v
FinFort
    |
    +--------------------+
    |                    |
    v                    v
OmniDocs           Internal GST Collection
Documents          JSON / GST response
                       |
                       | correlated using ffOrderId
                       v
                  GST Assessment State


The important distinction is:

> CAP initiates the GST assessment, but FinFort executes the external GST journey.

CAP is therefore the **upstream platform**, while FinFort is the **assessment/vendor integration**.

---

# 3. GST Trigger

GST is currently triggered only through the CAP portal.

CAP invokes the IA initiation API:


POST /income-assessment-service/v1/initiate-application


The request contains:


assessmentMode = "GST"


IA uses this assessment mode to determine that the requested journey is GST and routes execution to the GST flow.

Conceptually:


CAP
  |
  | assessmentMode = GST
  v
IA /initiate-application
  |
  v
GST Flow
  |
  v
FinFort


### Important invariant


assessmentMode = GST
        =>
IA must enter the GST assessment path


Do not assume that GST is triggered because the user is already in a BSA or ITR journey.

GST can be performed independently.

---

# 4. GST Is Independent of BSA and ITR

GST is currently an independent assessment journey.

It does not require:


BSA -> GST


or:


ITR -> GST


The current supported trigger is:


CAP -> IA -> GST -> FinFort


This is different from the Maximus ITR scenario where ITR can be triggered after completion of BSA.

For debugging, first establish the assessment mode:


assessmentMode = GST


before assuming that the issue belongs to BSA, ITR, Perfios, or Zenith.

---

# 5. Multiple GST Numbers

A user can have multiple GST numbers/GSTINs associated with the same PAN.

Therefore, a single user/PAN does not necessarily represent a single GST assessment.

Conceptually:


PAN
 |
 +-- GSTIN 1
 |
 +-- GSTIN 2
 |
 +-- GSTIN 3


The user may perform GST assessment for multiple GST numbers.

This introduces an important correlation requirement:

> GST debugging must distinguish the PAN-level identity from the individual GST assessment/vendor transaction.

Do not assume:


1 PAN = 1 GST assessment


Instead:


1 PAN
   |
   +-- GST assessment for GSTIN 1
   +-- GST assessment for GSTIN 2
   +-- GST assessment for GSTIN 3


The exact application/vendor correlation should be established using the persisted GST identifiers and `ffOrderId`.

---

# 6. FinFort Journey

After IA identifies that the requested assessment mode is GST, IA initiates the FinFort journey.

Conceptually:


CAP
  |
  | assessmentMode = GST
  v
IA
  |
  | Initiate GST assessment
  v
FinFort
  |
  | Generate/return vendor journey details
  v
IA
  |
  | Redirect user
  v
User


The user is redirected to the FinFort journey.

### Important distinction

Generating or receiving the FinFort journey information does **not** mean that GST assessment has completed.

There are several separate stages:


GST initiation
      !=
FinFort link/journey creation
      !=
User completion
      !=
Callback received
      !=
Insight report fetched
      !=
Documents fetched
      !=
IA GST data persisted


This distinction is important when debugging apparently successful vendor interactions followed by an incomplete IA journey.

---

# 7. User Journey and Redirect

The user leaves IA and completes the GST process on the vendor side.

High-level flow:


IA
 |
 | Redirect
 v
FinFort
 |
 | User performs GST assessment
 |
 | GST information processing
 v
FinFort completion
 |
 | Redirect back
 v
IA
 |
 | Wait for callback
 v
Callback processing


A successful redirect back to IA does not itself establish that the GST assessment has been successfully processed.

The callback remains an important integration boundary.

---

# 8. Callback Model

After completing the FinFort journey, the user is redirected back to IA and IA waits for the vendor callback.

GST has an important callback characteristic:

> Multiple callbacks may be received for different GST assessments, or a single callback may represent all GST assessments.

Therefore, callback processing cannot blindly assume:


1 callback = 1 GSTIN


or:


1 callback = all GSTINs


Both behaviors may occur.

Conceptually:

### Multiple callbacks


FinFort
 |
 +-- Callback -> GSTIN 1
 |
 +-- Callback -> GSTIN 2
 |
 +-- Callback -> GSTIN 3


### Single callback


FinFort
 |
 +-- Callback -> GSTIN 1 + GSTIN 2 + GSTIN 3


The callback payload and persisted identifiers should therefore be inspected to determine the actual callback scope.

---

# 9. Callback Processing

Once IA receives the callback, it proceeds with GST result processing.

Conceptually:


FinFort Callback
      |
      v
IA Callback Handler
      |
      v
Identify GST assessment / ffOrderId
      |
      v
Fetch Insight Reports
      |
      +-------------------+
      |                   |
      v                   v
Fetch Documents      Fetch JSON/Data
      |                   |
      v                   v
OmniDocs             GST Collection


The callback should be treated as a workflow trigger rather than simply a notification.

A callback may cause IA to perform additional external calls and persistence operations.

---

# 10. `ffOrderId` Correlation

During FinFort initiation, IA receives an `ffOrderId` from the vendor.

This identifier is important for GST result correlation.

The internal GST data is maintained against:


ffOrderId


Conceptually:


FinFort
   |
   | ffOrderId = X
   v
IA
   |
   +--> GST processing
   |
   +--> Insight reports
   |
   +--> Documents
   |
   +--> Internal GST collection
          |
          +--> ffOrderId = X


When debugging GST, `ffOrderId` should therefore be treated as a high-value correlation identifier.

Do not rely only on:

* PAN
* application reference
* user identity
* callback timestamp

when tracing a specific GST vendor execution.

---

# 11. Insight Report Processing

After receiving the callback, IA fetches the Insight Reports from FinFort.

The retrieved response may contain multiple pieces of GST-related information and documents.

Conceptually:


GST Callback
    |
    v
Fetch Insight Reports
    |
    +--> JSON response
    |
    +--> Documents / report artifacts


The JSON response is persisted into the internal GST collection.

Documents are handled separately and uploaded to OmniDocs.

---

# 12. GST Collection

IA maintains an internal GST collection for the GST-specific data.

The JSON response obtained from the vendor is persisted in this collection.

The primary vendor correlation mentioned for this data is:


ffOrderId


Conceptually:


GST Collection

ffOrderId
   |
   +-- GST JSON / Insight data
   +-- GST assessment information
   +-- related processing metadata


When investigating missing or incorrect GST data, inspect the GST collection using the relevant `ffOrderId`.

Do not assume that the OmniDocs document upload and GST collection update are the same persistence operation.

They represent different outputs of the GST processing stage.

---

# 13. Document Processing and OmniDocs

GST processing can produce different documents in addition to the JSON insight response.

The documents are uploaded to OmniDocs.

Conceptually:


FinFort
   |
   | Insight report / documents
   v
IA
   |
   +----------------------+
   |                      |
   v                      v
JSON/Data              Documents
   |                      |
   v                      v
GST Collection         OmniDocs


This creates two separate persistence boundaries:

1. **GST JSON/data → internal GST collection**
2. **GST documents → OmniDocs**

A successful document upload should therefore not automatically be interpreted as successful GST data persistence, and vice versa.

---

# 14. No GST Insight Validation Currently

A critical current-state behavior is:

> IA currently does not perform business validation on the GST insight data.

This means GST differs from assessment flows where vendor data is subsequently evaluated against business rules before determining an IA outcome.

Current GST processing is closer to:


Callback
   |
   v
Fetch Insight Report
   |
   +--> Persist JSON
   |
   +--> Upload Documents
   |
   v
GST Processing Complete


rather than:


Callback
   |
   v
Fetch Insight Report
   |
   v
Business Validation
   |
   v
Eligibility / Policy Decision
   |
   v
Final IA Status


Therefore, when debugging GST, do not search for a GST insight-validation rule unless newer code has introduced one.

---

# 15. GST vs ITR

GST and ITR both use FinFort-related processing, but their business purpose and data flow should not be conflated.

| Aspect                    | GST                       | ITR                                            |
| ------------------------- | ------------------------- | ---------------------------------------------- |
| Current upstream trigger  | CAP                       | CAP or Maximus                                 |
| Assessment mode           | `GST`                     | `ITR` / ITR-specific trigger                   |
| Vendor                    | FinFort                   | FinFort or Perfios depending on flow           |
| Can be independent?       | Yes                       | Yes, depending on trigger                      |
| Multiple GSTINs           | Yes                       | Not the same model                             |
| Vendor correlation        | `ffOrderId`               | ITR-specific transaction/correlation           |
| Insight report            | Yes                       | Yes                                            |
| Documents                 | Yes                       | Yes                                            |
| OmniDocs                  | Yes                       | Yes                                            |
| JSON persisted internally | GST collection            | ITR-specific processing                        |
| Insight validation        | **Currently none**        | Validation is performed in applicable ITR flow |
| Callback behavior         | One or multiple callbacks | Flow-specific                                  |

The important RAG distinction is:


GST != ITR


even though FinFort may participate in both flows.

---

# 16. GST Failure Boundaries

The GST flow has several independent failure boundaries.


CAP initiation
      |
      v
IA GST routing
      |
      v
FinFort initiation
      |
      v
User redirect
      |
      v
User completes vendor journey
      |
      v
Callback
      |
      v
Insight report retrieval
      |
      +--------------------+
      |                    |
      v                    v
Document retrieval     JSON retrieval
      |                    |
      v                    v
OmniDocs upload        GST collection


A failure at one boundary does not necessarily mean the entire GST journey failed at the same point.

---

# 17. Common GST Failure Scenarios

## 17.1 GST flow not triggered

Check:


CAP request
   |
   v
assessmentMode


Expected:


assessmentMode = GST


Then verify that IA routed the request to the GST implementation.

---

## 17.2 FinFort initiation failed

Investigate:

1. CAP request
2. `assessmentMode`
3. IA GST routing
4. FinFort request
5. FinFort response
6. `ffOrderId`
7. retry/error mapping
8. persisted application state

Important question:

> Did IA fail before FinFort created the vendor order, or did FinFort create an order and IA fail afterward?

---

## 17.3 User completed GST but callback was not received

Trace:


FinFort completion
      |
      v
Callback generated?
      |
      v
Callback reached IA?
      |
      v
Callback accepted?
      |
      v
Correct GST / ffOrderId identified?
      |
      v
Report processing started?


Do not immediately conclude that the user did not complete the journey.

The vendor may have completed processing while the callback integration failed.

---

## 17.4 Multiple callbacks

If multiple callbacks are observed, establish:


callback 1 -> which GST / ffOrderId?
callback 2 -> which GST / ffOrderId?
callback 3 -> which GST / ffOrderId?


Do not assume that callbacks are duplicates without examining their correlation identifiers and payload scope.

---

## 17.5 Callback received but insight report missing

Trace:


Callback
   |
   v
ffOrderId extraction
   |
   v
Insight report API
   |
   v
Vendor response
   |
   v
IA parsing
   |
   v
Persistence


The callback only establishes that the callback boundary was crossed; report retrieval is a separate integration step.

---

## 17.6 Documents missing from OmniDocs

Separate:


Insight report retrieved


from:


Document retrieved


and:


Document uploaded to OmniDocs


Check each boundary independently.

---

## 17.7 GST collection missing

Investigate:


Callback
   |
   v
Insight report
   |
   v
JSON response
   |
   v
GST persistence
   |
   v
GST collection


Use `ffOrderId` as the primary correlation point.

---

## 17.8 GST data looks incorrect

Because GST insight data currently has no business validation, distinguish:


Vendor returned incorrect/unexpected data


from:


IA validation rejected the data


The latter should not currently be assumed.

First inspect the raw vendor response and the persisted GST collection.

---

# 18. GST Debugging Decision Tree


GST issue reported
       |
       v
Was /initiate-application called?
       |
       +-- NO --> Investigate CAP
       |
       +-- YES
            |
            v
   assessmentMode = GST?
            |
            +-- NO --> Request/routing issue
            |
            +-- YES
                 |
                 v
        GST flow triggered?
                 |
                 +-- NO --> IA routing/config/code
                 |
                 +-- YES
                      |
                      v
             FinFort order created?
                      |
                      +-- NO --> FinFort initiation
                      |
                      +-- YES
                           |
                           v
                       ffOrderId
                           |
                           v
                  User completed journey?
                           |
                           v
                     Callback received?
                           |
              +------------+------------+
              |                         |
             NO                        YES
              |                         |
      callback/vendor issue        identify scope
                                        |
                                        v
                               one GST or multiple?
                                        |
                                        v
                                Fetch insight report
                                        |
                             +----------+----------+
                             |                     |
                           FAIL                  SUCCESS
                             |                     |
                    report retrieval issue    persist JSON
                                                   |
                                                   +--> GST collection
                                                   |
                                                   +--> fetch documents
                                                          |
                                                          v
                                                       OmniDocs


---

# 19. Debugging Correlation Identifiers

For a GST incident, collect as many of the following as available:


applicationReferenceId
incomeAssessmentId
commonClientTransactionId
serviceRequestId
requestId
partnerId
productCode
assessmentMode
ffOrderId
GSTIN
callback timestamp
callback payload
current IA status
GST collection record
OmniDocs document/reference
FinFort response
eventId
retry count


### Highest-value GST identifiers

For vendor-level GST debugging, prioritize:


ffOrderId
GSTIN
applicationReferenceId
incomeAssessmentId


The exact identifier hierarchy should follow the current implementation.

---

# 20. GST Observability Mental Model

For GST incidents, reconstruct the journey as:


CAP request
    ↓
assessmentMode = GST
    ↓
IA GST routing
    ↓
FinFort initiation
    ↓
ffOrderId
    ↓
User redirected
    ↓
User completes GST
    ↓
Callback(s)
    ↓
ffOrderId / GST correlation
    ↓
Insight report retrieval
    ↓
JSON persistence
    ↓
Document retrieval
    ↓
OmniDocs upload


Then ask:

> At which boundary did the actual GST journey first diverge from the expected flow?

This should be the primary RCA question.

---

# 21. Code and Configuration Investigation Anchors

When implementing or debugging GST, search for:

### Entry and routing


initiate-application
assessmentMode
GST


### FinFort


FinFort
ffOrderId


### Callback


GST callback
callback handler
callback consumer
ffOrderId


### GST persistence


GST collection
GST repository
GST entity/model
ffOrderId


### Reports


Insight Report
GST report


### Documents


OmniDocs
document upload
GST documents


### Configuration


FinFort endpoint configuration
GST configuration
document service configuration
OmniDocs configuration


Prefer current implementation over documentation when exact behavior is uncertain.

---

# 22. Source-of-Truth Hierarchy

For GST-specific questions, use this hierarchy:

1. Current GST service/handler implementation
2. FinFort gateway/client implementation
3. GST callback implementation
4. GST entity/repository/collection model
5. OmniDocs integration
6. Current configuration
7. Tests/stubs
8. README or historical documentation

If this document conflicts with current code, the current code wins.

---

# 23. RAG Retrieval Map

| Developer question                               | Retrieve first                                                     |
| ------------------------------------------------ | ------------------------------------------------------------------ |
| How is GST triggered?                            | `gst-flow.md` → GST Trigger                                        |
| How does CAP initiate GST?                       | `cap-flow.md` + `gst-flow.md`                                      |
| What does `assessmentMode = GST` do?             | `gst-flow.md` → GST Trigger                                        |
| How does GST use FinFort?                        | `gst-flow.md` → FinFort Journey                                    |
| Can one user have multiple GST assessments?      | `gst-flow.md` → Multiple GST Numbers                               |
| Why are there multiple GST callbacks?            | `gst-flow.md` → Callback Model                                     |
| How do I correlate a GST callback?               | `gst-flow.md` → `ffOrderId` Correlation                            |
| Where is GST JSON stored?                        | `gst-flow.md` → GST Collection + `database.md`                     |
| Where are GST documents stored?                  | `gst-flow.md` → Document Processing + `integrations.md`            |
| Why is GST data in the DB but document missing?  | `gst-flow.md` → Document Processing + `troubleshooting.md`         |
| Why did FinFort complete but IA not process GST? | `gst-flow.md` → Callback Model + `error-handling.md`               |
| Does IA validate GST insight data?               | `gst-flow.md` → No GST Insight Validation                          |
| How does GST differ from ITR?                    | `gst-flow.md` → GST vs ITR + `itr-flow.md`                         |
| How do I debug a GST issue?                      | `gst-flow.md` → GST Debugging Decision Tree + `troubleshooting.md` |
| Is GST independent of BSA?                       | `gst-flow.md` → GST Is Independent of BSA and ITR                  |
| Why is OmniDocs missing GST documents?           | `gst-flow.md` → Document Processing + `integrations.md`            |

---

# 24. Key RAG Terms


GST
GST flow
GST assessment
GSTIN
PAN
CAP
CAP portal
assessmentMode
assessmentMode = GST
FinFort
ffOrderId
GST callback
multiple GST callbacks
multiple GSTINs
Insight Report
GST Insight Report
GST collection
GST JSON
GST documents
OmniDocs
GST document upload
GST report retrieval
GST callback correlation
GST validation
GST insight validation


---

# 25. Important Invariants

The following statements should be treated as strong GST-flow invariants unless current code proves otherwise:


GST is currently initiated through CAP.

assessmentMode = GST identifies the GST journey.

GST can be performed independently.

A PAN can have multiple GST numbers/GSTINs.

A user may perform GST assessment for multiple GST numbers.

FinFort executes the external GST journey.

User redirect back to IA does not equal completed GST processing.

GST may result in multiple callbacks or a single callback covering multiple GSTs.

FinFort provides an ffOrderId during initiation.

GST internal data is correlated/persisted using ffOrderId.

GST documents are uploaded to OmniDocs.

GST JSON/Insight data is maintained in an internal GST collection.

GST insight data is currently not subjected to business validation by IA.

OmniDocs persistence and GST collection persistence are separate boundaries.

FinFort success does not automatically imply successful IA GST processing.


---

# 26. Canonical GST Mental Model

The most useful mental model for the entire GST journey is:


CAP
  |
  | assessmentMode = GST
  v
IA
  |
  | GST routing
  v
FinFort
  |
  | ffOrderId
  v
User GST Journey
  |
  v
Callback(s)
  |
  | GST / ffOrderId correlation
  v
Insight Report Retrieval
  |
  +-----------------------+
  |                       |
  v                       v
JSON/Data             Documents
  |                       |
  v                       v
GST Collection         OmniDocs


The most important debugging question is:

> **Did the GST journey fail during CAP initiation, FinFort execution, callback delivery/correlation, insight report retrieval, GST persistence, or document/OmniDocs processing?**

That boundary should be identified before assigning an RCA.
