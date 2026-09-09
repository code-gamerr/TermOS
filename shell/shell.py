"""Interactive TERMOS shell."""

from __future__ import annotations

import os
import shlex
from collections.abc import Callable
from typing import TYPE_CHECKING

from core.constants import DEFAULT_CWD, DEFAULT_USER
from core.errors import CommandNotFoundError, ShellError

if TYPE_CHECKING:
    from kernel.kernel import Kernel

CommandHandler = Callable[[list[str]], None]


class Shell:
    """Interactive command shell.

    Owns prompt, parsing, history, and the built-in commands available in
    this part. Later parts can register more commands on ``commands``.
    """

    def __init__(self, kernel: Kernel, user: str = DEFAULT_USER, cwd: str = DEFAULT_CWD) -> None:
        self._kernel = kernel
        self.user = user
        self.cwd = cwd
        self.history: list[str] = []
        self._running = False
        self.commands: dict[str, CommandHandler] = {
            "help": self._cmd_help,
            "version": self._cmd_version,
            "clear": self._cmd_clear,
            "echo": self._cmd_echo,
            "exit": self._cmd_exit,
        }

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
            except KeyboardInterrupt:
                print()
                continue

            if not line.strip():
                continue

            self.history.append(line)
            self.execute(line)

    def execute(self, line: str) -> None:
        """Parse and run a single command line."""
        try:
            argv = self.parse(line)
        except ShellError as exc:
            print(exc)
            return

        if not argv:
            return

        name, args = argv[0], argv[1:]
        handler = self.commands.get(name)
        if handler is None:
            print(CommandNotFoundError(name))
            return

        try:
            handler(args)
        except ShellError as exc:
            print(exc)

    @staticmethod
    def parse(line: str) -> list[str]:
        """Split a command line, honoring quotes and collapsing extra spaces."""
        try:
            return shlex.split(line, posix=True)
        except ValueError as exc:
            raise ShellError(f"termos: syntax error: {exc}") from exc

    def _enable_readline_history(self) -> None:
        # ponytail: readline only — arrow-key history on Windows needs a line editor later.
        try:
            import readline
        except ImportError:
            return
        readline.set_history_length(500)

    def _cmd_help(self, _args: list[str]) -> None:
        print("TERMOS commands:")
        for name in self.commands:
            print(f"  {name}")

    def _cmd_version(self, _args: list[str]) -> None:
        print(f"{self._kernel.name} v{self._kernel.version}")

    def _cmd_clear(self, _args: list[str]) -> None:
        if os.name == "nt":
            os.system("cls")
        else:
            print("\033[2J\033[H", end="", flush=True)

    def _cmd_echo(self, args: list[str]) -> None:
        print(" ".join(args))

    def _cmd_exit(self, _args: list[str]) -> None:
        self._running = False
