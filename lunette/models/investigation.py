from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class TrajectoryResult(BaseModel):
    """Result from analyzing a single trajectory."""

    original_trajectory_id: str
    investigation_trajectory_id: str
    result_key: str
    result_type: str | None
    data: dict[str, Any]


class InvestigationResults(BaseModel):
    """Results from an investigation run."""

    run_id: str
    source_run_id: str
    trajectory_count: int
    results: list[TrajectoryResult]
