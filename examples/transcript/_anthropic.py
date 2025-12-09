#!/usr/bin/env python3
"""
Trace Anthropic API calls and upload transcripts to Lunette.

Run with:
    uv run python examples/transcript/anthropic.py

Requires ANTHROPIC_API_KEY and LUNETTE_API_KEY in environment or .env file.
"""

import asyncio

from anthropic import AsyncAnthropic
from dotenv import load_dotenv

from lunette import LunetteTracer

load_dotenv()


async def main():
    client = AsyncAnthropic()

    # create a tracer for this evaluation run
    tracer = LunetteTracer(task="my-eval", model="claude-haiku-4-5")

    # each sample gets its own trajectory context
    async with tracer.trajectory(sample="question-1"):
        response = await client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=256,
            system="You are a helpful assistant.",
            messages=[{"role": "user", "content": "What is 2 + 2?"}],
        )
        print(f"Answer: {response.content[0].text}")

    # run another sample
    async with tracer.trajectory(sample="question-2"):
        response = await client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=256,
            system="You are a helpful assistant.",
            messages=[{"role": "user", "content": "What is the capital of France?"}],
        )
        print(f"Answer: {response.content[0].text}")

    # upload trajectories to Lunette
    result = await tracer.close()
    print(f"Uploaded run: {result['run_id']}")


if __name__ == "__main__":
    asyncio.run(main())
