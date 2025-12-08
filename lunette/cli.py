"""Lunette CLI for trajectory analysis."""

import argparse
import asyncio
import json
from pathlib import Path
from typing import Optional

from inspect_ai.log import read_eval_log, resolve_sample_attachments

from lunette.client import LunetteClient
from lunette.models.run import Run
from lunette.models.trajectory import Trajectory


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

    if not task:
        raise ValueError(
            "Unable to determine task from log; provide one with '--task TASK_NAME'."
        )
    if not model:
        raise ValueError(
            "Unable to determine model from log; provide one with '--model MODEL_NAME'."
        )

    print(f"Found {len(trajectories)} trajectories for task='{task}' model='{model}'")

    run = Run(task=task, model=model, trajectories=trajectories)

    async with LunetteClient() as client:
        print("Uploading run to Lunette...")
        result = await client.save_run(run)
        print(f"Upload complete. Run ID: {result.get('run_id')}")


async def investigate_command(plan_file: Path, limit: int):
    """Run investigation command."""
    with open(plan_file, "r", encoding="utf-8") as f:
        plan = f.read()

    async with LunetteClient() as client:
        result = await client.launch_investigation(plan, limit)
        print(json.dumps(result, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Lunette CLI")
    subparsers = parser.add_subparsers(dest="command")

    investigate_parser = subparsers.add_parser(
        "investigate", help="Launch an investigation plan"
    )
    investigate_parser.add_argument("plan_file", type=Path)
    investigate_parser.add_argument("--limit", type=int, default=10)

    upload_parser = subparsers.add_parser(
        "upload", help="Upload an Inspect .eval/.json log to Lunette"
    )
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
        asyncio.run(investigate_command(args.plan_file, args.limit))
    elif args.command == "upload":
        asyncio.run(upload_command(args.log_file, args.task, args.model))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
