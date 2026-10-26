# Maximus Master Release Documentation and Guidelines

> Source-normalized Markdown extracted from the provided Maximus release documentation.
>
> Intended use: Provide this file to GitHub Copilot or another AI assistant as the source document for creating RAG-ready context, chunks, metadata, embeddings, or retrieval documents.

---

## 1. Overview
This guide is the operational reference for planning, validating, approving, and deploying a Maximus master release across products, shared services, and environments. It is intended for Release Managers, Product Release Owners, QA leads, Tech Leads, DevOps, SRE, and business sign off stakeholders.
A master release must ensure synchronized promotion, consistent evidence, traceable versions, approved exceptions, and clear roll back readiness across the full release train.

### Purpose

This document defines the standard master release process for Maximus products and shared services. It covers:

- Scope
- Release principles
- Ownership
- Release flow
- Mandatory gates
- Evidence requirements
- Rollback expectations
- Deployment controls
- Environment deployment references

### Applies To

All Maximus products and shared services included in a master release train.

No product may bypass shared quality, security, approval, or rollback requirements.

### Operational Objective

This guide is the operational reference for planning, validating, approving, and deploying a Maximus master release across products, shared services, and environments.

It is intended for:

- Release Managers
- Product Release Owners
- QA Leads
- Tech Leads
- DevOps
- SRE
- Business sign-off stakeholders

A master release must ensure:

- Synchronized promotion
- Consistent evidence
- Traceable versions
- Approved exceptions
- Clear rollback readiness

These controls apply across the full release train.

---

## 2. Purpose and Scope

This guide applies to all Maximus products and shared services included in a master release train.

### Business Coverage

All in-scope product lines and journeys participating in the release.

### Technical Coverage

All affected repositories under the Bitbucket project `MAX`.

### Environment Coverage

Standard environments:

- SIT
- QA
- Sandbox
- UAT
- Pre-Prod
- Production

Hotfix lanes, where applicable:

- SIT1
- QA1
- Sandbox1

### Release Paths

#### Master Release

`SIT -> QA -> Sandbox -> UAT -> Pre-Prod -> Prod`

#### Hotfix Release

`SIT1 -> QA1 -> Sandbox1 -> UAT -> Pre-Prod -> Prod`

---

## 3. Release Principles and Tag Governance

### 3.1 Core Release Principles

The release sequence is mandatory:

`SIT/SIT1 -> QA/QA1 -> SB/SB1 -> UAT -> Pre-Prod -> Production`

Release rules:

1. In a master release, no product can bypass shared quality gates.
2. No deployment without approvals.
3. No release without regression evidence.
4. No unresolved critical security risk at go-live.
5. No production promotion without:
   - Required QA sign-off
   - Required UAT sign-off
   - Vulnerability closure
   - Rollback readiness
6. Release notes must include:
   - Impacted products
   - Shared services
   - Versions
   - Reports
   - Owners
   - Rollback plan

### 3.2 Release Tag Governance

| Release Type | Purpose | Tag Format |
|---|---|---|
| Maximus Master Release | Planned train release across products and shared services | `x.0.0` (example: `76.0.0`) |
| Maximus Hotfix Release | Critical bug, security, or compliance fix with high urgency | `x.1.0` (example: `76.1.0`) |
| Planned Independent Release | Non-master planned release for isolated product scope | `x.0.1` (example: `76.0.1`) |

---

## 4. Roles and Ownership

| Role | Primary Ownership | Expected Output |
|---|---|---|
| Release Manager / Master Release Owner | Release timeline, dependency management, go/no-go orchestration, final communication | Approved release plan, governance decisions, closure communication |
| Product Release Owners | Product scope, risk register, sign-off readiness | Product readiness confirmation and risk visibility |
| Tech Leads | Change readiness, version traceability, config and secret changes, deployment validation | Technical deployment readiness and traceable artifacts |
| QA Leads | Smoke, regression, backward compatibility evidence, defect disposition | QA sign-off and evidence package |
| UAT / Business SPOCs | Business validation and UAT sign-off | Explicit product-wise UAT approval or accepted risk |
| DevOps / Build Owner / SRE | Pipeline execution order, promotion flow, monitoring gates, rollback support | Controlled deployment execution and operational support |

---

## 5. End-to-End Release Flow

### Step 1: Plan and Freeze

Required activities:

- Confirm release train scope across all products.
- Lock the release calendar slot and branch strategy.
- Publish the SPOC matrix for:
  - Dev
  - QA
  - UAT
  - BA
  - Release
  - DevOps
- Enforce code cut-off.
- Common service cut-off exceptions require explicit approval.

### Step 2: SIT Cut and Quality Gates

Required activities:

- Cut release branches as per process.
- Auto-promote the SIT build to QA for smoke and regression.
- Run the QA cycle with a 9-day cap.
- Perform mandatory backward compatibility checks.

### Step 3: Sandbox and Pre-Prod Progression

Required activities:

- Target Day 5 push to Sandbox.
- Freeze QA pipelines after the QA build is accepted.
- Freeze Sandbox after promotion.
- Validate:
  - Journeys
  - Contract compatibility
  - Dependency behavior

