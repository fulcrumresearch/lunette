"""Lunette CLI for trajectory analysis."""

import asyncio
import json
import argparse
from pathlib import Path

from lunette.client import LunetteClient


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

    investigate_parser = subparsers.add_parser("investigate")
    investigate_parser.add_argument("plan_file", type=Path)
    investigate_parser.add_argument("--limit", type=int, default=10)

    args = parser.parse_args()

    if args.command == "investigate":
        asyncio.run(investigate_command(args.plan_file, args.limit))


if __name__ == "__main__":
    main()
