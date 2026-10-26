# Why We Use Jenkins

## Learning Objectives

By the end of this lesson, you should be able to:

- Explain why Jenkins is used in the software delivery process.
- Understand the value of automation and repeatability.
- Understand Jenkins' role in the company's deployment workflow.

## The Problem With a Fully Manual Process

A software release can involve several activities:

```text
Get the correct code
       ↓
Build
       ↓
Run tests
       ↓
Run quality checks
       ↓
Run security checks
       ↓
Create deployable output
       ↓
Deploy
       ↓
Validate
```

Doing these steps manually for every service and every release increases the possibility of human error.

Examples of problems include:

- Building the wrong branch.
- Forgetting a validation step.
- Using inconsistent commands.
- Deploying an incorrect version.
- Having no clear record of what was built.
- Spending time repeatedly performing the same tasks.

## What Jenkins Provides

Jenkins allows these activities to be defined as an automated workflow.

This provides:

### Automation

Repeated build and deployment activities can be executed by Jenkins instead of being performed manually each time.

### Consistency

The same configured process can be followed for repeated executions.

### Traceability

Jenkins maintains information about individual builds, including build numbers, parameters, Git information and execution logs.

### Faster Feedback

Build, test, quality and security checks can be performed as part of the pipeline so failures can be identified earlier.

### Repeatability

A particular pipeline can be run again when required, using the configured process and parameters.

## Jenkins in Our Company Context

The company has build pipelines for services, including UI and backend services.

Pipeline names can vary by service. Examples include:

```text
service-name-orchestrator-build
servicename-ui-build
servicename-build
```

The build pipeline is therefore the starting point for understanding how a service moves through the company's delivery process.

## Jenkins Is Part of a Larger Toolchain

Jenkins should not be viewed as the entire software delivery system.

A simplified view is:

```text
Developer
   ↓
Git / Bitbucket
   ↓
Jenkins
   ↓
Build + Checks
   ↓
Artifact / Image
   ↓
Deployment
   ↓
SIT
   ↓
Smoke Test
   ↓
QA
```

Different systems may participate in different stages, but Jenkins coordinates the automated workflow defined for the pipeline.

## Key Takeaway

The main reason we use Jenkins is not simply to "run a build."

Jenkins provides a repeatable automation layer for building, validating and progressing software through the company's delivery workflow.
