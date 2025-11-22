# Lunette

Lunette is a platform for understanding agents and evals through investigator agents. With Lunette, you can spin up investigator agents that read your agent traces and execute code in your agents’ environments. These investigators surface issues, which are checked by critics to mitigate hallucinations. Lunette allows users to better understand what their evals are measuring. Check out our [demo](https://demo.fulcrumresearch.ai/home) or book a [time to chat](https://cal.com/kaivu/30min).

Lunette is currently in beta, and quickly getting many improvements. Feel free to suggest things!

![lunette flow](lunette_flow.png)

## Installation

```bash
pip install lunette-sdk
```

Or with uv:

```bash
uv add lunette-sdk
```

## Quick Start

### 1. Get Your API Key

Visit [app.fulcrumresearch.ai](https://app.fulcrumresearch.ai) to sign up and get your API key.

### 2. Configure Lunette

Create a configuration file at `~/.lunette/config.json`:

```json
{
  "api_key": "your-api-key-here"
}
```

### 3. Run Your Evaluation

Run your Inspect AI evaluation with the Lunette sandbox:

```bash
inspect eval your_task.py --sandbox lunette
```

That's it! Your trajectories will automatically be logged to the Fulcrum platform, where you can:
- Browse and visualize agent trajectories
- Analyze performance across multiple runs

- Launch automated investigations to identify patterns and issues

You can also run almost all existing inspect sandboxes on lunette out of the box, including swebench!

```
uv run inspect eval inspect_evals/swe_bench_verified_mini --model openai/gpt-5-nano --limit 1 --sandbox lunette -T sandbox_config_template_file=examples/swebench.yaml -T sandbox_type=lunette -T build_docker_images=False
```

### Programmatic API

You can also use Lunette programmatically to upload trajectories:

```python
from lunette import LunetteClient, Run, Trajectory

async with LunetteClient() as client:
    run = Run(
        run_id="unique-run-id",
        task="your-task-name",
        model="your-model-name",
        trajectories=[trajectory1, trajectory2, ...]
    )
    await client.save_run(run)
```

We are currently adding support for various trajectory formats. The core `Trajectory` type signature is:

```python
class Trajectory(BaseModel):
    sample: int | str  # Sample ID
    messages: list[Message]  # Execution trace (System, User, Assistant, Tool messages)
    scores: dict[str, ScalarScore] | None  # Multi-metric scores
    metadata: dict[str, Any]  # Additional metadata
    solution: str | None  # Optional solution/patch
```

See the full data model in [lunette/models/](https://github.com/fulcrum-research/lunette/tree/main/lunette/lunette/models)

We will document this more and improve the non-inspect SDK soon.

### Uploading Inspect Logs

If you already have an Inspect `.eval` (or JSON) log from `inspect eval --log`, you can upload it directly with the Lunette CLI:

```
lunette upload logs/2025-11-04T11-10-16-05-00_swe-bench.eval --run-id swe-mini-nov04
```

The command extracts trajectories from the log, creates a run with the task/model metadata, and saves everything to Fulcrum. Use `--task` or `--model` if you need to override what was stored in the log, and `--run-id` to append to an existing run.

### Converting from Inspect AI

Lunette provides utilities to convert Inspect AI `EvalSample` objects to the standard `Trajectory` format:

```python
from lunette import Trajectory

trajectory = Trajectory.from_inspect(run_id="my-run", sample=eval_sample)
```

## Investigations

Users provide Lunette with investigation specs for agents or evals they want to understand. Lunette then launches investigator agents that operate in parallel. For each trajectory, an investigator agent reads the agent trace, modifies and runs commands in the eval environment to test hypotheses, and writes findings. Validator agents then critique these findings and filter for high-quality results. At the end, users can explore investigation results in the Fulcrum frontend and chat with an agent to learn more.

To launch an investigation, you can use the web UI or define an investigation plan in YAML. See [examples/task_underspecification.yaml](examples/task_underspecification.yaml) for a complete example that analyzes failed trajectories for task underspecification issues.

To run the example:

```bash
lunette investigate examples/task_underspecification.yaml
```

You can optionally pass `--limit N` to investigate only the first N matching trajectories.

Issues will start streaming in and you can see your investigations as they go.
