#!/usr/bin/env python3
"""
Trace OpenAI API calls and upload transcripts to Lunette.

Run with:
    uv run python examples/transcript/openai.py

Requires OPENAI_API_KEY and LUNETTE_API_KEY in environment or .env file.
"""

import asyncio

from dotenv import load_dotenv
from openai import AsyncOpenAI

from lunette import LunetteTracer


load_dotenv()


async def main():
    client = AsyncOpenAI()

    # --8<-- [start:tracer_init]
    # create a tracer for this evaluation run
    tracer = LunetteTracer(task="my-eval", model="gpt-4o-mini")
    # --8<-- [end:tracer_init]

    # --8<-- [start:trajectory]
    # each sample gets its own trajectory context
    async with tracer.trajectory(sample="question-1"):
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "What is 2 + 2?"},
            ],
        )
        print(f"Answer: {response.choices[0].message.content}")
    # --8<-- [end:trajectory]

    # run another sample
    async with tracer.trajectory(sample="question-2"):
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "What is the capital of France?"},
            ],
        )
        print(f"Answer: {response.choices[0].message.content}")

    # --8<-- [start:upload]
    # upload trajectories to Lunette
    print("\n--- Debug info ---")
    print(f"Trajectories collected: {len(tracer._trajectories)}")
    for i, t in enumerate(tracer._trajectories):
        print(f"  [{i}] sample={t.sample}, messages={len(t.messages)}")

    # manually create client to inspect config
    from lunette import LunetteClient

    client = LunetteClient()
    print(f"Base URL: {client.base_url}")
    print(f"API key set: {bool(client.api_key)}")
    print(f"API key prefix: {client.api_key[:10]}..." if client.api_key else "None")

    result = await tracer.close()
    print(f"Uploaded run: {result['run_id']}")
    # --8<-- [end:upload]


if __name__ == "__main__":
    asyncio.run(main())
