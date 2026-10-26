# Toggles & IA Configurations

## 1. Purpose

Income Assessment (IA) behavior is heavily controlled by runtime configuration.

Two configuration mechanisms are particularly important:

1. **Feature Toggles**

    * Stored in the `masters` database.
    * Collection: `featureToggles`
    * Used primarily to enable/disable specific IA capabilities or product-specific behavior.

2. **IA / Partner-Product Configurations**

    * Stored in the `income-assessment` database.
    * Collection: `configurations`
    * Used to control journey behavior, retries, timeouts, vendor selection, IA version, and other runtime business/configuration rules.

These configurations are critical during debugging because the same code path can behave differently depending on:


Partner
Product
Scope
Feature Toggle
PartnerProductConfig
IA Version
Assessment Medium


Therefore:

> Never conclude that a piece of IA behavior is hardcoded until the relevant feature toggle and PartnerProductConfig have been checked.

---

# 2. Configuration Architecture

The high-level model is:


Request
   |
   v
Identify Partner + Product + Context
   |
   +-----------------------------+
   |                             |
   v                             v
Feature Toggle Lookup      PartnerProductConfig Lookup
   |                             |
   v                             v
masters.featureToggles      income-assessment.configurations
   |                             |
   +-------------+---------------+
                 |
                 v
        IA Runtime Behavior
                 |
                 v
       Version / Journey / Rules
                 |
                 v
        External Integrations


The two mechanisms should not be treated as interchangeable.

### Feature Toggle

Answers:

> Is this capability enabled?

### PartnerProductConfig

Answers:

> How should this capability behave for this partner/product?

---

# 3. Feature Toggles

## 3.1 Database

Feature toggles are stored in:


Database: masters
Collection: featureToggles


Example query:


{name:/redirecttoaa/i,scope:"PERSONAL"}


This indicates that feature toggles can be scoped, including product/scope-specific behavior.

When debugging a toggle:

1. Identify the exact toggle name.
2. Identify the applicable scope/product.
3. Query the `featureToggles` collection.
4. Confirm the current value.
5. Find the code consuming the toggle.
6. Confirm which runtime branch the toggle activates.

Do not rely only on the toggle's name; verify the consuming code.

---

# 4. Feature Toggle Catalog

## 4.1 `uploadStatementPerfiosIA`

**Purpose:** Product-specific toggle that enables document uploads to OmniDocs for the Perfios IA flow.


uploadStatementPerfiosIA
        |
        v
Enable document upload
        |
        v
OmniDocs


### Debugging use

If a Perfios bank statement document is available from the vendor but is missing from OmniDocs, check this toggle before assuming that the document-service integration itself failed.

---

## 4.2 `enableTransactionReportEncrypted`

**Purpose:** Product-specific toggle that enables the encrypted ESB endpoint for fetching the vendor transaction report.

Conceptually:


Toggle OFF
   -> normal/report retrieval path

Toggle ON
   -> encrypted ESB report endpoint


### Debugging use

If report retrieval is behaving differently across products, compare this toggle before comparing business logic.

---

## 4.3 `enableRBIHVendorId`

**Purpose:** Business Loan (BL)-specific toggle that enables the RBIH vendor.

This toggle affects vendor selection/identification for the applicable BL flow.

### Debugging question

> Is the RBIH vendor expected for this product, and is `enableRBIHVendorId` enabled?

---

## 4.4 `enablePerfiosGenerateLinkEncrypted`

**Purpose:** Product-specific toggle that enables the encrypted ESB endpoint for generating the Perfios/vendor journey link.

Conceptually:


Generate Link
     |
     v
enablePerfiosGenerateLinkEncrypted?
     |
     +-- ON  -> encrypted ESB endpoint
     |
     +-- OFF -> alternate configured path


### Debugging use

Useful when one product successfully generates a vendor link while another product receives an endpoint or integration error.

---

## 4.5 `addMobileNumberAndInstitutionIdForAA`

**Purpose:** Product-specific toggle that enables passing:

* Mobile number
* Institution ID

when initiating an Account Aggregator (AA) journey.

Conceptually:


AA journey
    |
    v
addMobileNumberAndInstitutionIdForAA
    |
    +--> mobile number
    +--> institution ID


### Debugging use

If AA initiation differs between products, verify this toggle and inspect the generated request payload.

---

