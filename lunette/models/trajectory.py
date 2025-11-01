from typing import Any, Literal

from pydantic import BaseModel, Field

from lunette.models.messages import Message


class ScalarScore(BaseModel):
    """A scalar score for a trajectory."""

    value: float
    """The value of the score."""

    answer: str | None = None
    """Answer extracted from model output, if available."""

    explanation: str | None = None
    """Explanation of the score, if available."""

    metadata: dict[str, Any] = Field(default_factory=dict)
    """Additional metadata about the score."""


class Trajectory(BaseModel):
    """A single agent execution trace on an Inspect sample."""

    # sample-specific
    task: str
    sample: int | str  # Inspect sample ID
    model: str

    # trajectory-specific
    status: Literal[
        "started", "success", "cancelled", "error"
    ]  # note British spelling of "canceled" to match Inspect's `status` field
    messages: list[Message]
    scores: dict[str, ScalarScore] | None = None

    # metadata
    metadata: dict[str, Any] = Field(default_factory=dict)
    solution: str | None = None

    @property
    def score(self) -> ScalarScore | None:
        """Return the score for the trajectory, if there is exactly one score, otherwise `None`."""
        if self.scores is None or len(self.scores) != 1:
            return None
        [score] = self.scores.values()
        return score
