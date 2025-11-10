"""Lunette SDK Client for managing sandboxes."""

import json
import tarfile
import tempfile
from pathlib import Path
from typing import List, Optional

import httpx
from inspect_ai.util._sandbox.docker.service import ComposeService

from lunette.models.run import Run
from lunette.sandbox import Sandbox
from lunette.logger import get_lunette_logger

logger = get_lunette_logger(__name__)


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

    By default, the client loads configuration from ~/.lunette/config.json.
    You can override this by providing explicit parameters or a custom config path.

    Example:
        # Load from default config file (~/.lunette/config.json)
        async with LunetteClient() as client:
            service = {"image": "ubuntu:22.04"}
            sandbox = await client.create_sandbox(service)

        # Override with explicit parameters
        async with LunetteClient(
            base_url="https://api.lunette.dev",
            api_key="your-api-key"
        ) as client:
            sandbox = await client.create_sandbox(service)

        # Load from custom config file
        async with LunetteClient(config_path="./my-config.json") as client:
            sandbox = await client.create_sandbox(service)
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        """Initialize the Lunette client.

        If no parameters are provided, loads configuration from ~/.lunette/config.json.
        Explicit parameters override values from the config file.

        Args:
            base_url: Base URL for the Lunette API (e.g., "https://api.lunette.dev")
            api_key: API key for authentication
            timeout: Request timeout in seconds (default: 30)
            config_path: Path to config file (default: ~/.lunette/config.json)

        Raises:
            FileNotFoundError: If config file is needed but not found
            ValueError: If config is invalid or missing required fields
        """
        # Load from config file if needed
        config_data = {}
        config_path = Path.home() / ".lunette" / "config.json"

        if not config_path.exists():
            config_data = {}
        else:
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config_data = json.load(f)
            except json.JSONDecodeError as e:
                raise json.JSONDecodeError(
                    f"Invalid JSON in configuration file {config_path}: {e.msg}",
                    e.doc,
                    e.pos,
                )

        # Use explicit params or fall back to config file
        self.base_url = base_url or config_data.get(
            "base_url", "https://app.fulcrumresearch.ai"
        )
        self.api_key = api_key or config_data.get("api_key", "___")
        self.timeout = timeout or config_data.get("timeout", 200)

        # Validate required fields
        if not self.base_url:
            raise ValueError(
                "base_url is required (provide explicitly or in config file)"
            )
        if not self.api_key:
            raise ValueError(
                "api_key is required (provide explicitly or in config file)"
            )

        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers={"X-API-Key": self.api_key},
        )

    async def create_sandbox(
        self,
        service: ComposeService,
    ) -> Sandbox:
        """Create a sandbox by either pulling an image or building from context.

        Args:
            service: Docker Compose service specification containing either:
                - image: str (pull from registry)
                - build: str | dict (build from context)

        Returns:
            Sandbox instance ready for use

        Raises:
            FileNotFoundError: If build context directory doesn't exist
            ValueError: If response format is invalid
            httpx.HTTPError: For HTTP-related errors
        """
        image_name: Optional[str] = None
        tar_file = None

        if "image" in service and service["image"]:
            image_name = service["image"]
            logger.info(f"Creating sandbox from image: {image_name}")

        if "build" in service and service["build"]:
            # Build path: create tar of build context
            build_dir: Optional[Path] = None

            if isinstance(service["build"], str):
                build_dir = Path(service["build"]).expanduser().resolve()
            elif isinstance(service["build"], dict):
                build_dir = (
                    Path(service["build"].get("context", ".")).expanduser().resolve()
                )

            if build_dir is None or not build_dir.exists() or not build_dir.is_dir():
                raise FileNotFoundError(f"Build context not found: {build_dir}")

            logger.info(f"Creating sandbox from build context: {build_dir}")

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
            tag=result["tag"],
            container_id=result["sandbox_id"],
            service=service,
        )

        logger.info(f"Successfully created sandbox: {sandbox.container_id}")

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

    async def launch_investigation(self, plan: str, limit: int = 10) -> dict:
        """Launch an investigation using a plan YAML.

        Args:
            plan: Investigation plan in YAML format
            limit: Maximum number of trajectories to investigate (default: 10)

        Returns:
            dict with investigation results

        Raises:
            httpx.HTTPError: For HTTP-related errors
        """
        response = await self._client.post(
            "/investigations/run",
            json={"plan": plan, "limit": limit},
            timeout=None,
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