## 4.6 `enableKarzaNameMatchForBankStatement`

**Purpose:** Product-specific toggle that enables name matching through the Karza API for bank statement assessment.


Bank Statement
      |
      v
Karza Name Match
      |
      v
Name validation


### Debugging use

If Karza name-match behavior is observed for one product but not another, check this toggle.

---

## 4.7 `ignoreInvalidClientTransactionIdException`

**Purpose:** Product-specific toggle that prevents IA from performing callback-identifier format validation.

This is relevant to callback processing.

Conceptually:


Callback
   |
   v
callbackIdentifier format validation
   |
   +-- Toggle OFF -> validation performed
   |
   +-- Toggle ON  -> invalid-format exception ignored


### Debugging use

If a callback contains an unexpected `callbackIdentifier` format, inspect this toggle before concluding that the callback was rejected due to malformed input.

---

## 4.8 `isTwoYearItrEnabled`

**Purpose:** Product-specific toggle that enables ITR assessment for two years.

This affects the scope of ITR assessment.


isTwoYearItrEnabled
       |
       v
ITR assessment period
       |
       v
Two-year ITR processing


### Debugging use

When ITR processing unexpectedly covers one year vs two years, check this toggle.

---

## 4.9 `enableImputedIncome`

**Purpose:** Product-specific toggle that enables imputed income to be considered during bank statement insight validation.

Conceptually:


Insight Report
      |
      +--> Actual income
      |
      +--> Imputed income
                |
                v
       enableImputedIncome
                |
                v
        Validation calculation


### Important distinction

This toggle affects **validation input**, not necessarily whether the vendor returns imputed income.

---

## 4.10 `redirectToAA`

**Purpose:** Product-specific toggle that enables automatic redirection to the vendor through the Account Aggregator assessment medium.

Conceptually:


Assessment Medium = AA
          |
          v
redirectToAA
          |
          +-- enabled -> automatic vendor redirection
          |
          +-- disabled -> alternate/manual journey behavior


### Debugging use

If the expected AA journey does not automatically redirect the user to the vendor, inspect this toggle.

Example query:


{name:/redirecttoaa/i,scope:"PERSONAL"}


---

## 4.11 `publishPerfiosBankStatementReportFetchedEvent`

**Purpose:** Product-specific toggle that enables publishing the bank statement report-fetched event after the Perfios report is retrieved.

Conceptually:


Perfios Report Fetched
        |
        v
publishPerfiosBankStatementReportFetchedEvent
        |
        v
Kafka Event


### Debugging use

If the report is successfully fetched but downstream processing does not start, check whether this event is enabled and published.

This is particularly important when investigating:


Report fetched successfully
        BUT
Expected downstream event missing


---

## 4.12 `salaryMedianCalculationForCapability`

**Purpose:** Product-specific toggle that enables median salary calculation for capability/multibanking products.


Multiple banking data
       |
       v
Salary values
       |
       v
Median salary calculation


### Debugging use

If capability-related salary calculations differ between products, check this toggle.

---

## 4.13 `enableSalaryCategoryFilterForImputed`

**Purpose:** Product-specific toggle that causes only income belonging to the `SALARY` category to be considered for imputed-income processing.

Conceptually:


Imputed Income
      |
      v
Category filtering
      |
      v
SALARY only


This is related to `enableImputedIncome` but is a separate control.

### Important distinction


enableImputedIncome
    =
whether imputed income participates

enableSalaryCategoryFilterForImputed
    =
which imputed-income category participates


---

## 4.14 `enableEODBasedABBCalculation`

**Purpose:** Product-specific toggle that enables End-of-Day (EOD)-based Average Bank Balance (ABB) calculation.


Bank transactions
       |
       v
EOD balances
       |
       v
ABB calculation


### Debugging use

If ABB calculations differ between products, check this toggle and the corresponding calculation implementation.

---

## 4.15 `validateInterestTransactions`

**Purpose:** Product-specific toggle that enables validation of interest-credit transactions.


Bank Statement
      |
      v
Interest transactions
      |
      v
validateInterestTransactions
      |
      v
Interest validation


### Debugging use

Useful when interest credits are included/excluded differently across product journeys.

---

## 4.16 `modifyFcuTaskCreationForBigDebit`

**Purpose:** Product-specific toggle that modifies FCU task creation behavior for big-debit transactions.

