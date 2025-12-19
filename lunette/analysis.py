"""Pydantic models for defining analysis plans."""

from __future__ import annotations

from abc import ABC
from enum import Enum
from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import BaseModel, Field


# --- trajectory filters ---


class ScoreFilter(BaseModel):
    """Filter for score comparisons."""

    op: Literal["lt", "gt", "lte", "gte", "eq"] = Field(description="Comparison operator")
    value: float = Field(description="Value to compare against")


class TrajectoryFilters(BaseModel):
    """
    Filters for selecting which trajectories to analyze.

    All filters are optional. When multiple filters are specified, they are ANDed together.
    """

    task: str | None = Field(default=None, description="Filter by task name (via run.task)")
    sample: str | list[str] | None = Field(default=None, description="Filter by sample ID(s)")
    score: float | ScoreFilter | None = Field(default=None, description="Filter by score (exact value or comparison)")


# --- result schemas ---


class IssueRole(str, Enum):
    """Role/category of an issue."""

    AGENT = "agent"
    ENVIRONMENT = "environment"


class IssueResult(BaseModel):
    """Output schema for issue detection analysis."""

    name: str = Field(description="Short name/title for the issue")
    role: IssueRole = Field(description="Whether the issue is with the agent or environment")
    description: str = Field(description="Detailed description of the issue")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0")
    proof: str = Field(description="Evidence that this issue is real")
    message_ids: list[int] = Field(default_factory=list, description="Indices of messages related to this issue")


class BottleneckResult(BaseModel):
    """Output schema for bottleneck analysis."""

    bottleneck: str = Field(description="Description of the primary bottleneck")
    root_cause_message_id: int | None = Field(None, description="Index of the message where the root cause occurred")


class GradeResult(BaseModel):
    """Output schema for grading analysis."""

    score: float = Field(description="Numerical score between 0.0 and 1.0")
    explanation: str = Field(description="Explanation for the assigned score")


# --- analysis plans ---


class AnalysisPlanBase(ABC, BaseModel):
    """Base class for analysis plans."""

    name: str | None = Field(None, description="Name for analysis plan")
    prompt: str | None = Field(None, description="Instructions for the analysis agent")
    trajectory_filters: TrajectoryFilters = Field(
        default_factory=lambda: TrajectoryFilters(),
        description="Filters for selecting trajectories to analyze",
    )

    # optional overrides (`None` = use defaults from `AnalysisConfig`)
    enable_sandbox: bool | None = Field(None, description="Enable sandbox access")
    enable_claim_evaluator: bool | None = Field(None, description="Enable claim evaluator")

    # agent configuration
    model: str | None = Field(None, description="LLM model")
    max_turns: int | None = Field(None, description="Maximum number of turns")

    # result schema for structured output (None = no structured output, e.g. issue detection)
    result_schema: type[BaseModel] | None = Field(None, description="Pydantic model for structured result")

    @classmethod
    def from_yaml(cls, yaml_str: str) -> AnalysisPlan:
        """Load plan from YAML string.

        Args:
            yaml_str: YAML string representation of the plan

        Returns:
            AnalysisPlan instance (or specialized subclass)

        Raises:
            yaml.YAMLError: If YAML is invalid
            pydantic.ValidationError: If data doesn't match schema
        """
        data = yaml.safe_load(yaml_str)

        if not isinstance(data, dict):
            raise ValueError("YAML does not contain a valid analysis plan: not a dictionary")

        plan_type = data.get("type")
        if plan_type is None:
            raise ValueError("YAML does not contain a 'type' field")

        match plan_type:
            case "grading":
                return GradingPlan.model_validate(data)
            case "issue_detection":
                return IssueDetectionPlan.model_validate(data)
            case "bottleneck":
                return BottleneckPlan.model_validate(data)
            case _:
                raise ValueError(f"Unknown plan type: {plan_type}")

    def to_yaml(self) -> str:
        """
        Serialize plan to YAML string.

        Returns:
            YAML string representation of the plan
        """
        # convert to `dict`, excluding `None` values for cleaner YAML
        data_dict = self.model_dump(exclude_none=True, mode="python")
        return yaml.dump(data_dict)

    def to_yaml_file(self, path: str | Path) -> None:
        """
        Save plan to YAML file.

        Args:
            path: Path to save YAML file
        """
        Path(path).write_text(self.to_yaml(), encoding="utf-8")


class IssueDetectionPlan(AnalysisPlanBase):
    type: Literal["issue_detection"] = "issue_detection"
    result_schema: type[IssueResult] = IssueResult


class GradingPlan(AnalysisPlanBase):
    type: Literal["grading"] = "grading"
    score_name: str = Field(description="Name of the score to use for grading")
    result_schema: type[GradeResult] = GradeResult


class BottleneckPlan(AnalysisPlanBase):
    type: Literal["bottleneck"] = "bottleneck"
    result_schema: type[BottleneckResult] = BottleneckResult


AnalysisPlan = Annotated[AnalysisPlanBase, Field(discriminator="type")]
