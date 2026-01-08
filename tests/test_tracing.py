"""Tests for the tracing module - no external servers required."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from lunette.tracing.context import trajectory_context_id_var
from lunette.tracing.span_collector import SpanCollector
from lunette.tracing.span_converter import (
    _content_hash,
    _extract_indexed_attributes,
    _parse_tool_calls,
    convert_spans_to_messages,
)
from lunette.models.messages import (
    AssistantMessage,
    SystemMessage,
    UserMessage,
)


# --- Test span_converter helpers ---


def test_content_hash_deterministic():
    """Same inputs produce same hash."""
    h1 = _content_hash("user", "hello")
    h2 = _content_hash("user", "hello")
    assert h1 == h2


def test_content_hash_differs_by_role():
    """Different roles produce different hashes."""
    h1 = _content_hash("user", "hello")
    h2 = _content_hash("assistant", "hello")
    assert h1 != h2


def test_extract_indexed_attributes():
    """Extracts gen_ai.prompt.N.* style attributes correctly."""
    attrs = {
        "gen_ai.prompt.0.role": "system",
        "gen_ai.prompt.0.content": "You are helpful",
        "gen_ai.prompt.1.role": "user",
        "gen_ai.prompt.1.content": "Hello",
        "gen_ai.system": "openai",  # should be ignored
    }

    result = _extract_indexed_attributes(attrs, "gen_ai.prompt")

    assert len(result) == 2
    assert result[0] == {"role": "system", "content": "You are helpful"}
    assert result[1] == {"role": "user", "content": "Hello"}


def test_extract_indexed_attributes_empty():
    """Returns empty list when no matching attributes."""
    attrs = {"gen_ai.system": "openai"}
    result = _extract_indexed_attributes(attrs, "gen_ai.prompt")
    assert result == []


def test_extract_indexed_attributes_nested_tool_calls():
    """Extracts nested tool_calls attributes correctly."""
    attrs = {
        "gen_ai.completion.0.role": "assistant",
        "gen_ai.completion.0.tool_calls.0.name": "search",
        "gen_ai.completion.0.tool_calls.0.arguments": '{"q": "test"}',
        "gen_ai.completion.0.tool_calls.0.id": "call_abc",
        "gen_ai.completion.0.tool_calls.1.name": "lookup",
        "gen_ai.completion.0.tool_calls.1.arguments": '{"id": 123}',
        "gen_ai.completion.0.tool_calls.1.id": "call_def",
    }

    result = _extract_indexed_attributes(attrs, "gen_ai.completion")

    assert len(result) == 1
    assert result[0]["role"] == "assistant"
    assert "tool_calls" in result[0]
    assert len(result[0]["tool_calls"]) == 2
    assert result[0]["tool_calls"][0] == {
        "name": "search",
        "arguments": '{"q": "test"}',
        "id": "call_abc",
    }
    assert result[0]["tool_calls"][1] == {
        "name": "lookup",
        "arguments": '{"id": 123}',
        "id": "call_def",
    }


def test_parse_tool_calls_json_string():
    """Parses tool_calls from JSON string."""
    completion = {
        "tool_calls": '[{"id": "call_123", "function": {"name": "search", "arguments": "{\\"q\\": \\"test\\"}"}}]'
    }

    result = _parse_tool_calls(completion)

    assert result is not None
    assert len(result) == 1
    assert result[0].id == "call_123"
    assert result[0].function == "search"
    assert result[0].arguments == {"q": "test"}


def test_parse_tool_calls_single_function():
    """Parses single function call style."""
    completion = {
        "function.name": "get_weather",
        "function.arguments": '{"city": "NYC"}',
        "id": "call_456",
    }

    result = _parse_tool_calls(completion)

    assert result is not None
    assert len(result) == 1
    assert result[0].function == "get_weather"
    assert result[0].arguments == {"city": "NYC"}


def test_parse_tool_calls_none():
    """Returns None when no tool calls present."""
    completion = {"role": "assistant", "content": "Hello!"}
    result = _parse_tool_calls(completion)
    assert result is None


def test_parse_tool_calls_otel_nested_format():
    """Parses tool_calls in OTel nested format (name/arguments/id directly)."""
    # this is what _extract_indexed_attributes produces from:
    # gen_ai.completion.0.tool_calls.0.name, .arguments, .id
    completion = {
        "role": "assistant",
        "tool_calls": [{"name": "multiply", "arguments": '{"a": 7, "b": 8}', "id": "call_123"}],
    }

    result = _parse_tool_calls(completion)

    assert result is not None
    assert len(result) == 1
    assert result[0].id == "call_123"
    assert result[0].function == "multiply"
    assert result[0].arguments == {"a": 7, "b": 8}


# --- Test SpanCollector ---


def _make_mock_span(trajectory_id: str | None, start_time: int = 0) -> MagicMock:
    """Create a mock ReadableSpan."""
    span = MagicMock()
    span.attributes = {"lunette.trajectory_id": trajectory_id} if trajectory_id else {}
    span.start_time = start_time
    return span


def test_span_collector_groups_by_trajectory():
    """Spans are grouped by trajectory_id."""
    collector = SpanCollector()

    span1 = _make_mock_span("traj-1", start_time=100)
    span2 = _make_mock_span("traj-2", start_time=200)
    span3 = _make_mock_span("traj-1", start_time=300)

    collector.on_end(span1)
    collector.on_end(span2)
    collector.on_end(span3)

    traj1_spans = collector.pop_trajectory("traj-1")
    traj2_spans = collector.pop_trajectory("traj-2")

    assert len(traj1_spans) == 2
    assert len(traj2_spans) == 1


def test_span_collector_sorts_by_time():
    """Spans are returned sorted by start_time."""
    collector = SpanCollector()

    # add out of order
    collector.on_end(_make_mock_span("traj-1", start_time=300))
    collector.on_end(_make_mock_span("traj-1", start_time=100))
    collector.on_end(_make_mock_span("traj-1", start_time=200))

    spans = collector.pop_trajectory("traj-1")

    assert [s.start_time for s in spans] == [100, 200, 300]


def test_span_collector_pop_removes():
    """Pop removes spans from collector."""
    collector = SpanCollector()
    collector.on_end(_make_mock_span("traj-1"))

    first_pop = collector.pop_trajectory("traj-1")
    second_pop = collector.pop_trajectory("traj-1")

    assert len(first_pop) == 1
    assert len(second_pop) == 0


def test_span_collector_ignores_no_trajectory():
    """Spans without trajectory_id are ignored."""
    collector = SpanCollector()
    collector.on_end(_make_mock_span(None))

    # should not raise, just ignore
    spans = collector.pop_trajectory("any")
    assert spans == []


# --- Test convert_spans_to_messages ---


def _make_llm_span(
    prompts: list[dict],
    completions: list[dict],
    start_time: int = 0,
) -> MagicMock:
    """Create a mock span with GenAI semantic convention attributes."""
    attrs: dict[str, Any] = {}

    for i, p in enumerate(prompts):
        for key, value in p.items():
            attrs[f"gen_ai.prompt.{i}.{key}"] = value

    for i, c in enumerate(completions):
        for key, value in c.items():
            attrs[f"gen_ai.completion.{i}.{key}"] = value

    span = MagicMock()
    span.attributes = attrs
    span.start_time = start_time
    return span


def test_convert_simple_conversation():
    """Converts a simple user/assistant conversation."""
    span = _make_llm_span(
        prompts=[
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"},
        ],
        completions=[
            {"role": "assistant", "content": "Hi there!"},
        ],
    )

    messages = convert_spans_to_messages([span])

    assert len(messages) == 3
    assert isinstance(messages[0], SystemMessage)
    assert messages[0].content == "You are helpful"
    assert messages[0].position == 0

    assert isinstance(messages[1], UserMessage)
    assert messages[1].content == "Hello"
    assert messages[1].position == 1

    assert isinstance(messages[2], AssistantMessage)
    assert messages[2].content == "Hi there!"
    assert messages[2].position == 2


def test_convert_deduplicates_prompts():
    """Doesn't duplicate messages that appear in multiple spans' prompts."""
    # first span: system + user -> assistant
    span1 = _make_llm_span(
        prompts=[
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"},
        ],
        completions=[
            {"role": "assistant", "content": "Hi!"},
        ],
        start_time=100,
    )

    # second span: same prompts + previous assistant + new user -> new assistant
    span2 = _make_llm_span(
        prompts=[
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi!"},
            {"role": "user", "content": "How are you?"},
        ],
        completions=[
            {"role": "assistant", "content": "I'm great!"},
        ],
        start_time=200,
    )

    messages = convert_spans_to_messages([span1, span2])

    # should be: system, user, assistant, user, assistant
    assert len(messages) == 5
    assert [m.content for m in messages] == [
        "You are helpful",
        "Hello",
        "Hi!",
        "How are you?",
        "I'm great!",
    ]


def test_convert_with_tool_calls():
    """Converts tool call and tool result messages correctly (OpenAI format)."""
    from lunette.models.messages import ToolMessage

    # first span: user asks, assistant responds with tool call
    # uses OTel nested format: gen_ai.completion.0.tool_calls.0.name, etc.
    span1_attrs = {
        "gen_ai.prompt.0.role": "system",
        "gen_ai.prompt.0.content": "You are helpful",
        "gen_ai.prompt.1.role": "user",
        "gen_ai.prompt.1.content": "What is 7 times 8?",
        "gen_ai.completion.0.role": "assistant",
        "gen_ai.completion.0.tool_calls.0.name": "multiply",
        "gen_ai.completion.0.tool_calls.0.arguments": '{"a": 7, "b": 8}',
        "gen_ai.completion.0.tool_calls.0.id": "call_123",
    }
    span1 = MagicMock()
    span1.attributes = span1_attrs
    span1.start_time = 100

    # second span: includes previous messages + tool result (OpenAI format)
    span2_attrs = {
        "gen_ai.prompt.0.role": "system",
        "gen_ai.prompt.0.content": "You are helpful",
        "gen_ai.prompt.1.role": "user",
        "gen_ai.prompt.1.content": "What is 7 times 8?",
        "gen_ai.prompt.2.role": "assistant",
        "gen_ai.prompt.2.tool_calls.0.name": "multiply",
        "gen_ai.prompt.2.tool_calls.0.arguments": '{"a": 7, "b": 8}',
        "gen_ai.prompt.2.tool_calls.0.id": "call_123",
        "gen_ai.prompt.3.role": "tool",
        "gen_ai.prompt.3.content": "56",
        "gen_ai.prompt.3.tool_call_id": "call_123",
        "gen_ai.completion.0.role": "assistant",
        "gen_ai.completion.0.content": "7 times 8 is 56.",
    }
    span2 = MagicMock()
    span2.attributes = span2_attrs
    span2.start_time = 200

    messages = convert_spans_to_messages([span1, span2])

    # should be: system, user, assistant (with tool call), tool, assistant (final)
    assert len(messages) == 5

    assert isinstance(messages[0], SystemMessage)
    assert messages[0].content == "You are helpful"

    assert isinstance(messages[1], UserMessage)
    assert messages[1].content == "What is 7 times 8?"

    assert isinstance(messages[2], AssistantMessage)
    assert messages[2].content == ""
    assert messages[2].tool_calls is not None
    assert len(messages[2].tool_calls) == 1
    assert messages[2].tool_calls[0].function == "multiply"
    assert messages[2].tool_calls[0].id == "call_123"

    assert isinstance(messages[3], ToolMessage)
    assert messages[3].content == "56"
    assert messages[3].tool_call.id == "call_123"
    assert messages[3].tool_call.function == "multiply"

    assert isinstance(messages[4], AssistantMessage)
    assert messages[4].content == "7 times 8 is 56."


def test_convert_with_tool_calls_anthropic():
    """Converts tool call and tool result messages correctly (Anthropic format).

    Anthropic has two differences from OpenAI:
    1. Assistant messages with tool calls include JSON-serialized content
    2. Tool results come as user messages with JSON array content
    """
    from lunette.models.messages import ToolMessage

    # first span: user asks, assistant responds with tool call
    span1_attrs = {
        "gen_ai.prompt.0.role": "system",
        "gen_ai.prompt.0.content": "You are helpful",
        "gen_ai.prompt.1.role": "user",
        "gen_ai.prompt.1.content": "What is 7 times 8?",
        "gen_ai.completion.0.role": "assistant",
        "gen_ai.completion.0.tool_calls.0.name": "multiply",
        "gen_ai.completion.0.tool_calls.0.arguments": '{"a": 7, "b": 8}',
        "gen_ai.completion.0.tool_calls.0.id": "toolu_123",
    }
    span1 = MagicMock()
    span1.attributes = span1_attrs
    span1.start_time = 100

    # second span: includes previous messages + tool result (Anthropic format)
    # note: assistant content is JSON-serialized tool_use blocks
    # note: tool result comes as role=user with JSON content
    span2_attrs = {
        "gen_ai.prompt.0.role": "system",
        "gen_ai.prompt.0.content": "You are helpful",
        "gen_ai.prompt.1.role": "user",
        "gen_ai.prompt.1.content": "What is 7 times 8?",
        "gen_ai.prompt.2.role": "assistant",
        "gen_ai.prompt.2.content": '[{"id": "toolu_123", "input": {"a": 7, "b": 8}, "name": "multiply", "type": "tool_use"}]',
        "gen_ai.prompt.2.tool_calls.0.name": "multiply",
        "gen_ai.prompt.2.tool_calls.0.arguments": '{"a": 7, "b": 8}',
        "gen_ai.prompt.2.tool_calls.0.id": "toolu_123",
        "gen_ai.prompt.3.role": "user",  # Anthropic sends tool results as user messages
        "gen_ai.prompt.3.content": '[{"type": "tool_result", "tool_use_id": "toolu_123", "content": "56"}]',
        "gen_ai.completion.0.role": "assistant",
        "gen_ai.completion.0.content": "7 times 8 is 56.",
    }
    span2 = MagicMock()
    span2.attributes = span2_attrs
    span2.start_time = 200

    messages = convert_spans_to_messages([span1, span2])

    # should be: system, user, assistant (with tool call), tool, assistant (final)
    assert len(messages) == 5

    assert isinstance(messages[0], SystemMessage)
    assert messages[0].content == "You are helpful"

    assert isinstance(messages[1], UserMessage)
    assert messages[1].content == "What is 7 times 8?"

    assert isinstance(messages[2], AssistantMessage)
    assert messages[2].content == ""  # JSON content should be ignored
    assert messages[2].tool_calls is not None
    assert len(messages[2].tool_calls) == 1
    assert messages[2].tool_calls[0].function == "multiply"
    assert messages[2].tool_calls[0].id == "toolu_123"

    assert isinstance(messages[3], ToolMessage)  # should be TOOL, not USER
    assert messages[3].content == "56"
    assert messages[3].tool_call.id == "toolu_123"
    assert messages[3].tool_call.function == "multiply"

    assert isinstance(messages[4], AssistantMessage)
    assert messages[4].content == "7 times 8 is 56."


# --- Test context var ---


def test_trajectory_id_var_default():
    """Default value is None."""
    assert trajectory_context_id_var.get() is None


def test_trajectory_id_var_set_reset():
    """Can set and reset trajectory_id."""
    token = trajectory_context_id_var.set("test-id")
    assert trajectory_context_id_var.get() == "test-id"

    trajectory_context_id_var.reset(token)
    assert trajectory_context_id_var.get() is None


# --- Integration test with mocked OTel ---


@pytest.fixture(autouse=True)
def reset_tracer_state():
    """Reset global tracer state before and after each test."""
    import lunette.tracing.tracer as tracer_module

    tracer_module._initialized = False
    yield
    tracer_module._initialized = False


@pytest.fixture
def mock_instrumentors():
    """Mock both OpenAI and Anthropic instrumentors."""
    with (
        patch("lunette.tracing.tracer.OpenAIInstrumentor") as mock_openai,
        patch("lunette.tracing.tracer.AnthropicInstrumentor") as mock_anthropic,
    ):
        yield mock_openai, mock_anthropic


@pytest.mark.asyncio
async def test_tracer_basic_flow(mock_instrumentors):
    """Test full tracer flow with mocked OTel and client."""
    from lunette.tracing import LunetteTracer

    tracer = LunetteTracer(task="test-task", model="gpt-4")

    # manually inject a span into the collector (simulating OpenAI call)
    mock_span = _make_llm_span(
        prompts=[{"role": "user", "content": "Test question"}],
        completions=[{"role": "assistant", "content": "Test answer"}],
    )

    # simulate what would happen inside a trajectory context
    async with tracer.trajectory(sample=1) as ctx:
        # inject span with the trajectory_id that was set
        mock_span.attributes["lunette.trajectory_id"] = ctx._trajectory_id
        tracer._collector.on_end(mock_span)

    # trajectory should be buffered
    assert len(tracer._trajectories) == 1
    traj = tracer._trajectories[0]
    assert traj.sample == 1
    assert len(traj.messages) == 2
    assert traj.messages[0].content == "Test question"
    assert traj.messages[1].content == "Test answer"


@pytest.mark.asyncio
async def test_tracer_nested_trajectories_error(mock_instrumentors):
    """Nested trajectories should raise an error."""
    from lunette.tracing import LunetteTracer

    tracer = LunetteTracer(task="test", model="gpt-4")

    with pytest.raises(RuntimeError, match="Nested trajectories"):
        async with tracer.trajectory(sample=1):
            async with tracer.trajectory(sample=2):
                pass


@pytest.mark.asyncio
async def test_tracer_multiple_instances_error(mock_instrumentors):
    """Creating a second tracer should raise an error (one tracer per process)."""
    from lunette.tracing import LunetteTracer

    _ = LunetteTracer(task="test1", model="gpt-4")

    with pytest.raises(RuntimeError, match="Only one LunetteTracer"):
        LunetteTracer(task="test2", model="gpt-4")