Conceptually:


Bank transactions
      |
      v
Big debit detected
      |
      v
FCU task creation


The toggle controls whether the modified FCU task-creation behavior is active.

---

## 4.17 `enableIARetryableRuleValidation`

**Purpose:** Product-specific toggle that enables retry functionality for specific rule-validation failures.

Conceptually:


Business Rule Validation
       |
       v
Failure
       |
       v
enableIARetryableRuleValidation
       |
       +-- enabled -> retryable behavior
       |
       +-- disabled -> normal failure handling


### Debugging use

If an IA rule failure unexpectedly allows a retry or does not allow one, inspect this toggle together with the retry configuration.

---

# 5. PartnerProductConfig

The second major configuration mechanism is the PartnerProductConfig.

## Database


Database: income-assessment
Collection: configurations


Example query:


{group:/PartnerProductConfig/i,name:"Personal"}


This configuration controls runtime behavior for a particular partner/product context.

Conceptually:


PartnerProductConfig
        |
        +--> retry behavior
        +--> loader behavior
        +--> callback behavior
        +--> vendor selection
        +--> document processing
        +--> IA version
        +--> journey behavior


---

# 6. PartnerProductConfig Catalog

## 6.1 `retryErrorMsgScreen`

Controls whether the retry/error screen is enabled.

This configuration is particularly important for the post-vendor loading experience.

### Important behavior

It is **mandatory to enable the loading-screen behavior after the user returns to IA**.

If it is not enabled, the user may be redirected back to the product immediately instead of seeing the expected IA loading/retry experience.

Conceptually:


User returns from vendor
        |
        v
retryErrorMsgScreen
        |
        +-- enabled -> IA loading/retry experience
        |
        +-- disabled -> redirect back to product


---

## 6.2 `iaLoaderTimeoutEnabled`

Controls whether the IA loader timeout mechanism is enabled.

When enabled, IA can terminate the loading state after a configured duration if the expected callback has not been received.

Conceptually:


User returns to IA
        |
        v
Wait for callback
        |
        v
iaLoaderTimeoutEnabled
        |
        v
Timer starts
        |
        +--> callback received -> continue processing
        |
        +--> timeout -> loader timed out
                              |
                              v
                         retry available


---

## 6.3 `iaLoaderTimeoutDuration`

Controls the duration after which the IA loader times out.

This value should be interpreted together with:


iaLoaderTimeoutEnabled


The relationship is:


iaLoaderTimeoutEnabled = true
            +
iaLoaderTimeoutDuration = configured duration
            |
            v
IA loader timeout behavior


### Debugging use

If users remain stuck on the IA loader or receive the retry option earlier/later than expected, check both settings.

---

## 6.4 `iaFinacleFetch`

Controls whether the Finacle flow is enabled in IA.

Conceptually:


iaFinacleFetch
      |
      +-- enabled -> Finacle flow available
      |
      +-- disabled -> Finacle flow not used


---

## 6.5 `fetchAndSaveRawStatement`

Controls whether IA fetches the raw bank statement from the vendor and saves it.


Vendor
   |
   | Raw statement
   v
IA
   |
   v
fetchAndSaveRawStatement
   |
   v
Persist raw statement


### Debugging use

If the insight report is available but the expected raw statement is missing, inspect this configuration.

---

## 6.6 `agentProceedTimer`

Controls the duration for which an assisted-journey agent must wait before the **Proceed** button becomes available.

This is specific to assisted journeys.


Assisted Journey
      |
      v
agentProceedTimer
      |
      v
Wait
      |
      v
Proceed button enabled


---

## 6.7 `fetchAndSaveRawStatementForIAFailed`

Controls whether IA attempts to fetch and save the raw bank statement when the vendor returns a failure callback.

This is distinct from:


fetchAndSaveRawStatement


because it applies specifically to an IA/vendor failure scenario.


Failure Callback
      |
      v
fetchAndSaveRawStatementForIAFailed
      |
      v
Fetch raw statement
      |
      v
Persist


---

## 6.8 `enablePopUpForRetry`

Controls whether an error popup is shown instead of rendering the retry screen.

Conceptually:


Retry/Error
     |
     v
enablePopUpForRetry
     |
     +-- enabled -> Error popup
     |
     +-- disabled -> Retry screen


---

