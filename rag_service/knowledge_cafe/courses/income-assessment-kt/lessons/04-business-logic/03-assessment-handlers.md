# Assessment Handlers Specification

## 1. AssessmentHandler Interface Contract
```kotlin
interface AssessmentHandler {
    fun supports(journeyType: JourneyType, version: HandlerVersion): Boolean
    
    fun initiateAssessment(keyData: KeyData, payload: InitiationRequest): Mono<InitiationResponse>
    
    fun processCallback(keyData: KeyData, callbackData: ProviderCallbackData): Mono<AssessmentResult>
}
```

## 2. Implemented Handlers in Codebase
1. `FourWheelerPersonalAssessmentHandler`:
   - Enforces 6 months statements
   - Applies strict car loan risk policies
2. `TwoWheelerAssessmentHandler`:
   - Lightweight policy: 3 months statement or minimum balance checks
   - Supports fast approval lanes
3. `ItrAssessmentHandler`:
   - Validates Form 26AS, ITR-V acknowledgements, and compute taxable net income.
