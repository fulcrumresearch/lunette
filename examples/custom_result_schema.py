"""
Example: Custom Result Schema for Investigations

This example demonstrates how to define a custom result schema for investigations.
Users can create AnalysisPlan subclasses with custom Pydantic models as result schemas,
and the investigation agent will output data matching that schema.

This is useful for:
- Extracting specific features from trajectories
- Custom grading dimensions
- Structured analysis with domain-specific fields

Usage:
    # Set your API key and server URL
    export LUNETTE_API_KEY="your-api-key"
    export LUNETTE_BASE_URL="http://localhost:8000/api"  # or your server URL

    # Run the example
    cd lunette
    uv run python examples/custom_result_schema.py
"""

import asyncio
from typing import ClassVar, Literal

from pydantic import BaseModel, Field

from lunette import LunetteClient
from lunette.analysis import AnalysisPlanBase, TrajectoryFilters
from lunette.models.messages import AssistantMessage, SystemMessage, ToolCall, ToolMessage, UserMessage
from lunette.models.run import Run
from lunette.models.trajectory import ScalarScore, Trajectory


# =============================================================================
# Step 1: Define your custom result schema as a Pydantic model
# =============================================================================


class TaskDifficultyFeatures(BaseModel):
    """Custom result schema for analyzing task difficulty.

    This schema defines the exact structure of the output you want from
    the investigation agent. The agent will be instructed to output data
    matching this schema.
    """

    complexity_score: float = Field(description="Overall task complexity from 0.0 (trivial) to 1.0 (extremely complex)")
    reasoning_steps: int = Field(description="Estimated number of distinct reasoning steps required to solve the task")
    required_skills: list[str] = Field(
        description="List of skills/knowledge areas needed (e.g., 'file manipulation', 'API usage', 'debugging')"
    )
    potential_pitfalls: list[str] = Field(description="Common mistakes or challenges an agent might face")
    explanation: str = Field(description="Brief explanation of the difficulty assessment")


# =============================================================================
# Step 2: Create a custom AnalysisPlan subclass with your schema
# =============================================================================


class TaskDifficultyPlan(AnalysisPlanBase):
    """Custom analysis plan for extracting task difficulty features.

    The key is setting `result_schema` as a ClassVar pointing to your Pydantic model.
    The base class automatically handles serialization - no need to override model_dump().
    """

    kind: Literal["grading"] = "grading"  # use existing analysis type for the prompt template
    result_schema: ClassVar[type[TaskDifficultyFeatures]] = TaskDifficultyFeatures


# =============================================================================
# Step 3: Create a sample trajectory to analyze
# =============================================================================


def create_sample_trajectory() -> Trajectory:
    """Create a sample trajectory for demonstration.

    In a real scenario, this would come from an actual agent run.
    Here we create a mock trajectory that simulates an agent attempting
    a file manipulation task.
    """
    messages = [
        SystemMessage(
            position=0,
            content="You are a helpful assistant that can execute bash commands to complete tasks.",
        ),
        UserMessage(
            position=1,
            content="""Task: Find all Python files in /home/user/project that contain the word 'TODO',
count the total number of TODO comments across all files, and create a summary report
at /tmp/todo_report.txt listing each file and its TODO count.""",
        ),
        AssistantMessage(
            position=2,
            content="I'll help you find and summarize TODO comments. Let me start by searching for Python files with TODOs.",
            tool_calls=[
                ToolCall(
                    id="call_1",
                    function="bash",
                    arguments={"command": "find /home/user/project -name '*.py' -exec grep -l 'TODO' {} \\;"},
                )
            ],
        ),
        ToolMessage(
            position=3,
            content="/home/user/project/main.py\n/home/user/project/utils/helpers.py\n/home/user/project/tests/test_main.py",
            tool_call=ToolCall(
                id="call_1",
                function="bash",
                arguments={"command": "find /home/user/project -name '*.py' -exec grep -l 'TODO' {} \\;"},
            ),
        ),
        AssistantMessage(
            position=4,
            content="Found 3 files with TODOs. Now let me count the TODOs in each file.",
            tool_calls=[
                ToolCall(
                    id="call_2",
                    function="bash",
                    arguments={
                        "command": "grep -c 'TODO' /home/user/project/main.py /home/user/project/utils/helpers.py /home/user/project/tests/test_main.py"
                    },
                )
            ],
        ),
        ToolMessage(
            position=5,
            content="/home/user/project/main.py:3\n/home/user/project/utils/helpers.py:5\n/home/user/project/tests/test_main.py:2",
            tool_call=ToolCall(
                id="call_2",
                function="bash",
                arguments={
                    "command": "grep -c 'TODO' /home/user/project/main.py /home/user/project/utils/helpers.py /home/user/project/tests/test_main.py"
                },
            ),
        ),
        AssistantMessage(
            position=6,
            content="I have the counts. Let me create the summary report.",
            tool_calls=[
                ToolCall(
                    id="call_3",
                    function="bash",
                    arguments={
                        "command": """cat > /tmp/todo_report.txt << 'EOF'
TODO Summary Report
==================

File: /home/user/project/main.py
TODO count: 3

File: /home/user/project/utils/helpers.py
TODO count: 5

File: /home/user/project/tests/test_main.py
TODO count: 2

Total TODOs: 10
EOF"""
                    },
                )
            ],
        ),
        ToolMessage(
            position=7,
            content="",
            tool_call=ToolCall(
                id="call_3",
                function="bash",
                arguments={"command": "cat > /tmp/todo_report.txt << 'EOF'\n..."},
            ),
        ),
        AssistantMessage(
            position=8,
            content="Done! I've created the TODO summary report at /tmp/todo_report.txt. The report shows:\n- main.py: 3 TODOs\n- utils/helpers.py: 5 TODOs\n- test_main.py: 2 TODOs\n- Total: 10 TODOs across 3 files",
        ),
    ]

    return Trajectory(
        sample="todo_search_001",
        messages=messages,
        scores={
            "success": ScalarScore(
                value=1.0,
                explanation="Successfully found all TODOs and created the summary report",
            )
        },
        metadata={
            "task_type": "file_search_and_report",
            "complexity": "medium",
        },
    )


