# Income Assessment — Business Domain & Journeys

## 1. Supported Income Journeys
The microservice caters to two fundamental assessment tracks:

### A. Statement-Based Income Assessment
- Designed for salaried and self-employed borrowers providing bank account statements.
- Two ingestion modes:
  1. **Upload Journey (Perfios)**: Borrower uploads electronic bank statement PDFs (often password-protected). The service forwards the document to Perfios for OCR, parsing, and fraud checks.
  2. **Account Aggregator Journey (Zenith / AA-Orch)**: Borrower grants digital consent via RBI-regulated Account Aggregators. Zenith pulls encrypted Financial Information (FI) directly from the borrower's bank without manual PDF uploads.

### B. ITR-Based Income Assessment
- Intended for self-employed individuals and business proprietors.
- Assesses gross total income, business turnover, and tax deductions verified against the Income Tax e-filing portal.

## 2. Product Journey Types
Each request specifies a `journeyType` such as:
- `FOUR_WHEELER_PERSONAL`: High-ticket personal auto loans requiring multi-month statement analysis.
- `TWO_WHEELER_PERSONAL`: Rapid underwriting requiring automated bank balance extraction.
- `MERCHANT_CREDIT_LINE`: Daily sweep and POS transaction assessment.

Different journeys follow distinct validation rules, SLA thresholds, and fallback paths.
