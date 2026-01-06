#!/usr/bin/env python3
"""Run a custom analysis on a Lunette run and print results.

Usage:
    python scripts/run_analysis.py <run_id> [--type grading|issue_detection|bottleneck]

Example:
    python scripts/run_analysis.py abc123 --type grading
"""

import argparse
import asyncio

from dotenv import load_dotenv

from lunette import LunetteClient
from lunette.analysis import GradingPlan, IssueDetectionPlan, BottleneckPlan


load_dotenv()


async def main():
    parser = argparse.ArgumentParser(description="Run analysis on a Lunette run")
    parser.add_argument("run_id", help="ID of the run to analyze")
    parser.add_argument(
        "--type",
        choices=["grading", "issue_detection", "bottleneck"],
        default="grading",
        help="Type of analysis to run (default: grading)",
    )
    parser.add_argument("--limit", type=int, default=1, help="Max trajectories to analyze (default: 1)")
    parser.add_argument("--prompt", type=str, help="Custom prompt for the analysis")
    args = parser.parse_args()

    # Create the analysis plan based on type
    match args.type:
        case "grading":
            plan = GradingPlan(
                name="custom-grading",
                prompt=args.prompt
                or "Grade this trajectory on overall quality. Consider correctness, efficiency, and code style.",
            )
        case "issue_detection":
            plan = IssueDetectionPlan(
                name="custom-issue-detection",
                prompt=args.prompt or "Identify any issues in this trajectory.",
            )
        case "bottleneck":
            plan = BottleneckPlan(
                name="custom-bottleneck",
                prompt=args.prompt or "Identify the primary bottleneck in this trajectory.",
            )

    print(f"Running {args.type} analysis on run {args.run_id}...")
    print(f"Plan: {plan.name}")
    print(f"Prompt: {plan.prompt}")
    print(f"Limit: {args.limit} trajectory(ies)")
    print("-" * 50)

    async with LunetteClient() as client:
        # Run the investigation
        results = await client.investigate(
            run_id=args.run_id,
            plan=plan,
            limit=args.limit,
        )

        print("\nAnalysis complete!")
        print(f"Investigation run ID: {results.run_id}")
        print(f"Trajectories analyzed: {results.trajectory_count}")
        print("=" * 50)

        # Print each result
        for i, result in enumerate(results.results, 1):
            print(f"\n--- Result {i} ---")
            print(f"Original trajectory: {result.original_trajectory_id}")
            print(f"Investigation trajectory: {result.investigation_trajectory_id}")
            print(f"Result type: {result.result_type}")
            print("Data:")
            for key, value in result.data.items():
                if isinstance(value, str) and len(value) > 100:
                    # Truncate long strings
                    print(f"  {key}: {value[:100]}...")
                else:
                    print(f"  {key}: {value}")


if __name__ == "__main__":
    asyncio.run(main())
