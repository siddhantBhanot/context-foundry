---
id: kyc-aml-compliance
title: KYC, AML & Regulatory Compliance Masterclass
description: Essential operational guide to Customer Due Diligence (CDD), Video KYC, Anti-Money Laundering transaction monitoring, Suspicious Transaction Reports (STR), and Politically Exposed Persons (PEP) screening.
target_service: Compliance & Branch Operations
domain: Regulatory Affairs & Compliance
target_audience: Operations Managers, Compliance Officers & Branch Staff
difficulty: Intermediate
estimated_duration: 1 hour
icon: FileCheck
group: banking
tags:
  - KYC
  - AML
  - PMLA
  - PEP Screening
  - STR & CTR
  - RBI Master Directions
---

# KYC, AML & Regulatory Compliance Masterclass

## 01. Customer Due Diligence (CDD) & Video KYC Protocols
- **Summary**: RBI Master Directions on KYC, Officially Valid Documents (OVDs), Simplified vs Enhanced Due Diligence, and Video-based Customer Identification Process (V-CIP).
- **Context**:
  - lessons/01-cdd-protocols/01-cdd-and-kyc-standards.md
  - lessons/01-cdd-protocols/02-beneficial-ownership.md
- **Knowledge Check**:
  - **Question**: Which of the following is an Officially Valid Document (OVD) for Proof of Identity and Proof of Address under RBI Master Directions on KYC?
  - **Type**: multiple_choice
  - **Options**:
    - Utility electricity bill from 6 months ago
    - Credit card statement
    - [x] Passport, Voter ID Card, Driving Licence, or proof of possession of Aadhaar
    - PAN card copy (without address)
  - **Explanation**: Per RBI KYC Master Directions, the list of core OVDs includes Passport, Driving Licence, Proof of possession of Aadhaar, Voter's Identity Card, NREGA Job Card, and letter issued by National Population Register. A standalone PAN card is proof of identity but does not qualify as an OVD for address proof.
- **Knowledge Check**:
  - **Question**: Under the Video-based Customer Identification Process (V-CIP) guidelines, what is a mandatory control to prevent spoofing and ensure live presence?
  - **Type**: multiple_choice
  - **Options**:
    - Pre-recorded video upload by the customer
    - [x] Live interaction with geotagging, liveness detection, and OTP/Aadhaar verification
    - Customer self-attestation via emailed selfie
    - Verification solely through social media profile checks
  - **Explanation**: RBI V-CIP regulations mandate real-time face-to-face live interaction by authorized banking officials with geo-tagging (verifying customer is in India), AI-based liveness detection, and immediate digital credential verification.
- **Knowledge Check**:
  - **Question**: When must a bank perform Enhanced Due Diligence (EDD) instead of Simplified Due Diligence under PMLA?
  - **Type**: multiple_choice
  - **Options**:
    - For low-risk salary accounts of government employees
    - For small accounts opened with self-certification
    - [x] When a customer is categorized as high-risk, including PEPs, cross-border clients, or non-face-to-face accounts with anomalous transactions
    - Whenever an account holder deposits less than 10,000 INR
  - **Explanation**: Enhanced Due Diligence is legally required for high-risk customers, politically exposed persons (PEPs), correspondent banking, or customers originating from high-risk jurisdictions.

## 02. Anti-Money Laundering & Transaction Monitoring
- **Summary**: Detection of smurfing, cash structuring, trade-based money laundering, and regulatory reporting of CTRs and STRs to Financial Intelligence Unit - India (FIU-IND).
- **Context**:
  - lessons/02-aml-monitoring/01-aml-typologies.md
  - lessons/02-aml-monitoring/02-str-filing-workflows.md
- **Knowledge Check**:
  - **Question**: Within how many days must a Suspicious Transaction Report (STR) be furnished to the Director, Financial Intelligence Unit - India (FIU-IND) after reaching satisfaction that the transaction is suspicious?
  - **Type**: multiple_choice
  - **Options**:
    - 30 days
    - 15 days
    - [x] 7 working days
    - 24 hours
  - **Explanation**: Under the Prevention of Money Laundering Act (PMLA) Rules, banks are legally mandated to submit an STR to FIU-IND within 7 working days of the Principal Officer arriving at a conclusion of suspicion.
