import os
import shlex
import tempfile
from pathlib import Path
from typing import Literal, NamedTuple, Union, overload, Dict

from typing_extensions import override

from inspect_ai.util._subprocess import ExecResult, subprocess

from inspect_ai.util._sandbox.environment import (
    SandboxEnvironment,
    SandboxEnvironmentConfigType,
)
from inspect_ai.util._sandbox.registry import sandboxenv
from inspect_ai.util._sandbox.docker.cleanup import (
    cli_cleanup,
    project_cleanup,
    project_cleanup_shutdown,
    project_cleanup_startup,
    project_record_auto_compose,
    project_startup,
)
from inspect_ai.util._sandbox.docker.compose import (
    compose_build,
    compose_cleanup_images,
    compose_services,
)
from inspect_ai.util._sandbox.docker.config import CONFIG_FILES, DOCKERFILE
from inspect_ai.util._sandbox.docker.prereqs import validate_prereqs
from inspect_ai.util._sandbox.docker.util import ComposeProject, task_project_name

from lunette.client import LunetteClient
from lunette.sandbox import Sandbox
from lunette.logger import get_lunette_logger

logger = get_lunette_logger(__name__)


def _env_prefix(env: Dict[str, str]) -> str:
    if not env:
        return ""
    assigns = " ".join(f"{k}={shlex.quote(v)}" for k, v in env.items())
    return f"export {assigns} && "


