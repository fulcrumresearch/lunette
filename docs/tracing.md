# Tracing

Lunette captures your agent's trajectories using OpenTelemetry instrumentation. There are three ways to set it up:

## Inspect AI

If you're using Inspect AI, tracing is automatic. Lunette registers as an Inspect plugin, so trajectories are captured whenever you run an eval:

```bash
inspect eval your_task.py --model anthropic/claude-3-5-sonnet
```

No code changes required—just having `lunette-sdk` installed enables tracing.

## OpenAI / Anthropic

For direct API usage, wrap your calls in a `LunetteTracer`:

=== "Anthropic"

    ```python
    import asyncio
    from anthropic import AsyncAnthropic
    from lunette import LunetteTracer

    async def main():
        client = AsyncAnthropic()
        tracer = LunetteTracer(task="my-eval", model="claude-haiku-4-5")

        async with tracer.trajectory(sample="question-1"):
            response = await client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=256,
                messages=[{"role": "user", "content": "What is 2 + 2?"}],
            )
            print(response.content[0].text)

        # run more samples...
        async with tracer.trajectory(sample="question-2"):
            response = await client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=256,
                messages=[{"role": "user", "content": "What is the capital of France?"}],
            )

        result = await tracer.close()
        print(f"Uploaded: {result['run_id']}")

    asyncio.run(main())
    ```

=== "OpenAI"

    ```python
    import asyncio
    from openai import AsyncOpenAI
    from lunette import LunetteTracer

    async def main():
        client = AsyncOpenAI()
        tracer = LunetteTracer(task="my-eval", model="gpt-4o-mini")

        async with tracer.trajectory(sample="question-1"):
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "What is 2 + 2?"},
                ],
            )
            print(response.choices[0].message.content)

        result = await tracer.close()
        print(f"Uploaded: {result['run_id']}")

    asyncio.run(main())
    ```

All LLM calls inside `trajectory()` are captured automatically—messages, tool calls, and responses.

### Key Concepts

**Tracer**: Represents one evaluation run. Collects all trajectories for a task/model combination.

```python
tracer = LunetteTracer(task="math-eval", model="claude-haiku-4-5")
```

**Trajectory**: One sample's execution trace. Use as a context manager:

```python
async with tracer.trajectory(sample="problem-1"):
    # all LLM calls here are captured
    response = await client.messages.create(...)
```

**Upload**: Call `close()` to upload all trajectories:

```python
result = await tracer.close()
```

## Custom Integration

If you need manual control over message capture (e.g., for a custom LLM client), you can build trajectories directly using the message types:

```python
from lunette import LunetteClient, Run, Trajectory
from lunette.models.messages import SystemMessage, UserMessage, AssistantMessage, ToolMessage, ToolCall

messages = [
    SystemMessage(position=0, content="You are a helpful assistant."),
    UserMessage(position=1, content="What is 2 + 2?"),
    AssistantMessage(position=2, content="4"),
]

trajectory = Trajectory(
    sample="question-1",
    messages=messages,
)

run = Run(
    run_id="my-run-id",
    task="math-eval",
    model="my-custom-model",
    trajectories=[trajectory]
)

async with LunetteClient() as client:
    await client.save_run(run)
```

This is rarely needed—the tracer handles most cases automatically.
