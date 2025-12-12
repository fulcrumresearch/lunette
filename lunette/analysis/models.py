"""Pydantic models for defining analysis plans."""

from typing import Any
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class TrajectoryFilters(BaseModel):
    """Filter criteria for selecting trajectories to analyze.

    Simple dict-based filters - Cloud side will handle the filtering logic.
    Users can specify any fields from the Trajectory model.
    """

    filters: dict[str, Any] = Field(
        default_factory=dict, description="Filter criteria as key-value pairs"
    )

    def __init__(self, **data):
        """Allow passing filters directly as kwargs for convenience."""
        if "filters" not in data and data:
            # If no 'filters' key, treat all kwargs as filters
            super().__init__(filters=data)
        else:
            super().__init__(**data)


class AnalysisPlan(BaseModel):
    """Plan for running analysis on trajectories.

    Defines the analysis type, user prompt, trajectory filters, and optional overrides.
    """

    name: str | None = Field(
        None, description="Optional name for this analysis plan"
    )
    type: str = Field(
        "investigation",
        description="Analysis type: 'investigation', 'grading', 'bottleneck', etc.",
    )
    prompt: str = Field(
        "",
        description="User prompt/instructions for the analysis agent",
    )
    trajectory_filters: TrajectoryFilters = Field(
        default_factory=TrajectoryFilters,
        description="Criteria for selecting trajectories to analyze",
    )

    # Optional overrides (None = use defaults from AnalysisConfig)
    enable_sandbox: bool | None = Field(
        None,
        description="Override sandbox access (None = use type default)",
    )
    enable_claim_evaluator: bool | None = Field(
        None,
        description="Override claim evaluator access (None = use type default)",
    )

    # Type-specific params (e.g., score_name for grading)
    params: dict[str, Any] = Field(
        default_factory=dict,
        description="Type-specific parameters (e.g., {'score_name': 'quality'} for grading)",
    )

    def to_yaml(self) -> str:
        """Serialize plan to YAML string.

        Returns:
            YAML string representation of the plan
        """
        # Convert to dict, excluding None values for cleaner YAML
        data = self.model_dump(exclude_none=True, mode="python")
        return yaml.dump(data, sort_keys=False, default_flow_style=False)

    @classmethod
    def from_yaml(cls, yaml_str: str) -> "AnalysisPlan":
        """Load plan from YAML string.

        Args:
            yaml_str: YAML string representation of the plan

        Returns:
            AnalysisPlan instance

        Raises:
            yaml.YAMLError: If YAML is invalid
            pydantic.ValidationError: If data doesn't match schema
        """
        data = yaml.safe_load(yaml_str)
        return cls.model_validate(data)

    def to_yaml_file(self, path: str | Path) -> None:
        """Save plan to YAML file.

        Args:
            path: Path to save YAML file
        """
        Path(path).write_text(self.to_yaml(), encoding="utf-8")