## 6.9 `retryPopUpHoldTime`

Controls how long the retry/error popup remains visible.

It should be interpreted together with:


enablePopUpForRetry


Relationship:


enablePopUpForRetry
        +
retryPopUpHoldTime
        |
        v
Popup retry UX


---

# 7. Perfios-Specific Configurations

## 7.1 `enablePerfiosProductConfig`

Controls whether product-specific Perfios configuration is enabled.

This configuration can control:

* Callback timeout period
* Retry interval for the transaction-status API

Conceptually:


Perfios
   |
   v
enablePerfiosProductConfig
   |
   +--> product-specific callback timeout
   |
   +--> transaction-status retry interval


### Debugging use

If two products have different Perfios callback/retry behavior, inspect this configuration first.

---

## 7.2 `enableMultiplePerfiosCallbacks`

Controls whether IA supports/consumes multiple Perfios callbacks.

This is especially important for journeys where multiple vendor callback events may be generated.

Conceptually:


Perfios callbacks
      |
      v
enableMultiplePerfiosCallbacks
      |
      +-- enabled -> multiple callbacks supported
      |
      +-- disabled -> normal callback behavior


### Important distinction

Do not confuse:


enableMultiplePerfiosCallbacks


with:


maxAllowedRetryAttempt


The former controls callback behavior; the latter controls user retry attempts.

---

## 7.3 `limitMultipleRetryAttempt`

Controls limiting of multiple retry attempts.

This is a journey/user retry control.

Conceptually:


User Retry
    |
    v
limitMultipleRetryAttempt
    |
    v
Retry eligibility


---

## 7.4 `maxAllowedRetryAttempt`

Defines the maximum number of retries a user can perform.


User retries
     |
     v
maxAllowedRetryAttempt
     |
     v
Retry count limit


### Important distinction


limitMultipleRetryAttempt
    =
whether/how multiple retries are restricted

maxAllowedRetryAttempt
    =
maximum allowed retry count


These configurations should be analyzed together.

---

# 8. Zenith Configuration

## `enableZenithOrchAPI`

Controls whether the Zenith Orchestrator flow is enabled for the bank statement journey.

Conceptually:


Bank Statement Journey
        |
        v
enableZenithOrchAPI
        |
        +-- enabled -> Zenith Orchestrator
        |
        +-- disabled -> alternate configured journey


This configuration is particularly important when determining whether a product uses:


Perfios


or:


Zenith / AA-Orchestrator


for the bank statement journey.

For deeper Zenith behavior, retrieve:


zenith-flow.md


alongside this configuration document.

---

# 9. Finacle PDF Configuration

## `enableFinaclePdf`

Controls whether Finacle statements are converted into PDF and uploaded to OmniDocs.

Conceptually:


Finacle Statement
      |
      v
enableFinaclePdf
      |
      v
Convert to PDF
      |
      v
OmniDocs


### Debugging use

If Finacle data is available but the expected PDF is not present in OmniDocs, check this configuration before investigating the document service.

---

# 10. IA Version Configuration

## `iaVersion`

Controls which IA version is live/running for the applicable configuration.

Conceptually:


Request
   |
   v
Partner + Product
   |
   v
iaVersion
   |
   v
Version Bucket / Version Resolver
   |
   v
Versioned IA Service


This configuration is particularly important because the same API can execute different implementation versions.

### Debugging rule

If two apparently identical requests behave differently, verify:


partner
product
iaVersion
VersionBucket
resolved service implementation


before assuming that the business logic is inconsistent.

For the complete version-routing architecture, retrieve:


architecture.md
configurations.md


---

# 11. Related Configuration Groups

The broader IA configuration system contains several configuration groups that may interact with these toggles.

Important groups include:


PartnerProductConfigurations
IncomeAssessment
Callback
VersionBuckets
PerfiosErrorCodeAndConfigMapping
ZenithErrorCodeAndConfigMapping
FinacleErrorCodeAndConfigMapping
MaximusErrorCodeAndConfigMapping


The current document focuses specifically on the feature toggles and PartnerProductConfig values listed above.

For vendor error mappings, retrieve:


error-handling.md
configurations.md


---

# 12. Feature Toggle vs PartnerProductConfig

This distinction is critical for RAG retrieval.

