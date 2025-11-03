from __future__ import annotations

from inspect_ai import Task, task
from inspect_ai.dataset import Sample
from inspect_ai.util import sandbox
from inspect_ai.solver import system_message
from inspect_ai.scorer import Score, scorer, accuracy  # simple, no-LLM return type


@scorer(metrics=[accuracy()])
def lunette_smoke():
    async def score(state, target):
        sb = sandbox()

        cmds = [
            "echo 'hello from lunette'",
            "whoami",
            "pwd",
            "ls -la",
        ]

        outputs = []
        for c in cmds:
            r = await sb.exec(["bash", "-lc", c])
            outputs.append(f"$ {c}\n{r.stdout}{r.stderr}")

        # write + read a file
        await sb.write_file("/workspace/lunette_ok.txt", "it works\n")
        got = await sb.read_file("/workspace/lunette_ok.txt")
        outputs.append(f"readback: {got!r}")

        # show uname as a final check
        r = await sb.exec(["bash", "-lc", "uname -a"])
        outputs.append(f"$ uname -a\n{r.stdout}{r.stderr}")

        return Score(value=1)

    return score


@task
def test_lunette_docker():
    """
    Smoke test using your lunette-docker provider. Builds the Dockerfile in this folder,
    starts the container, and runs the smoke solver inside it.
    """
    return Task(
        dataset=[Sample(input="smoke")],
        sandbox="lunette",
        solver=system_message("lll"),
        scorer=lunette_smoke(),
    )
