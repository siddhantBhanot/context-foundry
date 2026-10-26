# Configuration

## Configuration Overview

Configuration in the Income Assessment (IA) service comes from two primary sources:

text id="f5v8ra"
Static / Infrastructure Configuration
        │
        └── src/main/resources/application.yaml

Dynamic / Business Configuration
        │
        └── MongoDB
              ↓
          ConfigFetcher


These two sources serve different purposes.

### `application.yaml`

Primarily controls:

* service endpoints
* infrastructure connectivity
* Kafka topics and consumer groups
* authentication/security
* retry/infrastructure settings
* MongoDB connectivity
* scheduler/locking
* ESB configuration
* vendor endpoint wiring

### Mongo-backed configuration

Primarily controls:

* partner/product behavior
* feature toggles
* IA version routing
* business configuration
* vendor error mappings
* callback configuration
* journey-specific behavior
* configurable business rules

This distinction is critical during RCA.

> **If the same code behaves differently for different partners, products, journeys, or environments, configuration should be investigated before assuming a code difference.**

**Source citations**

* `src/main/resources/application.yaml:1-754`
* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/utils/ConfigFetcher.kt:45-49`
* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/utils/ConfigFetcher.kt:409-448`

---

# Configuration Mental Model

The effective behavior of an IA request can be represented as:

text id="z8t1gq"
Request
   ↓
Resolve partner / product / journey context
   ↓
Read dynamic configuration
   ↓
Resolve feature toggles / version / rules
   ↓
Combine with static application configuration
   ↓
Execute selected business/integration path


Therefore:

text id="2x7p4a"
Same code
+
Different configuration
=
Potentially different behavior


Configuration should be treated as part of the runtime decision-making system, not merely deployment metadata.

---

# Configuration Source Hierarchy

When investigating a configuration-dependent behavior, use this hierarchy:

1. **Current code consuming the configuration**
2. **`ConfigFetcher` resolution logic**
3. **Mongo-backed configuration document/group**
4. **`application.yaml`**
5. **Environment-variable values**
6. **Tests/stubs**
7. **README or historical documentation**

The configuration key alone does not explain behavior.

Always inspect:

text id="6q2a0m"
Where is the key defined?
        ↓
Where is it fetched?
        ↓
How is it resolved?
        ↓
What default is applied?
        ↓
How does the caller use it?


---

# Static vs Dynamic Configuration

## Static Configuration

Static configuration is loaded from:

text id="w7h4x1"
src/main/resources/application.yaml


Typical examples:

text
platform.endpoints.*
platform.esb.*
platform.perfios.*
platform.gateway.*
platform.kafka.*
platform.security.*
platform.shedlock.*


These values generally control infrastructure and integration wiring.

---

## Dynamic Configuration

Dynamic configuration is fetched from MongoDB through `ConfigFetcher`.

It can vary based on:

* partner
* product
* journey
* application/request context
* configuration group
* feature-toggle key

This allows business behavior to be changed without changing the application code itself.

**Source**

* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/utils/ConfigFetcher.kt:45-49`
* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/utils/ConfigFetcher.kt:409-448`

---

# `application.yaml` Configuration Map

Important top-level configuration families include:

text id="p5x6i4"
platform.endpoints.*
platform.esb.*
platform.perfios.*
platform.gateway.*
platform.kafka.*
platform.security.*
platform.shedlock.*


The configuration should be interpreted by responsibility rather than simply by YAML location.

---

# `platform.endpoints.*`

Contains downstream service endpoint configuration.

Examples include services such as:

* loan orchestrators
* customer services
* document services
* CAP
* DG
* other internal dependencies

These values determine where the application sends HTTP requests.

For endpoint-related incidents, inspect:

text id="xqfl83"
base URL
+
path
+
HTTP method
+
headers
+
environment variables


A wrong endpoint configuration can manifest as:

* 404
* 405
* connection failure
* unexpected response format

**Source**

* `src/main/resources/application.yaml:53-203`