| Aspect            | Feature Toggle                | PartnerProductConfig          |
| ----------------- | ----------------------------- | ----------------------------- |
| Database          | `masters`                     | `income-assessment`           |
| Collection        | `featureToggles`              | `configurations`              |
| Typical purpose   | Enable/disable capability     | Configure journey behavior    |
| Scope             | Can be product/scope specific | Partner/product specific      |
| Examples          | `redirectToAA`                | `iaLoaderTimeoutEnabled`      |
| Vendor routing    | Can influence behavior        | Can influence behavior        |
| Retry behavior    | Specific capability toggles   | Timeout/retry parameters      |
| Version routing   | Usually not primary mechanism | `iaVersion`                   |
| Callback behavior | Callback-specific toggles     | Callback timeout/retry config |

### RAG rule

When the developer asks:

> "Which toggle enables X?"

Search `featureToggles` first.

When the developer asks:

> "How long is X configured for?"

or:

> "What is the retry/timeout behavior?"

Search `PartnerProductConfig` first.

When the question asks:

> "Why does Personal behave differently from another product?"

Search **both**.

---

# 13. Configuration Interaction Examples

## Example 1: User stuck on loader

Relevant configuration:


retryErrorMsgScreen
iaLoaderTimeoutEnabled
iaLoaderTimeoutDuration
enablePopUpForRetry
retryPopUpHoldTime


Debugging sequence:


User returns from vendor
        |
        v
Is loader/retry experience enabled?
        |
        v
Is timeout enabled?
        |
        v
What is timeout duration?
        |
        v
On failure, popup or retry screen?
        |
        v
If popup, what is hold time?


---

## Example 2: Perfios report fetched but downstream event missing

Relevant configuration:


publishPerfiosBankStatementReportFetchedEvent


Then inspect:


Perfios report retrieval
        |
        v
Feature toggle
        |
        v
Kafka event publication
        |
        v
Consumer


Retrieve `kafka-events.md` if the event was expected but not consumed.

---

## Example 3: AA doesn't auto-redirect

Relevant configuration:


redirectToAA


Also inspect:


assessmentMedium
Partner/Product
AA configuration


Expected chain:


AA selected
   |
   v
redirectToAA enabled?
   |
   v
Vendor redirect


---

## Example 4: User receives retry unexpectedly

Relevant configuration:


enableIARetryableRuleValidation
limitMultipleRetryAttempt
maxAllowedRetryAttempt


Also inspect:


business rule failure
retry count
current IA status
error mapping


---

## Example 5: Product uses Zenith instead of Perfios

Relevant configuration:


enableZenithOrchAPI


Then trace:


Partner + Product
      |
      v
PartnerProductConfig
      |
      v
enableZenithOrchAPI
      |
      +-- enabled -> Zenith
      |
      +-- disabled -> alternate bank statement flow


Retrieve `zenith-flow.md` and `perfios-flow.md` for the respective execution paths.

---

## Example 6: Raw statement missing after failure

Relevant configuration:


fetchAndSaveRawStatement
fetchAndSaveRawStatementForIAFailed


Important question:

> Was the raw statement expected during a normal successful journey or specifically after an IA/vendor failure?

The answer determines which configuration must be checked.

---

# 14. Configuration-Driven Debugging Workflow

When an incident appears to be configuration-related:

### Step 1 — Identify context

Collect:


partner
product
assessmentMode
assessmentMedium
applicationReferenceId
incomeAssessmentId


### Step 2 — Identify implementation version

Check:


iaVersion
VersionBucket
resolved IA service


### Step 3 — Search feature toggles

Check:


masters.featureToggles


for the relevant capability.

### Step 4 — Search PartnerProductConfig

Check:


income-assessment.configurations


for the relevant partner/product.

### Step 5 — Find the consuming code

Search for the exact configuration key in the repository.

For example:


enableZenithOrchAPI


should lead to the code deciding whether Zenith is used.

### Step 6 — Trace the runtime branch

Determine:


config value
   |
   v
conditional branch
   |
   v
service/gateway
   |
   v
external behavior


### Step 7 — Verify downstream effects

If the toggle controls an event, document, callback, or retry:


Toggle
  |
  v
Code branch
  |
  v
External/API/Kafka/DB operation
  |
  v
Observed behavior


---

# 15. Configuration Failure Patterns

## Toggle enabled but behavior not observed

Check:

