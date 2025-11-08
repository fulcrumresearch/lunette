from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

from inspect_ai.model import (
    ChatMessageAssistant as InspectAssistantMessage,
    ChatMessageSystem as InspectSystemMessage,
    ChatMessageTool as InspectToolMessage,
    ChatMessageUser as InspectUserMessage,
    Content as InspectContent,
    ContentReasoning as InspectReasoning,
    ContentText as InspectText,
)
from inspect_ai.tool import ToolCall as InspectToolCall


## content types ##


class Text(BaseModel):
    """Text content."""

    type: Literal["text"] = "text"
    text: str

    @classmethod
    def from_inspect(cls, content: InspectText) -> Text:
        """Convert an Inspect AI `ContentText` to our `Text` model."""
        return cls(text=content.text)


class Reasoning(BaseModel):
    """
    Reasoning content from models with explicit reasoning capability.

    Used by Claude (extended thinking) and OpenAI (reasoning models like GPT-5).
    See [Claude thinking blocks](https://docs.anthropic.com/en/docs/build-with-claude/extended-thinking#understanding-thinking-blocks).
    """

    type: Literal["reasoning"] = "reasoning"
    reasoning: str
    summary: str | None = None
    signature: str | None = None
    redacted: bool = True  # Conservative default: don't display unless explicitly safe

    @classmethod
    def from_inspect(cls, content: InspectReasoning) -> Reasoning:
        """Convert an Inspect AI `ContentReasoning` to our `Reasoning` model."""
        return cls(
            reasoning=content.reasoning,
            summary=content.summary,
            signature=content.signature,
            redacted=content.redacted,
        )


Content = Text | Reasoning


def _content_from_inspect(content: str | list[InspectContent]) -> str | list[Content]:
    """
    Convert Inspect AI content to Lunette content.

    Args:
        content: Either a string or a list of Inspect content items

    Returns:
        Either a string (unchanged) or a list of Lunette Content items
    """
    if isinstance(content, str):
        return content

    result: list[Content] = []
    for item in content:
        match item:
            case InspectText():
                result.append(Text.from_inspect(item))
            case InspectReasoning():
                result.append(Reasoning.from_inspect(item))
            # we ignore other content types for now

    return result


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
        """Get the text content of this message (excludes redacted reasoning)."""
        if isinstance(self.content, str):
            return self.content

        parts = []
        for content in self.content:
            if isinstance(content, Text):
                parts.append(content.text)
            elif isinstance(content, Reasoning):
                # For reasoning blocks:
                # - If summary exists, use it (human-readable)
                # - If explicitly not redacted, use reasoning (human-readable, e.g., Claude extended thinking)
                # - Otherwise skip (encrypted signature or unknown)
                if content.summary:
                    parts.append(content.summary)
                elif content.redacted is False:
                    parts.append(content.reasoning)

        return "\n".join(parts)


class SystemMessage(BaseMessage):
    """System message."""

    role: Literal["system"] = "system"

    @classmethod
    def from_inspect(
        cls, position: int, message: InspectSystemMessage
    ) -> SystemMessage:
        """Convert an Inspect AI `ChatMessageSystem` to `SystemMessage`."""
        return cls(position=position, content=_content_from_inspect(message.content))


class UserMessage(BaseMessage):
    """User message."""

    role: Literal["user"] = "user"

    @classmethod
    def from_inspect(cls, position: int, message: InspectUserMessage) -> UserMessage:
        """Convert an Inspect AI `ChatMessageUser` to `UserMessage`."""
        return cls(position=position, content=_content_from_inspect(message.content))


class AssistantMessage(BaseMessage):
    """Assistant message."""

    role: Literal["assistant"] = "assistant"
    tool_calls: list[ToolCall] | None = None

    @classmethod
    def from_inspect(
        cls, position: int, message: InspectAssistantMessage
    ) -> AssistantMessage:
        """Convert an Inspect AI `ChatMessageAssistant` to `AssistantMessage`."""
        tool_calls = (
            [ToolCall.from_inspect(tool_call) for tool_call in message.tool_calls]
            if message.tool_calls
            else None
        )

        return cls(
            position=position,
            content=_content_from_inspect(message.content),
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
        message: InspectToolMessage,
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