@sandboxenv(name="lunette")
class LunetteSandboxEnvironment(SandboxEnvironment):
    @classmethod
    def config_files(cls) -> list[str]:
        return CONFIG_FILES + [DOCKERFILE]

    @classmethod
    def default_concurrency(cls) -> int | None:
        count = os.cpu_count() or 1
        return 2 * count

    @classmethod
    async def task_init(
        cls, task_name: str, config: SandboxEnvironmentConfigType | None
    ) -> None:
        # validate prereqs
        await validate_prereqs()

        # intialize project cleanup
        project_cleanup_startup()

        try:
            # create project
            project = await ComposeProject.create(
                name=task_project_name(task_name), config=config
            )

            # record auto compose
            project_record_auto_compose(project)

            # build containers which are out of date
            await compose_build(project)

            # cleanup images created during build
            await compose_cleanup_images(project, timeout=60)

            services = await compose_services(project)

            if len(services) > 1:
                raise ValueError("Only one service is allowed")

        except BaseException as ex:
            await project_cleanup_shutdown(True)
            raise ex

    @override
    @classmethod
    async def task_init_environment(
        cls, config: SandboxEnvironmentConfigType | None, metadata: dict[str, str]
    ) -> dict[str, str]:
        # get interpolated environment variables and underlying config path and text
        resolved = resolve_config_environment(config, metadata)

        # don't even consider sample-specific environment if there are no sample metadata refs
        if resolved and len(resolved.env) > 0:
            # resolve images using our env vars
            result = await subprocess(
                ["docker", "compose", "-f", resolved.config_file, "config", "--images"],
                env=resolved.env,
            )
            if result.success:
                # look through the images, if one of them doesn't apper in the the
                # config text then this compose file requires its own sample specific
                # environment for resolution
                images = result.stdout.strip().splitlines()
                for image in images:
                    if image not in resolved.config_text:
                        return resolved.env
            else:
                logger.warning(
                    f"Unexpected error reading compose file '{resolved.config_file}': {result.stderr}"
                )

        # no per-sample environment required
        return {}

    @override
    @classmethod
    async def sample_init(
        cls,
        task_name: str,
        config: SandboxEnvironmentConfigType | None,
        metadata: dict[str, str],
    ) -> dict[str, SandboxEnvironment]:
        # create environment variables for sample metadata
        resolved = resolve_config_environment(config, metadata)
        env = resolved.env if resolved is not None else {}

        # create project
        from inspect_ai.log._samples import sample_active

        sample = sample_active()
        project = await ComposeProject.create(
            name=task_project_name(task_name),
            config=config,
            sample_id=sample.sample.id if sample is not None else None,
            epoch=sample.epoch if sample is not None else None,
            env=env,
        )

        # note that the project is running
        project_startup(project)

        try:
            # enumerate the services that will be created
            services = await compose_services(project)
            name, service = services.popitem()
            client = LunetteClient()
            sandbox = await client.create_sandbox(service)

            # Add sandbox container_id to sample metadata for trajectory tracking
            if sample is not None:
                if sample.sample.metadata is None:
                    sample.sample.metadata = {}
                sample.sample.metadata["lunette_sandbox_id"] = sandbox.container_id

            return {
                name: LunetteSandboxEnvironment(
                    sandbox=sandbox, client=client, service=name, project=project
                )
            }

        except BaseException as ex:
            await project_cleanup(project, True)
            raise ex

    @override
    @classmethod
    async def sample_cleanup(
        cls,
        task_name: str,
        config: SandboxEnvironmentConfigType | None,
        environments: dict[str, SandboxEnvironment],
        interrupted: bool,
    ) -> None:
        # if we were interrupted then wait unil the end of the task to cleanup
        # (this enables us to show output for the cleanup operation)
        pass

    @classmethod
    async def task_cleanup(
        cls, task_name: str, config: SandboxEnvironmentConfigType | None, cleanup: bool
    ) -> None:
        await project_cleanup_shutdown(cleanup)

    @classmethod
    async def cli_cleanup(cls, id: str | None) -> None:
        await cli_cleanup(id)

    def __init__(
        self,
        sandbox: Sandbox,
        client: LunetteClient,
        project: ComposeProject,
        service: str,
    ) -> None:
        super().__init__()
        self.client = client
        self.sandbox = sandbox
        self._project = project
        self._service = service
        # Working dir is fetched lazily since aexec is async
        self._working_dir: str | None = None

    async def _ensure_working_dir(self) -> str:
        """Lazily get working directory."""
        if self._working_dir is None:
            result = await self.sandbox.aexec("pwd")
            self._working_dir = result.stdout.strip()
        return self._working_dir

    @override
    async def exec(
        self,
        cmd: list[str],
        input: str | bytes | None = None,
        cwd: str | None = None,
        env: dict[str, str] = {},
        user: str | None = None,
        timeout: int | None = None,
        timeout_retry: bool = True,
        concurrency: bool = True,
    ) -> ExecResult[str]:
        # ignoring a bunch of shit

        from inspect_ai.solver._task_state import sample_state

        if not hasattr(self, "_metadata_set"):
            state = sample_state()
            if state.metadata is None:
                state.metadata = {}
            state.metadata["lunette_sandbox_id"] = self.sandbox.container_id
            self._metadata_set = True

        stdin_redir = ""
        cleanup = ""
        prefix = _env_prefix(env)

        if cwd is None:
            cwd = await self._ensure_working_dir()

        if input is not None:
            # stage stdin to a temp file in container
            tmp = f"/tmp/inspect_stdin_{os.getpid()}"
            await self.write_file(tmp, input)
            stdin_redir = f" < {shlex.quote(tmp)}"
            cleanup = f" ; rm -f {shlex.quote(tmp)}"

        cd_cmd = f"cd {shlex.quote(cwd)}" if cwd else ""
        cmd_str = " ".join(shlex.quote(arg) for arg in cmd)
        final_cmd = f"{prefix}{cd_cmd} && {cmd_str}{stdin_redir}{cleanup}"

        logger.info(f"Executing command: {final_cmd}")

        exec_result = await self.sandbox.aexec(
            final_cmd,
            timeout=timeout,
        )

        # Log the result
        if exec_result.exit_code == 0:
            logger.info(f"Command succeeded (exit_code={exec_result.exit_code})")
            if exec_result.stdout:
                logger.debug(
                    f"stdout: {exec_result.stdout[:500]}"
                )  # Truncate long output
        else:
            logger.error(f"Command failed (exit_code={exec_result.exit_code})")
            if exec_result.stderr:
                logger.error(f"stderr: {exec_result.stderr}")
            if exec_result.stdout:
                logger.debug(f"stdout: {exec_result.stdout[:500]}")

        parsed_result = ExecResult(
            stdout=exec_result.stdout,
            stderr=exec_result.stderr,
            returncode=exec_result.exit_code,
            success=exec_result.exit_code == 0,
        )

        return parsed_result

    @override
    async def write_file(
        self, file: str, contents: str | bytes, *, text: bool = True
    ) -> None:
        # Create temporary local file
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as tmp:
            if isinstance(contents, str):
                tmp.write(contents.encode("utf-8"))
            else:
                tmp.write(contents)
            tmp_path = tmp.name

        try:
            # Upload to sandbox
            await self.sandbox.aupload(tmp_path, file)
        finally:
            # Clean up temp file
            Path(tmp_path).unlink(missing_ok=True)

    @overload
    async def read_file(self, file: str, text: Literal[True] = True) -> str: ...

    @overload
    async def read_file(self, file: str, text: Literal[False]) -> bytes: ...

    @override
    async def read_file(self, file: str, text: bool = True) -> Union[str, bytes]:
        # Download to temp file
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name

        try:
            await self.sandbox.adownload(file, tmp_path)

            with open(tmp_path, "r" if text else "rb") as f:
                return f.read()
        finally:
            Path(tmp_path).unlink(missing_ok=True)


class ConfigEnvironment(NamedTuple):
    config_file: str
    config_text: str
    env: dict[str, str]


def resolve_config_environment(
    config: SandboxEnvironmentConfigType | None,
    metadata: dict[str, str],
) -> ConfigEnvironment | None:
    # create environment variables for sample metadata
    if isinstance(config, str) and Path(config).exists():
        # read the config file
        config_file = config
        with open(config, "r", encoding="utf-8") as f:
            config_text = f.read()

        # only add metadata files if the key is in the file
        env: dict[str, str] = {}
        for key, value in metadata.items():
            key = f"SAMPLE_METADATA_{key.replace(' ', '_').upper()}"
            if key in config_text:
                env[key] = str(value)

        # return resolved
        return ConfigEnvironment(config_file, config_text, env)
    else:
        return None
