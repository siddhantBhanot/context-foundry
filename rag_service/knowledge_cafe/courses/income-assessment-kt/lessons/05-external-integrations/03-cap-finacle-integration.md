# CAP & Finacle Integrations

## 1. Credit Application Processing (CAP)
- CAP is the overarching credit workflow engine that manages loan origination stages.
- `income-assessment-service` communicates with CAP to:
  - Validate that the loan application is in an assessable state (`DOCUMENTS_PENDING` or `UNDERWRITING`).
  - Notify CAP when income assessment is completed with calculated net income and eligibility score.

## 2. Finacle (Core Banking System)
- For Core Banking Partner account holders, Finacle integration enables direct internal account statement retrieval without needing third-party aggregators or PDF uploads.
- Communicates via secured internal mTLS REST connectors.
