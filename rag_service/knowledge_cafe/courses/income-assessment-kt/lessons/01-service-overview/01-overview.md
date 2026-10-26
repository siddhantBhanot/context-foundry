# Income Assessment Service — Service Overview

## 1. System Purpose
The `income-assessment-service` is an internal core microservice responsible for income verification and assessment for ContextFoundry lending and credit products. It evaluates financial eligibility of applicants by analyzing digital documentation and financial records.

## 2. Technology Stack
- **Language**: Kotlin 1.9+
- **Framework**: Spring Boot 3.x with Spring WebFlux (Project Reactor - `Mono` / `Flux`)
- **Persistence**: MongoDB (stateful journey persistence, assessment records, raw response payloads)
- **Event Streaming**: Apache Kafka (asynchronous outcome events, webhook ingestion, notification dispatch)
- **Build Tool**: Gradle (Kotlin DSL)
- **HTTP Client**: Spring WebClient with netty connection pooling and circuit breakers (Resilience4j)

## 3. High-Level Role in Lending Topology
When a user applies for a credit line, two-wheeler loan, four-wheeler loan, or merchant advance, upstream services (Loan Origination Service / UI Gateway) invoke `income-assessment-service` to initiate income verification.

The service coordinates with third-party verification partners (e.g. Perfios, Zenith Account Aggregator) or tax portals (ITR) to compute key underwriting parameters:
- Net monthly income (NMI)
- Average bank balance (ABB)
- Salary credits and employer verification
- Banking bounce history and financial health flags
