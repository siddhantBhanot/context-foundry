# Sandbox, Sandbox1, and UAT Deployment

## Build With Parameters

To deploy on:

- Sandbox
- SandboxNew
- sandbox1
- uat

use `BUILD WITH PARAMATERS` of that pipeline.

## Sandbox

Upstream:

`qa`

## Sandbox1

Upstream:

`qa1`

## UAT

UAT deploy parameters:

Upstream:

- sandbox
- sandbox1

VERSIONING:

- patching
- minor
- major

Minor is for hotfix deployment.

Major is for Master release deployment.
