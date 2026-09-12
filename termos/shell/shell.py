"""Interactive TERMOS shell."""

from __future__ import annotations

import getpass
import os
import shlex
import time
from collections.abc import Callable
from typing import TYPE_CHECKING

from core.constants import HOME_PATH
from core.errors import (
    AlreadyExistsError,
    AuthenticationError,
    CommandNotFoundError,
    DirectoryNotEmptyError,
    FileSystemError,
    NetworkError,
    NotADirectoryError,
    NotAFileError,
    NotFoundError,
    OutOfMemoryError,
    PermissionDeniedError,
    ProcessError,
    ProgramError,
    ShellError,
)
from filesystem.directory import Directory
from filesystem.node import Node
from permissions.permissions import Permissions
from processes.process import ProcessState

if TYPE_CHECKING:
    from kernel.kernel import Kernel
    from users.user import User

CommandHandler = Callable[[list[str]], None]


class Shell:
    """Interactive command shell.

    Uses the kernel for filesystem, users, and processes. Never owns those
    subsystems itself.
    """

    def __init__(self, kernel: Kernel, cwd: str | None = None) -> None:
        self._kernel = kernel
        user = kernel.users.require_current()
        start = cwd or user.home or HOME_PATH
        self.path = kernel.filesystem.abspath(start, "/")
        kernel.filesystem.set_home(user.home)
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
            "whoami": self._cmd_whoami,
            "id": self._cmd_id,
            "su": self._cmd_su,
            "passwd": self._cmd_passwd,
            "users": self._cmd_users,
            "groups": self._cmd_groups,
            "chmod": self._cmd_chmod,
            "chown": self._cmd_chown,
            "ps": self._cmd_ps,
            "top": self._cmd_top,
            "kill": self._cmd_kill,
            "sleep": self._cmd_sleep,
            "jobs": self._cmd_jobs,
            "scheduler": self._cmd_scheduler,
            "free": self._cmd_free,
            "memory": self._cmd_memory,
            "mem": self._cmd_memory,
            "memmap": self._cmd_memmap,
            "ifconfig": self._cmd_ifconfig,
            "ip": self._cmd_ifconfig,
            "ping": self._cmd_ping,
            "netstat": self._cmd_netstat,
            "connections": self._cmd_netstat,
            "route": self._cmd_route,
            "monitor": self._cmd_monitor,
            "run": self._cmd_run,
        }

    @property
    def user(self) -> str:
        """Current username."""
        return self._current().username

    @property
    def cwd(self) -> str:
        """Working directory as shown in the prompt."""
        return self._kernel.filesystem.display_path(self.path)

    @property
    def prompt(self) -> str:
        """Shell prompt, e.g. ``root@termos:~$ ``."""
        return f"{self.user}@{self._kernel.hostname}:{self.cwd}$ "

    def _current(self) -> User:
        return self._kernel.users.require_current()

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
            if self._kernel.programs.has(name):
                try:
                    self._kernel.run_program(self, name, args)
                except OutOfMemoryError:
                    print("TERMOS: Out of memory")
                except ProgramError as exc:
                    print(exc)
                except PermissionDeniedError:
                    print("Permission denied")
                return
            print(CommandNotFoundError(name))
            return

        try:
            handler(args)
        except ShellError as exc:
            print(exc)
        except PermissionDeniedError:
            print("Permission denied")
        except OutOfMemoryError:
            print("TERMOS: Out of memory")
        except ProgramError as exc:
            print(exc)
        except NetworkError as exc:
            print(f"network: {exc}")

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
            self._kernel.filesystem.mkdir(path, self.path, user=self._current())
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
        Permissions.require_execute(self._current(), node)
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
            Permissions.require_read(self._current(), node)
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
            self._kernel.filesystem.touch(path, self.path, user=self._current())
        except NotFoundError:
            raise ShellError(f"touch: {path}: No such file or directory") from None
        except NotAFileError:
            raise ShellError(f"touch: {path}: Is a directory") from None

    def _cmd_cat(self, args: list[str]) -> None:
        if not args:
            raise ShellError("cat: missing operand")
        for path in args:
            try:
                text = self._kernel.filesystem.read(path, self.path, user=self._current())
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
            self._kernel.filesystem.write(path, contents, self.path, user=self._current())
        except NotFoundError:
            raise ShellError(f"write: {path}: No such file or directory") from None
        except NotAFileError:
            raise ShellError(f"write: {path}: Is a directory") from None

    def _cmd_rm(self, args: list[str]) -> None:
        if not args:
            raise ShellError("rm: missing operand")
        path = args[0]
        try:
            self._kernel.filesystem.remove(path, self.path, user=self._current())
        except NotFoundError:
            raise ShellError(f"rm: {path}: No such file or directory") from None
        except NotAFileError:
            raise ShellError(f"rm: {path}: Is a directory") from None

    def _cmd_rmdir(self, args: list[str]) -> None:
        if not args:
            raise ShellError("rmdir: missing operand")
        path = args[0]
        try:
            self._kernel.filesystem.rmdir(path, self.path, user=self._current())
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

    def _cmd_whoami(self, _args: list[str]) -> None:
        print(self.user)

    def _cmd_id(self, _args: list[str]) -> None:
        user = self._current()
        primary = self._kernel.users.get_group_by_gid(user.gid).name
        groups = ",".join(user.groups)
        print(f"uid={user.uid}({user.username}) gid={user.gid}({primary}) groups={groups}")

    def _cmd_su(self, args: list[str]) -> None:
        if not args:
            raise ShellError("su: missing username")
        username = args[0]
        # ponytail: optional second arg for tests / non-interactive demos
        password = args[1] if len(args) > 1 else getpass.getpass("Password: ")
        try:
            user = self._kernel.users.switch_user(username, password)
        except NotFoundError:
            raise ShellError(f"su: user {username} does not exist") from None
        except AuthenticationError:
            raise ShellError("su: Authentication failure") from None
        self._kernel.filesystem.set_home(user.home)
        self.path = user.home

    def _cmd_passwd(self, args: list[str]) -> None:
        current = self._current()
        target_name = args[0] if args else current.username
        if target_name != current.username and not current.is_root:
            raise ShellError("passwd: Permission denied")
        try:
            target = self._kernel.users.get_user(target_name)
        except NotFoundError:
            raise ShellError(f"passwd: user {target_name} does not exist") from None
        if len(args) >= 2:
            new_password = args[1]
        else:
            new_password = getpass.getpass("New password: ")
            confirm = getpass.getpass("Retype password: ")
            if new_password != confirm:
                raise ShellError("passwd: passwords do not match")
        target.set_password(new_password)
        print(f"passwd: password updated for {target_name}")

    def _cmd_users(self, _args: list[str]) -> None:
        print(" ".join(sorted(self._kernel.users.users)))

    def _cmd_groups(self, args: list[str]) -> None:
        if args:
            try:
                user = self._kernel.users.get_user(args[0])
            except NotFoundError:
                raise ShellError(f"groups: {args[0]}: no such user") from None
            print(f"{user.username} : {' '.join(user.groups)}")
            return
        print(" ".join(sorted(self._kernel.users.groups)))

    def _cmd_chmod(self, args: list[str]) -> None:
        if len(args) < 2:
            raise ShellError("chmod: missing operand")
        mode_text, path = args[0], args[1]
        try:
            mode = Permissions.parse_mode(mode_text)
        except ValueError as exc:
            raise ShellError(f"chmod: {exc}") from None
        try:
            self._kernel.filesystem.chmod(path, mode, self.path, user=self._current())
        except NotFoundError:
            raise ShellError(f"chmod: {path}: No such file or directory") from None

    def _cmd_chown(self, args: list[str]) -> None:
        if len(args) < 2:
            raise ShellError("chown: missing operand")
        owner_spec, path = args[0], args[1]
        owner_name, _, group_name = owner_spec.partition(":")
        try:
            owner = self._kernel.users.get_user(owner_name)
        except NotFoundError:
            raise ShellError(f"chown: invalid user: {owner_name}") from None
        group = None
        gid = None
        if group_name:
            try:
                group = self._kernel.users.get_group(group_name)
            except NotFoundError:
                raise ShellError(f"chown: invalid group: {group_name}") from None
            gid = group.gid
            group_name = group.name
        else:
            group_name = None
        try:
            self._kernel.filesystem.chown(
                path,
                owner.username,
                group_name,
                self.path,
                uid=owner.uid,
                gid=gid,
                user=self._current(),
            )
        except NotFoundError:
            raise ShellError(f"chown: {path}: No such file or directory") from None

    def _cmd_ps(self, _args: list[str]) -> None:
        self._print_process_table(self._kernel.processes.active())

    def _cmd_top(self, _args: list[str]) -> None:
        processes = sorted(
            self._kernel.processes.active(),
            key=lambda process: process.cpu_usage,
            reverse=True,
        )
        self._print_process_table(processes)

    def _cmd_kill(self, args: list[str]) -> None:
        if not args:
            raise ShellError("kill: missing pid")
        try:
            pid = int(args[0])
        except ValueError as exc:
            raise ShellError("kill: invalid pid") from exc
        try:
            self._kernel.processes.terminate(pid)
        except NotFoundError:
            raise ShellError(f"kill: ({pid}): No such process") from None
        except ProcessError as exc:
            raise ShellError(f"kill: {exc}") from None
        print(f"[ OK ] Process {pid} terminated.")

    def _cmd_sleep(self, args: list[str]) -> None:
        if not args:
            raise ShellError("sleep: missing operand")
        try:
            seconds = float(args[0])
        except ValueError as exc:
            raise ShellError("sleep: invalid time") from exc
        shell = self._kernel.processes.get(2)
        self._kernel.processes.sleep(shell.pid)
        try:
            time.sleep(max(0.0, seconds))
        finally:
            self._kernel.processes.wake(shell.pid)
            shell.set_state(ProcessState.RUNNING)
            self._kernel.scheduler.running_pid = shell.pid

    def _cmd_jobs(self, _args: list[str]) -> None:
        jobs = [
            self._kernel.processes.get(pid)
            for pid in self._kernel.processes.jobs
            if pid in self._kernel.processes.processes
            and self._kernel.processes.get(pid).state
            in {ProcessState.SLEEPING, ProcessState.WAITING}
        ]
        if not jobs:
            return
        for process in jobs:
            print(f"[{process.pid}]  {process.state.value}  {process.command}")

    def _cmd_scheduler(self, _args: list[str]) -> None:
        status = self._kernel.scheduler.status()
        print("Scheduler")
        print("---------")
        print(f"Algorithm: {status['algorithm']}")
        print(f"Quantum: {status['quantum_ms']}ms")
        print()
        running = status["running"]
        print("RUNNING:")
        if running is None:
            print("(none)")
        else:
            print(f"PID {running.pid} {running.name}")
        print()
        print("READY:")
        ready = status["ready"]
        if not ready:
            print("(none)")
        else:
            for process in ready:
                print(f"PID {process.pid} {process.name}")

    def _cmd_free(self, _args: list[str]) -> None:
        stats = self._kernel.memory.get_memory_stats()
        print(f"{'':14}{'TOTAL':<10}{'USED':<10}{'FREE'}")
        print(
            f"{'RAM':14}"
            f"{int(stats['total_mb'])}MB{'':<6}"
            f"{int(stats['used_mb'])}MB{'':<6}"
            f"{int(stats['free_mb'])}MB"
        )

    def _cmd_memory(self, _args: list[str]) -> None:
        stats = self._kernel.memory.get_memory_stats()
        print("Memory Manager")
        print("--------------")
        print(f"Total:        {int(stats['total_mb'])} MB")
        print(f"Used:         {int(stats['used_mb'])} MB")
        print(f"Free:         {int(stats['free_mb'])} MB")
        print(f"Fragmentation: {stats['fragmentation']}%")
        print(f"Allocator:     {stats['allocator']}")

    def _cmd_memmap(self, _args: list[str]) -> None:
        print(f"{'ADDRESS':<12}{'SIZE':<9}{'STATUS':<12}OWNER")
        for block in self._kernel.memory.get_memory_map():
            status = "FREE" if block.free else "USED"
            size = f"{block.size_mb:g}MB"
            print(f"{block.format_address():<12}{size:<9}{status:<12}{block.owner}")

    def _cmd_ifconfig(self, _args: list[str]) -> None:
        print(self._kernel.network.ifconfig())

    def _cmd_ping(self, args: list[str]) -> None:
        if not args:
            raise ShellError("ping: missing host")
        host = args[0]
        count = 4
        if len(args) >= 3 and args[1] == "-c":
            try:
                count = int(args[2])
            except ValueError as exc:
                raise ShellError("ping: invalid count") from exc
        for line in self._kernel.network.ping(host, count=count):
            print(line)

    def _cmd_netstat(self, _args: list[str]) -> None:
        print(self._kernel.network.netstat())

    def _cmd_route(self, _args: list[str]) -> None:
        print(self._kernel.network.route_table())

    def _cmd_monitor(self, args: list[str]) -> None:
        live = "--live" in args or "-l" in args
        if not live:
            _print_monitor(self._kernel.monitor.render())
            return
        try:
            while True:
                if os.name == "nt":
                    os.system("cls")
                else:
                    print("\033[2J\033[H", end="", flush=True)
                _print_monitor(self._kernel.monitor.render())
                print("\n(Ctrl+C to exit)")
                time.sleep(1.0)
        except KeyboardInterrupt:
            print()

    def _cmd_run(self, args: list[str]) -> None:
        if not args:
            raise ShellError("run: missing program")
        name, prog_args = args[0], args[1:]
        if not self._kernel.programs.has(name):
            raise CommandNotFoundError(name)
        self._kernel.run_program(self, name, prog_args)

    def _print_process_table(self, processes: list) -> None:
        print(f"{'PID':<5} {'USER':<8} {'STATE':<10} {'CPU':<6} {'MEM':<6} COMMAND")
        for process in processes:
            try:
                username = self._kernel.users.get_user_by_uid(process.uid).username
            except NotFoundError:
                username = str(process.uid)
            mem = f"{process.memory_mb:.0f}MB"
            print(
                f"{process.pid:<5} {username:<8} {process.state.value:<10} "
                f"{process.cpu_usage:<6.1f} {mem:<6} {process.command}"
            )


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
    entries = [
        (name, child)
        for name, child in directory.children.items()
        if show_all or not name.startswith(".")
    ]
    entries.sort(key=lambda item: item[0])
    if show_all:
        parent = directory.parent if isinstance(directory.parent, Directory) else directory
        return [(".", directory), ("..", parent), *entries]
    return entries


def _print_tree(rendered: str) -> None:
    try:
        print(rendered)
    except UnicodeEncodeError:
        print(
            rendered.replace("├── ", "|-- ")
            .replace("└── ", "`-- ")
            .replace("│   ", "|   ")
        )


def _print_monitor(rendered: str) -> None:
    try:
        print(rendered)
    except UnicodeEncodeError:
        print(rendered.replace("█", "#").replace("░", "-"))


def _long_listing(name: str, node: Node) -> str:
    kind = "d" if isinstance(node, Directory) else "-"
    return f"{kind}{node.mode_string} {node.owner} {node.group_name} {node.size} {name}"
