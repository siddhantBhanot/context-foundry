# Four Wheeler Personal Journey Lifecycle

## 1. Journey Characteristics
- Strictest underwriting requirements among consumer products.
- Requires minimum 6 months continuous bank statements.
- Checks specifically for:
  - Minimum 3 salary credits with salary transaction narration patterns (`SAL/`, `NEFT-SAL`, `CMS/`).
  - Average Monthly Balance (AMB) > threshold.
  - Maximum allowable EMI-to-Income (FOIR) ratio.

## 2. Execution Handler
`FourWheelerPersonalAssessmentHandler.kt`:
- Performs pre-checks on banking IFSC to ensure bank is supported.
- Configures Perfios profile with customized car loan parameter weights.
- Handles `PerfiosCallbackPayload` by running the eligibility rule engine before publishing outcome.
