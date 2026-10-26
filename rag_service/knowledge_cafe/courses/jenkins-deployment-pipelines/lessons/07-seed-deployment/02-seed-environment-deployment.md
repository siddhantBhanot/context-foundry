# Seed Environment Deployment

## SIT

`isForceUpdate:True`

Use when you want to update all the seed data in SIT env.

## SIT1

`isForceUpdate:True`

Use when you want to update all the seed data in SIT1 env.

## QA

`isForceUpdate:True`

Use when you want to update all the seed data in QA env.

Upstream:

`SIT`

## QA1

`isForceUpdate:True`

Use when you want to update all the seed data in QA1 env.

Upstream:

- PROD
- QA
- SANDBOX1
- SANDBOX

## PERF

`isForceUpdate:True`

Use when you want to update all the seed data in PERF env.

Upstream:

- PROD
- QA
- SANDBOX1
- SANDBOX

## SANDBOX

`isForceUpdate:True`

Use when you want to update all the seed data in SANDBOX env.

Upstream:

`QA1`

## SANDBOX1

`isForceUpdate:True`

Use when you want to update all the seed data in SANDBOX1 env.

Upstream:

- QA1
- prod

## UAT

For sit deployment on the UAT ENV.

## PROD

For prod env master branch is used.

DB team merge the release branch to master and deploy.
