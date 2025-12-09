# Recording Trajectories

Lunette captures your agent's trajectories in two modes:

| Mode | What's captured | Best for |
|------|-----------------|----------|
| **[Environment](environment.md)** (recommended) | Conversation + sandbox environment | Code execution, file manipulation, debugging |
| **[Transcript](transcript.md)** | Conversation only | Quick integration, any LLM code |

## Why Environment Mode is Recommended

When you capture trajectories with environment access, our investigator agents can:

- **Re-run commands** in the original sandbox
- **Inspect files** the agent created or modified  
- **Reproduce errors** by executing the same commands
- **Test hypotheses** by running code in the environment

Without environment access, investigators can only analyze the transcript—they can see what the agent *said* it did, but they can't verify it or explore further.

!!! tip "Give investigators full access whenever possible"
    If your agent executes code or modifies files, use environment mode. The extra investigation capabilities are significant.

## Choosing a Mode

**Use Environment Mode if:**

- Your agent runs code (Python, bash, etc.)
- Your agent reads or writes files
- You're using Inspect AI
- You want the best investigation capabilities

**Use Transcript Mode if:**

- Your agent only has conversations (no tool use)
- You're quickly prototyping and don't need deep debugging
- You can't use our sandbox infrastructure

## Quick Comparison

<div class="grid cards" markdown>

-   :material-server: **[Environment Mode](environment.md)**

    ---

    Full sandbox access. Investigators can execute commands and inspect files.

    ```bash
    inspect eval task.py --sandbox lunette
    ```

-   :material-text-box-outline: **[Transcript Mode](transcript.md)**

    ---

    Conversation capture only. Lightweight, works with any LLM.

    ```python
    async with tracer.trajectory(sample=1):
        response = await client.chat(...)
    ```

</div>
