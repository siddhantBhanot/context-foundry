# Knowledge Check & Engineering Readiness Rubric

## Congratulations on Completing the Income Assessment KT!

### Key Architectural Concepts Mastered:
1. **Domain Isolation**: Distinction between Statement-based and ITR-based underwriting.
2. **Spring WebFlux Execution**: Reactive non-blocking pipeline handling high throughput.
3. **KeyData & Version Resolution**: Decoupling API versions from journey business handlers via `CommonVersionResolver`.
4. **Integration Gateways**: Understanding role of Perfios (PDF parsing) and Zenith (Account Aggregator).
5. **Observability & Resilience**: Circuit breakers, MongoDB persistence, Kafka outcome events, and triaging runbooks.

### You Are Now Ready To:
- Pick up Jira tickets for `income-assessment-service`.
- Review PRs involving assessment handlers and partner integrations.
- Debug stuck journeys in Kibana and MongoDB.
- Add new lending journeys by implementing `AssessmentHandler`.
