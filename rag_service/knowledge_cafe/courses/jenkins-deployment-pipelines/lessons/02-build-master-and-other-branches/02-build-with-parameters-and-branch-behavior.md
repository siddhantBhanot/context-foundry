# Build With Parameters and Branch Behavior

## Build With Parameters

For build, use:

`BUILD WITH PARAMATERS`

For the build pipeline, provide the branch parameter.

Branch values:

- Feature
- Hotfix
- Custom
- Release
- Master

## Master Branch

If the `master` branch is passed:

- It will build the branch.
- It will deploy the branch to the SIT and QA environment if the build is successful.
- There should be no deployment issue.

## Other Branches

If another branch is passed:

- It will create the Image for that branch.
- The Image can be used in other deployment processes.

## Automated SCM

Sometimes the automated SCM is not triggered.

In that case, deployment can be manually triggered on:

- SIT Environment
- QA Environment
