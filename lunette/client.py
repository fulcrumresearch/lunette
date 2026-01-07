"""Lunette SDK Client for managing sandboxes."""

import json
import os
import tarfile
import tempfile
import uuid
from pathlib import Path
from typing import List, Optional

import httpx
from inspect_ai.util._sandbox.docker.service import ComposeService

from lunette.analysis import AnalysisPlan
from lunette.logger import get_lunette_logger
from lunette.models.investigation import InvestigationResults
from lunette.models.run import Run
from lunette.models.trajectory import Trajectory
from lunette.sandbox import Sandbox

logger = get_lunette_logger(__name__)


def _read_dockerfile(build_dir: Path) -> str:
    """Read Dockerfile from build directory."""
    for name in ("Dockerfile", "dockerfile"):
        p = build_dir / name
        if p.exists():
            return p.read_text()
    raise FileNotFoundError(f"No Dockerfile found in: {build_dir}")


def _read_dockerignore(build_dir: Path) -> List[str]:
    p = build_dir / ".dockerignore"
    if not p.exists():
        return []
    # very light parsing: non-empty, non-comment lines as glob patterns
    rules = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            rules.append(line)
    return rules


def _should_include(root: Path, rel: Path, ignore_rules: List[str]) -> bool:
    """Best-effort .dockerignore: fnmatch on the posix path."""
    if not ignore_rules:
        return True
    import fnmatch

    s = rel.as_posix()
    for pat in ignore_rules:
        if fnmatch.fnmatch(s, pat) or fnmatch.fnmatch("/" + s, pat):
            return False
    return True


def _tar_build_context(src_dir: Path, tar_path: Path) -> None:
    """Create a .tar for the build context honoring a light .dockerignore."""
    ignore = _read_dockerignore(src_dir)
    with tarfile.open(tar_path, "w") as tar:
        for p in src_dir.rglob("*"):
            if not p.is_file():
                continue
            rel = p.relative_to(src_dir)
            if _should_include(src_dir, rel, ignore):
                tar.add(p, arcname=str(rel))


