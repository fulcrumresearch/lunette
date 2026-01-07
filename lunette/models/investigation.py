from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel


class TrajectoryResult(BaseModel):
    """Result from analyzing a single trajectory."""

    original_trajectory_id: uuid.UUID
    investigation_trajectory_id: uuid.UUID
    result_key: str
    result_type: str | None
    data: dict[str, Any]


class InvestigationResults(BaseModel):
    """Results from an investigation run."""

    run_id: uuid.UUID
    source_run_id: uuid.UUID
    trajectory_count: int
    results: list[TrajectoryResult]
