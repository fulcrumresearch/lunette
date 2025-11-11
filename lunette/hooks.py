"""Inspect AI hooks for auto-saving runs."""

import logging
import uuid
from pathlib import Path

from inspect_ai.hooks import Hooks, SampleEnd, TaskEnd, TaskStart, hooks

from lunette.client import LunetteClient
from lunette.models.run import Run
from lunette.models.trajectory import Trajectory

# Ensure log directory exists
log_dir = Path.home() / ".lunette" / "logs"
log_dir.mkdir(parents=True, exist_ok=True)

# Configure logging to file
log_file = log_dir / "hook.log"
logging.basicConfig(
    filename=str(log_file),
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    force=True,  # Override any existing config
)

logger = logging.getLogger(__name__)


@hooks(name="lunette_logger", description="Auto-save evaluation runs to backend")
class LunetteLoggerHook(Hooks):
    """Hook that automatically saves evaluation runs to the backend.

    This hook buffers all trajectory samples as they complete during an evaluation,
    then uploads the complete Run (with all trajectories) at task end.

    The Run is uploaded as a single atomic operation, ensuring all trajectories
    from an evaluation are grouped together.

    Configuration:
        Uses LunetteClient which reads from ~/.lunette/config.json or environment:
        - LUNETTE_BACKEND_URL: Backend API URL
        - LUNETTE_API_KEY: API key for authentication
    """

    def __init__(self):
        super().__init__()
        self.client = LunetteClient()
        self.task: str | None = None
        self.model: str | None = None
        self.trajectories: list[Trajectory] = []

    async def on_task_start(self, data: TaskStart) -> None:
        """Called when a task starts. Initializes run metadata.

        Args:
            data: Task start data containing the eval spec
        """
        self.task = data.spec.task
        self.model = data.spec.model
        self.trajectories = []

        logger.info(f"Starting task '{self.task}' with model '{self.model}'")

    async def on_sample_end(self, data: SampleEnd) -> None:
        """Called when a sample completes. Buffers the trajectory.

        Args:
            data: Sample end data containing the completed sample
        """
        if self.task is None:
            logger.error("Task not set - skipping trajectory buffer")
            return

        try:
            trajectory = Trajectory.from_inspect(
                sample=data.sample,
            )

            self.trajectories.append(trajectory)
            logger.info(
                f"Buffered trajectory for sample {trajectory.sample} ({len(self.trajectories)} total)"
            )

        except Exception as e:
            logger.error(
                f"Failed to buffer trajectory for sample {data.sample_id}: {e}"
            )

    async def on_task_end(self, data: TaskEnd) -> None:
        """Called when a task completes. Uploads the complete run.

        Args:
            data: Task end data
        """
        if not self.trajectories:
            logger.warning("No trajectories to save")
            return

        if self.task is None:
            logger.error("Task not set - cannot save run")
            return

        try:
            run = Run(
                task=self.task,
                model=self.model,
                trajectories=self.trajectories,
            )

            result = await self.client.save_run(run)

            logger.info(
                f"Saved run {result['run_id']} with {len(result['trajectory_ids'])} trajectories"
            )

        except Exception as e:
            logger.error(f"Failed to save run: {e}")