class LunetteClient:
    """Client for interacting with the Lunette backend API.

    Provides methods for creating and managing sandbox environments.

    Configuration is loaded from explicit arguments, environment variables,
    or a config file (~/.lunette/config.json).

    Example:

    ```python
    async with LunetteClient() as client:
        sandbox = await client.create_sandbox({"image": "python:3.11-slim"})
        result = await sandbox.aexec("python --version")
        print(result.stdout)
        await sandbox.destroy()
    ```
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: int | None = None,
    ) -> None:
        """Initialize the Lunette client.

        Args:
            api_key: API key for authentication
            base_url: Base URL for the Lunette API
            timeout: Request timeout in seconds

        Raises:
            ValueError: If no API key is found
        """
        config = self._load_config_file()

        # priority: explicit args > env vars > config file > defaults
        self.api_key = api_key or os.environ.get("LUNETTE_API_KEY") or config.get("api_key")
        self.base_url = (
            base_url or os.environ.get("LUNETTE_BASE_URL") or config.get("base_url", "https://lunette.dev/api")
        )
        self.timeout = timeout or config.get("timeout", 200)

        if not self.api_key:
            raise ValueError(
                "No API key found. Either:\n"
                "  - Set LUNETTE_API_KEY environment variable\n"
                "  - Add api_key to ~/.lunette/config.json\n"
                "  - Pass api_key to LunetteClient()"
            )

        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers={"X-API-Key": self.api_key},
        )

    @staticmethod
    def _load_config_file() -> dict:
        """Load config from ~/.lunette/config.json (or $LUNETTE_HOME/config.json)."""
        home = os.environ.get("LUNETTE_HOME", Path.home() / ".lunette")
        config_path = Path(home) / "config.json"
        if not config_path.exists():
            return {}
        return json.loads(config_path.read_text())

    async def create_sandbox(
        self,
        service: ComposeService | Path | str,
    ) -> Sandbox:
        """Create a sandbox by either pulling an image or building from context.

        Args:
            service: One of:
                - Path or str: Path to a directory containing a Dockerfile
                - dict: Docker Compose service specification with 'image' or 'build' key

        Returns:
            Sandbox instance ready for use

        Raises:
            FileNotFoundError: If build context directory doesn't exist
            ValueError: If response format is invalid
            httpx.HTTPError: For HTTP-related errors
        """
        # convert path to service dict
        if isinstance(service, (Path, str)):
            service = {"build": {"context": str(service)}}
        image_name: Optional[str] = None
        tar_file = None
        dockerfile_content: Optional[str] = None

        if "image" in service and service["image"]:
            image_name = service["image"]
            logger.info(f"Creating sandbox from image: {image_name}")

        if "build" in service and service["build"]:
            # Build path: create tar of build context
            build_dir: Optional[Path] = None

            if isinstance(service["build"], str):
                build_dir = Path(service["build"]).expanduser().resolve()
            elif isinstance(service["build"], dict):
                build_dir = Path(service["build"].get("context", ".")).expanduser().resolve()

            if build_dir is None or not build_dir.exists() or not build_dir.is_dir():
                raise FileNotFoundError(f"Build context not found: {build_dir}")

            logger.info(f"Creating sandbox from build context: {build_dir}")

            # Read Dockerfile for Morph backend support
            dockerfile_content = _read_dockerfile(build_dir)

            # Create tar of build context
            with tempfile.NamedTemporaryFile(suffix=".tar", delete=False) as tmp:
                tar_path = Path(tmp.name)

            _tar_build_context(build_dir, tar_path)
            tar_file = open(tar_path, "rb")

        if not image_name and not tar_file:
            raise ValueError("Service must specify either 'image' or 'build'")

        data = {}
        files = {}

        if image_name:
            data["image"] = image_name

        if tar_file:
            files["build_context"] = tar_file

        if dockerfile_content:
            data["dockerfile"] = dockerfile_content

        # Send full service spec as JSON string (includes working_dir, environment, etc.)
        data["service"] = json.dumps(service)

        response = await self._client.post(
            "/sandboxes",
            data=data if data else None,
            files=files if files else None,
        )

        response.raise_for_status()

        # Parse response
        result = response.json()

        if tar_file:
            tar_file.close()
            Path(tar_file.name).unlink(missing_ok=True)

        sandbox = Sandbox(
            client=self,
            sandbox_id=uuid.UUID(result["sandbox_id"]),
            service=service,
        )

        logger.info(f"Successfully created sandbox: {sandbox.sandbox_id}")

        return sandbox

    async def save_run(self, run: Run) -> dict:
        """Save an evaluation run with all its trajectories to the backend.

        This is the primary method for uploading evaluation results. A run represents
        a single execution of an evaluation (e.g., `inspect eval`) that produces
        multiple trajectory samples for the same task and model.

        Args:
            run: Run object containing id, task, model, and list of trajectories

        Returns:
            dict with:
                - run_id: str - The ID of the saved run
                - trajectory_ids: list[str] - IDs of all saved trajectories

        Raises:
            httpx.HTTPError: For HTTP-related errors
            ValueError: If run validation fails
        """
        if not run.trajectories:
            raise ValueError("Cannot save run with empty trajectory list")

        # Serialize run to JSON
        run_dict = run.model_dump()

        response = await self._client.post("/runs/save", json=run_dict)
        response.raise_for_status()
        return response.json()

    async def get_run(self, run_id: str) -> Run:
        """Fetch a run by its ID.

        Args:
            run_id: The ID of the run to fetch

        Returns:
            Run object

        Raises:
            httpx.HTTPError: For HTTP-related errors
        """
        response = await self._client.get(f"/runs/{run_id}")
        response.raise_for_status()
        return Run.model_validate(response.json())

    async def get_trajectory(self, trajectory_id: str) -> Trajectory:
        """Fetch a trajectory by its ID.

        Args:
            trajectory_id: The ID of the trajectory to fetch

        Returns:
            Trajectory object

        Raises:
            httpx.HTTPError: For HTTP-related errors
        """
        response = await self._client.get(f"/trajectories/{trajectory_id}")
        response.raise_for_status()
        return Trajectory.model_validate(response.json())

    async def investigate(
        self,
        run_id: str,
        plan: AnalysisPlan,
        limit: int | None = None,
        batch_size: int | None = None,
    ) -> InvestigationResults:
        """Run an investigation on a run and return results.

        Args:
            run_id: ID of the run to investigate
            plan: AnalysisPlan with prompt, result_schema, filters, model, max_turns
            limit: Max trajectories to investigate
            batch_size: Agents to run concurrently

        Returns:
            InvestigationResults with all trajectory results
        """
        # 1. Launch the investigation
        response = await self._client.post(
            "/investigations/run",
            json={
                "plan": plan.model_dump(mode="python"),
                "run_id": run_id,
                "limit": limit,
                "batch_size": batch_size,
                "blocking": True,  # Wait for completion to get results
            },
            timeout=None,
        )
        response.raise_for_status()
        investigation_run_id = response.json()["run_id"]

        # 2. Fetch the results
        results_response = await self._client.get(f"/investigations/{investigation_run_id}/results")
        results_response.raise_for_status()
        return InvestigationResults.model_validate(results_response.json())

    async def stop_sandboxes(self, sandbox_ids: List[uuid.UUID], save_state: bool = False) -> dict:
        """Stop one or more sandbox containers and optionally save their state.

        This should be called after an evaluation run completes to clean up sandboxes.
        With save_state=True, the sandbox workdir is saved to S3 for later restoration
        during investigations.

        Args:
            sandbox_ids: List of sandbox IDs to stop
            save_state: If True, save sandbox state to S3 before stopping (default: False)

        Returns:
            dict with:
                - stopped: list of successfully stopped sandboxes
                - failed: list of failed sandboxes with error messages

        Raises:
            httpx.HTTPError: For HTTP-related errors
        """
        response = await self._client.post(
            "/sandboxes/stop",
            json={"sandbox_ids": [str(sid) for sid in sandbox_ids], "save_state": save_state},
        )
        response.raise_for_status()
        return response.json()

    async def close(self) -> None:
        """Close the HTTP client and clean up resources."""
        await self._client.aclose()

    async def __aenter__(self) -> "LunetteClient":
        """Enter async context manager."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit async context manager and close client."""
        await self.close()
