# End-to-End ITR Assessment Journey

## Step-by-Step Production Trace: Self-Employed Borrower
1. **Initiation**:
   - Upstream client requests `POST /initiation-application` with `assessmentType: ITR`.
2. **Consent & e-Filing Login / XML Upload**:
   - Customer provides PAN and date of birth, authenticates via e-filing portal OTP or uploads signed ITR-V acknowledgment.
3. **Assessment Computation**:
   - `ItrAssessmentHandler` parses:
     - Gross Total Income (GTI) across Past 2 Assessment Years.
     - Tax deductions under Chapter VI-A.
     - Business turnover and depreciation additions.
   - Calculates 2-year average adjusted business income.
4. **Completion**:
   - Record committed to MongoDB with `status: COMPLETED`.
   - Event published to Kafka notifying credit policy engine.
