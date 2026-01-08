#!/usr/bin/env python3
"""
Simple end-to-end test script for the tracing module.

Run with:
    uv run python tests/test_tracing_openai_e2e.py

Expects OPENAI_API_KEY in .env file or environment.

This makes real OpenAI calls and captures them as trajectories,
but skips the upload to the Lunette server.
"""

import asyncio
import json

from dotenv import load_dotenv
from openai import AsyncOpenAI

from lunette.models.run import Run
from lunette.tracing import LunetteTracer


load_dotenv()

# small 10x10 red square PNG for testing (base64 encoded)
TEST_IMAGE_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAIAAAACUFjqAAAAEklEQVR4nGP8z4APMOGVHbHSAEEsAROxCnMTAAAAAElFTkSuQmCC"
)


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
        messages.append({"role": "assistant", "content": response1.choices[0].message.content})
        messages.append({"role": "user", "content": "What's its population?"})

        response2 = await client.chat.completions.create(
            model="gpt-5-nano",
            messages=messages,
        )
        print(f"Turn 2: {response2.choices[0].message.content}\n")

    # trajectory 3: image input (multimodal)
    # NOTE: The OpenAI OTel instrumentation does NOT capture multimodal content.
    # The API call works, but the image content is not recorded in the span.
    # This is a known limitation of opentelemetry-instrumentation-openai.
    print("=" * 50)
    print("Trajectory 3: Image input (multimodal)")
    print("=" * 50)

    async with tracer.trajectory(sample=3):
        response = await client.chat.completions.create(
            model="gpt-4o-mini",  # need a vision-capable model
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "What color is this image? Reply in one word.",
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{TEST_IMAGE_BASE64}",
                                "detail": "low",
                            },
                        },
                    ],
                }
            ],
            max_tokens=50,
        )
        print(f"Response: {response.choices[0].message.content}")

    # check what was captured (OpenAI instrumentation doesn't capture multimodal content)
    image_traj = tracer._trajectories[-1]
    user_msg = image_traj.messages[0]
    print(f"Content type captured: {type(user_msg.content).__name__}")
    print(f"Content: {repr(user_msg.content)[:100]}")
    print("⚠ OpenAI instrumentation does not capture multimodal content (known limitation)\n")

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

    print("\n✓ Tracing works! (skipped actual upload)")


if __name__ == "__main__":
    asyncio.run(main())
