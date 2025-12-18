"""Pydantic models for defining analysis plans."""

from __future__ import annotations

from abc import ABC
from typing import Annotated, Literal
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class AnalysisPlanBase(ABC, BaseModel):
    """Base class for analysis plans."""

    name: str | None = Field(None, description="Name for analysis plan")
    prompt: str | None = Field(None, description="Instructions for the analysis agent")

    # optional overrides (`None` = use defaults from `AnalysisConfig`)
    enable_sandbox: bool | None = Field(None, description="Enable sandbox access")
    enable_claim_evaluator: bool | None = Field(None, description="Enable claim evaluator")

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


class GradingPlan(AnalysisPlanBase):
    type: Literal["grading"] = "grading"
    score_name: str = Field(description="Name of the score to use for grading")


class BottleneckPlan(AnalysisPlanBase):
    type: Literal["bottleneck"] = "bottleneck"


AnalysisPlan = Annotated[AnalysisPlanBase, Field(discriminator="type")]
