"""Main tracing API for capturing LLM calls as Lunette Trajectories."""

from __future__ import annotations

import functools
import inspect
import os
import uuid
from typing import TYPE_CHECKING, Any, Callable, TypeVar

from opentelemetry import context as otel_context
from opentelemetry import trace
from opentelemetry.instrumentation.anthropic import AnthropicInstrumentor
from opentelemetry.instrumentation.openai import OpenAIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider

from lunette.client import LunetteClient
from lunette.logger import get_lunette_logger
from lunette.models.run import Run
from lunette.models.trajectory import Trajectory
from lunette.tracing.context import trajectory_context_id_var
from lunette.tracing.span_collector import SpanCollector
from lunette.tracing.span_converter import convert_spans_to_messages

if TYPE_CHECKING:
    from opentelemetry.context import Token

F = TypeVar("F", bound=Callable[..., Any])

logger = get_lunette_logger(__name__)


# one tracer per process
_initialized: bool = False


class LunetteTracer:
    """Main entry point for tracing LLM calls as Lunette Trajectories.

    Initializes OpenTelemetry instrumentation for OpenAI and Anthropic,
    and provides trajectory contexts for grouping API calls into samples.

    Example:
        tracer = LunetteTracer(task="math-eval", model="gpt-4o")

        async with tracer.trajectory(sample=1):
            response = await client.chat.completions.create(...)

        await tracer.close()
    """

    def __init__(self, task: str, model: str) -> None:
        """Initialize the Lunette tracing system.

        Args:
            task: The name of the task (e.g., 'math-eval')
            model: The name of the model (e.g., 'gpt-4o')

        Raises:
            RuntimeError: If a LunetteTracer has already been created in this process
        """
        global _initialized
        if _initialized:
            raise RuntimeError(
                "Only one LunetteTracer can be created per process. "
                "LunetteTracer is designed for single-use; restart the process for a new run."
            )
        _initialized = True

        self.task = task
        self.model = model

        self._trajectories: list[Trajectory] = []
        self._collector = SpanCollector()
        self._provider = self._create_tracer_provider()
        self._instrument_clients()

        self._provider.add_span_processor(self._collector)
        self._otel_tracer = self._provider.get_tracer("lunette")

    def _create_tracer_provider(self) -> TracerProvider:
        """Create an isolated tracer provider for Lunette."""
        resource = Resource.create(
            {
                "service.name": "lunette-agent",
                "lunette.task": self.task,
                "lunette.model": self.model,
            }
        )
        return TracerProvider(resource=resource)

    def _instrument_clients(self) -> None:
        """Instrument LLM clients with our isolated tracer provider."""
        # enable message content capture
        os.environ["OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"] = "true"
        os.environ["TRACELOOP_TRACE_CONTENT"] = "true"

        # instrument with explicit tracer_provider for isolation
        OpenAIInstrumentor().instrument(tracer_provider=self._provider)
        logger.debug("Instrumented OpenAI")

        AnthropicInstrumentor().instrument(tracer_provider=self._provider)
        logger.debug("Instrumented Anthropic")

    def trajectory(self, sample: int | str, sandbox_id: str | None = None, **metadata: Any) -> TrajectoryContext:
        """Create a context for tracking a single trajectory (sample).

        Can be used as a context manager or decorator:

        ```python
        # context manager
        async with tracer.trajectory(sample=1):
            ...

        # decorator
        @tracer.trajectory(sample=2)
        async def solve_problem():
            ...
        ```

        Args:
            sample: Sample identifier (e.g., problem number)
            sandbox_id: Optional sandbox container ID for this trajectory
            **metadata: Additional metadata to attach to the trajectory

        Returns:
            TrajectoryContext that can be used as context manager or decorator
        """
        return TrajectoryContext(self, sample, sandbox_id, metadata)

    def _add_trajectory(self, trajectory: Trajectory) -> None:
        """Add a completed trajectory to the buffer."""
        self._trajectories.append(trajectory)

    async def close(self) -> dict[str, Any]:
        """Flush pending traces and upload the Run to the backend.

        Returns:
            Dict with run_id and trajectory_ids from the server response
        """
        if self._provider:
            self._provider.force_flush()

        if not self._trajectories:
            return {"run_id": None, "trajectory_ids": []}

        run = Run(
            id=None,  # let server generate ID for new runs
            task=self.task,
            model=self.model,
            trajectories=self._trajectories,
        )

        async with LunetteClient() as client:
            return await client.save_run(run)


class TrajectoryContext:
    """Context manager / decorator for tracking a single trajectory.

    Supports sync and async usage, as well as decorator syntax.
    """

    def __init__(
        self,
        tracer: LunetteTracer,
        sample: int | str,
        sandbox_id: str | None,
        metadata: dict[str, Any],
    ) -> None:
        self._tracer = tracer
        self._sample = sample
        self._sandbox_id = sandbox_id
        self._metadata = metadata
        self._trajectory_id = str(uuid.uuid4())
        self._token: Any = None
        self._span: trace.Span | None = None
        self._otel_token: Token | None = None

    def _start(self) -> None:
        """Start tracking this trajectory."""
        # check for nested trajectories
        if trajectory_context_id_var.get() is not None:
            raise RuntimeError(
                "Nested trajectories are not supported. Complete the current trajectory before starting a new one."
            )

        # set contextvar for async propagation
        self._token = trajectory_context_id_var.set(self._trajectory_id)

        # start an OTel span to mark trajectory boundaries
        # child spans (LLM calls) will inherit the trajectory_id attribute
        if self._tracer._otel_tracer:
            self._span = self._tracer._otel_tracer.start_span(
                name=f"trajectory_{self._sample}",
                attributes={
                    "lunette.trajectory_id": self._trajectory_id,
                    "lunette.sample": str(self._sample),
                },
            )
            ctx = trace.set_span_in_context(self._span)
            self._otel_token = otel_context.attach(ctx)

    def _end(self, exc_val: BaseException | None) -> None:
        """End tracking and create the Trajectory object."""
        # end OTel span
        if self._span:
            if exc_val:
                self._span.record_exception(exc_val)
                self._span.set_status(trace.Status(trace.StatusCode.ERROR, str(exc_val)))
            self._span.end()

        if self._otel_token is not None:
            otel_context.detach(self._otel_token)

        # reset contextvar
        if self._token is not None:
            trajectory_context_id_var.reset(self._token)

        # collect spans and convert to messages
        spans = self._tracer._collector.pop_trajectory(self._trajectory_id)
        messages = convert_spans_to_messages(spans)

        # add error info to metadata if there was an exception
        metadata = dict(self._metadata)
        if exc_val:
            metadata["error"] = str(exc_val)
            metadata["error_type"] = type(exc_val).__name__

        # create and buffer the trajectory
        trajectory = Trajectory(
            sample=self._sample,
            messages=messages,
            metadata=metadata,
            sandbox_id=self._sandbox_id,
        )
        self._tracer._add_trajectory(trajectory)

    # sync context manager
    def __enter__(self) -> TrajectoryContext:
        self._start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        self._end(exc_val)

    # async context manager
    async def __aenter__(self) -> TrajectoryContext:
        self._start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        self._end(exc_val)

    # decorator support
    def __call__(self, func: F) -> F:
        """Use as a decorator for functions."""
        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                async with self:
                    return await func(*args, **kwargs)

            return async_wrapper  # type: ignore[return-value]
        else:

            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                with self:
                    return func(*args, **kwargs)

            return sync_wrapper  # type: ignore[return-value]
