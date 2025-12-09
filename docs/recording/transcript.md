# Transcript Mode

Transcript mode captures the conversation between your agent and the LLM—messages, tool calls, and responses—without a sandbox environment.

!!! note "Consider Environment Mode"
    If your agent executes code or modifies files, [environment mode](environment.md) provides much better investigation capabilities.

## When to Use

Transcript mode is useful when:

- Your agent only has conversations (no code execution)
- You're quickly prototyping and don't need deep debugging
- You can't use Lunette's sandbox infrastructure
- You want minimal integration overhead

## How It Works

1. Create a `LunetteTracer` for your evaluation run
2. Wrap each sample in a `trajectory()` context
3. Make your LLM calls inside the context—they're captured automatically
4. Call `tracer.close()` to upload

## Example with OpenAI

```python
--8<-- "examples/transcript/openai.py"
```

Run it:

```bash
uv run python examples/transcript/openai.py
```

## Example with Anthropic

```python
--8<-- "examples/transcript/anthropic.py"
```

## Key Concepts

### Tracer

A `LunetteTracer` represents one evaluation run. It collects all trajectories for a given task and model.

```python
tracer = LunetteTracer(task="my-task", model="gpt-4o")
```

### Trajectory

A trajectory is one sample's execution trace. Use `tracer.trajectory()` as a context manager:

```python
async with tracer.trajectory(sample="problem-1"):
    # all LLM calls here are captured
    response = await client.chat.completions.create(...)
```

The `sample` can be any identifier (string or int).

### Uploading

Call `close()` to upload all trajectories:

```python
await tracer.close()
```

## What Gets Captured

The tracer uses OpenTelemetry instrumentation to automatically capture:

- All messages (system, user, assistant)
- Tool calls and their results  
- Multi-turn conversations

You don't need to manually log anything—just make your normal API calls inside the trajectory context.

## Limitations

Without environment access, investigators can only analyze the transcript. They can see what the agent *said* it did, but they can't:

- Verify the agent's claims by running commands
- Inspect files the agent referenced
- Reproduce errors in the original environment
- Test alternative approaches

For deeper investigation capabilities, use [environment mode](environment.md).
