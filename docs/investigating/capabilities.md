# Investigator Capabilities

Lunette's investigator agents have access to several tools for analyzing trajectories. The capabilities available depend on how the trajectory was recorded.

## Always Available

These tools are available regardless of recording mode:

### Trajectory Access

Investigators can read the complete trajectory transcript:

- **Messages**: Every user prompt, assistant response, and tool call
- **Metadata**: Task name, model, sample ID, scores
- **Summary**: High-level overview of what the agent did

### Search

Investigators can search across trajectories to find patterns:

- Find similar failures across samples
- Look for counter-evidence to hypotheses
- Identify systematic issues

### Issue Creation

Investigators submit findings as structured issues:

- Name and description
- Evidence and proof
- Confidence score (0.0-1.0)
- References to specific messages

## With Environment Mode

When trajectories are recorded with [environment mode](../recording/environment.md), investigators gain powerful additional capabilities:

### Sandbox Execution

Investigators can run commands in the original sandbox environment:

```
mcp__sandbox__exec("ls -la")
mcp__sandbox__exec("python test.py")
mcp__sandbox__exec("cat solution.py")
```

This allows them to:

- **Verify agent claims** — Did the agent actually create that file?
- **Reproduce errors** — Run the same command that failed
- **Test hypotheses** — Try alternative approaches
- **Inspect state** — See what files exist, check configurations

### File Access

Investigators can read files from the sandbox:

- Source code the agent wrote
- Configuration files
- Test outputs and logs
- Any file in the working directory

### Environment Exploration

Investigators can explore the environment to understand context:

- Check installed packages and versions
- Verify dependencies exist
- Understand the file structure
- Test environment assumptions

## Why Environment Access Matters

Without sandbox access, investigators can only analyze what the agent *said* it did. They see:

> "I created a file called `solution.py` with the fix"

With sandbox access, they can verify:

```bash
$ cat solution.py
# Actually see the contents
$ python -m pytest test.py
# Actually run the tests
```

This makes a huge difference for:

- **Debugging failures** — Reproduce the exact error
- **Validating fixes** — Confirm the solution works
- **Finding edge cases** — Test scenarios the agent didn't consider
- **Understanding context** — See what the agent was working with

## Claim Evaluation

Before submitting issues, investigators use a claim evaluator that:

1. Checks if the claim is specific and falsifiable
2. Verifies evidence supports the conclusion
3. Searches for counter-evidence
4. Ensures appropriate scope (not overgeneralized)

This helps ensure issues are well-supported and actionable.

## Summary

| Capability | Transcript Mode | Environment Mode |
|------------|-----------------|------------------|
| Read trajectory | ✓ | ✓ |
| Search trajectories | ✓ | ✓ |
| Create issues | ✓ | ✓ |
| Execute commands | ✗ | ✓ |
| Read files | ✗ | ✓ |
| Reproduce errors | ✗ | ✓ |
| Test hypotheses | ✗ | ✓ |

!!! tip "Maximize investigation power"
    Use [environment mode](../recording/environment.md) whenever possible. The additional capabilities significantly improve investigation quality.
