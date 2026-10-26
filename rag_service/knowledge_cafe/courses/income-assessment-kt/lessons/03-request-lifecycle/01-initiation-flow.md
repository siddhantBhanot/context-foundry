# Request Initiation Flow

## 1. Primary Ingress Endpoint: `/initiation-application`
- HTTP Method: `POST`
- Contract:
  ```json
  {
    "applicationId": "APP-2026-9812",
    "journeyType": "FOUR_WHEELER_PERSONAL",
    "assessmentType": "BANK_STATEMENT",
    "applicant": {
      "customerId": "CUST-4410",
      "mobile": "9876543210",
      "pan": "ABCDE1234F"
    },
    "bankDetails": {
      "accountNumber": "912345678901",
      "ifsc": "UTIB0000001",
      "bankName": "Core Banking Partner"
    }
  }
  ```

## 2. Initiation Sequence
1. Request arrives at `ApplicationController.initiateApplication()`.
2. Validation ensures `applicationId` and `pan` conform to regex standards.
3. Service checks MongoDB for existing active assessment to enforce idempotency.
4. If valid, an initial record is created with status `INITIATED`.
5. Service invokes `/generate-link` downstream to generate a customer-facing statement upload URL or AA consent link.
6. Returns HTTP 200 with `transactionId` and upload URL.