# =============================================================================
# Step 4: Run the investigation with your custom plan
# =============================================================================


async def main():
    """Run the end-to-end example."""

    print("=" * 70)
    print("Custom Result Schema Example")
    print("=" * 70)
    print()

    async with LunetteClient() as client:
        # Create and save a sample run
        print("Step 1: Creating sample trajectory...")
        trajectory = create_sample_trajectory()

        run = Run(
            task="todo-search-task",
            model="claude-sonnet-4-mock",
            trajectories=[trajectory],
        )

        result = await client.save_run(run)
        run_id = result["run_id"]
        print(f"  ✓ Run saved: {run_id}")
        print(f"  ✓ Trajectory ID: {result['trajectory_ids'][0]}")
        print()

        # Create custom analysis plan
        print("Step 2: Creating custom analysis plan...")
        plan = TaskDifficultyPlan(
            name="task-difficulty-analysis",
            prompt="""Analyze the difficulty of this task based on the trajectory.

Consider:
1. How many distinct steps were required?
2. What skills/knowledge did the agent need?
3. What could have gone wrong?
4. How complex was the overall task?

Provide your assessment using the structured output format.""",
            trajectory_filters=TrajectoryFilters(),  # no filters - analyze all
        )

        # Verify the schema is included
        print(f"  ✓ Plan type: {type(plan).__name__}")
        print(f"  ✓ Result schema: {plan.result_schema.__name__}")
        print(f"  ✓ Schema fields: {list(plan.result_schema.model_fields.keys())}")
        print()

        # Run the investigation
        print("Step 3: Running investigation...")
        print("  (This may take a minute as an agent analyzes the trajectory)")
        print()

        try:
            results = await client.investigate(
                run_id=run_id,
                plan=plan,
                limit=1,
            )

            print("Step 4: Results")
            print("-" * 50)
            print(f"Investigation run ID: {results.run_id}")
            print(f"Trajectories analyzed: {results.trajectory_count}")
            print()

            if results.results:
                for r in results.results:
                    print(f"Trajectory: {r.original_trajectory_id}")
                    print(f"Result type: {r.result_type}")
                    print()
                    print("Custom output data:")
                    data = r.data
                    if "complexity_score" in data:
                        print(f"  complexity_score: {data['complexity_score']}")
                    if "reasoning_steps" in data:
                        print(f"  reasoning_steps: {data['reasoning_steps']}")
                    if "required_skills" in data:
                        print(f"  required_skills: {data['required_skills']}")
                    if "potential_pitfalls" in data:
                        print(f"  potential_pitfalls: {data['potential_pitfalls']}")
                    if "explanation" in data:
                        print(f"  explanation: {data['explanation'][:200]}...")
            else:
                print("No results returned (agent may not have submitted output)")

        except Exception as e:
            print(f"Investigation failed: {e}")
            print()
            print("Note: This example requires a running Lunette server with")
            print("investigation agents enabled (ANTHROPIC_API_KEY must be set on server)")

        print()
        print("=" * 70)
        print("Example complete!")
        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
