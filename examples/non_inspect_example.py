"""
Example: Using Lunette without Inspect AI

This example demonstrates how to use Lunette's sandbox API with a real LLM agent.
The agent receives a task, uses bash tools to interact with the sandbox, and the
trajectory is saved to Fulcrum for analysis.

This is useful for:
- Custom evaluation frameworks
- Integrating Lunette into existing agent systems
- Building your own agent evaluation tools
"""

import asyncio
import json
from anthropic import AsyncAnthropic
from lunette import LunetteClient
from lunette.models.run import Run
from lunette.models.trajectory import Trajectory
from lunette.models.messages import (
    SystemMessage,
    UserMessage,
    AssistantMessage,
    ToolMessage,
    ToolCall,
)
from lunette.models.trajectory import ScalarScore


# Define the bash tool schema for Claude
BASH_TOOL = {
    "name": "bash",
    "description": "Execute a bash command in the sandbox environment. Use this to interact with the system, run scripts, check files, etc.",
    "input_schema": {
        "type": "object",
        "properties": {"command": {"type": "string", "description": "The bash command to execute"}},
        "required": ["command"],
    },
}


async def main():
    """Run a real agent task using Lunette sandboxes and save the trajectory."""

    # Initialize clients
    anthropic = AsyncAnthropic()  # Requires ANTHROPIC_API_KEY env var

    async with LunetteClient() as lunette_client:
        print("Creating sandbox...")

        # Create a sandbox with Python installed
        service = {"image": "python:3.11-slim"}
        sandbox = await lunette_client.create_sandbox(service)
        print(f"Sandbox created: {sandbox}\n")

        # Start building our trajectory
        messages = []
        position = 0

        # System message
        system_prompt = """You are a helpful agent that can execute bash commands in a sandbox environment.
You have access to a bash tool to run commands. Use it to complete tasks accurately."""

        system_msg = SystemMessage(position=position, content=system_prompt)
        messages.append(system_msg)
        position += 1

        # User task
        task = """Create a Python script that prints the Fibonacci sequence up to n=10,
save it to /tmp/fibonacci.py, then execute it and show me the output."""

        print(f"Task: {task}\n")
        user_msg = UserMessage(position=position, content=task)
        messages.append(user_msg)
        position += 1

        # Agent loop
        claude_messages = [{"role": "user", "content": task}]
        max_turns = 10

        for turn in range(max_turns):
            print(f"--- Turn {turn + 1} ---")

            # Call Claude
            response = await anthropic.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=4096,
                system=system_prompt,
                messages=claude_messages,
                tools=[BASH_TOOL],
            )

            # Process response
            assistant_content = ""
            tool_calls = []

            for block in response.content:
                if block.type == "text":
                    assistant_content += block.text
                    print(f"Agent: {block.text}")
                elif block.type == "tool_use":
                    tool_call = ToolCall(id=block.id, function=block.name, arguments=block.input)
                    tool_calls.append(tool_call)
                    print(f"Tool call: {block.name}({json.dumps(block.input, indent=2)})")

            # Add assistant message to trajectory
            assistant_msg = AssistantMessage(
                position=position, content=assistant_content or "", tool_calls=tool_calls if tool_calls else None
            )
            messages.append(assistant_msg)
            position += 1

            # Add to Claude conversation
            claude_messages.append({"role": "assistant", "content": response.content})

            # If no tool calls, agent is done
            if not tool_calls:
                print("Agent finished.\n")
                break

            # Execute tool calls
            tool_results = []
            for tool_call in tool_calls:
                if tool_call.function == "bash":
                    command = tool_call.arguments["command"]
                    print(f"\nExecuting: {command}")

                    result = await sandbox.aexec(command)

                    output = f"Exit code: {result.exit_code}\n"
                    if result.stdout:
                        output += f"stdout:\n{result.stdout}"
                    if result.stderr:
                        output += f"\nstderr:\n{result.stderr}"

                    print(f"Result: {output[:200]}..." if len(output) > 200 else f"Result: {output}")

                    # Add tool message to trajectory
                    tool_msg = ToolMessage(position=position, content=output, tool_call=tool_call)
                    messages.append(tool_msg)
                    position += 1

                    # Add to Claude conversation
                    tool_results.append({"type": "tool_result", "tool_use_id": tool_call.id, "content": output})

            claude_messages.append({"role": "user", "content": tool_results})

            print()

        # Evaluate success - did the agent complete the task?
        # Check if the fibonacci script was created and executed
        verification = await sandbox.aexec("cat /tmp/fibonacci.py && python /tmp/fibonacci.py")
        task_succeeded = verification.success and "fibonacci" in verification.stdout.lower()

        print(f"\n{'=' * 50}")
        print(f"Task succeeded: {task_succeeded}")
        print(f"{'=' * 50}\n")

        # Create trajectory with score
        score = ScalarScore(
            value=1.0 if task_succeeded else 0.0,
            explanation="Successfully created and executed Fibonacci script"
            if task_succeeded
            else "Failed to complete task",
        )

        trajectory = Trajectory(
            sample="fibonacci_task_001",
            messages=messages,
            scores={"success": score},
            metadata={"task": "fibonacci_script", "turns": turn + 1},
        )

        # Create and save run
        run = Run(
            task="fibonacci-script-creation",
            model="claude-sonnet-4-5",
            trajectories=[trajectory],
        )

        print("Saving run to Fulcrum...")
        result = await lunette_client.save_run(run)
        print("✓ Run saved successfully!")
        print(f"  Run ID: {result['run_id']}")
        print(f"  Trajectory IDs: {result['trajectory_ids']}")

        # Clean up
        print("\nCleaning up sandbox...")
        await sandbox.destroy()
        print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
