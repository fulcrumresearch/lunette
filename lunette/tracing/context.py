"""Context variables for async-safe state management in tracing."""

from contextvars import ContextVar

# tracks the current trajectory ID for async propagation
# run_id is an instance variable on LunetteTracer (no contextvar needed)
trajectory_id_var: ContextVar[str | None] = ContextVar(
    "lunette_trajectory_id", default=None
)
