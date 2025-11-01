"""Inspect AI hooks for auto-saving trajectories."""

import logging
import os
from pathlib import Path

from inspect_ai.hooks import Hooks, TaskEnd, hooks

from lunette.client import LunetteClient
from lunette.models import Trajectory, sample_to_trajectory

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

    async def on_sample_end(self, data: TaskEnd) -> None:
        """
        Called when a task completes. Saves all trajectories to the backend.

        Args:
            data: Task end data containing the complete task log
        """

        trajectory = sample_to_trajectory(
            sample=data.sample,  # get model name?
        )
        # Add run_id and eval_id to metadata
        if trajectory.metadata is None:
            trajectory.metadata = {}

        try:
            saved = await self.client.save_trajectories(
                [trajectory]
            )  # todo: check return type here, also add batching
            if saved:
                logger.info(f"Saved trajectory {trajectory.id}")

        except Exception as e:
            logger.error(f"Failed to save: {e}")
