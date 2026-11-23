"""Exception types shared by the engine.

Every refusal names the rule or door that refused and, where one exists, the fix. Nothing in the
engine catches these to carry on: a refusal stops the command (fail loudly).
"""


class TreerouteError(Exception):
    """Base class for every engine error."""


class RefusedError(TreerouteError):
    """A guard or a closed door refused the request.

    ``rule`` is the rule id (for example ``G-NOOVERWRITE``); ``fix`` says what to do instead.
    """

    def __init__(self, rule, message, fix=None):
        self.rule = rule
        self.fix = fix
        text = "[%s] %s" % (rule, message)
        if fix:
            text += " Fix: %s" % fix
        super().__init__(text)


class LaunchError(TreerouteError):
    """The launcher could not pin the thread pools or verify the backend."""


class RegistryError(TreerouteError):
    """The shipped-results registry is missing or unreadable, so no write can be checked."""


class RegistryRefusal(RefusedError):
    """A write under a protected (shipped) path was refused."""


class ResumeRefusal(RefusedError):
    """A resume was refused (finished run, fingerprint mismatch, name collision)."""


class PreflightRefusal(RefusedError):
    """Disk, RAM, orphan files or the heavy-job lock refused the run."""


class TempMatrixError(TreerouteError):
    """A temporary memory-mapped matrix could not be created or deleted cleanly."""


class PackageError(TreerouteError):
    """A dataset package failed to load (closed folder, schema, include hash)."""


class UnsetConstantError(TreerouteError):
    """An engine constant whose value is not fixed yet was read."""


class NotBuiltError(TreerouteError):
    """The requested engine part is a stub in the skeleton."""
