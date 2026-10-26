# Build Failure and Jenkins Build Options

## Build Failure

Build can fail due to:

- Bitbucket fetch issue
- Vulnerability
- Test case failed
- Any other check failed

The failure can be checked in the build number Console Output.

## Build Number Left Side Panel Options

### Status

Shows the current result of the build:

- Running
- Success
- Failed
- Aborted

### Changes

Shows the code changes or Git commits included in this build.

### Console Output

Shows the complete logs generated during the build.

This is usually the first place to check when a build fails.

### View Build Information

Shows:

- Build number
- Duration
- Start time
- Result
- Information about who or what triggered the build

### Parameters

Shows the parameters and values used when triggering this build.

### Timings

Shows how much time different parts of the build took.

Useful for finding slow stages or processes.

### Git Build Data

Shows:

- Branch
- Commit
- Revision used

### See Fingerprints

Shows artifact fingerprints.

Jenkins uses these to track which builds produced or used particular artifacts across different jobs.

### Lockable Resources

Shows resources that were locked or reserved during the build.

Example:

Preventing multiple builds from using the same server or environment simultaneously.

### Rebuild

Run the build with the same/modified parameters.

### Open Blue Ocean

Opens the build in the Blue Ocean interface.

Provides a more visual representation of Pipeline stages and their execution status.

### Restart from Stage

Allows restarting the Pipeline from a particular stage instead of running the entire Pipeline from the beginning.

### Rebuild (Second One)

Run the same build again.

### Pipeline Steps

Shows detailed internal steps executed by the Jenkins Pipeline.

Useful for advanced debugging.

### Previous Build

Opens the build immediately before the current build.

### Next Build

Opens the build immediately after the current build, if one exists.
