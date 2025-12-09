# Getting Started

The fastest way to start capturing trajectories is with **Inspect AI**. This gives you full environment access—the recommended mode for maximum investigation capabilities.

## Installation

```bash
pip install lunette-sdk
```

Or with uv:

```bash
uv add lunette-sdk
```

## Configuration

Get your API key from [app.fulcrumresearch.ai](https://app.fulcrumresearch.ai), then set it:

**Option 1: Environment variable** (recommended for CI/containers)
```bash
export LUNETTE_API_KEY="your-api-key-here"
```

**Option 2: Config file** (convenient for local dev)
```bash
mkdir -p ~/.lunette
echo '{"api_key": "your-api-key-here"}' > ~/.lunette/config.json
```

## Run your first eval

If you have an Inspect AI task, just add `--sandbox lunette`:

```bash
inspect eval your_task.py --sandbox lunette
```

That's it. Your trajectories are now being captured with full environment access.

## Example task

Here's a simple coding task that runs in the Lunette sandbox:

```python
--8<-- "examples/environment/inspect_task.py"
```

Run it:

```bash
inspect eval examples/environment/inspect_task.py --sandbox lunette
```

## What happens next

1. **View trajectories** at [app.fulcrumresearch.ai](https://app.fulcrumresearch.ai)
2. **Filter** by score, task, model, or metadata
3. **Investigate** failures with AI agents that can access the original environment

## Next steps

- [Recording Trajectories](recording/index.md) — Learn about transcript vs environment modes
- [Investigating Trajectories](investigating/index.md) — Understand what investigators can do
