"""Lunette SDK Sandbox operations."""

import httpx
from typing import TYPE_CHECKING, Optional

from inspect_ai.util._sandbox.docker.service import ComposeService

if TYPE_CHECKING:
    from lunette.client import LunetteClient


class SandboxDestroyedError(Exception):
    """Raised when attempting to use a destroyed sandbox."""

    pass


class ExecResult:
    """Result from executing a command in a sandbox."""

    def __init__(
        self,
        stdout: str,
        stderr: str,
        exit_code: int,
        success: bool,
    ):
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = exit_code
        self.success = success

    def __repr__(self) -> str:
        return f"ExecResult(exit_code={self.exit_code}, success={self.success})"


class Sandbox:
    """Represents a running sandbox environment.

    Provides async operations for interacting with remote sandbox instances
    managed by the Fulcrum backend service.

    Example:
        async with client.create_sandbox(image="ubuntu:22.04") as sandbox:
            result = await sandbox.aexec("echo 'hello'")
            print(result.stdout)

            await sandbox.aupload("./script.py", "/workspace/script.py")
            result = await sandbox.aexec("python /workspace/script.py")
    """

    def __init__(
        self,
        client: "LunetteClient",
        tag: str,
        container_id: str,
        service: ComposeService,
    ):
        """Initialize sandbox instance.

        Args:
            client: LunetteClient instance for API communication
            tag: Docker image tag for this sandbox
            container_id: Docker container ID for this sandbox
            service: Docker Compose service specification
        """
        self.client = client
        self.tag = tag
        self.container_id = container_id
        self.service = service
        self._destroyed = False

    async def aexec(
        self,
        cmd: str,
        timeout: Optional[int] = None,
        cwd: Optional[str] = None,
        env: Optional[dict[str, str]] = None,
    ) -> ExecResult:
        """Execute a command in the sandbox asynchronously.

        Args:
            cmd: Command to execute
            timeout: Optional timeout in seconds (not yet supported by backend)
            cwd: Working directory for command execution (not yet supported by backend)
            env: Environment variables to set (not yet supported by backend)

        Returns:
            ExecResult with stdout, stderr, and exit code

        Raises:
            SandboxDestroyedError: If sandbox has been destroyed
            SandboxTimeoutError: If command times out
            SandboxError: For other sandbox-related errors
        """
        if self._destroyed:
            raise SandboxDestroyedError(
                f"Sandbox {self.container_id} has been destroyed"
            )

        # Make HTTP POST to /sandboxes/{container_id}/exec
        response = await self.client._client.post(
            f"/sandboxes/{self.container_id}/exec", json={"command": cmd}
        )

        response.raise_for_status()
        result = response.json()

        return ExecResult(
            stdout=result["stdout"],
            stderr=result["stderr"],
            exit_code=result["exit_code"],
            success=(result["exit_code"] == 0),
        )

    async def aupload(
        self,
        local_path: str,
        remote_path: str,
    ) -> None:
        """Upload a file to the sandbox asynchronously.

        Args:
            local_path: Path to local file
            remote_path: Destination path in sandbox

        Raises:
            FileNotFoundError: If local file doesn't exist
            SandboxDestroyedError: If sandbox has been destroyed
            SandboxError: For other sandbox-related errors
        """
        if self._destroyed:
            raise SandboxDestroyedError(
                f"Sandbox {self.container_id} has been destroyed"
            )

        # Read local file
        try:
            with open(local_path, "r") as f:
                content = f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Local file not found: {local_path}")

        # POST to write endpoint
        response = await self.client._client.post(
            f"/sandboxes/{self.container_id}/write",
            json={"path": remote_path, "content": content},
        )

        response.raise_for_status()

    async def adownload(
        self,
        remote_path: str,
        local_path: str,
    ) -> None:
        """Download a file from the sandbox asynchronously.

        Args:
            remote_path: Path to file in sandbox
            local_path: Destination path on local filesystem

        Raises:
            FileNotFoundError: If remote file doesn't exist
            SandboxDestroyedError: If sandbox has been destroyed
            SandboxError: For other sandbox-related errors
        """
        if self._destroyed:
            raise SandboxDestroyedError(
                f"Sandbox {self.container_id} has been destroyed"
            )

        # GET from read endpoint
        try:
            response = await self.client._client.get(
                f"/sandboxes/{self.container_id}/read", params={"path": remote_path}
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise FileNotFoundError(f"Remote file not found: {remote_path}")
            raise

        result = response.json()
        content = result["content"]

        # Write to local file
        with open(local_path, "w") as f:
            f.write(content)

    async def destroy(self) -> None:
        """Destroy the sandbox and clean up resources.

        This is idempotent - calling multiple times is safe.
        """
        if self._destroyed:
            return

        # Backend doesn't have DELETE endpoint yet, so just mark as destroyed locally
        # TODO: When backend adds DELETE /sandboxes/{container_id}, call it here
        self._destroyed = True

    def __repr__(self) -> str:
        status = "destroyed" if self._destroyed else "active"
        return f"Sandbox(container_id={self.container_id}, status={status})"
