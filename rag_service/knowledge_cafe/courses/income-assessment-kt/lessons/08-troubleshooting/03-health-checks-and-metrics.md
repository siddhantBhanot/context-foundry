# Health Checks & Observability

## 1. Actuator Endpoints
- `/actuator/health`: Standard Kubernetes readiness and liveness probe.
  - Checks MongoDB ping connectivity.
  - Checks Kafka broker cluster availability.
- `/actuator/prometheus`: Exposes Micrometer metrics:
  - `income_assessment_requests_total{journey="...", status="..."}`
  - `income_assessment_duration_seconds` (histogram for SLA monitoring)
  - `third_party_call_duration_seconds{client="perfios|zenith"}`

## 2. Alert Thresholds
- P1 Alert: 5xx error rate > 2% over 5 minutes.
- P1 Alert: Average callback latency > 120 seconds.
- P2 Alert: Kafka consumer lag > 500 messages.
