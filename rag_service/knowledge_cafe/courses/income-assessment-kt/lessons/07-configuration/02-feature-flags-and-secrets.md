# Feature Flags & Secrets Management

## 1. Feature Flag Integration
- Evaluated via `FeatureFlagService` backed by internal configuration service.
- Flags:
  - `income.assessment.v2.enabled`: Global kill-switch for Revamped handlers.
  - `income.assessment.aa.fallback.enabled`: Automatically falls back to manual PDF upload if Account Aggregator consent fails or times out.

## 2. Secrets Handling
- Secrets (API credentials, HMAC keys, MongoDB URIs) are NEVER committed to git or stored in plain-text config files.
- Injected at container runtime via Kubernetes Secrets / AWS Secrets Manager environment variables (`PERFIOS_API_KEY`, `ZENITH_CLIENT_SECRET`).
