"""Run model for grouping trajectories from a single evaluation."""

from pydantic import BaseModel

from lunette.models.trajectory import Trajectory


class Run(BaseModel):
    """A collection of trajectories from a single evaluation run.

    This is the primary unit for uploading evaluation results. A run represents
    a single execution of `inspect eval` that produces multiple trajectory samples.
    All trajectories in a run share the same task and model.
    """

    id: str | None = None
    """Optional server-assigned run ID. If None, server generates a UUID. If provided, appends to existing run."""

    task: str
    """Task name for this run (e.g., 'math-eval', 'swe-bench')."""

    model: str
    """Model identifier used for this run (e.g., 'claude-sonnet-4', 'gpt-4')."""

    trajectories: list[Trajectory]
    """List of trajectory samples produced during this evaluation run."""
