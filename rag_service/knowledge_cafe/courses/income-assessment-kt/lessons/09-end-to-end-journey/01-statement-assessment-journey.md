# End-to-End Statement Assessment Journey Walkthrough

## Step-by-Step Production Trace: FOUR_WHEELER_PERSONAL
1. **Loan Application Submission**:
   - Customer applies on ContextFoundry App. Loan Origination Service calls `POST /initiation-application` with PAN, mobile, bank account.
2. **Link Generation & Customer Action**:
   - `income-assessment-service` calls Perfios to generate secure upload session.
   - User receives SMS / in-app modal, enters bank statement PDF password, and uploads statement.
3. **Third-Party Processing**:
   - Perfios parses 6 months of transactions, runs tamper checks, categorizes salaries, and signs webhook notification.
4. **Webhook Processing & Rule Evaluation**:
   - Webhook arrives at `/callback/perfios`.
   - Signature verified. `CommonVersionResolver` dispatches to `FourWheelerPersonalAssessmentHandler`.
   - Evaluates:
     - 3 consecutive salary credits found: Verified ✅ (Salary = ₹85,000/mo)
     - Average Monthly Balance: ₹18,400 (Above threshold ₹10,000) ✅
     - Inward bounces in 6 months: 0 ✅
5. **State Finalization & Event Emission**:
   - MongoDB updated to `COMPLETED`.
   - `IncomeAssessmentOutcomeEvent` published to Kafka with computed net salary and risk flags.
   - Downstream Underwriting Engine consumes event and approves car loan in under 60 seconds!
