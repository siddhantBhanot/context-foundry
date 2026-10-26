# Zenith / AA-Orch Integration

## 1. Role of Zenith in Account Aggregator (AA) Ecosystem
Zenith is the internal enterprise integration orchestrator for RBI Account Aggregators (Setu, Anumati, Finvu).

## 2. Integration Mechanics
1. **Consent Handle Creation**:
   - `POST /zenith/v1/consent/handle`
   - Defines consent parameters: date range (past 12 months), frequency, data types (Profile, Summary, Transactions).
2. **Web Redirection & Approval**:
   - Customer approves AA request via SMS OTP or AA mobile app.
3. **Encrypted Financial Information (FI) Fetch**:
   - Once consent status reaches `ACTIVE`, `income-assessment-service` calls Zenith to trigger FI fetch.
   - Zenith delivers standardized financial JSON directly, eliminating PDF OCR failures.
