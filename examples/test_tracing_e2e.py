#!/usr/bin/env python3
"""
Simple end-to-end test script for the tracing module.

Run with:
    uv run python examples/test_tracing_e2e.py

Expects OPENAI_API_KEY in .env file or environment.

This makes real OpenAI calls and captures them as trajectories,
but skips the upload to the Lunette server.
"""

import asyncio
import json

from dotenv import load_dotenv
from openai import AsyncOpenAI

from lunette.tracing import LunetteTracer


load_dotenv()


async def main():
    client = AsyncOpenAI()
    tracer = LunetteTracer(task="test-math", model="gpt-5-nano")

    print(f"Run ID: {tracer.run_id}\n")

    # trajectory 1: simple question
    print("=" * 50)
    print("Trajectory 1: Simple math question")
    print("=" * 50)

    async with tracer.trajectory(sample=1):
        response = await client.chat.completions.create(
            model="gpt-5-nano",
            messages=[
                {"role": "system", "content": "You are a helpful math tutor."},
                {"role": "user", "content": "What is 2 + 2?"},
            ],
        )
        print(f"Response: {response.choices[0].message.content}\n")

    # trajectory 2: multi-turn conversation
    print("=" * 50)
    print("Trajectory 2: Multi-turn conversation")
    print("=" * 50)

    async with tracer.trajectory(sample=2):
        # first turn
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What's the capital of France?"},
        ]
        response1 = await client.chat.completions.create(
            model="gpt-5-nano",
            messages=messages,
        )
        print(f"Turn 1: {response1.choices[0].message.content}")

        # second turn
        messages.append(
            {"role": "assistant", "content": response1.choices[0].message.content}
        )
        messages.append({"role": "user", "content": "What's its population?"})

        response2 = await client.chat.completions.create(
            model="gpt-5-nano",
            messages=messages,
        )
        print(f"Turn 2: {response2.choices[0].message.content}\n")

    # print captured trajectories (without uploading)
    print("=" * 50)
    print("CAPTURED TRAJECTORIES")
    print("=" * 50)

    for traj in tracer._trajectories:
        print(
            f"\n--- Trajectory sample={traj.sample} ({len(traj.messages)} messages) ---"
        )
        for msg in traj.messages:
            role = msg.role
            content = (
                msg.content[:80] + "..." if len(str(msg.content)) > 80 else msg.content
            )
            print(f"  [{msg.position}] {role}: {content}")

    # show what would be uploaded
    print("\n" + "=" * 50)
    print("RUN PAYLOAD (what would be uploaded)")
    print("=" * 50)

    from lunette.models.run import Run

    run = Run(
        id=tracer.run_id,
        task=tracer.task,
        model=tracer.model,
        trajectories=tracer._trajectories,
    )
    print(
        json.dumps(run.model_dump(), indent=2, default=str, ensure_ascii=False)[:2000]
        + "\n..."
    )

    print("\n✓ Tracing works! (skipped actual upload)")


if __name__ == "__main__":
    asyncio.run(main())