### Step 4: UAT Sign-Off

Required activities:

- Complete the Product Owner sanity window with a target of 3 days.
- Publish the product-wise evidence package.
- Capture:
  - Explicit UAT sign-off, or
  - Approved risk acceptance

### Step 5: Production Readiness Gate

Verify:

- Vulnerabilities
- Configuration synchronization
- Secret synchronization
- Deployment sequence
- Rollback assets
- AOPM approval status

### Step 6: Production Deployment and Closure

Required activities:

- Deploy in the approved release window.
- Validate post-deployment smoke tests and monitoring.
- Publish the closure note and known issues.

---

## 6. Stage Timeline Targets

| Stage | Target Window | Outcome |
|---|---|---|
| Cut-off and branch readiness | Day 0 | Release scope frozen and branches prepared |
| QA functional, regression, and backward compatibility checks | Day 1-4 | Validated build with evidence |
| Sandbox promotion target | Day 5 | Promotion candidate stabilized |
| PO and UAT validation | Day 6-8 | Business validation completed |
| Final QA sign-off and production readiness review | Day 9 | Go/no-go decision prepared |

---

## 7. Mandatory Checklists and Release Controls

### 7.1 Global Release Checklist

- Scope matrix finalized and approved.
- Release notes page created or updated in Confluence.
- Vulnerability status reviewed for all in-scope repositories.
- Shared and common service dependency checks completed.
- Deployment sequence and rollback owners published.
- Seed branch cut completed for current release + 1 and verified with Build COP.
- Back-office seed branch cut completed for current release + 1 and verified with Build COP.
- `maximus-dlp-helm` diff review completed between current release and target release.
- `secret-config.txt` review completed, including:
  - Whitespace hygiene
  - Trailing-line hygiene

### 7.2 Product Readiness Checklist

- Product service repositories identified.
- Product UI repositories identified.
- Product test repositories identified.
- Planned version-to-commit-and-build mapping completed.
- Configuration changes documented.
- Toggle changes documented.
- Secret changes documented.
- Smoke evidence attached.
- Regression evidence attached.
- Backward compatibility evidence attached.
- Open defects triaged with a release decision.

### 7.3 Platform and Shared Services Checklist

- Helm changes validated in the target environment.
- Configuration changes validated in the target environment.
- Seed changes validated in the target environment.
- Shared services verified for compatibility, including examples such as:
  - Identity
  - Authentication
  - Backoffice
  - Common services
- API contract compatibility reviewed for:
  - Producer impact
  - Consumer impact
- Monitoring dashboards validated.
- Alert thresholds validated.

### 7.4 Release Manager Final Gate

- QA sign-off captured for all products in scope.
- UAT sign-off captured for all products in scope.
- Go/no-go decision logged with:
  - Timestamp
  - Approvers
- Post-release communication issued.
- Teams call for the release window created in advance.

---

## 8. Mandatory Approvals and Governance Gates

Required approvals include:

- QA sign-off from QA Head or delegate
- IT approval
- Security or InfoSec approval
- Product Owner sign-off
- AOPM multi-level approval from L2-L5, as applicable

### Hard Stop Rule

Production go-live must be blocked if any of the following are incomplete:

- Required approvals
- Regression evidence
- Backward compatibility evidence
- Security treatment
- Rollback readiness

---

## 9. Mandatory Release Evidence

Every in-scope product must provide:

- Service version deployed
- UI version deployed
- Smoke test report links
- Regression test report links
- Backward compatibility status
- Known issues
- Waivers
- Mitigations
- Rollback notes
- Rollback owner
- QA sign-off
- UAT sign-off

---

## 10. Rollback Guideline

For each in-scope product:

1. Keep a rollback artifact or tag ready.
2. Define rollback triggers.

Examples of rollback triggers:

- Critical journey failure
- Sustained error rate
- Data inconsistency
- Severe security issue

3. Assign:
   - Rollback executor
   - Rollback approver

This must be done for each product and shared service.

4. Record:
   - Exact rollback pipeline or command
   - Post-rollback validation checks

5. For temporary override image or pod patch changes, document reversibility.

---

## 11. Exception Handling and Edge Cases

### Missed Cut-Off for Product-Only Service

Move the change to the next planned release unless an exception is approved.

### Missed Cut-Off for Common Service

The release remains blocked unless a time-boxed extension is approved by release governance.

### Missing Hotfix Merge into Master Release Branch

Block go-live until the merge or reconciliation is complete.

### Open High or Critical Security Findings

Block production go-live unless approved risk treatment exists.

### Incomplete Regression or Backward Compatibility Evidence

Block production promotion.

---

## 12. Operational Deployment Controls and Environment References

### 12.1 Common Operational Controls

- Trigger and validate common service builds from the approved branch strategy.
- Freeze and unfreeze QA and Sandbox pipelines only through Release Owner and Build COP control.
- Keep the release Confluence page current with every environment promotion.

### 12.2 Patching Controls

For temporary override patches:

- Use the approved self-service patching flow.
- Applicable environments:
  - QA
  - PERF
  - Sandbox
