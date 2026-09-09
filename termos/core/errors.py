"""TERMOS error types."""


class TermOSError(Exception):
    """Base class for TERMOS errors."""


class ShellError(TermOSError):
    """A shell command failed to parse or run."""


class CommandNotFoundError(ShellError):
    """The shell does not recognize the requested command."""

    def __init__(self, command: str) -> None:
        self.command = command
        super().__init__(f"termos: command not found: {command}")
