# Spring Profiles & Configuration Hierarchy

## 1. Application Profiles
- `application.yml`: Base common configuration.
- `application-dev.yml`: Local mock integrations and simulated provider stubs.
- `application-staging.yml`: Sandbox environments with test API keys.
- `application-prod.yml`: Production clustering, strict timeouts, and AWS IAM role authentication.

## 2. Key Configuration Keys
```yaml
income:
  assessment:
    default-timeout-seconds: 180
    statement-months-required: 6
    integrations:
      perfios:
        base-url: "https://api.perfios.com/v2"
        connect-timeout-ms: 5000
        read-timeout-ms: 30000
      zenith:
        base-url: "https://gateway.internal.contextfoundry.dev"
        connect-timeout-ms: 3000
        read-timeout-ms: 15000
```