- Validate pod image versions:
  - Before patch
  - After patch
- Record for each patch:
  - Reason
  - Owner
  - Start time
  - Rollback time

### 12.3 Deployment Sequence

1. Execute release foundation pipelines, including:
   - All-release flows
   - Shared platform flows
2. Promote seed and back-office seed paths according to the release gate.
3. Trigger product all-release pipelines in approved batches.
4. Run deployments in parallel only where it is safe to do so.

---

## 13. Vulnerability Dashboard Process

For the Non-Prod Environment Vulnerability Dashboard:

1. Access the dashboard URL.
2. Select **Group by Service Name** in view mode.
3. Expand the target service.
4. Review:
   - Grace period
   - Applicable CVEs
5. Plan and complete remediation before the grace period ends.

The referenced dashboard is named:

`Spring Boot Upgrade Dashboard`

---

## 14. Checking Smoke Tests Before SIT Cut or QA Freeze

Process:

1. Log in to Jenkins.
2. Navigate to:

`Maximus_916_NonProd -> sit -> Master Deploy / Master Release Smoke`

3. Review each service pipeline.
4. Confirm successful smoke test execution for each service.

The source document references:

`Maximus Jenkins`

---

## 15. Environment Deployment References

The source document indicates that product-wise Jenkins deployment links should be opened and used for environment-specific deployment.

### Environment Categories

- SIT / SIT1
- QA / QA1
- Sandbox / SB1
- UAT
- Pre-Prod
- Production
- All Release, where applicable

### Products Listed

| Product / Area | Environment References Indicated |
|---|---|
| Commons | SIT, SIT1, QA, QA1, SB, SB1, UAT, Prod |
| Personal Loan (PL) | SIT, QA, QA1, SB, SB1, UAT, Prod |
| Business Loan (BL) | SIT, SIT1, QA, QA1, SB, SB1, UAT, Prod, All Release |
| Home Loan (HL) | SIT, SIT1, QA, QA1, SB, SB1, UAT, Prod, All Release |
| Auto Loan | SIT, SIT1, QA, QA1, SB, SB1, UAT, Prod, All Release |
| Credit Card (CC) | SIT, SIT1, QA, QA1, Sandbox, SB1, UAT, Prod, All Release |
| Working Capital | SIT, SIT1, QA, QA1, SB, SB1, UAT, Prod, All Release |
| LAS | SIT, SIT1, QA, QA1, SB, SB1, UAT, Prod, All Release |
| ODSAL | SIT, SIT1, QA, QA1, SB, SB1, UAT, Prod, All Release |
| Forex | SIT, SIT1, QA, QA1, SB, SB1, UAT, Prod, All Release |
| Tractor Loan | SIT, SIT1, QA, QA1, SB, SB1, UAT, Prod |

> Note: The source contains product-wise deployment link labels. The actual URLs are not included in the extracted text available for this Markdown normalization.

---

## 16. Recommended Release Note Minimum Fields

Every release note should contain at least:

1. Release tag and release type
2. In-scope products and shared services
3. Repository and version mapping
4. Environment promotion history
5. Smoke evidence links
6. Regression evidence links
7. Backward compatibility evidence links
8. Approvals and sign-off status
9. Known issues
10. Accepted risks
11. Rollback owner
12. Rollback method
13. Final go/no-go decision
14. Closure summary

---

## 17. Key RAG Source Concepts

The following concepts are central to this document and should remain distinguishable during later RAG chunking:

### Release Types

- Master Release
- Hotfix Release
- Planned Independent Release

### Environments

- SIT
- SIT1
- QA
- QA1
- Sandbox
- SB
- SB1
- UAT
- Pre-Prod
- Production / Prod
- PERF

### Release Gates

- Code cut-off
- SIT quality gate
- QA validation
- Regression evidence
- Backward compatibility validation
- Sandbox promotion
- UAT sign-off
- Vulnerability closure
- AOPM approval
- Production readiness
- Go/no-go decision

### Primary Roles

- Release Manager / Master Release Owner
- Product Release Owner
- Tech Lead
- QA Lead
- UAT / Business SPOC
- DevOps
- Build Owner
- SRE
- QA Head or delegate
- Product Owner

### Required Evidence

- Version mapping
- Smoke reports
- Regression reports
- Backward compatibility status
- Defect disposition
- Vulnerability status
- QA approval
- UAT approval
- Known issues
- Waivers
- Mitigations
- Rollback details

### Blocking Conditions

Production or promotion can be blocked by:

- Missing required approvals
- Missing regression evidence
- Missing backward compatibility evidence
- Open high or critical security findings without approved risk treatment
- Missing rollback readiness
- Missing hotfix merge or reconciliation
- Missed common-service cut-off without approved time-boxed extension

---

## 18. Source Preservation Notes

This Markdown is a normalized representation of the supplied release documentation. It preserves the documented terminology, release stages, roles, controls, checklists, and governance rules.

Where the source contains visual deployment-link tables, the environment labels and product names have been retained. The extracted source does not provide all underlying destination URLs in the normalized text.

