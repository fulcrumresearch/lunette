"""Converts OpenTelemetry spans to Lunette Message objects.

The OpenAI instrumentation creates one span per API call with attributes following
the GenAI semantic conventions:
- gen_ai.prompt.N.role / gen_ai.prompt.N.content - input messages
- gen_ai.completion.N.role / gen_ai.completion.N.content - output messages
- Tool calls embedded in completion attributes
"""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Any

from lunette.models.messages import (
    AssistantMessage,
    Message,
    SystemMessage,
    ToolCall,
    ToolMessage,
    UserMessage,
)

if TYPE_CHECKING:
    from opentelemetry.sdk.trace import ReadableSpan


def _content_hash(role: str, content: str) -> str:
    """Create a hash of message content for deduplication."""
    return hashlib.md5(f"{role}:{content}".encode()).hexdigest()


def _extract_indexed_attributes(
    attributes: dict[str, Any], prefix: str
) -> list[dict[str, Any]]:
    """Extract indexed attributes like gen_ai.prompt.0.role, gen_ai.prompt.1.role, etc.

    Args:
        attributes: Span attributes dict
        prefix: Attribute prefix (e.g., "gen_ai.prompt")

    Returns:
        List of dicts, each containing the attributes for one indexed item
    """
    items: dict[int, dict[str, Any]] = {}

    for key, value in attributes.items():
        if not key.startswith(prefix + "."):
            continue

        # parse "gen_ai.prompt.0.role" -> index=0, field="role"
        rest = key[len(prefix) + 1 :]
        parts = rest.split(".", 1)
        if len(parts) != 2:
            continue

        try:
            index = int(parts[0])
        except ValueError:
            continue

        field = parts[1]
        if index not in items:
            items[index] = {}
        items[index][field] = value

    # return sorted by index
    return [items[i] for i in sorted(items.keys())]


def _parse_tool_calls(completion: dict[str, Any]) -> list[ToolCall] | None:
    """Parse tool calls from a completion dict.

    Tool calls may be stored as:
    - tool_calls: JSON string of array
    - function.name / function.arguments: single function call
    """
    # check for tool_calls array (JSON encoded)
    if "tool_calls" in completion:
        try:
            tool_calls_data = completion["tool_calls"]
            if isinstance(tool_calls_data, str):
                tool_calls_data = json.loads(tool_calls_data)

            if not tool_calls_data:
                return None

            result = []
            for tc in tool_calls_data:
                if isinstance(tc, dict):
                    func = tc.get("function", {})
                    args = func.get("arguments", "{}")
                    if isinstance(args, str):
                        args = json.loads(args) if args else {}
                    result.append(
                        ToolCall(
                            id=tc.get("id", ""),
                            function=func.get("name", ""),
                            arguments=args,
                        )
                    )
            return result if result else None
        except (json.JSONDecodeError, TypeError, KeyError):
            pass

    # check for single function call
    if "function.name" in completion:
        args_str = completion.get("function.arguments", "{}")
        try:
            args = json.loads(args_str) if isinstance(args_str, str) else args_str
        except json.JSONDecodeError:
            args = {}

        return [
            ToolCall(
                id=completion.get("id", ""),
                function=completion["function.name"],
                arguments=args if isinstance(args, dict) else {},
            )
        ]

    return None


def _extract_messages_from_span(
    span: ReadableSpan,
    seen_hashes: set[str],
    tool_calls_by_id: dict[str, ToolCall],
    position: int,
) -> tuple[list[Message], int]:
    """Extract new messages from a span.

    Args:
        span: The OTel span to extract from
        seen_hashes: Set of content hashes already seen (for dedup)
        tool_calls_by_id: Dict mapping tool call IDs to ToolCall objects
        position: Starting position for new messages

    Returns:
        Tuple of (list of new messages, next position)
    """
    attributes = dict(span.attributes or {})
    messages: list[Message] = []

    # extract prompt messages (these may include duplicates from conversation history)
    prompts = _extract_indexed_attributes(attributes, "gen_ai.prompt")
    for prompt in prompts:
        role = prompt.get("role", "")
        content = str(prompt.get("content", ""))

        # skip if we've seen this exact message before
        msg_hash = _content_hash(role, content)
        if msg_hash in seen_hashes:
            continue
        seen_hashes.add(msg_hash)

        match role:
            case "system":
                messages.append(SystemMessage(position=position, content=content))
                position += 1

            case "user":
                messages.append(UserMessage(position=position, content=content))
                position += 1

            case "tool":
                # tool messages reference a previous tool call
                tool_call_id = prompt.get("tool_call_id", "")
                tool_call = tool_calls_by_id.get(tool_call_id)
                if tool_call:
                    messages.append(
                        ToolMessage(
                            position=position, content=content, tool_call=tool_call
                        )
                    )
                    position += 1
                # if tool_call not found, we skip this message (shouldn't happen in well-formed traces)

            case "assistant":
                # assistant messages in prompts are from previous turns
                # parse tool calls if present
                tool_calls = _parse_tool_calls(prompt)
                if tool_calls:
                    for tc in tool_calls:
                        tool_calls_by_id[tc.id] = tc

                messages.append(
                    AssistantMessage(
                        position=position, content=content, tool_calls=tool_calls
                    )
                )
                position += 1

    # extract completion messages (these are always new)
    completions = _extract_indexed_attributes(attributes, "gen_ai.completion")
    for completion in completions:
        role = completion.get("role", "assistant")
        content = str(completion.get("content", ""))

        # completions are always new, but we still hash them to prevent re-adding if
        # they appear in the next span's prompts
        msg_hash = _content_hash(role, content)
        seen_hashes.add(msg_hash)

        # parse tool calls
        tool_calls = _parse_tool_calls(completion)
        if tool_calls:
            for tc in tool_calls:
                tool_calls_by_id[tc.id] = tc

        messages.append(
            AssistantMessage(position=position, content=content, tool_calls=tool_calls)
        )
        position += 1

    return messages, position


def convert_spans_to_messages(spans: list[ReadableSpan]) -> list[Message]:
    """Convert a list of OTel spans to Lunette Message objects.

    Args:
        spans: List of spans for a single trajectory, should be sorted by start_time

    Returns:
        List of Message objects representing the full conversation
    """
    messages: list[Message] = []
    seen_hashes: set[str] = set()
    tool_calls_by_id: dict[str, ToolCall] = {}
    position = 0

    for span in spans:
        # only process spans that look like OpenAI chat completions
        attributes = span.attributes or {}
        gen_ai_system = attributes.get("gen_ai.system") or attributes.get("llm.system")
        if gen_ai_system != "openai":
            continue

        new_messages, position = _extract_messages_from_span(
            span, seen_hashes, tool_calls_by_id, position
        )
        messages.extend(new_messages)

    return messages
