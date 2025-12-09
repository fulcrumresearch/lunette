#!/usr/bin/env python3
"""
Test OpenAI tool call tracing.

Run with:
    uv run python examples/transcript/openai_tools.py

Requires OPENAI_API_KEY in environment or .env file.
"""

import asyncio
import json

from dotenv import load_dotenv
from openai import AsyncOpenAI

from lunette import LunetteTracer


load_dotenv()


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "multiply",
            "description": "Multiply two numbers",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "number", "description": "First number"},
                    "b": {"type": "number", "description": "Second number"},
                },
                "required": ["a", "b"],
            },
        },
    }
]


async def main():
    client = AsyncOpenAI()
    tracer = LunetteTracer(task="openai-tool-test", model="gpt-4o-mini")

    print(f"Task: {tracer.task}, Model: {tracer.model}\n")

    async with tracer.trajectory(sample="multiply-test"):
        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant. Use the multiply tool when asked to multiply numbers.",
            },
            {"role": "user", "content": "What is 137 times 177?"},
        ]

        # first call - should get tool call
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )

        assistant_msg = response.choices[0].message
        print(f"Assistant: {assistant_msg.content or '(tool call)'}")

        if assistant_msg.tool_calls:
            messages.append(assistant_msg.model_dump())

            for tool_call in assistant_msg.tool_calls:
                print(
                    f"Tool call: {tool_call.function.name}({tool_call.function.arguments})"
                )

                if tool_call.function.name == "multiply":
                    args = json.loads(tool_call.function.arguments)
                    result = args["a"] * args["b"]
                    print(f"Tool result: {result}")

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": str(result),
                        }
                    )

            # second call with tool result
            response2 = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
            )

            print(f"Final answer: {response2.choices[0].message.content}")

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

            content = msg.content[:60] + "..." if len(msg.content) > 60 else msg.content
            print(f"  #{msg.position} {msg.role.upper()}: {content}{tool_info}")

    await tracer.close()


if __name__ == "__main__":
    asyncio.run(main())
