# SIT, SIT1, QA, QA1, PERF, and prodSanbox Deployment

## Build With Parameters

To deploy on:

- SIT
- SIT1
- QA
- QA1
- PERF
- prodSanbox

use `BUILD WITH PARAMATERS` of that pipeline.

Pipelines:

- `Service Name-sit-deploy`
- `Service Name-qa-deploy`
- `Service Name-perf-deploy`
- `Service Name-prodsandbox-deploy`
- `Service Name-sit1-deploy`
- `Service Name-qa1-deploy`

## Parameters

### upstream_environment

Meaning: Upstream environment/source.

Defines the environment/source from which the build is taken.

### branch

Meaning: Helm branch to use.

Specifies the Helm branch whose changes should be used.

### enableRegressionTests

Meaning: Enable/disable regression testing.

- `true`: regression tests will run.
- `false`: regression tests will be skipped.

### override_versions

Meaning: Build version(s) to use.

Specifies the build version(s) that you want to use instead of the default/recent build version.

### runTwistlock

Meaning: Enable/disable Twistlock security scan.

- `true`: Twistlock security scan will run.
- `false`: it will be skipped.

### config_change

Meaning: Whether to use Helm configuration changes.

- `true`: Helm configuration changes will be picked up/applied.
- `false`: Helm configuration changes will not be updated.
