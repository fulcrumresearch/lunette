# Lunette

Lunette is a platform for understanding agents and evals through investigator agents. With Lunette, you can spin up investigator agents that read your agent traces and execute code in your agents’ environments. These investigators surface issues, which are checked by critics to mitigate hallucinations. Lunette allows users to better understand what their evals are measuring. Check out our [demo](https://demo.fulcrumresearch.ai/home) or book a [time to chat](https://cal.com/kaivu/30min).

Lunette is currently in beta, and quickly getting many improvements. Feel free to suggest things!

## Installation

```bash
pip install lunette-sdk
```

Or with uv:

```bash
uv add lunette-sdk
```

## Configuration

### 1\. Get Your API Key

Visit [app.fulcrumresearch.ai](https://app.fulcrumresearch.ai) to sign up and get your API key.

### 2\. Configure Client

Create a configuration file at `~/.lunette/config.json`:

```json
{
  "api_key": "your-api-key-here",
  "base_url": "https://app.fulcrumresearch.ai/api",
  "timeout": 200
}
```

Alternatively, you can provide these details via environment variables or pass them directly to the `LunetteClient` constructor.

## Running with Inspect AI

Lunette integrates seamlessly with the [Inspect AI](https://github.com/UKGovernmentBEIS/inspect_ai) framework. By changing just one line in your task definition, you can offload execution from your local Docker daemon to Lunette's cloud infrastructure.

### Quick Start

Run your Inspect AI evaluation with the Lunette sandbox:

```bash
inspect eval your_task.py --sandbox lunette
```

Your trajectories will automatically be logged to the Fulcrum platform, where you can browse visualizations, analyze performance, and launch investigations.

### Defining a Task

In your Inspect task definition, set the `sandbox` parameter to `"lunette"`.

```python
from inspect_ai import Task, task
from inspect_ai.dataset import Sample
from inspect_ai.solver import system_message

@task
def my_agent_task():
    return Task(
        dataset=[Sample(input="List files", target=".")],
        plan=[system_message("Run 'ls -la'")],
        # Tell Inspect to use Lunette instead of local Docker
        sandbox="lunette" 
    )
```

### Configuring the Environment

Lunette uses standard Docker Compose files to define the sandbox environment. Ensure your `compose.yaml` defines the service you want to run:

```yaml
services:
  default:
    image: python:3.11-slim
    command: tail -f /dev/null  # Keep container alive
    working_dir: /app
```

### Running Standard Benchmarks (e.g., SWE-bench)

You can run almost all existing inspect sandboxes on Lunette out of the box. Here is an example running SWE-bench Verified Mini:

```bash
uv run inspect eval inspect_evals/swe_bench_verified_mini \
  --model openai/gpt-5-nano \
  --limit 1 \
  --sandbox lunette \
  -T sandbox_config_template_file=examples/swebench.yaml \
  -T sandbox_type=lunette \
  -T build_docker_images=False
```

## Running with Python SDK (No Inspect)

If you are not using Inspect AI, you can use the `LunetteClient` to manage sandboxes directly. This is ideal for custom agent loops, CI/CD pipelines, or bespoke evaluation harnesses.

### Initialization

Use `LunetteClient` as an async context manager. It automatically loads credentials from `~/.lunette/config.json`.

```python
import asyncio
from lunette import LunetteClient

async def main():
    async with LunetteClient() as client:
        # Your code here
        pass

asyncio.run(main())
```

### Creating a Sandbox

The simplest way to create a sandbox is to point to a directory containing a Dockerfile:

```python
sandbox = await client.create_sandbox("./my-agent-code")
print(f"Sandbox created with ID: {sandbox.sandbox_id}")
```

Lunette reads the Dockerfile, bundles the build context (respecting `.dockerignore`), and builds the image remotely.

**Advanced: Service Dictionary**

For more control, pass a service dictionary (similar to Docker Compose):

```python
# Pull an existing image
sandbox = await client.create_sandbox({
    "image": "python:3.11-slim",
    "command": "tail -f /dev/null",  # keep the container running
    "working_dir": "/workspace"
})

# Build with additional options
sandbox = await client.create_sandbox({
    "build": {"context": "./my-agent-code"},
    "command": "python agent.py",
    "working_dir": "/app"
})
```

### Executing Commands

Use `aexec` to run shell commands inside the sandbox.

```python
result = await sandbox.aexec("echo 'Hello World'")

if result.success:
    print(f"Stdout: {result.stdout}")
else:
    print(f"Error ({result.exit_code}): {result.stderr}")
```

### File I/O

Upload and download files easily between your local machine and the remote sandbox.

```python
# Upload a local script
await sandbox.aupload(local_path="./local_script.py", remote_path="/workspace/script.py")

# Download results
await sandbox.adownload(remote_path="/workspace/results.json", local_path="./results.json")
```

### Cleanup

Explicitly stop sandboxes when done to free up resources.

```python
await sandbox.destroy()
```

## Service Specification Reference

When using a service dictionary with `create_sandbox`, Lunette supports a subset of the [Docker Compose V2 specification](https://docs.docker.com/compose/compose-file/).

| Field | Description | Example |
| :--- | :--- | :--- |
| **`image`** | Docker image to pull. | `"ubuntu:22.04"` |
| **`build`** | Build context path or dict. | `"."` or `{"context": "."}` |
| **`command`** | Startup command. | `"python app.py"` |
| **`working_dir`** | Directory to execute in. | `"/app"` |
| **`environment`** | Env vars (dict or list). | `{"API_KEY": "..."}` |
| **`ports`** | Port mapping list. | `["8080:80"]` |
| **`volumes`** | Volume mounts. | `["/host:/container"]` |
| **`resources`** | Resource limits. | `{"mem_limit": "512m"}` |

*Note: Orchestration fields like `depends_on`, `links`, and `deploy` are currently ignored as Lunette runs single-service sandboxes.*

## Data Management & API

### Programmatic API: Uploading Results

You can use Lunette to upload evaluation trajectories programmatically:

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

The core `Trajectory` type signature is:

```python
class Trajectory(BaseModel):
    sample: int | str  # Sample ID
    messages: list[Message]  # Execution trace (System, User, Assistant, Tool messages)
    scores: dict[str, ScalarScore] | None  # Multi-metric scores
    metadata: dict[str, Any]  # Additional metadata
    solution: str | None  # Optional solution/patch
```

See the full data model in [lunette/models/](https://github.com/fulcrum-research/lunette/tree/main/lunette/lunette/models).

### Uploading Inspect Logs

If you have an Inspect `.eval` (or JSON) log from `inspect eval --log`, you can upload it directly with the CLI:

```bash
lunette upload logs/2025-11-04T11-10-16-05-00_swe-bench.eval
```

The command extracts trajectories, creates a run with metadata, and saves everything to Fulcrum. Attachments referenced via `attachment://` URIs are automatically resolved and embedded.

### Converting from Inspect AI

Utilities are provided to convert Inspect AI `EvalSample` objects to the standard `Trajectory` format:

```python
from lunette import Trajectory
trajectory = Trajectory.from_inspect(run_id="my-run", sample=eval_sample)
```

## Investigations

Users provide Lunette with investigation specs for agents or evals they want to understand. Lunette launches investigator agents that operate in parallel to read traces, execute code in the eval environment, and surface issues.

To launch an investigation, use the web UI or define a plan in YAML (see [examples/task\_underspecification.yaml](https://www.google.com/search?q=examples/task_underspecification.yaml)):

```bash
lunette investigate examples/task_underspecification.yaml
```

You can optionally pass `--limit N` to investigate only the first N matching trajectories.
