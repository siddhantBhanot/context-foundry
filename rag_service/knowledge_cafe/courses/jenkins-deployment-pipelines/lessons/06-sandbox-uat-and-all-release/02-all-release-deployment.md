# All Release Deployment

UAT can also be deployed by the all release pipeline of that service.

The all release pipeline is used for PROD as well.

Pipeline:

`Service-name-all-release-pipeline`

## All Release Parameters

Release:

From where you want to pick your changes:

- Sandbox
- sandbox1

## UAT Deployment

To publish your changes to UAT via all release pipelines, abort it once the UAT deployment starts.

## PROD Deployment

If you want to completely deploy it to prod, continue the process.

Once it reaches PREPROD, Infra team approval is needed to deploy it on prod.
