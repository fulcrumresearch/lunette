# Lunette

**Lunette captures your agent's trajectories and helps you understand what's happening.**

When your AI agent runs—whether it's solving coding tasks, answering questions, or using tools—Lunette records every step. You can then browse these trajectories, see where things went wrong, and launch *investigator agents* that analyze failures for you.

## Two capture modes

Lunette can capture your agent's work in two ways:

<div class="grid cards" markdown>

-   :material-text-box-outline: **Transcript**

    ---

    Captures the **conversation only**: messages, tool calls, and responses. Lightweight, works with any LLM code.

    Best for: Understanding what your agent said and did.

-   :material-server: **Transcript + Environment**

    ---

    Captures conversation **plus a cloud sandbox**. The investigator can re-run commands and access files from the original environment.

    Best for: Debugging agents that execute code or modify files.

</div>

## How to use each mode

<div class="grid cards" markdown>

-   :material-code-braces: **[Transcript: Custom Agents](custom-agents.md)**

    ---

    Wrap your LLM calls with the tracer:

    ```python
    async with tracer.trajectory(sample=1):
        response = await client.chat(...)
    ```

-   :material-flask: **[Environment: Inspect AI](inspect-ai.md)**

    ---

    Add one flag to run in a Lunette sandbox:

    ```bash
    inspect eval task.py --sandbox lunette
    ```

</div>

## What happens next?

Once your trajectories are captured:

1. **Browse** them at [app.fulcrumresearch.ai](https://app.fulcrumresearch.ai)
2. **Filter** by score, task, model, or custom metadata
3. **Investigate** failures with AI agents that analyze your traces (and execute code in the environment, if captured)

## Installation

```bash
pip install lunette-sdk
```

Or with uv:

```bash
uv add lunette-sdk
```

## Configuration

Get your API key from [app.fulcrumresearch.ai](https://app.fulcrumresearch.ai), then either:

**Option 1: Environment variable** (recommended for CI/containers)
```bash
export LUNETTE_API_KEY="your-api-key-here"
```

**Option 2: Config file** (convenient for local dev)
```bash
mkdir -p ~/.lunette
echo '{"api_key": "your-api-key-here"}' > ~/.lunette/config.json
```

## Links

- [Web App](https://app.fulcrumresearch.ai) — Browse trajectories and launch investigations
- [Demo](https://demo.fulcrumresearch.ai/home) — Try out the platform
- [GitHub](https://github.com/fulcrum-research/lunette) — Source code

