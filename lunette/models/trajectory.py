from __future__ import annotations

from typing import Any


from pydantic import BaseModel, Field, computed_field

from inspect_ai.log import EvalSample
from inspect_ai.model import (
    ChatMessageAssistant,
    ChatMessageSystem,
    ChatMessageUser,
    ChatMessageTool,
)
from inspect_ai.scorer import Score

from lunette.models.messages import (
    AssistantMessage,
    Message,
    SystemMessage,
    ToolCall,
    ToolMessage,
    UserMessage,
)


class ScalarScore(BaseModel):
    """A scalar score for a trajectory."""

    value: float
    """The value of the score."""

    answer: str | None = None
    """Answer extracted from model output, if available."""

    explanation: str | None = None
    """Explanation of the score, if available."""

    metadata: dict[str, Any] | None = None
    """Additional metadata about the score."""

    @classmethod
    def from_inspect(cls, score: Score) -> ScalarScore:
        """Convert an Inspect AI `Score` to a `ScalarScore`."""

        try:
            value: str | int | float | bool = score._as_scalar()
        except ValueError:
            raise ValueError("Score is not a scalar")

        match value:
            case "C":
                value = 1.0
            case "P":
                value = 0.5
            case "I":
                value = 0.0
            case str():
                try:
                    value = float(value)
                except ValueError:
                    raise ValueError(f"Invalid score value string '{value}'")
            case int() | float() | bool():
                value = float(value)

        return cls(
            value=value,
            answer=score.answer,
            explanation=score.explanation,
            metadata=score.metadata,
        )


class Trajectory(BaseModel):
    """A single agent execution trace on an Inspect sample.

    Trajectories are grouped into Runs, which provide task and model context.
    A trajectory represents one sample's execution trace.
    """

    sample: int | str
    """Inspect sample ID - identifies which sample this trajectory is for."""

    messages: list[Message]
    """Sequence of messages (System, User, Assistant, Tool) in this execution."""

    scores: dict[str, ScalarScore] | None = None
    """Multi-metric scores for this trajectory, if available."""

    metadata: dict[str, Any] = Field(default_factory=dict)
    """Additional metadata about this trajectory execution."""

    solution: str | None = None
    """Optional solution or patch produced by the agent."""

    @computed_field
    @property
    def score(self) -> float | None:
        """Return the unique score value for the trajectory if it exists and `None` otherwise."""
        if self.scores is None or len(self.scores) != 1:
            return None
        [score] = self.scores.values()
        return score.value

    @classmethod
    def from_inspect(cls, sample: EvalSample) -> Trajectory:
        """Convert an Inspect AI `EvalSample` to a `Trajectory`.

        Args:
            sample: The Inspect AI sample to convert

        Returns:
            Trajectory object containing the sample's execution trace
        """

        # fail fast if the sample has an error
        if sample.error:
            raise ValueError(f"Sample {sample.id} has an error: {sample.error.message}")

        # start by extracting scores, so we fail fast if they aren't scalars
        scores: dict[str, ScalarScore] | None = (
            {
                name: ScalarScore.from_inspect(score)
                for name, score in sample.scores.items()
            }
            if sample.scores is not None
            else None
        )

        # convert InspectAI `ChatMessage`s to our `Message`s
        messages: list[Message] = []
        tool_calls: dict[str, ToolCall] = {}  # tool call ID -> `ToolCall`

        for position, message in enumerate(sample.messages):
            match message:
                case ChatMessageAssistant():
                    assistant_message = AssistantMessage.from_inspect(position, message)
                    messages.append(assistant_message)
                    if assistant_message.tool_calls is not None:
                        for tool_call in assistant_message.tool_calls:
                            tool_calls[tool_call.id] = tool_call

                case ChatMessageTool():
                    tool_call_id = message.tool_call_id
                    if tool_call_id not in tool_calls:
                        raise ValueError(f"Tool call ID {tool_call_id} not found")
                    tool_message = ToolMessage.from_inspect(
                        position, message, tool_calls[tool_call_id]
                    )
                    messages.append(tool_message)

                case ChatMessageSystem():
                    system_message = SystemMessage.from_inspect(position, message)
                    messages.append(system_message)

                case ChatMessageUser():
                    user_message = UserMessage.from_inspect(position, message)
                    messages.append(user_message)

        # extract solution from metadata if available
        # TODO: make this more general; currently only supports the "patch" key (used in SWE-bench)
        solution: str | None = sample.metadata.get("patch", None)

        return cls(
            sample=sample.id,
            messages=messages,
            scores=scores,
            metadata=sample.metadata,
            solution=solution,
        )