1. Correct product/scope?
2. Correct configuration database?
3. Correct configuration name?
4. Runtime cache/config refresh?
5. Correct IA version?
6. Is the toggle actually consumed in the executed code path?
7. Is another configuration overriding the behavior?

---

## Toggle disabled but behavior observed

Check:

1. Correct product/scope?
2. Another toggle controls the same capability?
3. Different IA version?
4. Different service implementation?
5. Existing persisted state from a previous configuration?
6. Is the observed behavior actually controlled by this toggle?

---

## Different products behave differently

Compare:


Product A
    |
    +--> featureToggles
    +--> PartnerProductConfig
    +--> iaVersion
    +--> assessmentMedium
    +--> vendor configuration

Product B
    |
    +--> featureToggles
    +--> PartnerProductConfig
    +--> iaVersion
    +--> assessmentMedium
    +--> vendor configuration


Do not compare only application code.

---

# 16. Configuration Debugging Decision Tree


Unexpected IA behavior
        |
        v
Is behavior configuration-driven?
        |
        +-- UNKNOWN
        |      |
        |      v
        |   Search config key / feature name in code
        |
        +-- YES
             |
             v
       What type of config?
             |
       +-----+------+
       |            |
       v            v
 Feature Toggle   PartnerProductConfig
       |            |
       v            v
masters          income-assessment
featureToggles   configurations
       |            |
       +-----+------+
             |
             v
       Correct product/scope?
             |
             v
       Correct IA version?
             |
             v
      Find consuming code
             |
             v
       Identify runtime branch
             |
             v
      Trace resulting behavior


---

# 17. High-Value Configuration Correlations

Some configuration keys should usually be retrieved together.

### Loader / callback UX


retryErrorMsgScreen
iaLoaderTimeoutEnabled
iaLoaderTimeoutDuration
enablePopUpForRetry
retryPopUpHoldTime


### Retry behavior


enableIARetryableRuleValidation
limitMultipleRetryAttempt
maxAllowedRetryAttempt


### Perfios behavior


uploadStatementPerfiosIA
enableTransactionReportEncrypted
enablePerfiosGenerateLinkEncrypted
enablePerfiosProductConfig
enableMultiplePerfiosCallbacks
publishPerfiosBankStatementReportFetchedEvent
fetchAndSaveRawStatement
fetchAndSaveRawStatementForIAFailed


### AA / Zenith


redirectToAA
addMobileNumberAndInstitutionIdForAA
enableZenithOrchAPI


### Income / validation


enableImputedIncome
enableSalaryCategoryFilterForImputed
salaryMedianCalculationForCapability
enableEODBasedABBCalculation
validateInterestTransactions
enableKarzaNameMatchForBankStatement


### Documents


uploadStatementPerfiosIA
fetchAndSaveRawStatement
fetchAndSaveRawStatementForIAFailed
enableFinaclePdf


### ITR


isTwoYearItrEnabled


### Versioning


iaVersion


---

# 18. RAG Retrieval Strategy

Configuration questions should not always retrieve the entire configuration document.

Use targeted retrieval.

| Question                                        | First retrieval                                        |
| ----------------------------------------------- | ------------------------------------------------------ |
| Which toggle enables AA redirect?               | `Feature Toggles` → `redirectToAA`                     |
| Why is AA not auto-redirecting?                 | `redirectToAA` + `cap-flow.md`/AA flow                 |
| What controls loader timeout?                   | `iaLoaderTimeoutEnabled` + `iaLoaderTimeoutDuration`   |
| Why did user return directly to product?        | `retryErrorMsgScreen`                                  |
| Why isn't Perfios document uploaded?            | `uploadStatementPerfiosIA` + `integrations.md`         |
| Which config controls Perfios callback retries? | `enablePerfiosProductConfig`                           |
| Why are multiple Perfios callbacks ignored?     | `enableMultiplePerfiosCallbacks` + `perfios-flow.md`   |
| How many retries can user perform?              | `limitMultipleRetryAttempt` + `maxAllowedRetryAttempt` |
| Why is Zenith being used?                       | `enableZenithOrchAPI` + `zenith-flow.md`               |
| Why is ITR processing two years?                | `isTwoYearItrEnabled` + `itr-flow.md`                  |
| Why is imputed income affecting validation?     | `enableImputedIncome`                                  |
| Why isn't raw statement saved after failure?    | `fetchAndSaveRawStatementForIAFailed`                  |
| Why is Finacle PDF missing?                     | `enableFinaclePdf`                                     |
| Which IA version is running?                    | `iaVersion` + `architecture.md`                        |
| Why do two products behave differently?         | Feature Toggle + PartnerProductConfig + `iaVersion`    |
| Where is this toggle stored?                    | Feature Toggle database section                        |
| Where is this runtime config stored?            | PartnerProductConfig database section                  |

