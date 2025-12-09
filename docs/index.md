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

    Capture trajectories as your agent runs. Choose between [transcript mode](recording/transcript.md) (conversation only) or [environment mode](recording/environment.md) (conversation + sandbox).

-   :material-magnify: **Investigate**

    ---

    Launch AI investigators that analyze your trajectories. They can [read transcripts, search for patterns, and—with environment mode—execute commands](investigating/capabilities.md) in the original sandbox.

-   :material-bug: **Find Issues**

    ---

    Investigators create structured issues with evidence, confidence scores, and message references. Find test mis-specifications, environment problems, and agent failures.

</div>

## Recording Modes

Lunette can capture trajectories in two ways:

| Mode | What's Captured | Investigation Power |
|------|-----------------|---------------------|
| **[Environment](recording/environment.md)** | Conversation + sandbox | Full (can execute commands, read files) |
| **[Transcript](recording/transcript.md)** | Conversation only | Limited (transcript analysis only) |

!!! tip "Use Environment Mode"
    We strongly recommend environment mode whenever possible. Investigators are much more effective when they can access the original sandbox—they can verify agent claims, reproduce errors, and test hypotheses.

## Links

- **[Web App](https://app.fulcrumresearch.ai)** — Browse trajectories and launch investigations
- **[Demo](https://demo.fulcrumresearch.ai)** — Try the platform
- **[GitHub](https://github.com/fulcrum-research/lunette)** — Source code
