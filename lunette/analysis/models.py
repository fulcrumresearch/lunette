"""Pydantic models for defining investigation plans."""

from typing import Any, Literal
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class InvestigationAgent(BaseModel):
    """Agent definition for investigating trajectories.

    The agent configuration (model, max_turns, etc.) is handled Cloud-side,
    so only name and prompt are needed in the SDK.
    """

    name: str = Field(..., description="Unique identifier for this agent")
    prompt: str = Field(
        ..., description="Investigation prompt/instructions for the agent"
    )


class TrajectoryFilters(BaseModel):
    """Filter criteria for selecting trajectories to investigate.

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
    """Top-level investigation plan definition.

    Defines agents to run and filters for selecting trajectories to investigate.
    """

    name: str | None = Field(
        None, description="Optional name for this investigation plan"
    )
    type: Literal["investigation"] = Field(
        "investigation",
        description="Plan type (currently only 'investigation' is supported)",
    )
    agents: list[InvestigationAgent] = Field(
        ...,
        description="List of agents to run on each matching trajectory",
        min_length=1,
    )
    trajectory_filters: TrajectoryFilters = Field(
        ..., description="Criteria for selecting trajectories to investigate"
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
