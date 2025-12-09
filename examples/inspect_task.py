#!/usr/bin/env python3
"""
Inspect AI task with Lunette sandbox — agent writes and runs Python code.

Run with:
    inspect eval examples/inspect_task.py --sandbox lunette --model anthropic/claude-haiku-4-5
"""

from inspect_ai import Task, task
from inspect_ai.dataset import Sample
from inspect_ai.scorer import match
from inspect_ai.solver import generate, system_message, use_tools
from inspect_ai.tool import bash


@task
def python_coding():
    """Agent writes Python code to solve problems, runs it, and reports the answer."""
    return Task(
        dataset=[
            Sample(
                input="What is the sum of the first 100 prime numbers? Write Python code to compute this and report ONLY the final number.",
                target="24133",
            ),
            Sample(
                input="What is 2^100? Write Python code to compute this and report ONLY the final number.",
                target="1267650600228229401496703205376",
            ),
            Sample(
                input="How many digits does 1000! (factorial) have? Write Python code to compute this and report ONLY the final number.",
                target="2568",
            ),
        ],
        solver=[
            system_message(
                "You are a coding assistant. Write Python code to solve the problem, "
                "execute it using bash (python3 -c '...'), and report ONLY the final numeric answer."
            ),
            use_tools([bash()]),
            generate(),
        ],
        scorer=match(numeric=True),
        sandbox="lunette",
    )
