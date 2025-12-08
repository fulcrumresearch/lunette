"""SpanProcessor that collects spans for later conversion to Trajectories."""

from __future__ import annotations

import threading
from collections import defaultdict
from typing import TYPE_CHECKING

from opentelemetry.context import Context
from opentelemetry.sdk.trace import SpanProcessor

from lunette.tracing.context import trajectory_context_id_var

if TYPE_CHECKING:
    from opentelemetry.sdk.trace import ReadableSpan, Span


class SpanCollector(SpanProcessor):
    """Collects OTel spans keyed by trajectory ID for later conversion.

    This processor accumulates spans in memory rather than exporting them.
    Spans are grouped by trajectory_id and can be retrieved via pop_trajectory().

    Thread-safe: OTel may call on_end() from background threads.
    """

    def __init__(self) -> None:
        self._spans: dict[str, list[ReadableSpan]] = defaultdict(list)
        self._lock = threading.Lock()

    def on_start(self, span: Span, parent_context: Context | None = None) -> None:
        """Called when a span starts. Inject trajectory_id from contextvar."""
        traj_id = trajectory_context_id_var.get()
        if traj_id:
            span.set_attribute("lunette.trajectory_id", traj_id)

    def on_end(self, span: ReadableSpan) -> None:
        """Called when a span ends. Store it if it has a trajectory ID."""
        attributes = span.attributes or {}
        traj_id = attributes.get("lunette.trajectory_id")
        if traj_id:
            with self._lock:
                self._spans[str(traj_id)].append(span)

    def pop_trajectory(self, trajectory_id: str) -> list[ReadableSpan]:
        """Remove and return all spans for a trajectory.

        Args:
            trajectory_id: The trajectory ID to retrieve spans for

        Returns:
            List of spans for this trajectory, sorted by start time.
            Returns empty list if no spans found.
        """
        with self._lock:
            spans = self._spans.pop(trajectory_id, [])
        # sort by start time to ensure proper ordering
        spans.sort(key=lambda s: s.start_time or 0)
        return spans

    def shutdown(self) -> None:
        """Clean up resources."""
        with self._lock:
            self._spans.clear()

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Force flush is a no-op since we don't export."""
        return True
