# How Jenkins Works

## Learning Objectives

By the end of this lesson, you should be able to:

- Understand the basic lifecycle of a Jenkins build.
- Explain the relationship between source control, pipeline, stages and build number.
- Understand how the concepts introduced here connect to the company's pipelines.

## Basic Jenkins Lifecycle

A simplified Jenkins lifecycle looks like this:

```text
1. Trigger
   ↓
2. Select / receive inputs
   ↓
3. Get source code
   ↓
4. Execute pipeline stages
   ↓
5. Produce build output
   ↓
6. Record build information
   ↓
7. Continue to deployment when configured
```

## 1. Trigger

A pipeline needs something to start it.

Examples include:

- An automated source-control trigger.
- A user manually starting a build.
- A deployment being manually triggered when automation does not occur.

The exact trigger depends on the pipeline.

## 2. Inputs and Parameters

Some pipelines require parameters when they are started.

For the company's build pipeline, the branch to build is provided through **Build With Parameters**.

For example:

```text
Branch = feature/ABC-123
```

Jenkins then uses the selected branch as the input for the build.

## 3. Source Code

Jenkins obtains the source code associated with the selected branch/revision.

The build information records Git-related details such as:

- Branch
- Commit
- Revision

These details are useful when verifying exactly what code was built.

## 4. Pipeline Stages

Jenkins executes the configured stages.

A simplified example is:

```text
Checkout
   ↓
Build
   ↓
Quality Checks
   ↓
Security Checks
   ↓
Package / Image
```

The actual pipeline can contain additional stages.

## 5. Build Result

The build eventually reaches a result such as:

```text
SUCCESS
FAILED
ABORTED
```

Jenkins also records the execution as a build number.

Example:

```text
servicename-build #3340
```

## 6. Logs and Build Information

Every build provides information that can be used to understand what happened.

Important areas include:

- Console Output
- Parameters
- Changes
- Git Build Data
- Build Information
- Timings
- Pipeline Steps

These become particularly important when a build fails.

## 7. Deployment

For the Master branch workflow, a successful build can continue into the deployment process.

The high-level flow is:

```text
Master Build
    ↓
Build Successful
    ↓
Version Manifest
    ↓
SIT Deployment
    ↓
Smoke Test
    ↓
QA Deployment
```

## The Most Important Mental Model

When looking at a Jenkins build, always ask:

1. **What pipeline am I running?**
2. **What triggered it?**
3. **What branch/commit is being built?**
4. **Which stages have executed?**
5. **Did the build pass or fail?**
6. **What artifact/image/version was produced?**
7. **Where is that version being deployed?**

If you can answer these questions, you can navigate the company's Jenkins workflow confidently.
