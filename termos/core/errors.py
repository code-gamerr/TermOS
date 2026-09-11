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


class FileSystemError(TermOSError):
    """A virtual filesystem operation failed."""

    def __init__(self, path: str = "") -> None:
        self.path = path
        super().__init__(path)


class NotFoundError(FileSystemError):
    """The path does not exist."""


class AlreadyExistsError(FileSystemError):
    """A file or directory already exists at the path."""


class NotADirectoryError(FileSystemError):
    """A directory was required, but the path is not one."""


class NotAFileError(FileSystemError):
    """A file was required, but the path is not one."""


class DirectoryNotEmptyError(FileSystemError):
    """A directory still contains entries."""


class PermissionDeniedError(TermOSError):
    """The current user lacks permission for an operation."""

    def __init__(self, message: str = "Permission denied") -> None:
        super().__init__(message)


class AuthenticationError(TermOSError):
    """Login or password verification failed."""


class ProcessError(TermOSError):
    """A simulated process operation failed."""
