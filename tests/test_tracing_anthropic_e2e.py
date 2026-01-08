#!/usr/bin/env python3
"""
End-to-end test script for Anthropic tracing.

Run with:
    uv run python tests/test_tracing_anthropic_e2e.py

Expects ANTHROPIC_API_KEY in .env file or environment.

This makes real Anthropic calls and captures them as trajectories,
but skips the upload to the Lunette server.
"""

import asyncio
import json

from anthropic import AsyncAnthropic
from dotenv import load_dotenv

from lunette.models.messages import Image
from lunette.models.run import Run
from lunette.tracing import LunetteTracer

load_dotenv()

# small 10x10 red square PNG for testing (base64 encoded)
TEST_IMAGE_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAIAAAACUFjqAAAAEklEQVR4nGP8z4APMOGVHbHSAEEsAROxCnMTAAAAAElFTkSuQmCC"
)


async def main():
    client = AsyncAnthropic()
    tracer = LunetteTracer(task="test-anthropic", model="claude-haiku-4-5")

    print(f"Run ID: {tracer.run_id}\n")

    # trajectory 1: simple question
    print("=" * 50)
    print("Trajectory 1: Simple question")
    print("=" * 50)

    async with tracer.trajectory(sample=1):
        response = await client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=256,
            system="You are a helpful assistant.",
            messages=[
                {"role": "user", "content": "What is 2 + 2?"},
            ],
        )
        print(f"Response: {response.content[0].text}\n")

    # trajectory 2: multi-turn conversation
    print("=" * 50)
    print("Trajectory 2: Multi-turn conversation")
    print("=" * 50)

    async with tracer.trajectory(sample=2):
        # first turn
        messages = [
            {"role": "user", "content": "What's the capital of France?"},
        ]
        response1 = await client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=256,
            system="You are a helpful assistant.",
            messages=messages,
        )
        assistant_text = response1.content[0].text
        print(f"Turn 1: {assistant_text}")

        # second turn
        messages.append({"role": "assistant", "content": assistant_text})
        messages.append({"role": "user", "content": "What's its population?"})

        response2 = await client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=256,
            system="You are a helpful assistant.",
            messages=messages,
        )
        print(f"Turn 2: {response2.content[0].text}\n")

    # trajectory 3: image input (multimodal)
    print("=" * 50)
    print("Trajectory 3: Image input (multimodal)")
    print("=" * 50)

    async with tracer.trajectory(sample=3):
        response = await client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=50,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "What color is this image? Reply in one word.",
                        },
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": TEST_IMAGE_BASE64,
                            },
                        },
                    ],
                }
            ],
        )
        print(f"Response: {response.content[0].text}\n")

    # verify image was captured
    image_traj = tracer._trajectories[-1]
    user_msg = image_traj.messages[0]
    assert isinstance(user_msg.content, list), "Expected list content for multimodal message"
    content_types = [type(c).__name__ for c in user_msg.content]
    print(f"Captured content types: {content_types}")
    assert any(isinstance(c, Image) for c in user_msg.content), "Expected Image in content"
    print("✓ Image content captured correctly!\n")

    # print captured trajectories (without uploading)
    print("=" * 50)
    print("CAPTURED TRAJECTORIES")
    print("=" * 50)

    for traj in tracer._trajectories:
        print(f"\n--- Trajectory sample={traj.sample} ({len(traj.messages)} messages) ---")
        for msg in traj.messages:
            role = msg.role
            # handle both string and list content
            if isinstance(msg.content, list):
                content_str = f"[{len(msg.content)} content blocks]"
            else:
                content_str = msg.content[:80] + "..." if len(msg.content) > 80 else msg.content
            print(f"  [{msg.position}] {role}: {content_str}")

    # show what would be uploaded
    print("\n" + "=" * 50)
    print("RUN PAYLOAD (what would be uploaded)")
    print("=" * 50)

    run = Run(
        id=tracer.run_id,
        task=tracer.task,
        model=tracer.model,
        trajectories=tracer._trajectories,
    )
    print(json.dumps(run.model_dump(), indent=2, default=str, ensure_ascii=False)[:2000] + "\n...")

    print("\n✓ Anthropic tracing works! (skipped actual upload)")


if __name__ == "__main__":
    asyncio.run(main())
