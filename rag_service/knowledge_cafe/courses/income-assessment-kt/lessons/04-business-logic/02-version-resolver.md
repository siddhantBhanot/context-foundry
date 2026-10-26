# CommonVersionResolver Pattern & Architecture

## 1. Motivation
In early iterations of `income-assessment-service`, all journey business logic was intermingled in large monolithic services. The Revamped architecture introduced `CommonVersionResolver` to enable zero-downtime journey migration, A/B testing, and modular handler isolation.

## 2. Implementation Pattern
```kotlin
@Component
class CommonVersionResolver(
    private val handlers: List<AssessmentHandler>,
    private val featureFlagService: FeatureFlagService
) {
    fun resolveHandler(keyData: KeyData): AssessmentHandler {
        val useV2 = featureFlagService.isEnabled("income.assessment.v2.${keyData.journeyType.name.lowercase()}")
        val targetVersion = if (useV2) HandlerVersion.V2 else HandlerVersion.V1
        
        return handlers.firstOrNull { it.supports(keyData.journeyType, targetVersion) }
            ?: throw HandlerNotFoundException("No handler found for ${keyData.journeyType} version $targetVersion")
    }
}
```

This ensures that adding a new journey (e.g. `COMMERCIAL_VEHICLE`) only requires adding a new `@Component` implementing `AssessmentHandler` without touching existing code.
