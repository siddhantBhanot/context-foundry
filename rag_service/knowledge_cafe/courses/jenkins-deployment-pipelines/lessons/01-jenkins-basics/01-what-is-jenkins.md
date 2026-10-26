# What Is Jenkins?

## Learning Objectives

By the end of this lesson, you should be able to:

- Explain Jenkins in simple terms.
- Understand what a Jenkins job, build and pipeline are.
- Understand the role Jenkins plays between source code and deployment.

## Jenkins in Simple Terms

Jenkins is an automation tool used to execute software delivery tasks consistently.

Instead of developers manually performing every step required to build and validate an application, Jenkins can run those steps as a defined pipeline.

A simplified flow is:

```text
Source Code
    ↓
Jenkins
    ↓
Build
    ↓
Checks
    ↓
Artifact / Image
    ↓
Deployment
```

## Why Is This Important?

Consider a manual process:

```text
Fetch code
   ↓
Build application
   ↓
Run tests
   ↓
Run quality/security checks
   ↓
Create deployable output
   ↓
Deploy application
   ↓
Validate deployment
```

If every developer or team member performs these steps manually, the process can become inconsistent and error-prone.

Jenkins provides an automated and repeatable way to execute the process.

## Important Jenkins Terms

### Job / Pipeline

A Jenkins job or pipeline represents an automated workflow.

For example, a service may have a build pipeline with a name such as:

```text
home-loan-home-loan-orchestrator-build
```

The company has build pipelines for services, including UI and backend services.

### Build

A build is one execution of a Jenkins job/pipeline.

For example:

```text
servicename-build #3340
```

Here:

- `servicename-build` identifies the pipeline/job.
- `#3340` identifies that particular execution.

A later execution may have a different build number.

### Stage

A stage is a logical part of a pipeline.

A pipeline may contain stages for activities such as:

```text
Checkout
Build
Quality Checks
Security Checks
Deployment
```

The exact stages depend on the pipeline.

### Parameter

A parameter is an input supplied when triggering a parameterized build.

For the company's build pipelines, the branch to build is an important parameter.

### Trigger

A trigger is an event or action that starts a Jenkins pipeline.

For example, a Master branch build can be triggered after code is merged into `master`.

## Jenkins and Source Control Are Different

Jenkins does not replace Git or Bitbucket.

A simplified relationship is:

```text
Git / Bitbucket
     │
     │ source code
     ▼
  Jenkins
     │
     │ automation
     ▼
Build / Checks / Deployment
```

Source control stores the code and its history. Jenkins executes the automated workflow using that code.

## Key Takeaway

Think of Jenkins as the automation engine that takes code and runs the company's defined build and deployment workflow.

You do not need to understand Jenkins administration to use the deployment pipelines. You first need to understand how a pipeline is triggered, what it does, how to verify it, and how to troubleshoot it.
