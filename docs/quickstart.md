# Quickstart

## Installation

```bash
pip install lunette-sdk
```

## Configuration

Get your API key from [app.fulcrumresearch.ai](https://app.fulcrumresearch.ai), then set it:

```bash
export LUNETTE_API_KEY="your-api-key-here"
```

## Option 1: Inspect AI

If you have an Inspect AI task, just add `--sandbox lunette`:

```bash
inspect eval your_task.py --sandbox lunette
```

That's it. Your trajectories are captured with full environment access.

## Option 2: SDK

### Step 1: Trace LLM Calls

The simplest integration—wrap your LLM calls to capture trajectories:

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

    result = await tracer.close()
    print(f"Uploaded: {result['run_id']}")

asyncio.run(main())
```

All LLM calls inside `trajectory()` are captured automatically via OpenTelemetry—also works for OpenAI, see [Tracing](tracing.md).

### Step 2: Add a Sandbox

If your agent executes code, add a sandbox for deeper investigation capabilities:

```python
import asyncio
from anthropic import AsyncAnthropic
from lunette import LunetteClient, LunetteTracer

TOOLS = [{
    "name": "bash",
    "description": "Execute a bash command",
    "input_schema": {
        "type": "object",
        "properties": {"command": {"type": "string"}},
        "required": ["command"]
    }
}]

async def run_agent(sandbox, task: str) -> str:
    client = AsyncAnthropic()
    messages = [{"role": "user", "content": task}]

    while True:
        response = await client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1024,
            system="You are a coding assistant. Run Python with: python3 -c 'code'",
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            return next((b.text for b in response.content if b.type == "text"), "")

        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = await sandbox.aexec(block.input["command"])
                output = result.stdout if result.success else f"Error: {result.stderr}"
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": output
                })
        messages.append({"role": "user", "content": tool_results})

async def main():
    tracer = LunetteTracer(task="math-eval", model="claude-haiku-4-5")

    async with LunetteClient() as client:
        sandbox = await client.create_sandbox({"image": "python:3.11-slim"})

        async with tracer.trajectory(sample="problem-1"):
            answer = await run_agent(sandbox, "What is 2^100? Compute it with Python.")

        print(f"Answer: {answer}")
        await sandbox.destroy()

    result = await tracer.close()
    print(f"Uploaded: {result['run_id']}")

asyncio.run(main())
```

With a sandbox, investigators can re-run commands, inspect files, and reproduce errors in the original environment.

You can now view your trajectories at [app.fulcrumresearch.ai](https://app.fulcrumresearch.ai), and then start an investigation to understand your agent behavior.
