"""Tests for the tracing module - no external servers required."""

from __future__ import annotations

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


def _make_openai_span(
    prompts: list[dict],
    completions: list[dict],
    start_time: int = 0,
) -> MagicMock:
    """Create a mock span with OpenAI-style attributes."""
    attrs = {"gen_ai.system": "openai"}

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
    span = _make_openai_span(
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
    span1 = _make_openai_span(
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
    span2 = _make_openai_span(
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


def test_convert_skips_non_openai():
    """Skips spans that aren't from OpenAI."""
    openai_span = _make_openai_span(
        prompts=[{"role": "user", "content": "Hello"}],
        completions=[{"role": "assistant", "content": "Hi!"}],
    )

    other_span = MagicMock()
    other_span.attributes = {"gen_ai.system": "anthropic"}
    other_span.start_time = 0

    messages = convert_spans_to_messages([other_span, openai_span])

    # only the OpenAI span should be processed
    assert len(messages) == 2


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

    tracer_module._active_tracer = None
    tracer_module._tracer_provider = None
    yield
    tracer_module._active_tracer = None
    tracer_module._tracer_provider = None


@pytest.mark.asyncio
async def test_tracer_basic_flow():
    """Test full tracer flow with mocked OTel and client."""
    # patch OpenAI instrumentation to avoid actually instrumenting
    mock_instrumentor = MagicMock()
    mock_instrumentor.is_instrumented_by_opentelemetry = False
    with patch(
        "lunette.tracing.tracer.OpenAIInstrumentor", return_value=mock_instrumentor
    ):
        from lunette.tracing import LunetteTracer

        tracer = LunetteTracer(task="test-task", model="gpt-4")

        # manually inject a span into the collector (simulating OpenAI call)
        mock_span = _make_openai_span(
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
async def test_tracer_nested_trajectories_error():
    """Nested trajectories should raise an error."""
    mock_instrumentor = MagicMock()
    mock_instrumentor.is_instrumented_by_opentelemetry = False
    with patch(
        "lunette.tracing.tracer.OpenAIInstrumentor", return_value=mock_instrumentor
    ):
        from lunette.tracing import LunetteTracer

        tracer = LunetteTracer(task="test", model="gpt-4")

        with pytest.raises(RuntimeError, match="Nested trajectories"):
            async with tracer.trajectory(sample=1):
                async with tracer.trajectory(sample=2):
                    pass


@pytest.mark.asyncio
async def test_tracer_multiple_instances_error():
    """Creating a second tracer without closing the first should raise an error."""
    mock_instrumentor = MagicMock()
    mock_instrumentor.is_instrumented_by_opentelemetry = False
    with patch(
        "lunette.tracing.tracer.OpenAIInstrumentor", return_value=mock_instrumentor
    ):
        from lunette.tracing import LunetteTracer

        _ = LunetteTracer(task="test1", model="gpt-4")

        with pytest.raises(RuntimeError, match="Only one LunetteTracer"):
            LunetteTracer(task="test2", model="gpt-4")

        # after closing, we can create a new one
        import lunette.tracing.tracer as tracer_module

        tracer_module._active_tracer = None  # simulate close()

        tracer2 = LunetteTracer(task="test2", model="gpt-4")
        assert tracer2.task == "test2"
