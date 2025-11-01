from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


## content types


class Text(BaseModel):
    """Text content."""

    type: Literal["text"] = "text"
    text: str


class Reasoning(BaseModel):
    """
    Reasoning content. Only used for models in the Claude family.

    See the specification for [thinking blocks](https://docs.anthropic.com/en/docs/build-with-claude/extended-thinking#understanding-thinking-blocks) for Claude models.
    """

    type: Literal["reasoning"] = "reasoning"
    reasoning: str


class ToolUse(BaseModel):
    """Tool use content."""

    type: Literal["tool_use"] = "tool_use"
    name: str
    arguments: str
    result: str


Content = Text | Reasoning | ToolUse


## message types


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
    tool_calls: list[ToolUse] | None = None


Message = SystemMessage | UserMessage | AssistantMessage
