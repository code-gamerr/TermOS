"""Interactive TERMOS shell."""

from __future__ import annotations

import os
import shlex
from collections.abc import Callable
from typing import TYPE_CHECKING

from core.constants import DEFAULT_USER, HOME_PATH
from core.errors import (
    AlreadyExistsError,
    CommandNotFoundError,
    DirectoryNotEmptyError,
    FileSystemError,
    NotADirectoryError,
    NotAFileError,
    NotFoundError,
    ShellError,
)
from filesystem.directory import Directory
from filesystem.node import Node

if TYPE_CHECKING:
    from kernel.kernel import Kernel

CommandHandler = Callable[[list[str]], None]


class Shell:
    """Interactive command shell.

    Owns prompt, parsing, history, and the built-in commands available in
    this part. Later parts can register more commands on ``commands``.
    """

    def __init__(self, kernel: Kernel, user: str = DEFAULT_USER, cwd: str = HOME_PATH) -> None:
        self._kernel = kernel
        self.user = user
        self.path = kernel.filesystem.abspath(cwd, "/")
        self.history: list[str] = []
        self._running = False
        self.commands: dict[str, CommandHandler] = {
            "help": self._cmd_help,
            "version": self._cmd_version,
            "clear": self._cmd_clear,
            "echo": self._cmd_echo,
            "exit": self._cmd_exit,
            "mkdir": self._cmd_mkdir,
            "cd": self._cmd_cd,
            "pwd": self._cmd_pwd,
            "ls": self._cmd_ls,
            "touch": self._cmd_touch,
            "cat": self._cmd_cat,
            "write": self._cmd_write,
            "rm": self._cmd_rm,
            "rmdir": self._cmd_rmdir,
            "tree": self._cmd_tree,
        }

    @property
    def cwd(self) -> str:
        """Working directory as shown in the prompt."""
        return self._kernel.filesystem.display_path(self.path)

    @property
    def prompt(self) -> str:
        """Shell prompt, e.g. ``root@termos:~$ ``."""
        return f"{self.user}@{self._kernel.hostname}:{self.cwd}$ "

    def run(self) -> None:
        """Read and execute commands until the user exits."""
        self._running = True
        self._enable_readline_history()
        while self._running:
            try:
                line = input(self.prompt)
            except EOFError:
                print()
                self._running = False
                break