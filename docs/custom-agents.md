# Custom Agent Loop

If you have your own agent code (not using Inspect AI), use `LunetteTracer` to capture trajectories.

## How it works

1. Create a `LunetteTracer` for your evaluation run
2. Wrap each sample in a `trajectory()` context
3. Make your LLM calls inside the context — they're captured automatically
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

