# Seed Deployment Overview and Build

## Seed

Seed contains:

- Feature toggles
- Master data
- Product specific configuration
- Template data

It contains the data which can be updated and changed without re deploy and restart the service.

## Seed Pipeline

`Maximus-seed-build`

Makes the build of:

- Specific branch
- Release branch
- Development branch
- Master branch

## Branch by Environment

SIT:

Development branch is used.

QA:

Release branch is used.

Sandbox:

Release branch is used.

SandboxNew:

Release branch is used.

UAT:

Release branch is used.

PROD:

Master branch is used.
