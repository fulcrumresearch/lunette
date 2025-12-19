"""Lunette CLI for trajectory analysis."""

import argparse
import asyncio
import importlib.resources
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

from inspect_ai.log import read_eval_log, resolve_sample_attachments

from lunette.analysis import parse_analysis_plan
from lunette.client import LunetteClient
from lunette.models.run import Run
from lunette.models.trajectory import Trajectory


def _get_preset_path(filename: str) -> str:
    """Get the path to a preset file bundled with the package."""
    return str(importlib.resources.files("lunette.presets").joinpath(filename))


def get_eval_presets() -> dict:
    """Build eval presets with resolved paths."""
    return {
        "swebench": {
            "task": "inspect_evals/swe_bench_verified_mini",
            "task_args": {
                "sandbox_config_template_file": _get_preset_path("swebench.yaml"),
                "sandbox_type": "lunette",
                "build_docker_images": "False",
            },
        },
    }


async def upload_command(
    log_file: Path,
    task_override: Optional[str] = None,
    model_override: Optional[str] = None,
) -> None:
    """Upload an Inspect eval log (.eval/.json) directly to Lunette."""

    log_path = log_file.expanduser()
    if not log_path.exists():
        raise FileNotFoundError(f"Log file not found: {log_file}")

    print(f"Reading {log_path}...")
    log = read_eval_log(str(log_path))
    samples = log.samples or []
    if not samples:
        raise ValueError(f"No samples found in {log_path}")

    trajectories: list[Trajectory] = []
    for sample in samples:
        hydrated = resolve_sample_attachments(sample, resolve_attachments=True)
        trajectories.append(Trajectory.from_inspect(hydrated))

    task = task_override or getattr(log.eval, "task", None)
    model = model_override or getattr(log.eval, "model", None)

    print(f"Found {len(trajectories)} trajectories for task='{task}' model='{model}'")

    run = Run(task=task, model=model, trajectories=trajectories)

    async with LunetteClient() as client:
        print("Uploading run to Lunette...")
        result = await client.save_run(run)
        print(f"Upload complete. Run ID: {result.get('run_id')}")


async def investigate_command(plan_file: Path, run_id: str, limit: int):
    """Run investigation command."""
    with open(plan_file, "r", encoding="utf-8") as f:
        yaml_content = f.read()

    plan = parse_analysis_plan(yaml_content)

    async with LunetteClient() as client:
        results = await client.investigate(run_id, plan, limit=limit)
        print(json.dumps(results.model_dump(), indent=2))


def eval_command(eval_args: list[str]) -> int:
    """Forward to inspect eval with lunette defaults.

    Supports preset configurations like 'swebench' that expand to full inspect eval commands.

    Examples:
        lunette eval swebench --model openai/gpt-4 --limit 5
        lunette eval my_task.py --sandbox lunette --model anthropic/claude-3-5-sonnet
    """
    presets = get_eval_presets()

    if not eval_args:
        print("Usage: lunette eval <task|preset> [inspect eval args...]")
        print(f"\nAvailable presets: {', '.join(presets.keys())}")
        print("\nExamples:")
        print("  lunette eval swebench --model openai/gpt-4 --limit 5")
        print("  lunette eval my_task.py --sandbox lunette --model anthropic/claude-3-5-sonnet")
        return 1

    # Use the same Python interpreter that's running lunette
    cmd = [sys.executable, "-m", "inspect_ai", "eval"]
    first_arg = eval_args[0]
    remaining_args = eval_args[1:]

    # Check if first arg is a preset
    if first_arg in presets:
        preset = presets[first_arg]
        cmd.append(preset["task"])

        # Add task args (-T key=value)
        for key, value in preset.get("task_args", {}).items():
            cmd.extend(["-T", f"{key}={value}"])
    else:
        # Not a preset, treat as task path
        cmd.append(first_arg)

    # Always add --sandbox lunette unless user overrides
    if "--sandbox" not in remaining_args:
        cmd.extend(["--sandbox", "lunette"])

    # Add all remaining arguments
    cmd.extend(remaining_args)

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    return result.returncode


def main():
    # Handle 'eval' command specially since it needs to forward all args to inspect
    if len(sys.argv) > 1 and sys.argv[1] == "eval":
        eval_args = sys.argv[2:]
        exit_code = eval_command(eval_args)
        sys.exit(exit_code)

    parser = argparse.ArgumentParser(description="Lunette CLI")
    subparsers = parser.add_subparsers(dest="command")

    # Eval command (documented but handled above)
    subparsers.add_parser(
        "eval",
        help="Run inspect eval with lunette presets (e.g., lunette eval swebench --model ...)",
    )

    investigate_parser = subparsers.add_parser("investigate", help="Launch an investigation plan")
    investigate_parser.add_argument("plan_file", type=Path, help="Path to investigation plan YAML")
    investigate_parser.add_argument("--run-id", required=True, help="ID of the run to investigate")
    investigate_parser.add_argument("--limit", type=int, default=10, help="Max trajectories to investigate")

    upload_parser = subparsers.add_parser("upload", help="Upload an Inspect .eval/.json log to Lunette")
    upload_parser.add_argument(
        "log_file",
        type=Path,
        help="Path to Inspect log (.eval or .json) created by `inspect eval --log`",
    )
    upload_parser.add_argument(
        "--task",
        dest="task",
        help="Override task name stored in the log (defaults to Inspect metadata)",
    )
    upload_parser.add_argument(
        "--model",
        dest="model",
        help="Override model name stored in the log (defaults to Inspect metadata)",
    )

    args = parser.parse_args()

    if args.command == "investigate":
        asyncio.run(investigate_command(args.plan_file, args.run_id, args.limit))
    elif args.command == "upload":
        asyncio.run(upload_command(args.log_file, args.task, args.model))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