---

# 19. Key RAG Terms


FeatureToggle
featureToggles
masters
scope
PERSONAL
PartnerProductConfig
PartnerProductConfigurations
income-assessment
configurations
product-specific toggle
IA configuration
runtime configuration
retryErrorMsgScreen
iaLoaderTimeoutEnabled
iaLoaderTimeoutDuration
iaFinacleFetch
fetchAndSaveRawStatement
agentProceedTimer
fetchAndSaveRawStatementForIAFailed
enablePopUpForRetry
retryPopUpHoldTime
enablePerfiosProductConfig
enableMultiplePerfiosCallbacks
limitMultipleRetryAttempt
maxAllowedRetryAttempt
enableZenithOrchAPI
enableFinaclePdf
iaVersion
uploadStatementPerfiosIA
enableTransactionReportEncrypted
enableRBIHVendorId
enablePerfiosGenerateLinkEncrypted
addMobileNumberAndInstitutionIdForAA
enableKarzaNameMatchForBankStatement
ignoreInvalidClientTransactionIdException
isTwoYearItrEnabled
enableImputedIncome
redirectToAA
publishPerfiosBankStatementReportFetchedEvent
salaryMedianCalculationForCapability
enableSalaryCategoryFilterForImputed
enableEODBasedABBCalculation
validateInterestTransactions
modifyFcuTaskCreationForBigDebit
enableIARetryableRuleValidation


---

# 20. Critical Invariants


Feature toggles are stored in masters.featureToggles.

Partner/product runtime configurations are stored in income-assessment.configurations.

Feature toggles and PartnerProductConfig are separate configuration mechanisms.

A toggle name alone does not establish its runtime behavior; the consuming code is the final authority.

Product/scope matters when resolving feature toggles.

Partner/product context matters when resolving PartnerProductConfig.

iaVersion can change which IA implementation executes the same API request.

Loader timeout behavior depends on both enablement and configured duration.

Retry UX can be controlled by multiple related configurations.

Perfios callback behavior can be configuration-driven.

Zenith vs alternate bank statement behavior can be configuration-driven.

Document persistence can be configuration-driven.

Event publication can be configuration-driven.

Business validation inputs can be configuration-driven.

Two products can legitimately execute different IA behavior because their runtime configuration differs.

A configuration-related RCA should identify the configuration value, consuming code branch, and resulting behavior—not merely state that a toggle was enabled/disabled.


---

# 21. Canonical Configuration Mental Model

The most useful mental model for configuration-driven IA debugging is:


                REQUEST
                   |
                   v
          Partner + Product
                   |
          +--------+--------+
          |                 |
          v                 v
   Feature Toggle     PartnerProductConfig
     (masters)        (income-assessment)
          |                 |
          +--------+--------+
                   |
                   v
              iaVersion
                   |
                   v
          Version Resolver
                   |
                   v
          IA Implementation
                   |
                   v
        Journey / Integration
                   |
                   v
         Observed Behavior


When a developer asks:

> **"Why is IA behaving differently for this product?"**

the copilot should not immediately inspect business logic.

It should first establish:


Which partner?
Which product?
Which assessment mode?
Which assessment medium?
Which feature toggles?
Which PartnerProductConfig?
Which IA version?
Which implementation?


Only then should it trace the business logic and integration flow.

---

# 22. RCA Principle

For configuration-driven incidents, the preferred RCA chain is:


Observed behavior
      |
      v
Expected behavior
      |
      v
Relevant configuration
      |
      v
Actual configuration value
      |
      v
Code consuming configuration
      |
      v
Runtime branch selected
      |
      v
External/API/Kafka/DB effect
      |
      v
User-visible behavior


The key RCA question is:

> **Was the unexpected behavior caused by the configuration value itself, incorrect configuration resolution, the code consuming the configuration, or a downstream failure after the correct configuration branch was selected?**
