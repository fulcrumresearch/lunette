#!/usr/bin/env python3
"""
Run an agent in a Lunette cloud sandbox with full environment capture.

This example shows how to:
1. Create a cloud sandbox with LunetteClient
2. Run an agent loop that executes code in the sandbox
3. Capture the full trajectory (transcript + environment)

Run with:
    uv run python examples/environment/custom_task.py

Requires ANTHROPIC_API_KEY and LUNETTE_API_KEY in environment or .env file.
"""

import asyncio

from anthropic import AsyncAnthropic
from dotenv import load_dotenv

from lunette import LunetteClient, LunetteTracer

load_dotenv()


# the problem for the agent to solve
PROBLEM = """
What is the sum of the first 100 prime numbers?
Write Python code to compute this.
When you have the answer, respond with ONLY the number, nothing else.
"""

EXPECTED_ANSWER = "24133"

SYSTEM_PROMPT = """
You are a coding assistant with access to a Python environment.
When asked to compute something, write Python code and execute it using the bash tool.
To run Python code, use: python3 -c 'your code here'
When you have the final answer, respond with ONLY the number, nothing else.
"""

TOOLS = [
    {
        "name": "bash",
        "description": "Execute a bash command in the sandbox environment",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The bash command to execute",
                }
            },
            "required": ["command"],
        },
    }
]


async def run_agent(sandbox, problem: str) -> str:
    """Run the agent loop until it produces a final answer."""
    client = AsyncAnthropic()
    messages = [{"role": "user", "content": problem}]

    while True:
        # call the model
        response = await client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        # check if we're done
        if response.stop_reason == "end_turn":
            # extract final text response
            for block in response.content:
                if block.type == "text":
                    return block.text
            return "No answer provided"

        # handle tool use
        if response.stop_reason == "tool_use":
            # add assistant message with tool use
            messages.append({"role": "assistant", "content": response.content})

            # process each tool call
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"Executing: {block.input.get('command', '')[:80]}...")

                    # execute in sandbox
                    result = await sandbox.aexec(block.input["command"])
                    output = (
                        result.stdout if result.success else f"Error: {result.stderr}"
                    )

                    print(f"Result: {output[:200]}...")

                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": output,
                        }
                    )

            # add tool results
            messages.append({"role": "user", "content": tool_results})


def score_answer(answer: str, expected: str) -> bool:
    """Check if the model's answer exactly matches the expected value."""
    return answer.strip() == expected


async def main():
    print("Creating sandbox...")

    # create tracer to capture the trajectory
    tracer = LunetteTracer(task="prime-sum", model="claude-haiku-4-5")

    async with LunetteClient() as client:
        # create a sandbox with Python
        sandbox = await client.create_sandbox({"image": "python:3.11-slim"})
        print(f"Sandbox created: {sandbox.sandbox_id}\n")

        print(f"Problem: {PROBLEM.strip()}")
        print(f"Expected answer: {EXPECTED_ANSWER}\n")
        print("=" * 50)

        # run the agent inside a trajectory context
        async with tracer.trajectory(sample="prime-sum-1"):
            answer = await run_agent(sandbox, PROBLEM)

        print("=" * 50)
        print(f"\nModel's answer: {answer}")

        # score the answer
        correct = score_answer(answer, EXPECTED_ANSWER)
        print(f"Score: {'✓ CORRECT' if correct else '✗ INCORRECT'}")

        # clean up
        await sandbox.destroy()

    # upload trajectory to Lunette
    result = await tracer.close()
    print(f"\nUploaded to Lunette: run_id={result['run_id']}")


if __name__ == "__main__":
    asyncio.run(main())
