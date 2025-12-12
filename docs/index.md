# Lunette

**Lunette captures your agent's trajectories and helps you understand what's happening.**

When your AI agent runs—whether it's solving coding tasks, answering questions, or using tools—Lunette records every step. You can then browse these trajectories, see where things went wrong, and launch *investigator agents* that analyze failures for you.

## Why Lunette?

Issues in agent evals are pernicious. Even SWE-bench Verified, the most popular software engineering benchmark, has unsolvable tasks that are useless for understanding agent abilities.

Lunette uses investigator agents that probe the same environment your agents ran in. You run your agent in isolated Lunette sandboxes, then launch investigations to find both issues and performance bottlenecks. These agents read the trace, modify and run commands in the eval environment to test hypotheses, and report findings that get filtered for high-quality results.

There are two ways to use it:

- **With Inspect AI** — One-line integration if you're already using Inspect
- **With any LLM** — Wrap your API calls to capture trajectories

→ **[Get Started](quickstart.md)**

## How It Works

<div class="grid cards" markdown>

-   :material-record-circle: **Record**

    ---

    Capture trajectories as your agent runs. Use [tracing](tracing.md) for any LLM, or [run agents](running-agents.md) in Lunette sandboxes.

-   :material-magnify: **Investigate**

    ---

    Launch investigator agents that operate in parallel across trajectories. For each trajectory, an investigator reads the agent trace, modifies and runs commands in the eval environment to test hypotheses, and writes findings.

-   :material-bug: **Find Issues**

    ---

    Validator agents critique findings and filter for high-quality results. Browse structured issues with evidence, confidence scores, and message references. Find test mis-specifications, environment problems, and agent failures.

</div>


## Documentation

**Guides**

- **[Quickstart](quickstart.md)** — Get up and running with Lunette
- **[Tracing](tracing.md)** — Capture trajectories from any LLM
- **[Running Agents](running-agents.md)** — Run agents in Lunette sandboxes
- **[Issues and Judging](issues-and-judging.md)** — How investigator agents find problems and evaluate performance
- **[Investigations](investigating/index.md)** — Launch investigator agents to analyze trajectories

**API Reference**

- **[API Overview](api/index.md)** — Complete API documentation
- **[Client](api/client.md)** — LunetteClient API
- **[Tracer](api/tracer.md)** — LunetteTracer API
- **[Sandbox](api/sandbox.md)** — Sandbox API
- **[Trajectory](api/trajectory.md)** — Trajectory data models

## Links

- **[Web App](https://app.fulcrumresearch.ai)** — Browse trajectories and launch investigations
- **[Demo](https://demo.fulcrumresearch.ai)** — Try the platform
- **[GitHub](https://github.com/fulcrum-research/lunette)** — Source code
