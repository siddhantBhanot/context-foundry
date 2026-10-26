# Configuration Code Snippets

## Purpose

This file contains implementation-level evidence showing how configuration and feature toggles affect IA execution.

Use this file to answer:

* Where is this configuration read?
* Which service consumes this toggle?
* Is the configuration static or dynamic?
* Which partner/product gets this configuration?
* How does a toggle change execution?
* Why did two otherwise similar requests take different paths?

This file complements `09-configuration.md` and `toggles-and-ia-configurations.md`.

---

# 1. Configuration Execution Model

The preferred mental model is:


Request
   ↓
Partner / Product / Context
   ↓
ConfigFetcher
   ↓
PartnerProductConfigurations / Feature Toggle
   ↓
Resolved configuration
   ↓
Business / Integration decision
   ↓
Execution path


---

# 2. ConfigFetcher


ConfigFetcher



[Snippet to be added]


Capture:

* configuration source
* group
* name
* partner/product lookup
* fallback behavior
* caching, if applicable

---

# 3. PartnerProductConfigurations

Known configuration group:


PartnerProductConfigurations



[Snippet to be added]


Capture how the configuration is:


resolved
→ mapped
→ passed to service
→ consumed


---

# 4. Feature Toggle Lookup

Feature toggle source:


DB: masters
Collection: featureToggles



[Snippet to be added]


Capture:

* toggle name
* scope
* product/partner resolution
* default behavior
* caller

---

# 5. Zenith Selection

Important toggle:


enableZenithOrchAPI



[Snippet to be added]


Document the exact decision:


toggle = true
→ Zenith path

toggle = false
→ alternate/default path


Do not assume the fallback until repository code confirms it.

---

# 6. IA Version Routing

Important configuration:


iaVersion


Expected conceptual path:


Partner/Product configuration
       ↓
iaVersion
       ↓
VersionBuckets
       ↓
CommonVersionResolver
       ↓
Facade
       ↓
Concrete implementation



[Snippet to be added]


---

# 7. Loader / Retry Configuration

Important keys:


retryErrorMsgScreen
iaLoaderTimeoutEnabled
iaLoaderTimeoutDuration
enablePopUpForRetry
retryPopUpHoldTime
limitMultipleRetryAttempt
maxAllowedRetryAttempt



[Snippet to be added]


Document how these jointly affect:


vendor callback missing
→ loader
→ timeout
→ retry UI
→ retry limit


---

# 8. Perfios Configuration

Important keys:


enablePerfiosProductConfig
enableMultiplePerfiosCallbacks
fetchAndSaveRawStatement
fetchAndSaveRawStatementForIAFailed
enablePerfiosGenerateLinkEncrypted
enableTransactionReportEncrypted
uploadStatementPerfiosIA
publishPerfiosBankStatementReportFetchedEvent



[Snippets to be added]


For every toggle, capture:


Where read?
↓
What branch changes?
↓
What API/event/DB behavior changes?


---

# 9. ITR Configuration

Important keys include:


isTwoYearItrEnabled



[Snippet to be added]


Capture:

* where evaluated
* how document requirements change
* how assessment path changes

---

# 10. GST Configuration / Routing

GST is identified through:


assessmentMode = GST



[Snippet to be added]


Capture:


assessmentMode
→ GST path
→ FinFort
→ ffOrderId
→ GST persistence


---

# 11. Business Rule Configuration

Known rules include:


incomeCreditGapRule
chequeBounceLimitRule
lastNMonthsIncomeRule
numberOfIncomeCreditsRule
statementStatusRule



[Snippet to be added]


Document:


configuration
→ rule evaluation
→ pass/fail
→ resulting status


---

# 12. Configuration Snippet Template

````text
### CODE-CONFIG-XXX — <Configuration>

**Configuration key**

`<key>`

**Source**

<Feature Toggle / PartnerProductConfig / application.yaml>

**Lookup**

<Class + method>

**Consumer**

<Class + method>

**Relevant snippet**

kotlin
<small snippet>
````

**Default / fallback**

<if confirmed>

**Execution effect**

<what changes when enabled/disabled>

**Business impact**

<why this matters>

**Debugging questions**

* Was the expected configuration resolved?
* Was the correct partner/product used?
* Was the toggle enabled?
* Was the value actually consumed?
* Did the configuration route execution differently?

**Related context**

* `09-configuration.md`
* `toggles-and-ia-configurations.md`
* relevant flow

````

---

# 13. Configuration Debugging Principle

Never debug a configuration-driven issue only from the configuration value.

Trace:


Configured value
      ↓
Configuration lookup
      ↓
Resolved object
      ↓
Calling code
      ↓
Conditional branch
      ↓
Actual execution
````

A configuration existing in Mongo does not prove that the running code used it.
