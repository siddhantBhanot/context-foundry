# Common Production Failure Modes

## 1. Statement Parsing Failures
- **Symptom**: Assessment stuck in `IN_PROGRESS` or marked `FAILED` with code `ERR_PARSING_FAILED`.
- **Root Cause**:
  - Customer uploaded scanned photo images rather than digital electronic PDF bank statement.
  - Password-protected PDF with invalid password supplied.
  - Unsupported co-operative bank format.

## 2. Callback Webhook Timeouts
- **Symptom**: Third party completed processing, but outcome event never triggered.
- **Root Cause**:
  - Network glitch or firewall dropping incoming webhook packet.
  - Reconciliation cron job (`AssessmentReconciliationJob`) polls pending records every 10 minutes to recover lost callbacks.

## 3. MongoDB Connection Pool Exhaustion
- **Symptom**: Spike in latency, `Cannot acquire connection from pool within 5000ms`.
- **Root Cause**: Blocking operations inside reactive Reactor streams or missing indexes on `applicationId`.