- **Knowledge Check**:
  - **Question**: What is "Structuring" or "Smurfing" in the context of Anti-Money Laundering?
  - **Type**: multiple_choice
  - **Options**:
    - Consolidating large corporate debts into syndicated credit
    - [x] Breaking down large cash deposits into multiple smaller amounts below the regulatory reporting threshold to evade CTR triggers
    - Converting fixed-rate loans into floating-rate mortgages
    - Investing in high-yield mutual funds across multiple asset management companies
  - **Explanation**: Structuring (or smurfing) is the deliberate practice of executing multiple small financial transactions below the reporting limit (such as CTR limit of INR 10 Lakh) specifically to avoid regulatory scrutiny and automated threshold alerts.
- **Knowledge Check**:
  - **Question**: Under PMLA Rules, what is the threshold for mandatory reporting of Cash Transaction Reports (CTR) to FIU-IND?
  - **Type**: multiple_choice
  - **Options**:
    - All cash transactions above INR 50,000
    - [x] All cash transactions where the value exceeds INR 10 Lakhs (or equivalent foreign currency) in a month
    - Any foreign inward remittance regardless of value
    - Transactions exceeding INR 1 Crore only
  - **Explanation**: Banks must submit a Cash Transaction Report (CTR) to FIU-IND for all cash transactions of value exceeding INR 10 Lakhs (or its equivalent in foreign currency) or integrally connected transactions aggregating to more than INR 10 Lakhs in a month.

## 03. Politically Exposed Persons (PEP) & High-Risk Accounts
- **Summary**: Governance, senior management onboarding approvals, source of wealth scrutiny, and enhanced ongoing transaction monitoring for domestic and international PEPs.
- **Context**:
  - lessons/03-pep-sanctions/01-pep-governance.md
  - lessons/03-pep-sanctions/02-sanctions-screening.md
- **Knowledge Check**:
  - **Question**: What mandatory governance requirement must be fulfilled before opening an account or establishing a relationship with a Politically Exposed Person (PEP)?
  - **Type**: multiple_choice
  - **Options**:
    - Mandatory police clearance certificate from local authorities
    - [x] Prior approval of a Senior Management Official (typically General Manager / Zonal Head) and verified Source of Wealth
    - 100% upfront cash security deposit
    - Waiver of all KYC documentation due to diplomatic status
  - **Explanation**: RBI mandates that onboarding a PEP or continuing a relationship with an existing client who subsequently becomes a PEP requires prior approval from senior management and thorough verification of the legitimate source of funds and wealth.
- **Knowledge Check**:
  - **Question**: Who qualifies as a Politically Exposed Person (PEP) according to FATF and RBI guidelines?
  - **Type**: multiple_choice
  - **Options**:
    - Any individual employed in a commercial bank
    - [x] Individuals who are or have been entrusted with prominent public functions in a foreign country and their immediate family members / close associates
    - All citizens registered to vote in local municipality elections
    - Corporate executives of private unlisted software companies
  - **Explanation**: PEPs are defined as individuals who are or have been entrusted with prominent public functions in a foreign country, such as Heads of States, senior politicians, senior government/judicial/military officials, senior executives of state-owned corporations, and their immediate family members/close associates.
- **Knowledge Check**:
  - **Question**: If an existing customer subsequently becomes a Politically Exposed Person (PEP), what action must the branch or operations team take?
  - **Type**: multiple_choice
  - **Options**:
    - Automatically freeze and terminate the account immediately without notice
    - [x] Obtain Senior Management approval to continue the relationship and subject the account to Enhanced Due Diligence (EDD)
    - Transfer all customer funds to the Reserve Bank of India
    - Downgrade the account to a basic savings bank deposit account (BSBDA)
  - **Explanation**: Per RBI regulations, when an existing account holder subsequently becomes a PEP, senior management approval is required to continue the business relationship, and the customer must be subjected to enhanced ongoing monitoring.
