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

    def _cmd_mkdir(self, args: list[str]) -> None:
        if not args:
            raise ShellError("mkdir: missing operand")
        path = args[0]
        try:
            self._kernel.filesystem.mkdir(path, self.path)
        except AlreadyExistsError:
            raise ShellError("mkdir: cannot create directory: File exists") from None
        except NotFoundError:
            raise ShellError(f"mkdir: {path}: No such file or directory") from None
        except NotADirectoryError:
            raise ShellError(f"mkdir: {path}: Not a directory") from None

    def _cmd_cd(self, args: list[str]) -> None:
        target = args[0] if args else "~"
        try:
            node = self._kernel.filesystem.resolve(target, self.path)
        except NotFoundError:
            raise ShellError(f"cd: {target}: No such directory") from None
        except NotADirectoryError:
            raise ShellError(f"cd: {target}: Not a directory") from None
        if not isinstance(node, Directory):
            raise ShellError(f"cd: {target}: Not a directory")
        self.path = self._kernel.filesystem.abspath(target, self.path)

    def _cmd_pwd(self, _args: list[str]) -> None:
        print(self.path)

    def _cmd_ls(self, args: list[str]) -> None:
        flags, paths = _split_flags(args)
        target = paths[0] if paths else "."
        try:
            node = self._kernel.filesystem.resolve(target, self.path)
        except NotFoundError:
            raise ShellError(f"ls: {target}: No such file or directory") from None
        if isinstance(node, Directory):
            entries = _dir_entries(node, "a" in flags)
        else:
            entries = [(node.name, node)]
        if "l" in flags:
            for name, entry in entries:
                print(_long_listing(name, entry))
            return
        for name, _entry in entries:
            print(name)

    def _cmd_touch(self, args: list[str]) -> None:
        if not args:
            raise ShellError("touch: missing operand")
        path = args[0]
        try:
            self._kernel.filesystem.touch(path, self.path)
        except NotFoundError:
            raise ShellError(f"touch: {path}: No such file or directory") from None
        except NotAFileError:
            raise ShellError(f"touch: {path}: Is a directory") from None

    def _cmd_cat(self, args: list[str]) -> None:
        if not args:
            raise ShellError("cat: missing operand")
        for path in args:
            try:
                text = self._kernel.filesystem.read(path, self.path)
            except NotFoundError:
                raise ShellError(f"cat: {path}: No such file or directory") from None
            except NotAFileError:
                raise ShellError(f"cat: {path}: Is a directory") from None
            if not text:
                continue
            print(text, end="" if text.endswith("\n") else "\n")

    def _cmd_write(self, args: list[str]) -> None:
        if not args:
            raise ShellError("write: missing operand")
        path, contents = args[0], " ".join(args[1:])
        try:
            self._kernel.filesystem.write(path, contents, self.path)
        except NotFoundError:
            raise ShellError(f"write: {path}: No such file or directory") from None
        except NotAFileError:
            raise ShellError(f"write: {path}: Is a directory") from None

    def _cmd_rm(self, args: list[str]) -> None:
        if not args:
            raise ShellError("rm: missing operand")
        path = args[0]
        try:
            self._kernel.filesystem.remove(path, self.path)
        except NotFoundError:
            raise ShellError(f"rm: {path}: No such file or directory") from None
        except NotAFileError:
            raise ShellError(f"rm: {path}: Is a directory") from None

    def _cmd_rmdir(self, args: list[str]) -> None:
        if not args:
            raise ShellError("rmdir: missing operand")
        path = args[0]
        try:
            self._kernel.filesystem.rmdir(path, self.path)
        except NotFoundError:
            raise ShellError(f"rmdir: {path}: No such file or directory") from None
        except NotADirectoryError:
            raise ShellError(f"rmdir: {path}: Not a directory") from None
        except DirectoryNotEmptyError:
            raise ShellError(f"rmdir: {path}: Directory not empty") from None
        except FileSystemError:
            raise ShellError(f"rmdir: {path}: Invalid argument") from None

    def _cmd_tree(self, args: list[str]) -> None:
        path = args[0] if args else "/"
        try:
            rendered = self._kernel.filesystem.tree(path, self.path)
        except NotFoundError:
            raise ShellError(f"tree: {path}: No such file or directory") from None
        _print_tree(rendered)


def _split_flags(args: list[str]) -> tuple[set[str], list[str]]:
    flags: set[str] = set()
    paths: list[str] = []
    for arg in args:
        if arg.startswith("-") and len(arg) > 1:
            flags.update(arg[1:])
        else:
            paths.append(arg)
    return flags, paths


def _dir_entries(directory: Directory, show_all: bool) -> list[tuple[str, Node]]:
    entries = [(name, child) for name, child in directory.children.items() if show_all or not name.startswith(".")]
    entries.sort(key=lambda item: item[0])
    if show_all:
        parent = directory.parent if isinstance(directory.parent, Directory) else directory
        return [(".", directory), ("..", parent), *entries]
    return entries


def _print_tree(rendered: str) -> None:
    # cp1252 consoles cannot encode box drawing; keep the tree, drop the glyphs.
    try:
        print(rendered)
    except UnicodeEncodeError:
        print(
            rendered.replace("├── ", "|-- ")
            .replace("└── ", "`-- ")
            .replace("│   ", "|   ")
        )


def _long_listing(name: str, node: Node) -> str:
    kind = "d" if isinstance(node, Directory) else "-"
    return f"{kind}{node.mode} {node.owner} {node.size} {name}"
