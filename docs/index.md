# Lunette

**Lunette captures your agent's trajectories and helps you understand what's happening.**

When your AI agent runs—whether it's solving coding tasks, answering questions, or using tools—Lunette records every step. You can then browse these trajectories, see where things went wrong, and launch *investigator agents* that analyze failures for you.

## Quick Start

The fastest path is with Inspect AI:

```bash
pip install lunette-sdk
inspect eval your_task.py --sandbox lunette
```

Your trajectories are now being captured with full environment access.

→ **[Getting Started Guide](getting-started.md)**

## How It Works

<div class="grid cards" markdown>

-   :material-record-circle: **Record**

    ---

    Capture trajectories as your agent runs. Use [tracing](tracing.md) for any LLM, or [run agents](running-agents.md) in Lunette sandboxes.

-   :material-magnify: **Investigate**

    ---

    Launch AI investigators that analyze your trajectories. They can read transcripts, search for patterns, and—with environment mode—execute commands in the original sandbox.

-   :material-bug: **Find Issues**

    ---

    Investigators create structured issues with evidence, confidence scores, and message references. Find test mis-specifications, environment problems, and agent failures.

</div>


## Links

- **[Web App](https://app.fulcrumresearch.ai)** — Browse trajectories and launch investigations
- **[Demo](https://demo.fulcrumresearch.ai)** — Try the platform
- **[GitHub](https://github.com/fulcrum-research/lunette)** — Source code