---

# `platform.esb.*`

Contains ESB-related configuration.

This controls integration behavior for flows that communicate through the configured ESB layer.

When debugging ESB-backed integrations, inspect:

* base URL
* endpoint/path
* request configuration
* authentication/metadata
* timeout/retry settings where applicable

Do not assume that every external API is called directly with `WebClient`; some flows are routed through ESB abstractions.

**Source**

* `src/main/resources/application.yaml:229-350`

---

# `platform.perfios.*`

Contains Perfios-specific configuration.

Relevant configuration can include:

* Perfios endpoint URLs
* request metadata
* retry configuration
* vendor-specific integration settings

When a Perfios flow behaves unexpectedly, compare:

text id="v0m9gd"
Perfios configuration
+
Perfios gateway/client
+
application state
+
callback configuration


Configuration can affect the initiation and processing behavior without requiring a code change.

**Source**

* `src/main/resources/application.yaml:229-350`

---

# `platform.gateway.*`

Contains Zenith / AA-Orchestrator configuration.

Relevant values include:

* Zenith base URL
* encrypted endpoint paths
* BSA endpoint
* integration-specific configuration

A known endpoint is:

text id="4y7x0z"
/aa-orch/fiu/api/v1/initiateBSA


When debugging Zenith/BSA issues, verify the resolved URL rather than assuming that the configured base URL and code path are correct in combination.

Configuration errors can result in:

text id="9qv8cw"
wrong path
    ↓
404
    ↓
unexpected response
    ↓
secondary parsing error


**Source**

* `src/main/resources/application.yaml:341-350`

---

# `platform.kafka.*`

Kafka configuration controls asynchronous event routing.

Important configuration dimensions include:

* topic names
* consumer groups
* retry behavior
* event/config mappings
* filter/transformer configuration

Kafka behavior should therefore be traced as:

text id="k4w2s9"
Event
 ↓
Topic configuration
 ↓
Consumer group
 ↓
Filter / transformer
 ↓
Consumer


When an event is "not consumed", check configuration before assuming the consumer implementation is broken.

**Source**

* `src/main/resources/application.yaml:353-533`

For detailed event semantics, use `kafka-events.md`.

---

# `platform.security.*`

Security configuration includes allow-listed unauthenticated endpoints.

Example configuration family:

text id="7u6p3q"
platform.security.unauthenticated-endpoints


This configuration determines which routes can bypass normal authentication requirements.

When investigating unexpected authentication behavior, verify:

* endpoint path
* configured allow-list
* request route
* authentication middleware behavior

Do not infer endpoint accessibility only from controller annotations.

**Source**

* `src/main/resources/application.yaml:53-203`

---

# Scheduler and Lock Configuration

Configuration also controls background processing and distributed scheduling.

Relevant families include:

text id="qj8n1k"
platform.shedlock.*


Operational/archival configuration is also present in the YAML.

These settings should be investigated for:

* scheduled jobs not executing
* duplicate scheduled execution
* lock acquisition problems
* migration coordination
* archival processing issues

These are operational concerns and should not be confused with the main IA business configuration.

**Source**

* `src/main/resources/application.yaml:37-52`
* `src/main/resources/application.yaml:542-552`

---

# Partner/Product Configuration

Partner/product configuration is one of the most important dynamic configuration areas.

A major configuration group is:

text id="x4s7kn"
PartnerProductConfigurations


This configuration can influence behavior based on the combination of:

text id="g4q8mn"
partnerId
+
productCode
+
journey/request context


This is why a behavior observed for one product or partner should not automatically be generalized to all IA journeys.

When investigating product-specific behavior, retrieve:

text id="f2s9kd"
PartnerProductConfigurations
+
ConfigFetcher
+
caller using the resolved value


**Source**

* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/utils/ConfigFetcher.kt:486-530`

---

# Feature Toggle Model

Feature toggles are dynamically resolved through configuration.

Important toggle families include:

text id="5i0w9e"
enableZenithOrchAPI
enableFinaclePdf
iaVersion
retryErrorMsgScreen
fetchAndSaveRawStatement
fetchAndSaveRawStatementForIAFailed
enablePopUpForRetry
limitMultipleRetryAttempt
autoRedirectScreen


These toggles can change:

* integration path
* IA version
* retry behavior
* UI behavior
* raw-statement persistence
* AA/Zenith routing
* recovery behavior

Therefore, feature toggles should be treated as **business/runtime behavior switches**.

**Source citations**

* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/utils/ConfigFetcher.kt:676-712`
* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/revamp/service/impl/IncomeAssessmentApplicationServiceV3.kt:110-111`

---

# Journey-Wise Toggle Resolution

The service can derive journey-specific toggle names before retrieving their values.

Conceptually:

text id="o8x6s2"
Request Context
      ↓
Journey
      ↓
Toggle Name Resolution
      ↓
ConfigFetcher
      ↓
Configured Value
      ↓
Business Flow


This means searching for only the final boolean variable may be insufficient.

For a toggle-related RCA, inspect:

1. how the toggle name is derived
2. which configuration group is queried
3. what context is used
4. what value is returned
5. how the caller branches on the value

**Source**

* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/utils/ConfigFetcher.kt:676-712`

---

# IA Version Resolution

`iaVersion` is not simply a global version number.

Version resolution is configuration-driven.

The conceptual flow is:

text id="j8t7v3"
Request / Application Context
        ↓
Resolve iaVersion bucket key
        ↓
Read VersionBuckets
        ↓
Resolve facade
        ↓
Concrete IA service version


Therefore, two requests with apparently similar business context may execute different service implementations if their resolved configuration differs.

**Source citations**

* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/revamp/versionresolvers/CommonVersionResolver.kt:53-69`
* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/revamp/versionresolvers/CommonVersionResolver.kt:202-233`

---

# `VersionBuckets`

`VersionBuckets` controls mapping between configuration buckets and concrete IA versions/facades.

When investigating:

* "why is this API using V2/V3?"
* "why does this product execute different code?"
* "why does the same endpoint behave differently?"

inspect:

text id="w5p8eh"
request context
+
iaVersion
+
VersionBuckets
+
CommonVersionResolver
+
resolved facade


Do not assume the controller endpoint alone determines the implementation version.

---

# Configuration Groups

Important Mongo-backed configuration groups referenced by the code include:

text id="7k1v3r"
PartnerProductConfigurations
IncomeAssessment
Callback
VersionBuckets
PerfiosErrorCodeAndConfigMapping
ZenithErrorCodeAndConfigMapping
FinacleErrorCodeAndConfigMapping
MaximusErrorCodeAndConfigMapping


These groups serve different purposes.

| Configuration group                | Primary responsibility            |
| ---------------------------------- | --------------------------------- |
| `PartnerProductConfigurations`     | Partner/product-specific behavior |
| `IncomeAssessment`                 | IA-related business configuration |
| `Callback`                         | Callback-related configuration    |
| `VersionBuckets`                   | IA version/facade routing         |
| `PerfiosErrorCodeAndConfigMapping` | Perfios error interpretation      |
| `ZenithErrorCodeAndConfigMapping`  | Zenith error interpretation       |
| `FinacleErrorCodeAndConfigMapping` | Finacle error interpretation      |
| `MaximusErrorCodeAndConfigMapping` | Maximus error interpretation      |

**Source citations**

* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/utils/ConfigFetcher.kt:486-530`
* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/utils/ConfigFetcher.kt:762-792`

---

# Configuration-Driven Error Mapping

Vendor errors can be translated through configuration rather than only through hardcoded logic.

Conceptual flow:

text id="2j9s8m"
Vendor Error
    ↓
Vendor-specific mapping
    ↓
Configured IA interpretation
    ↓
IA error/status/retry behavior


Therefore, when a vendor error is mapped unexpectedly, inspect:

