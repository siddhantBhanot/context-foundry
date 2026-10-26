# Component Responsibilities & Boundaries

## 1. ApplicationController
- Located at: `com.contextfoundry.incomeassessment.controller.ApplicationController`
- Responsibilities:
  - Validates request payload `@Valid @RequestBody InitiationRequest`
  - Extracts correlation headers (`X-Correlation-Id`, `X-App-Id`)
  - Invokes `AssessmentOrchestrationService`
  - Handles client-facing HTTP status code mapping

## 2. KeyData
- Central immutable context passed across all layers:
  ```kotlin
  data class KeyData(
      val applicationId: String,
      val journeyType: JourneyType,
      val customerId: String,
      val assessmentVersion: String,
      val metadata: Map<String, Any> = emptyMap()
  )
  ```

## 3. CommonVersionResolver
- Decouples API contract versions from internal handler logic.
- Evaluates feature toggle `income.assessment.v2.enabled` and journey type.
- Returns the target `AssessmentHandler` bean from the Spring ApplicationContext.

## 4. Assessment Handlers
- Single Responsibility: Each handler owns the business rules and workflow for a specific product journey.
- Implements `processInitiation(keyData, request): Mono<InitiationResult>`
- Implements `handleCallback(keyData, callbackPayload): Mono<AssessmentOutcome>`
