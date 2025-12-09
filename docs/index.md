# Lunette

**Lunette captures your agent's trajectories and helps you understand what's happening.**

When your AI agent runs—whether it's solving coding tasks, answering questions, or using tools—Lunette records every step. You can then browse these trajectories, see where things went wrong, and launch *investigator agents* that analyze failures for you.

## Two ways to use Lunette

<div class="grid cards" markdown>

-   :material-flask: **[Using Inspect AI](inspect-ai.md)**

    ---

    Already using Inspect AI for evals? Add one flag and your trajectories are captured automatically.

    ```bash
    inspect eval task.py --sandbox lunette
    ```

-   :material-code-braces: **[Custom Agent Loop](custom-agents.md)**

    ---

    Have your own agent code? Wrap it with the tracer to capture trajectories.

    ```python
    async with tracer.trajectory(sample=1):
        response = await client.chat(...)
    ```

</div>

## What happens next?

Once your trajectories are captured:

1. **Browse** them at [app.fulcrumresearch.ai](https://app.fulcrumresearch.ai)
2. **Filter** by score, task, model, or custom metadata
3. **Investigate** failures with AI agents that read your traces and execute code in the original environment

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