text id="c6t4ny"
raw vendor error
+
mapping configuration
+
ConfigFetcher
+
call site
+
resulting status/retry behavior


This is especially important for Perfios, Zenith, Finacle, and Maximus.

**Source citations**

* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/utils/ConfigFetcher.kt:722-728`
* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/utils/ConfigFetcher.kt:762-792`
* `src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/utils/ConfigFetcher.kt:921-975`

For detailed error semantics, use `error-handling.md`.

---

# Business Rules and Configuration

Some IA business rules are configurable rather than hardcoded.

Examples include bank-statement validation rule families such as:

text id="w0h6ko"
incomeCreditGapRule
chequeBounceLimitRule
lastNMonthsIncomeRule
numberOfIncomeCreditsRule
statementStatusRule


When a business outcome differs unexpectedly, investigate:

text id="r2x4sm"
partner/product configuration
+
rule configuration
+
rule evaluation code
+
input data


Do not conclude that the business logic changed simply because the outcome changed.

**Source**

* `src/main/resources/application.yaml:560-569`

For business-state semantics, use `business-logic.md`.

---

# Retry Configuration

Retry behavior can be influenced by both code and configuration.

The important distinction is:

text id="9b7h1e"
Code
  → defines how retry is implemented

Configuration
  → may define whether/when a retry-related behavior is enabled or how it is parameterized


When investigating a retry issue, inspect:

1. retry configuration
2. retry operator
3. exception type
4. retry condition
5. maximum attempts
6. delay/backoff
7. caller behavior after retries are exhausted

A configured retry value does not necessarily mean every error is retried.

---

# Callback Configuration

Callback-related behavior can be influenced by the `Callback` configuration group and Kafka wiring.

A callback journey may depend on:

text id="v2s7qp"
Callback configuration
+
Kafka event
+
consumer
+
application state guard
+
vendor transaction identity


When callback processing behaves differently between journeys, compare the resolved configuration rather than assuming the callback consumer code changed.

---

# Environment-Sensitive Configuration

Environment-specific values are generally parameterized through environment variables.

Important examples include:

text id="4m8x2a"
PERSONAL_LOAN_ORCHESTRATOR_BASE_URL
DOCUMENT_SERVICE_BASE_URL
CAP_SERVICE_BASE_URL
ZENITH_BASE_URL
TOKEN_SERVICE_BASE_URL
KAFKA_URL
MONGODB_URI


For RAG and source documentation, the **configuration key** is more useful than the actual environment value.

Never treat a development/staging/production URL as a universal endpoint.

**Source citations**

* `src/main/resources/application.yaml:53-145`
* `src/main/resources/application.yaml:341-365`

---

# Configuration vs Environment Variables

An important distinction:

text id="5a8x9f"
application.yaml
      ↓
references environment variable
      ↓
runtime environment
      ↓
resolved configuration value


Therefore, an issue can originate from:

* incorrect YAML key
* missing environment variable
* incorrect environment variable value
* wrong deployment configuration
* wrong environment
* incorrect path appended to a correct base URL

For endpoint incidents, verify the complete resolved URL.

---

# Configuration Failure Patterns

## Wrong endpoint

text id="4kw1sj"
Correct code
+
wrong base URL/path
=
404 / connection failure


---

## Wrong Kafka routing

text id="7k2x3a"
Correct event
+
wrong topic/group configuration
=
consumer appears not to receive event


---

## Wrong feature toggle

text id="6x8v4c"
Correct code
+
toggle disabled
=
expected feature path never executes


---

## Wrong version bucket

text id="3d6q1p"
Correct request
+
different VersionBuckets mapping
=
different service implementation


---

## Wrong error mapping

text id="1r5c8n"
Vendor error
+
incorrect mapping configuration
=
unexpected IA error/status


---

## Partner/product configuration mismatch

text id="4f6z8q"
Correct request
+
unexpected partner/product configuration
=
different business behavior


---

