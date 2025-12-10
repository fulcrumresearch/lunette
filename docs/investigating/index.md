# Investigating Trajectories

Once you've captured trajectories, you can investigate them to understand agent behavior and identify issues.

## The Investigation Flow

1. **Browse trajectories** at [app.fulcrumresearch.ai](https://app.fulcrumresearch.ai)
2. **Filter** by score, task, model, or metadata to find interesting cases
3. **Launch an investigation** on a trajectory or set of trajectories
4. **Review findings** — investigators create issues with evidence and confidence scores

## What Investigators Do

When you launch an investigation, an AI agent analyzes your trajectories. The investigator:

1. **Reads the trajectory** — Understands what the agent was trying to do
2. **Analyzes the execution** — Identifies where things went wrong (or right)
3. **Accesses the environment** (if available) — Runs commands, inspects files, reproduces errors
4. **Creates issues** — Documents findings with evidence and confidence scores

## Types of Issues

Investigators look for several categories of problems:

### Test Mis-specification

- **Under-specification**: Tests are too permissive, accepting incorrect solutions
- **Over-specification**: Tests are too restrictive, rejecting valid solutions
- **Mis-alignment**: Tests contradict the problem description

### Environment Problems

- Missing files or dependencies
- Broken tools or inconsistent behavior
- Configuration issues

### Agent Behavior

- Reward hacking (attempting to cheat)
- Unusual failure patterns
- Systematic errors

## Investigation Output

Each issue includes:

- **Name**: Brief description of the problem
- **Description**: Detailed explanation with message references
- **Proof**: Evidence demonstrating the issue is real
- **Confidence**: Score from 0.0-1.0 based on evidence strength
- **Trajectory references**: Links to specific messages

## Best Practices

1. **Use sandboxes** — Investigators are much more effective when they can access the environment
2. **Filter before investigating** — Focus on failed or interesting trajectories
3. **Review confidence scores** — Higher confidence means stronger evidence
4. **Check the proof** — Investigators include reproduction steps when possible

