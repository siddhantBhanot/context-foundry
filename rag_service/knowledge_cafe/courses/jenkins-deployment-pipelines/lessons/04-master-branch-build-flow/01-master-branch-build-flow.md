# Master Branch Build Flow

## Build

`home-loan-home-loan-ui-build #3340`

Code is merged into master and the Jenkins build is triggered.

Jenkins builds the Home Loan UI and runs the configured:

- Build checks
- Quality checks
- Security checks

## Build Successful

`BUILD SUCCESSFUL`

Once the master build completes successfully, the build is automatically promoted to SIT.

## Generate Version Manifest

`home-loan-generate-version-manifest #3410`

Generates the version and deployment metadata required for the application release.

## SIT Deployment

`home-loan-sit-deploy #2673`

The successfully built artifact/version is deployed to the SIT environment.

SIT deployment can also be triggered directly by manually running the SIT Deploy pipeline.

## SIT Deployment Successful

`SIT DEPLOYMENT SUCCESSFUL`

Once the deployment is completed successfully, automated smoke tests are triggered.

## SIT Smoke Test

`home-loan-sit-run-smoke #3235`

Basic validation is performed on the SIT environment to ensure the deployed application is working correctly.

## Smoke Tests

`SMOKE TESTS GREEN / SUCCESSFUL`

Only after the smoke tests pass successfully, the build is promoted to the QA environment.

## QA Deployment

`home-loan-qa-deploy #2225`

`BUILD PROMOTED TO QA`
