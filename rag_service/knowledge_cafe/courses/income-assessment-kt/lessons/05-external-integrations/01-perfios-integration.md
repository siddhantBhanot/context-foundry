# Perfios Integration Specification

## 1. Overview
Perfios is the statement analysis engine utilized for parsing bank statement PDFs and extracting transaction records.

## 2. Request & Callback Flow
1. **Transaction Initialization**:
   - `POST /perfios/api/v2/transactions/initiate`
   - Passes transaction ID, institution code, customer details, and our callback webhook URL.
   - Perfios returns an encrypted upload token and redirect link.
2. **Customer Document Upload**:
   - Customer completes upload on the Perfios secure widget.
3. **Webhook Callback**:
   - Perfios invokes `POST /callback/perfios/statement-ready` with encrypted payload.
   - `income-assessment-service` verifies HMAC signature, downloads the parsed financial JSON report, and feeds it into the rule engine.
