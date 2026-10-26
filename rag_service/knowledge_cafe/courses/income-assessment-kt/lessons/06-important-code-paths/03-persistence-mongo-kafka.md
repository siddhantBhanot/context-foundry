# Persistence & Messaging Code Paths

## 1. MongoDB Document Models
- `AssessmentDocument`:
  - `id`: MongoDB ObjectId
  - `applicationId`: Unique indexed business identifier
  - `status`: Current state (`INITIATED`, `IN_PROGRESS`, `COMPLETED`, `FAILED`)
  - `journeyType`: e.g. `FOUR_WHEELER_PERSONAL`
  - `assessmentOutcome`: Embedded sub-document storing computed net salary, ABB, and eligibility flags.
  - `rawProviderPayload`: Archived raw response from Perfios/Zenith for auditability.

## 2. Kafka Event Infrastructure
- `KafkaTemplate<String, IncomeAssessmentOutcomeEvent>`
- Topic: `fc.lending.income-assessment.outcomes.v1`
- Published upon status reaching `COMPLETED` or `FAILED`. Downstream underwriting engines subscribe to this topic to make final credit approval decisions.
