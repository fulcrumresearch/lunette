# Environment Mode

!!! success "Recommended"
    Environment mode gives investigators full access to the agent's execution environment, enabling much deeper analysis.

Environment mode captures both the conversation transcript **and** a cloud sandbox that investigators can access later. This means investigators can:

- Re-run commands the agent executed
- Inspect files the agent created or modified
- Reproduce and debug errors
- Test hypotheses about what went wrong

## With Inspect AI

The simplest way to use environment mode is with Inspect AI:

```bash
inspect eval your_task.py --sandbox lunette
```

Lunette registers as an Inspect AI sandbox provider. When you use `--sandbox lunette`, your task runs in a cloud sandbox that gets snapshotted for later investigation.

### Example Task

```python
--8<-- "examples/environment/inspect_task.py"
```

Run it:

```bash
inspect eval examples/environment/inspect_task.py --sandbox lunette
```

## With Custom Agent Loops

You can also use environment mode with your own agent code by combining `LunetteTracer` (for conversation capture) with `LunetteClient.create_sandbox()` (for environment access).

```python
--8<-- "examples/environment/custom_task.py"
```

Run it:

```bash
uv run python examples/environment/custom_task.py
```

### Key Points

1. **Create a tracer** with `LunetteTracer(task=..., model=...)`
2. **Create a sandbox** with `client.create_sandbox()`
3. **Wrap your agent loop** in `tracer.trajectory(sample=...)`
4. **Execute commands** in the sandbox with `sandbox.aexec()`
5. **Upload** with `tracer.close()`

The trajectory is automatically linked to the sandbox, so investigators can access the environment later.

## What Gets Captured

- **Transcript**: All LLM messages, tool calls, and responses
- **Environment**: The sandbox state at the end of execution
- **Metadata**: Task name, model, sample ID, scores

Investigators can then:

- Read the transcript to understand what the agent did
- Access the sandbox to verify claims and reproduce issues
- Run additional commands to test hypotheses
