# Custom Agent Loop

If you have your own agent code (not using Inspect AI), use `LunetteTracer` to capture trajectories.

## How it works

1. Create a `LunetteTracer` for your evaluation run
2. Wrap each sample in a `trajectory()` context
3. Make your LLM calls inside the context — they're captured automatically
4. Call `tracer.close()` to upload

## Transcript only

These examples capture just the conversation (no environment access).

### OpenAI

```python
--8<-- "examples/transcript/openai.py"
```

Run it:

```bash
uv run python examples/transcript/openai.py
```

### Anthropic

```python
--8<-- "examples/transcript/anthropic.py"
```

## Transcript + Environment

To capture both the conversation and a sandbox environment that investigators can access later, combine `LunetteTracer` with `LunetteClient.create_sandbox()`.

This example runs an agent that solves a coding problem in a cloud sandbox:

```python
--8<-- "examples/environment/custom_task.py"
```

Run it:

```bash
uv run python examples/environment/custom_task.py
```

The trajectory is uploaded with the sandbox ID, so investigators can later access the environment to inspect files, re-run commands, and debug issues.

## Key concepts

### Tracer

A `LunetteTracer` represents one evaluation run. It has a unique `run_id` and collects all trajectories for a given task and model.

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

## What gets captured

The tracer uses OpenTelemetry instrumentation to automatically capture:

- All messages (system, user, assistant)
- Tool calls and their results  
- Multi-turn conversations
- Image inputs (with Anthropic; OpenAI instrumentation has limitations)

You don't need to manually log anything—just make your normal API calls inside the trajectory context.

