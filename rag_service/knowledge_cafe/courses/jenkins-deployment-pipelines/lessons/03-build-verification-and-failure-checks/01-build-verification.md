# Build Verification

## Confirm Build by Last Commit

A build can be confirmed by the last commit on that branch.

Example:

The last commit in the master branch can be compared with the build number in Jenkins.

In the console output of the build number:

- Search the last commit first 5 value.
- The value should match.

Example:

`Home-loan-ui:build-3340-ad9cb`

## Image Format

Format:

`service name:build-buildNo.-first 5 values of the commit`

Example:

`Home-loan-ui:build-3340-ad9cb`

## Kibana Verification

The build can also be verified in the latest Kibana logs of that service.

Field:

`Kubernetes.container_image`

Value contains:

`servicename:Env-buildNo.-first 5 values of the commit`
