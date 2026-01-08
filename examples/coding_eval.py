import asyncio
from anthropic import AsyncAnthropic
from lunette import LunetteClient, LunetteTracer

PROBLEMS = [
    {
        "id": "fizzbuzz",
        "prompt": "Write a function fizzbuzz(n) that returns a list of strings from 1 to n, where multiples of 3 are 'Fizz', multiples of 5 are 'Buzz', and multiples of both are 'FizzBuzz'. Save it to /workspace/fizzbuzz.py",
    },
    {
        "id": "palindrome",
        "prompt": "Write a function is_palindrome(s) that returns True if s is a palindrome (ignoring case and non-alphanumeric characters). Save it to /workspace/palindrome.py",
    },
    {
        "id": "merge-sort",
        "prompt": "Write a function merge_sort(arr) that sorts a list using merge sort. Save it to /workspace/merge_sort.py",
    },
]

TOOLS = [
    {
        "name": "bash",
        "description": "Execute a bash command",
        "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]},
    }
]


async def run_agent(sandbox, prompt: str) -> str:
    client = AsyncAnthropic()
    messages = [{"role": "user", "content": prompt}]

    for _ in range(10):  # max turns
        response = await client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2048,
            system="You are a Python developer. Write clean, well-documented code.",
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            return "done"

        messages.append({"role": "assistant", "content": response.content})
        tool_results = []

        for block in response.content:
            if block.type == "tool_use":
                result = await sandbox.aexec(block.input["command"])
                output = result.stdout if result.success else f"Error: {result.stderr}"
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": output})

        messages.append({"role": "user", "content": tool_results})

    return "max_turns"


async def main():
    tracer = LunetteTracer(task="coding-eval", model="claude-sonnet-4")

    async with LunetteClient() as client:
        sandbox = await client.create_sandbox({"image": "python:3.11-slim"})

        for problem in PROBLEMS:
            print(f"Running: {problem['id']}")
            async with tracer.trajectory(sample=problem["id"], sandbox_id=sandbox.sandbox_id):
                await run_agent(sandbox, problem["prompt"])

        await sandbox.destroy()

    result = await tracer.close()
    print(f"Run ID: {result['run_id']}")


asyncio.run(main())
