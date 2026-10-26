# Income Assessment — Rule Engine & Calculations

## 1. Underwriting Rule Evaluation
Once financial statements are parsed into transactional line items, the rule engine computes key eligibility metrics:

```kotlin
interface IncomeRuleEvaluator {
    fun evaluate(context: AssessmentContext, transactions: List<BankTransaction>): RuleEvaluationResult
}
```

### Key Evaluators:
1. **SalaryCreditDetector**: Scans credit transactions matching known employer narration patterns and recurring monthly frequencies (+/- 3 calendar days).
2. **ABBCalculator**: Computes Day-End Balance sum / days in month.
3. **BounceDetector**: Identifies inward clearing cheque bounces and ECS/NACH mandate failures. If inward bounces exceed journey tolerance (e.g. > 2 in 6 months), flags high-risk recommendation.
4. **FOIRCalculator**: Calculates Fixed Obligation to Income Ratio by identifying existing loan debit EMI transactions.
