from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

from inspect_ai.model import (
    ChatMessageAssistant,
    ChatMessageSystem,
    ChatMessageTool,
    ChatMessageUser,
)
from inspect_ai.tool import ToolCall as InspectToolCall


## content types ##


class Text(BaseModel):
    """Text content."""

    type: Literal["text"] = "text"
    text: str


class Reasoning(BaseModel):
    """
    Reasoning content. Only used for models in the Claude family, according to the Inspect AI documentation.

    See the specification for [thinking blocks](https://docs.anthropic.com/en/docs/build-with-claude/extended-thinking#understanding-thinking-blocks) for Claude models.
    """

    type: Literal["reasoning"] = "reasoning"
    reasoning: str


Content = Text | Reasoning


## tool call ##


class ToolCall(BaseModel):
    """
    A tool call.

    Does not include the result of the tool call, as it is not available until a later `ToolMessage` is received.
    """

    id: str
    function: str
    arguments: dict[str, Any]

    @classmethod
    def from_inspect(cls, tool_call: InspectToolCall) -> ToolCall:
        """Convert an Inspect AI `ToolCall` to our `ToolCall` model."""
        return cls(
            id=tool_call.id,
            function=tool_call.function,
            arguments=tool_call.arguments,
        )


## message types ##


class BaseMessage(BaseModel):
    """Base message model."""

    position: int
    content: str | list[Content]

    @property
    def text(self) -> str:
        """Get the text content of this message."""
        if isinstance(self.content, str):
            return self.content
        else:
            return "\n".join(
                [content.text for content in self.content if hasattr(content, "text")]
            )


class SystemMessage(BaseMessage):
    """System message."""

    role: Literal["system"] = "system"

    @classmethod
    def from_inspect(cls, position: int, message: ChatMessageSystem) -> SystemMessage:
        """Convert an Inspect AI `ChatMessageSystem` to `SystemMessage`."""
        return cls(position=position, content=message.content)


class UserMessage(BaseMessage):
    """User message."""

    role: Literal["user"] = "user"

    @classmethod
    def from_inspect(cls, position: int, message: ChatMessageUser) -> UserMessage:
        """Convert an Inspect AI `ChatMessageUser` to `UserMessage`."""
        return cls(position=position, content=message.content)


class AssistantMessage(BaseMessage):
    """Assistant message."""

    role: Literal["assistant"] = "assistant"
    tool_calls: list[ToolCall] | None = None

    @classmethod
    def from_inspect(
        cls, position: int, message: ChatMessageAssistant
    ) -> AssistantMessage:
        """Convert an Inspect AI `ChatMessageAssistant` to `AssistantMessage`."""
        tool_calls = (
            [ToolCall.from_inspect(tool_call) for tool_call in message.tool_calls]
            if message.tool_calls
            else None
        )

        return cls(
            position=position,
            content=message.content,
            tool_calls=tool_calls,
        )


class ToolMessage(BaseMessage):
    """
    Tool message.

    The `content` field contains the result of the tool call.
    """

    role: Literal["tool"] = "tool"
    tool_call: ToolCall

    @classmethod
    def from_inspect(
        cls,
        position: int,
        message: ChatMessageTool,
        tool_call: ToolCall,
    ) -> ToolMessage:
        """
        Convert an Inspect AI `ChatMessageTool` to `ToolMessage`.

        Args:
            position: Position in the trajectory
            message: The Inspect ChatMessageTool
            tool_call: The matching ToolCall (found by the caller)

        Returns:
            ToolMessage with proper tool_call reference
        """
        return cls(
            position=position,
            content=message.text,
            tool_call=tool_call,
        )

    @property
    def function(self) -> str:
        """Get the function name of this tool call."""
        return self.tool_call.function

    @property
    def arguments(self) -> dict[str, Any]:
        """Get the arguments of this tool call."""
        return self.tool_call.arguments

    @property
    def result(self) -> str:
        """Get the result of this tool call."""
        return self.text


Message = SystemMessage | UserMessage | AssistantMessage | ToolMessage