# Configuration Debugging Workflow

When behavior appears configuration-dependent, use this order.

## Step 1 — Identify the behavior difference

Examples:

text
different IA version
different vendor
different retry behavior
different error code
different status
different Kafka topic
different endpoint
different UI flow


---

## Step 2 — Identify the configuration key

Find the exact key consumed by the relevant code.

Avoid searching only for generic terms such as:

text
config
toggle
setting


Prefer the exact configuration key.

---

## Step 3 — Find the resolution logic

Determine:

text id="b4x7y2"
Where is the key fetched?
Which ConfigFetcher method?
Which configuration group?
Which context?


---

## Step 4 — Determine the resolved value

Check the effective value for the affected:

text
partner
product
journey
environment
version bucket


---

## Step 5 — Trace the caller

Find where the configuration value changes behavior.

For example:

text id="1z8f4r"
toggle
   ↓
if/else
   ↓
different gateway


or:

text id="8j4p2c"
iaVersion
   ↓
VersionBuckets
   ↓
different facade/service


---

## Step 6 — Verify runtime side effects

Determine whether configuration actually caused:

* different endpoint
* different Kafka event
* different retry behavior
* different MongoDB status
* different business rule result
* different downstream call

---

# Configuration RCA Decision Tree

Use this decision tree for configuration-related incidents:

text id="7r2x4k"
Unexpected behavior
        ↓
Is behavior environment-specific?
        |
        +-- YES → inspect application.yaml + environment variables
        |
        +-- NO
        ↓
Is behavior partner/product-specific?
        |
        +-- YES → inspect PartnerProductConfigurations
        |
        +-- NO
        ↓
Is behavior journey-specific?
        |
        +-- YES → inspect journey-wise toggle/config resolution
        |
        +-- NO
        ↓
Is behavior version-specific?
        |
        +-- YES → inspect iaVersion + VersionBuckets
        |
        +-- NO
        ↓
Is behavior vendor-error-specific?
        |
        +-- YES → inspect vendor error mapping configuration
        |
        +-- NO
        ↓
Inspect static YAML + caller implementation


---

# Important Configuration Code Anchors

### Configuration fetcher

text id="7b1p4x"
src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/utils/ConfigFetcher.kt


This is the primary code anchor for understanding dynamic configuration retrieval and interpretation.

### Version resolution

text id="9x3w7q"
src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/revamp/versionresolvers/CommonVersionResolver.kt


### Main IA service

text id="2n6f8m"
src/main/kotlin/com/contextfoundry/lending/incomeassesmentservice/revamp/service/impl/IncomeAssessmentApplicationServiceV3.kt


This is an important caller when determining how resolved configuration affects runtime behavior.

### Static configuration

text id="4v7s2k"
src/main/resources/application.yaml


---

# High-Value Configuration Search Terms

## Static configuration

text id="4n8j1p"
application.yaml
platform.endpoints
platform.esb
platform.perfios
platform.gateway
platform.kafka
platform.security
platform.shedlock


## Dynamic configuration

text id="7q2m5x"
ConfigFetcher
PartnerProductConfigurations
IncomeAssessment
Callback
VersionBuckets


## Feature toggles

text id="2h8c6w"
enableZenithOrchAPI
enableFinaclePdf
iaVersion
retryErrorMsgScreen
fetchAndSaveRawStatement
fetchAndSaveRawStatementForIAFailed
enablePopUpForRetry
limitMultipleRetryAttempt
autoRedirectScreen


## Error mappings

text id="8m4v1s"
PerfiosErrorCodeAndConfigMapping
ZenithErrorCodeAndConfigMapping
FinacleErrorCodeAndConfigMapping
MaximusErrorCodeAndConfigMapping


## Environment variables

text id="5c9x2a"
PERSONAL_LOAN_ORCHESTRATOR_BASE_URL
DOCUMENT_SERVICE_BASE_URL
CAP_SERVICE_BASE_URL
ZENITH_BASE_URL
TOKEN_SERVICE_BASE_URL
KAFKA_URL
MONGODB_URI


