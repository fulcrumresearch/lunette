# Issues and Judging

Investigator agents can be configured to produce either **issues** or **scores**, depending on what you need.

## Issues

Issues are structured findings about problems in your eval or agent. Investigator agents write issues when they detect:

- **Test mis-specifications** — Tasks with vague requirements or overly strict tests
- **Environment problems** — Missing dependencies, incorrect setup, or broken tooling
- **Agent failures** — Bugs in agent behavior or reasoning errors

Each issue includes:

- **Description** — What the problem is
- **Evidence** — Message references and supporting data
- **Confidence score** — How certain the investigator is
- **Reproduction steps** — Commands to verify the issue

Validator agents critique these findings and filter for high-quality results, reducing false positives.

## Judging (Scores)

Investigator agents can also track and score specific behaviors across trajectories. This is useful when you want to measure:

- Agent verbosity, reasoning quality, or other qualitative aspects
- Any behavior that's hard to capture with automated metrics

Scores can be:

- **Binary** — Pass/fail judgments
- **Scalar** — Numeric ratings (0-1, 1-10, etc.)
- **Multi-metric** — Multiple scores for different criteria

Like issues, scores come with evidence and reasoning, making the judgment transparent and auditable.

## How It Works

When you launch an investigation:

1. **Investigator agents** read trajectories and execute commands in the eval environment
2. They write either issues (if looking for problems) or scores (if evaluating performance)
3. **Validator agents** critique the findings
4. High-quality results are surfaced in the web UI

Both types of output reference specific messages in the trajectory, so you can see exactly what led to each finding.
