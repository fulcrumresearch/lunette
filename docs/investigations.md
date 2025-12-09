# Investigations

After capturing trajectories, you can launch *investigator agents* that analyze them. These agents read your traces, execute code in the original environment, and surface issues.

## What investigators do

1. **Read trajectories** — They see the full conversation history
2. **Execute code** — They can run commands in a replica of your sandbox
3. **Surface issues** — They identify problems like task underspecification, incorrect tool usage, or reasoning errors
4. **Validate findings** — Critic agents check their work to reduce hallucinations

## Launching an investigation

### Via the web UI

The easiest way: go to [app.fulcrumresearch.ai](https://app.fulcrumresearch.ai), navigate to a run, and click **Investigate**.

### Via CLI

Create an investigation spec in YAML:

```yaml
--8<-- "examples/investigation.yaml"
```

Run it:

```bash
lunette investigate examples/investigation.yaml --run-id <your-run-id>
```

Use `--limit N` to investigate only the first N matching trajectories.

## Investigation specs

An investigation spec defines:

| Field | Description |
|-------|-------------|
| `name` | Identifier for this investigation type |
| `type` | Always `investigation` |
| `trajectory_filters` | Which trajectories to analyze (e.g., failed ones) |
| `agent.prompt` | What the investigator should look for |

## Understanding results

Investigation results include:

- **Issues** — Problems the investigator found
- **Evidence** — Code execution results and trace analysis supporting each issue
- **Confidence** — How certain the investigator is

Issues are validated by critic agents before being shown to you.

