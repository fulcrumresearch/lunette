"""Context variables for async-safe state management in tracing."""

from contextvars import ContextVar


trajectory_context_id_var = ContextVar[str | None]("lunette_trajectory_context_id", default=None)
"""
Correlation ID for grouping OpenTelemetry spans by trajectory.

Set on entry to `tracer.trajectory()`, injected into spans, reset on exit.
Uses contextvar for async task isolation.
"""