---

# Configuration Source-of-Truth Rules

Use these rules when answering configuration questions:

1. **Current caller behavior is the final authority for how a configuration value is interpreted.**
2. **`ConfigFetcher` is the primary authority for dynamic configuration resolution.**
3. **Mongo-backed configuration is authoritative for partner/product/business runtime values.**
4. **`application.yaml` is authoritative for static application/infrastructure wiring.**
5. **Environment variables provide runtime environment-specific values.**
6. **A configuration key does not explain behavior without its resolution and caller logic.**
7. **A feature toggle may alter integration, version, retry, UI, or persistence behavior.**
8. **Partner/product configuration can make identical code behave differently.**
9. **Version routing must be traced through `iaVersion` and `VersionBuckets`.**
10. **Vendor error mappings can change the resulting IA error/status without code changes.**
11. **Configured retry values do not imply that every exception is retryable.**
12. **Environment-specific endpoint values must never be generalized across deployments.**

---

# RAG Retrieval Guidance

Configuration retrieval should be intent-driven.

### "Why is this feature enabled for one product but not another?"

Retrieve:

text id="0z8y3a"
PartnerProductConfigurations
+
ConfigFetcher
+
exact toggle
+
caller


### "Why is this request going through a different IA version?"

Retrieve:

text id="3p6n9k"
iaVersion
+
VersionBuckets
+
CommonVersionResolver
+
resolved facade


### "Why is this API calling the wrong endpoint?"

Retrieve:

text id="6x2k8q"
application.yaml
+
environment variable
+
gateway/client
+
endpoint path


### "Why is Kafka using the wrong topic/group?"

Retrieve:

text id="1c5m7v"
platform.kafka
+
event definition
+
consumer


### "Why is the same vendor error producing a different IA error?"

Retrieve:

text id="9v4b2s"
vendor error mapping
+
ConfigFetcher
+
error catalog
+
call site


### "Why didn't retry happen?"

Retrieve:

text id="5k8x3m"
retry configuration
+
retry operator
+
exception type
+
caller


### "Why does this partner follow a different journey?"

Retrieve:

text id="7n3q6w"
partner/product configuration
+
feature toggles
+
version resolution
+
business logic
+
integration


### "Why is the staging environment behaving differently?"

Retrieve:

text id="4m7x1c"
application.yaml
+
environment variables
+
dynamic Mongo configuration
+
resolved runtime values


---

# Cross-Document Retrieval Map

Configuration should usually be retrieved together with another context file depending on the question.

| Question                                   | Primary context     | Supporting context  |
| ------------------------------------------ | ------------------- | ------------------- |
| Why did business status change?            | `business-logic.md` | `configurations.md` |
| Why did vendor call fail?                  | `integrations.md`   | `configurations.md` |
| Why did Kafka event not route?             | `kafka-events.md`   | `configurations.md` |
| Why did error map differently?             | `error-handling.md` | `configurations.md` |
| Why is DB state different?                 | `database.md`       | `configurations.md` |
| Why does partner X behave differently?     | `configurations.md` | `business-logic.md` |
| Why does environment X behave differently? | `configurations.md` | `integrations.md`   |
| Why is a different IA version executing?   | `configurations.md` | `business-logic.md` |

---

# Preferred Configuration Debugging Mental Model

For any configuration-dependent issue, reason through:


What behavior is different?
        ↓
Which configuration controls it?
        ↓
Is it static or dynamic?
        ↓
Which context determines the value?
        ↓
Where is it fetched?
        ↓
What value was resolved?
        ↓
How does the caller interpret it?
        ↓
What runtime path changed?
        ↓
What DB / Kafka / integration side effect changed?
        ↓
What was the final business impact?


The canonical principle for configuration-related RCA is:

> **Do not stop at the configuration key. Trace the key from definition → resolution → effective value → caller → runtime behavior → business impact.**
