"""Run a programmatic investigation on a Lunette run."""

import asyncio
import os

from lunette import LunetteClient
from lunette.analysis import GradingPlan

# replace with your run ID (or set RUN_ID env var)
RUN_ID = os.environ.get("RUN_ID", "your-run-id")


async def main():
    async with LunetteClient() as client:
        results = await client.investigate(
            run_id=RUN_ID,
            plan=GradingPlan(
                name="quality-check",
                prompt="Grade this trajectory on code quality and correctness.",
            ),
            limit=1,
        )

        print(f"Investigation run: {results.run_id}")
        print(f"Analyzed {results.trajectory_count} trajectory(s)\n")

        for result in results.results:
            print(f"Trajectory: {result.original_trajectory_id}")
            print(f"Score: {result.data['score']}")
            print(f"Explanation: {result.data['explanation']}")


if __name__ == "__main__":
    asyncio.run(main())
