"""Converts OpenTelemetry spans to Lunette Message objects.

LLM instrumentation (OpenAI, Anthropic) creates one span per API call with
attributes following the GenAI semantic conventions:
- gen_ai.prompt.N.role / gen_ai.prompt.N.content - input messages
- gen_ai.completion.N.role / gen_ai.completion.N.content - output messages
- Tool calls embedded in completion attributes
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from typing import TYPE_CHECKING, Any

from lunette.models.messages import (
    AssistantMessage,
    Content,
    Image,
    Message,
    SystemMessage,
    Text,
    ToolCall,
    ToolMessage,
    UserMessage,
)

if TYPE_CHECKING:
    from opentelemetry.sdk.trace import ReadableSpan


def _content_hash(role: str, content: str | list[Content], tool_calls: list[ToolCall] | None = None) -> str:
    """Create a hash of message content for deduplication.

    For assistant messages with tool_calls, include the tool call IDs in the hash
    to properly deduplicate messages that may have different content representations
    (empty string vs JSON serialization of tool blocks).
    """
    if isinstance(content, list):
        content_str = json.dumps([c.model_dump() for c in content], sort_keys=True)
    else:
        content_str = content

    # include tool_calls in hash for assistant messages
    if tool_calls:
        tc_ids = sorted(tc.id for tc in tool_calls)
        return hashlib.md5(f"{role}:{content_str}:{tc_ids}".encode()).hexdigest()

    return hashlib.md5(f"{role}:{content_str}".encode()).hexdigest()


def _parse_tool_results(content: str) -> list[dict[str, Any]] | None:
    """Parse tool_result blocks from Anthropic-style user messages.

    Anthropic tool results are sent as user messages with JSON array content:
    [{"type": "tool_result", "tool_use_id": "...", "content": "..."}]

    Returns list of parsed tool results, or None if content isn't tool results.
    """
    if not content or not content.strip().startswith("["):
        return None

    try:
        parsed = json.loads(content)
        if not isinstance(parsed, list):
            return None

        # check if all items are tool_result blocks
        tool_results = []
        for item in parsed:
            if not isinstance(item, dict):
                return None
            if item.get("type") != "tool_result":
                return None
            tool_results.append(item)

        return tool_results if tool_results else None
    except json.JSONDecodeError:
        return None


def _is_tool_use_json(content: str) -> bool:
    """Check if content is a JSON array of tool_use blocks (Anthropic format).

    When Anthropic assistant messages with tool calls are included in prompts,
    the content is serialized as JSON: [{"type": "tool_use", "id": "...", ...}]
    We should ignore this content since we have the proper tool_calls attributes.
    """
    if not content or not content.strip().startswith("["):
        return False

    try:
        parsed = json.loads(content)
        if not isinstance(parsed, list) or not parsed:
            return False

        # check if first item looks like a tool_use block
        first = parsed[0]
        return isinstance(first, dict) and first.get("type") == "tool_use"
    except json.JSONDecodeError:
        return False


def _parse_content(raw_content: Any) -> str | list[Content]:
    """Parse message content from OTel attributes.

    Content may be:
    - A simple string
    - A JSON string representing an array of content blocks
    - Already a list/dict structure

    Supported formats:
    - OpenAI: [{"type": "text", "text": "..."}, {"type": "image_url", "image_url": {"url": "...", "detail": "..."}}]
    - Anthropic: [{"type": "text", "text": "..."}, {"type": "image", "source": {"type": "base64", "media_type": "...", "data": "..."}}]

    Note: The Anthropic OTel instrumentation captures content in Anthropic's native format,
    while the OpenAI instrumentation currently does not capture multimodal content at all.

    Returns:
        Either a string or a list of Content objects (Text, Image)
    """
    if raw_content is None:
        return ""

    # if it's already a string, try to parse as JSON array
    if isinstance(raw_content, str):
        try:
            parsed = json.loads(raw_content)
            if isinstance(parsed, list):
                raw_content = parsed
            else:
                # not an array, treat as plain text
                return raw_content
        except (json.JSONDecodeError, TypeError):
            # not JSON, treat as plain text
            return raw_content

    # if it's a list, convert each block to Content
    if isinstance(raw_content, list):
        result: list[Content] = []
        for block in raw_content:
            if not isinstance(block, dict):
                continue

            block_type = block.get("type", "")

            match block_type:
                case "text":
                    text = block.get("text", "")
                    if text:
                        result.append(Text(text=text))

                case "image_url":
                    # OpenAI format: {"type": "image_url", "image_url": {"url": "...", "detail": "..."}}
                    image_data = block.get("image_url", {})
                    if isinstance(image_data, dict):
                        url = image_data.get("url", "")
                        detail = image_data.get("detail", "auto")
                        if detail not in ("auto", "low", "high"):
                            detail = "auto"
                        if url:
                            result.append(Image(image=url, detail=detail))

                case "image":
                    # Anthropic format: {"type": "image", "source": {"type": "base64", "media_type": "...", "data": "..."}}
                    source = block.get("source", {})
                    if isinstance(source, dict) and source.get("type") == "base64":
                        media_type = source.get("media_type", "image/png")
                        data = source.get("data", "")
                        if data:
                            # convert to data URI format for consistency
                            url = f"data:{media_type};base64,{data}"
                            result.append(Image(image=url, detail="auto"))

        if result:
            return result

    # fallback: convert to string
    return str(raw_content)


def _extract_indexed_attributes(attributes: dict[str, Any], prefix: str) -> list[dict[str, Any]]:
    """Extract indexed attributes like gen_ai.prompt.0.role into a list of dicts.

    Handles nested indexed attributes like:
    - gen_ai.prompt.0.role -> items[0]["role"]
    - gen_ai.prompt.0.tool_calls.0.name -> items[0]["tool_calls"][0]["name"]
    """
    # match top-level index and everything after
    pattern = re.compile(rf"^{re.escape(prefix)}\.(\d+)\.(.+)$")
    items: defaultdict[int, dict[str, Any]] = defaultdict(dict)

    for key, value in attributes.items():
        if match := pattern.match(key):
            idx = int(match[1])
            rest = match[2]

            # check for nested indexed attributes like tool_calls.0.name
            nested_match = re.match(r"^(tool_calls)\.(\d+)\.(.+)$", rest)
            if nested_match:
                nested_key, nested_idx, nested_attr = nested_match.groups()
                nested_idx = int(nested_idx)

                if nested_key not in items[idx]:
                    items[idx][nested_key] = {}
                if nested_idx not in items[idx][nested_key]:
                    items[idx][nested_key][nested_idx] = {}
                items[idx][nested_key][nested_idx][nested_attr] = value
            else:
                items[idx][rest] = value

    # convert nested dicts of tool_calls to lists
    result = []
    for i in sorted(items):
        item = dict(items[i])
        if "tool_calls" in item and isinstance(item["tool_calls"], dict):
            # convert {0: {...}, 1: {...}} to [{...}, {...}]
            tc_dict = item["tool_calls"]
            item["tool_calls"] = [tc_dict[j] for j in sorted(tc_dict)]
        result.append(item)

    return result


def _parse_tool_calls(msg_attrs: dict[str, Any]) -> list[ToolCall] | None:
    """Parse tool calls from a message attribute dict.

    Tool calls may be stored as:
    - tool_calls: list of dicts with {name, arguments, id} (from nested OTel attributes)
    - tool_calls: JSON string of array with {id, function: {name, arguments}}
    - function.name / function.arguments: single function call
    """
    if "tool_calls" not in msg_attrs:
        # check for single function call (legacy format)
        if "function.name" in msg_attrs:
            args_str = msg_attrs.get("function.arguments", "{}")
            try:
                args = json.loads(args_str) if isinstance(args_str, str) else args_str
            except json.JSONDecodeError:
                args = {}

            return [
                ToolCall(
                    id=msg_attrs.get("id", ""),
                    function=msg_attrs["function.name"],
                    arguments=args if isinstance(args, dict) else {},
                )
            ]
        return None

    tool_calls_data = msg_attrs["tool_calls"]

    # handle JSON string format
    if isinstance(tool_calls_data, str):
        try:
            tool_calls_data = json.loads(tool_calls_data)
        except json.JSONDecodeError:
            return None

    if not tool_calls_data:
        return None

    result = []
    for tc in tool_calls_data:
        if not isinstance(tc, dict):
            continue

        # OTel nested format: {name, arguments, id} directly in the dict
        if "name" in tc:
            args = tc.get("arguments", "{}")
            if isinstance(args, str):
                try:
                    args = json.loads(args) if args else {}
                except json.JSONDecodeError:
                    args = {}
            result.append(
                ToolCall(
                    id=tc.get("id", ""),
                    function=tc["name"],
                    arguments=args if isinstance(args, dict) else {},
                )
            )
        # legacy format: {id, function: {name, arguments}}
        elif "function" in tc:
            func = tc.get("function", {})
            args = func.get("arguments", "{}")
            if isinstance(args, str):
                try:
                    args = json.loads(args) if args else {}
                except json.JSONDecodeError:
                    args = {}
            result.append(
                ToolCall(
                    id=tc.get("id", ""),
                    function=func.get("name", ""),
                    arguments=args if isinstance(args, dict) else {},
                )
            )

    return result if result else None


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
        raw_content = prompt.get("content", "")

        # always track tool_calls from assistant messages for tool message lookups,
        # even if we skip the message itself due to deduplication
        tool_calls = None
        if role == "assistant":
            tool_calls = _parse_tool_calls(prompt)
            if tool_calls:
                for tc in tool_calls:
                    tool_calls_by_id[tc.id] = tc

        # for assistant messages with tool_calls, check if raw content is tool_use JSON
        # (Anthropic serializes tool blocks as JSON content - we should ignore it)
        # must check BEFORE _parse_content which mangles the JSON
        if role == "assistant" and tool_calls and isinstance(raw_content, str) and _is_tool_use_json(raw_content):
            content = ""
        else:
            content = _parse_content(raw_content)

        # skip if we've seen this exact message before (include tool_calls in hash)
        msg_hash = _content_hash(role, content, tool_calls if role == "assistant" else None)
        if msg_hash in seen_hashes:
            continue
        seen_hashes.add(msg_hash)

        match role:
            case "system":
                messages.append(SystemMessage(position=position, content=content))
                position += 1

            case "user":
                # check if this is an Anthropic-style tool result message
                # (must check raw_content since _parse_content mangles JSON)
                tool_results = None
                if isinstance(raw_content, str):
                    tool_results = _parse_tool_results(raw_content)

                if tool_results:
                    # convert to TOOL messages
                    for tr in tool_results:
                        tool_call_id = tr.get("tool_use_id", "")
                        tool_call = tool_calls_by_id.get(tool_call_id)
                        if tool_call:
                            messages.append(
                                ToolMessage(
                                    position=position,
                                    content=str(tr.get("content", "")),
                                    tool_call=tool_call,
                                )
                            )
                            position += 1
                else:
                    messages.append(UserMessage(position=position, content=content))
                    position += 1

            case "tool":
                # tool messages reference a previous tool call (OpenAI format)
                tool_call_id = prompt.get("tool_call_id", "")
                tool_call = tool_calls_by_id.get(tool_call_id)
                if tool_call:
                    messages.append(ToolMessage(position=position, content=content, tool_call=tool_call))
                    position += 1

            case "assistant":
                messages.append(AssistantMessage(position=position, content=content, tool_calls=tool_calls))
                position += 1

    # extract completion messages (these are always new)
    completions = _extract_indexed_attributes(attributes, "gen_ai.completion")
    for completion in completions:
        role = completion.get("role", "assistant")
        content = _parse_content(completion.get("content"))

        # parse tool calls
        tool_calls = _parse_tool_calls(completion)
        if tool_calls:
            for tc in tool_calls:
                tool_calls_by_id[tc.id] = tc

        # completions are always new, but we still hash them to prevent re-adding if
        # they appear in the next span's prompts (include tool_calls for proper dedup)
        msg_hash = _content_hash(role, content, tool_calls)
        seen_hashes.add(msg_hash)

        messages.append(AssistantMessage(position=position, content=content, tool_calls=tool_calls))
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
        new_messages, position = _extract_messages_from_span(span, seen_hashes, tool_calls_by_id, position)
        messages.extend(new_messages)

    return messages
