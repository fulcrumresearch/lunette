from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


## content types ##


class Text(BaseModel):
    """Text content."""

    type: Literal["text"] = "text"
    text: str


class Reasoning(BaseModel):
    """
    Reasoning content. Only used for models in the Claude family, according to the Inspect documentation.

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


class UserMessage(BaseMessage):
    """User message."""

    role: Literal["user"] = "user"


class AssistantMessage(BaseMessage):
    """Assistant message."""

    role: Literal["assistant"] = "assistant"
    tool_calls: list[ToolCall] | None = None


class ToolMessage(BaseMessage):
    """
    Tool message.

    The `content` field contains the result of the tool call.
    """

    role: Literal["tool"] = "tool"
    tool_call: ToolCall

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
