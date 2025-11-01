def lunette():
    from lunette.inspect_sandbox import (
        LunetteSandboxEnvironment,
    )  # registers via @sandboxenv

    return LunetteSandboxEnvironment

from lunette.hooks import LunetteLoggerHook


lunette()
