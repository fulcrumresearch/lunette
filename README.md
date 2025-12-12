<div align="center">
  <img src="docs/assets/logo.svg" alt="Lunette" width="120" height="120">
</div>

# Lunette

**Lunette captures your agent's trajectories and helps you understand what's happening.**

When your AI agent runs—whether it's solving coding tasks, answering questions, or using tools—Lunette records every step. You can then browse these trajectories, see where things went wrong, and launch *investigator agents* that analyze failures for you.

## Why Lunette?

Issues in agent evals are pernicious. Even SWE-bench Verified, the most popular software engineering benchmark, has unsolvable tasks that are useless for understanding agent abilities.

Lunette uses investigator agents that probe the same environment your agents ran in. You run your agent in isolated Lunette sandboxes, then launch investigations to find both issues and performance bottlenecks. These agents read the trace, modify and run commands in the eval environment to test hypotheses, and report findings that get filtered for high-quality results.

There are two ways to use it:

- **With Inspect AI** — One-line integration if you're already using Inspect
- **With any LLM** — Wrap your API calls to capture trajectories

## Installation

```bash
pip install lunette-sdk
```

## Configuration

Get your API key from [app.fulcrumresearch.ai](https://app.fulcrumresearch.ai), then set it:

```bash
export LUNETTE_API_KEY="your-api-key-here"
```

## Usage

### With Inspect AI

If you have an Inspect AI task, just add `--sandbox lunette`:

```bash
inspect eval your_task.py --sandbox lunette
```

That's it. Your trajectories are captured with full environment access.

### With the SDK

Wrap your LLM calls to capture trajectories:

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

All LLM calls inside `trajectory()` are captured automatically via OpenTelemetry—also works for OpenAI.

You can now view your trajectories at [app.fulcrumresearch.ai](https://app.fulcrumresearch.ai), and then start an investigation to understand your agent behavior.

## Documentation

**[Read the full documentation →](https://lunette.fulcrumresearch.ai)**

- [Quickstart](https://lunette.fulcrumresearch.ai/quickstart) — Get up and running
- [Tracing](https://lunette.fulcrumresearch.ai/tracing) — Capture trajectories from any LLM
- [Running Agents](https://lunette.fulcrumresearch.ai/running-agents) — Run agents in Lunette sandboxes
- [Issues and Judging](https://lunette.fulcrumresearch.ai/issues-and-judging) — How investigator agents find problems
- [API Reference](https://lunette.fulcrumresearch.ai/api) — Complete API documentation

## Links

- **[Web App](https://app.fulcrumresearch.ai)** — Browse trajectories and launch investigations
- **[Demo](https://demo.fulcrumresearch.ai)** — Try the platform
- **[Documentation](https://lunette.fulcrumresearch.ai)** — Full docs
