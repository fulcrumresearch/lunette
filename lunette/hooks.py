"""Inspect AI hooks for auto-saving trajectories."""

import logging
from pathlib import Path

from inspect_ai.hooks import Hooks, SampleEnd, TaskStart, hooks

from lunette.client import LunetteClient
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


@hooks(name="lunette_logger", description="Auto-save trajectories to backend")
class LunetteLoggerHook(Hooks):
    """
    Hook that automatically saves trajectories to the backend at task end.

    This hook:
    1. Converts all samples from the task log to Trajectory objects
    2. Batches them together
    3. POSTs them to the backend /save endpoint
    4. Handles errors gracefully without breaking the evaluation

    Configuration:
        The hook uses LunetteClient which reads from ~/.lunette/config.json
        or environment variables:
        - LUNETTE_BACKEND_URL: Backend API URL
        - LUNETTE_API_KEY: API key for authentication
        - LUNETTE_BATCH_SIZE: Number of trajectories per batch (default: 10)
    """

    def __init__(self):
        super().__init__()
        self.client = LunetteClient()
        self.task: str | None = None
        self.model: str | None = None

    async def on_task_start(self, data: TaskStart) -> None:
        """
        Called when a task starts. Stores task and model info for later use.

        Args:
            data: Task start data containing the eval spec
        """
        self.task = data.spec.task
        self.model = data.spec.model
        logger.info(f"Starting task '{self.task}' with model '{self.model}'")

    async def on_sample_end(self, data: SampleEnd) -> None:
        """
        Called when a sample completes. Saves the trajectory to the backend.

        Args:
            data: Sample end data containing the completed sample
        """
        if self.task is None or self.model is None:
            logger.error("Task or model not set - skipping trajectory save")
            return

        try:
            trajectory = Trajectory.from_inspect(
                task=self.task,
                model=self.model,
                sample=data.sample,
            )

            saved = await self.client.save_trajectories(
                [trajectory]
            )  # todo: check return type here, also add batching

            if saved:
                logger.info(f"Saved trajectory for sample {trajectory.sample}")

        except Exception as e:
            logger.error(f"Failed to save trajectory for sample {data.sample_id}: {e}")
