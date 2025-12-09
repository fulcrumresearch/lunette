#!/usr/bin/env python3
"""
Test Anthropic tool call tracing.

Run with:
    uv run python examples/transcript/anthropic_tools.py

Requires ANTHROPIC_API_KEY in environment or .env file.
"""

import asyncio

from anthropic import AsyncAnthropic
from dotenv import load_dotenv

from lunette import LunetteTracer


load_dotenv()


TOOLS = [
    {
        "name": "multiply",
        "description": "Multiply two numbers",
        "input_schema": {
            "type": "object",
            "properties": {
                "a": {"type": "number", "description": "First number"},
                "b": {"type": "number", "description": "Second number"},
            },
            "required": ["a", "b"],
        },
    }
]


async def main():
    client = AsyncAnthropic()
    tracer = LunetteTracer(task="anthropic-tool-test", model="claude-haiku-4-5")

    print(f"Task: {tracer.task}, Model: {tracer.model}\n")

    async with tracer.trajectory(sample="multiply-test"):
        messages = [{"role": "user", "content": "What is 137 times 177?"}]

        # first call - should get tool use
        response = await client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1024,
            system="You are a helpful assistant. Use the multiply tool when asked to multiply numbers.",
            tools=TOOLS,
            messages=messages,
        )

        print(f"Stop reason: {response.stop_reason}")

        if response.stop_reason == "tool_use":
            # add assistant message
            messages.append({"role": "assistant", "content": response.content})

            # process tool calls
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"Tool call: {block.name}({block.input})")

                    if block.name == "multiply":
                        result = block.input["a"] * block.input["b"]
                        print(f"Tool result: {result}")

                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": str(result),
                            }
                        )

            messages.append({"role": "user", "content": tool_results})

            # second call with tool result
            response2 = await client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=1024,
                system="You are a helpful assistant. Use the multiply tool when asked to multiply numbers.",
                tools=TOOLS,
                messages=messages,
            )

            for block in response2.content:
                if block.type == "text":
                    print(f"Final answer: {block.text}")

    # show captured trajectory
    print("\n" + "=" * 50)
    print("CAPTURED TRAJECTORY")
    print("=" * 50)

    for traj in tracer._trajectories:
        print(f"\nSample: {traj.sample} ({len(traj.messages)} messages)")
        for msg in traj.messages:
            tool_info = ""
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                tool_info = f" [tool_calls: {[tc.function for tc in msg.tool_calls]}]"
            if hasattr(msg, "tool_call") and msg.tool_call:
                tool_info = f" [tool_call: {msg.tool_call.function}]"

            content_str = str(msg.content)
            content = content_str[:60] + "..." if len(content_str) > 60 else content_str
            print(f"  #{msg.position} {msg.role.upper()}: {content}{tool_info}")

    await tracer.close()


if __name__ == "__main__":
    asyncio.run(main())
