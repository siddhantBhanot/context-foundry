# On-Call Triaging Runbook

## 1. Initial Diagnostic Steps
When an alert fires or customer support reports a stuck assessment:
1. Obtain `applicationId` or `transactionId`.
2. Query Kibana / CloudWatch logs:
   ```text
   correlationId:"APP-2026-9812" AND service:"income-assessment-service"
   ```
3. Inspect current MongoDB state:
   ```javascript
   db.assessments.findOne({ "applicationId": "APP-2026-9812" })
   ```
4. Verify Kafka publish status: Check if `KafkaTemplate` acknowledged event delivery to `fc.lending.income-assessment.outcomes.v1`.

## 2. Emergency Actions
- If Perfios is degraded: Toggle `income.assessment.aa.fallback.enabled = true` or switch to fallback manual underwriting mode.
- To re-trigger an outcome: Execute management actuator endpoint `POST /actuator/management/reprocess/{applicationId}`.
