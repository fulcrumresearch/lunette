# API Reference

## Core Classes

- [`LunetteClient`](client.md) — Main client for creating sandboxes and uploading runs
- [`LunetteTracer`](tracer.md) — Captures LLM calls as trajectories
- [`Sandbox`](sandbox.md) — Cloud sandbox for command execution

## Data Models

- [`Trajectory`](trajectory.md) — Captured agent execution trace
- [`Run`](trajectory.md#lunette.models.run.Run) — Collection of trajectories from an evaluation
- [Messages](trajectory.md#messages) — SystemMessage, UserMessage, AssistantMessage, ToolMessage

