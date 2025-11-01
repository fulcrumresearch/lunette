"""Inspect AI integration utilities.

This module provides utilities for working with Inspect AI:
- Message/sample conversion: Convert Inspect AI evaluation samples to our Trajectory format
- Interactive sessions: Manage interactive inspect-ai sessions for MCP
"""

from __future__ import annotations
from typing import Any, Optional

from inspect_ai.event import ToolEvent
from inspect_ai.model import (
    ChatMessageAssistant,
    ChatMessageSystem,
    ChatMessageTool,
    ChatMessageUser,
)

from inspect_ai.log import EvalSample

import logging
from enum import Enum
from typing import Any, Optional, Union

from pydantic import BaseModel, Field, field_validator


logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """Types of messages in agent trajectories."""

    CHAT = "chat"
    ACTION = "action"
    OBSERVATION = "observation"


class ChatMessage(BaseModel):
    """Chat messages (user instructions, agent thoughts, etc)."""

    content: str
    role: str = Field(
        ..., description="Role of the message sender (user, assistant, etc)"
    )


class ActionMessage(BaseModel):
    """Agent's tool call/command."""

    name: str = Field(..., description="Name of the tool or action")
    args: dict[str, Any] = Field(
        default_factory=dict, description="Arguments for the action"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Action name cannot be empty")
        return v.strip()


class ObservationMessage(BaseModel):
    """Environment's response/output."""

    name: str = Field(
        ..., description="Name of the tool that produced this observation"
    )
    output: str = Field(..., description="The observation output")


class Message(BaseModel):
    """Base message model with common fields."""

    position: Optional[int] = Field(None, description="Position in the trajectory")
    value: Union[ChatMessage, ActionMessage, ObservationMessage]
    type: MessageType


class SolverSpec(BaseModel):
    """Information about the model and scaffolding configuration used."""

    model: str
    iterations: int
    allowed_tools: Optional[list]


class Trajectory(BaseModel):
    """
    A single agent execution trace over a problem instance.
    """

    score: Optional[float] = None
    messages: list[Message]
    solver_spec: Optional[SolverSpec] = None

    task_name: Optional[str] = ""
    id: Optional[str] = ""
    status: Optional[str] = ""

    metadata: Optional[dict[str, Any]] = None  # Store additional trajectory metadata
    solution: Optional[str] = None  # Store the solution for this trajectory
    sandbox_id: Optional[str] = None  # Lunette sandbox container ID

    def add_message(self, message: Message) -> None:
        """Add a message to the trajectory."""
        self.messages.append(message)


def convert_messages(sample: EvalSample) -> list[Message]:
    """
    Convert Inspect AI evaluation sample messages and tool events to BaseMessage list.

    This function processes an Inspect AI sample in two phases:
    1. Chat history from sample.messages (ChatMessageSystem, ChatMessageUser,
       ChatMessageAssistant, ChatMessageTool)
    2. Tool events from sample.events (ToolEvent)

    Conversion strategy:
      * ChatMessageSystem/User/Assistant → MessageType.CHAT
      * ChatMessageAssistant with tool_calls → MessageType.CHAT + MessageType.ACTION (for each tool call)
      * ChatMessageTool → MessageType.OBSERVATION
      * ToolEvent → MessageType.ACTION + MessageType.OBSERVATION (paired)

    Args:
        sample: Inspect AI evaluation sample with messages and events

    Returns:
        List of BaseMessage objects with sequential positioning
    """
    msg_list: list[Message] = []
    pos = 0

    for m in sample.messages:
        if isinstance(m, (ChatMessageSystem, ChatMessageUser)):
            # Handle both string content and multimodal content (list of Content objects)
            content_str = ""
            if isinstance(m.content, str):
                content_str = m.content
            elif isinstance(m.content, list):
                # For multimodal content, concatenate all text parts
                text_parts = []
                for content_item in m.content:
                    if hasattr(content_item, "text") and content_item.text:
                        text_parts.append(content_item.text)
                content_str = "\n".join(text_parts)
            else:
                # Fallback for other types
                content_str = str(m.content)

            assert isinstance(m.role, str), (
                f"Expected str for role, got {type(m.role)}: {m.role}"
            )

            msg_list.append(
                Message(
                    position=pos,
                    type=MessageType.CHAT,
                    value=ChatMessage(content=content_str, role=m.role),
                )
            )
            pos += 1

        elif isinstance(m, ChatMessageAssistant):
            # Handle assistant content
            content_str = ""
            if isinstance(m.content, str):
                content_str = m.content
            elif isinstance(m.content, list):
                # For multimodal content, concatenate all text parts
                text_parts = []
                for content_item in m.content:
                    if hasattr(content_item, "text") and content_item.text:
                        text_parts.append(content_item.text)
                    if hasattr(content_item, "reasoning") and content_item.reasoning:
                        text_parts.append(content_item.reasoning)
                content_str = "\n".join(text_parts)
            else:
                # Fallback for other types
                content_str = str(m.content)

            # Always add the assistant message if it has content
            if content_str:
                msg_list.append(
                    Message(
                        position=pos,
                        type=MessageType.CHAT,
                        value=ChatMessage(content=content_str, role=m.role),
                    )
                )
                pos += 1

            # Check for tool calls
            if hasattr(m, "tool_calls") and m.tool_calls:
                for tool_call in m.tool_calls:
                    # Add ACTION message for each tool call
                    msg_list.append(
                        Message(
                            position=pos,
                            type=MessageType.ACTION,
                            value=ActionMessage(
                                name=tool_call.function, args=tool_call.arguments
                            ),
                        )
                    )
                    pos += 1

        elif isinstance(m, ChatMessageTool):
            # Assert we require a function name and don't support cases where it's None
            assert isinstance(m.function, str), (
                f"Expected str for function, got {type(m.function)}: {m.function}"
            )

            # Handle both string content and multimodal content
            content_str = ""
            if isinstance(m.content, str):
                content_str = m.content
            elif isinstance(m.content, list):
                # For multimodal content, concatenate all text parts
                text_parts = []
                for content_item in m.content:
                    if hasattr(content_item, "text") and content_item.text:
                        text_parts.append(content_item.text)
                content_str = "\n".join(text_parts)
            else:
                # Fallback for other types
                content_str = str(m.content)

            # Treat tool‐echoed content as an observation
            msg_list.append(
                Message(
                    position=pos,
                    type=MessageType.OBSERVATION,
                    value=ObservationMessage(name=m.function, output=content_str),
                )
            )
            pos += 1

    # Process tool events from sample.events (these might be duplicates of tool_calls)
    for ev in sample.events:
        if isinstance(ev, ToolEvent):
            # Assert we only support simple string results, not rich ToolResult objects
            assert isinstance(ev.function, str), (
                f"Expected str for function, got {type(ev.function)}: {ev.function}"
            )

            # Handle both string results and multimodal results
            result_str = ""
            if isinstance(ev.result, str):
                result_str = ev.result
            elif isinstance(ev.result, list):
                # For multimodal content, concatenate all text parts
                text_parts = []
                for content_item in ev.result:
                    if hasattr(content_item, "text") and content_item.text:
                        text_parts.append(content_item.text)
                result_str = "\n".join(text_parts)
            else:
                # Fallback for other types
                result_str = str(ev.result)

            msg_list.append(
                Message(
                    position=pos,
                    type=MessageType.ACTION,
                    value=ActionMessage(name=ev.function, args=ev.arguments),
                )
            )
            pos += 1
            msg_list.append(
                Message(
                    position=pos,
                    type=MessageType.OBSERVATION,
                    value=ObservationMessage(name=ev.function, output=result_str),
                )
            )
            pos += 1

    return msg_list


def sample_to_trajectory(
    sample: EvalSample,
    model_name: str = "",
    tools: list[str] | None = None,
) -> Trajectory:
    """
    Convert an Inspect AI evaluation sample to a Trajectory object.

    Extracts key information from the sample and converts messages using convert_messages().

    Score conversion logic:
      * 'C' → 1 (correct/success)
      * 'I' → 0 (incorrect/failure)
      * Numeric values → preserved as float
      * Invalid/None → 0 (no score or invalid format)

    Args:
        sample: Inspect AI evaluation sample containing messages, events, scores, etc.
        model_name: Name of the model used for evaluation (default: "")
        tools: List of allowed tools for the solver (default: None → [])

    Returns:
        Trajectory object with:
          * id: stringified sample.id
          * score: converted score (0 or 1)
          * status: "error" if sample.error else "finished"
          * solver_spec: SolverSpec with model, iterations=1, allowed_tools
          * messages: converted BaseMessage list from convert_messages()
          * metadata: sample.metadata
          * solution: extracted from metadata["patch"] if available
          * sandbox_id: extracted from metadata["lunette_sandbox_id"] if available
    """
    score = next(iter(sample.scores.values())).value if sample.scores else None

    # Handle different score formats safely
    if score == "C":
        score = 1
    elif score == "I":
        score = 0
    elif score is not None:
        # Try to preserve float scores
        try:
            score = float(score)
        except (ValueError, TypeError):
            # If conversion fails, default to 0
            score = 0
    else:
        # No score available
        score = 0

    # Convert messages first
    messages = convert_messages(sample)

    # Extract solution patch from metadata if available
    solution = None
    if sample.metadata and "patch" in sample.metadata:
        solution = sample.metadata["patch"]

    # Extract sandbox_id from metadata if available
    sandbox_id = None
    if sample.metadata and "lunette_sandbox_id" in sample.metadata:
        sandbox_id = sample.metadata["lunette_sandbox_id"]

    return Trajectory(
        task_name=str(sample.id),
        score=score,
        status="error" if sample.error else "finished",
        solver_spec=SolverSpec(
            model=model_name, iterations=1, allowed_tools=tools or []
        ),
        messages=messages,
        metadata=sample.metadata,
        solution=solution,
        sandbox_id=sandbox_id,
    )
