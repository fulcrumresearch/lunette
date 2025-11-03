from lunette.hooks import LunetteLoggerHook  # registers via @hooks  # noqa: F401


def lunette():
    from lunette.inspect_sandbox import (
        LunetteSandboxEnvironment,
    )  # registers via @sandboxenv

    return LunetteSandboxEnvironment


lunette()
