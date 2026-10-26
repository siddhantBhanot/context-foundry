# Service Orchestrators in Codebase

## 1. AssessmentOrchestrationService
- Core application service binding HTTP controllers to business handlers:
  ```kotlin
  @Service
  class AssessmentOrchestrationService(
      private val versionResolver: CommonVersionResolver,
      private val assessmentRepository: AssessmentRepository,
      private val eventPublisher: OutcomeEventPublisher
  ) {
      fun initiate(request: InitiationRequest): Mono<InitiationResponse> {
          val keyData = KeyData.from(request)
          val handler = versionResolver.resolveHandler(keyData)
          return handler.initiateAssessment(keyData, request)
      }
  }
  ```

## 2. CallbackOrchestrationService
- Validates callback source authenticity (HMAC signature).
- Idempotently loads the corresponding assessment record from MongoDB.
- Passes payload to the matching handler to execute the underwriting rule engine.
