"""Interactive TERMOS shell."""

from __future__ import annotations

import getpass
import io
import os
import shlex
import time
from collections.abc import Callable
from contextlib import redirect_stdout
from typing import TYPE_CHECKING

from core import colors
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
from shell.completion import Completer
from shell.demo import run_demo
from shell.manpages import ManPages
from shell.parser import parse_stage, split_pipeline
from shell.scripting import ScriptEngine, can_execute_script, is_script_path

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
        self._stdin: str | None = None
        self.last_status = 0
        self.env: dict[str, str] = {
            "HOME": user.home,
            "USER": user.username,
            "SHELL": kernel.config.get("shell", "termos-sh"),
            "HOSTNAME": kernel.hostname,
            "PATH": "/bin",
            "PWD": self.path,
            "0": "termos-sh",
            "#": "0",
            "?": "0",
        }
        self.aliases: dict[str, str] = {
            "ll": "ls -l",
            "la": "ls -a",
        }
        self.scripts = ScriptEngine(self)
        self.man = ManPages()
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
            "df": self._cmd_df,
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
            "history": self._cmd_history,
            "man": self._cmd_man,
            "dmesg": self._cmd_dmesg,
            "verbose": self._cmd_verbose,
            "demo": self._cmd_demo,
            "grep": self._cmd_grep,
            "head": self._cmd_head,
            "tail": self._cmd_tail,
            "wc": self._cmd_wc,
            "export": self._cmd_export,
            "unset": self._cmd_unset,
            "env": self._cmd_env,
            "set": self._cmd_set,
            "alias": self._cmd_alias,
            "unalias": self._cmd_unalias,
            "sh": self._cmd_sh,
            "source": self._cmd_source,
            ".": self._cmd_source,
            "test": self._cmd_test,
            "[": self._cmd_test_bracket,
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
        user = colors.green(self.user)
        host = colors.green(self._kernel.hostname)
        path = colors.directory(self.cwd)
        return f"{user}@{host}:{path}$ "

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

    def execute(self, line: str) -> int:
        """Parse and run a command line, including pipes and redirects."""
        return self.execute_line(line, from_script=False)

    def execute_line(self, line: str, from_script: bool = False) -> int:
        """Execute one logical line and return the exit status."""
        self.env["PWD"] = self.path
        self.env["USER"] = self.user
        self.env["HOME"] = self._current().home
        self.env["?"] = str(self.last_status)

        try:
            stripped = self.scripts._strip_comment(line.strip())
            if not from_script and re_full_assign(stripped):
                from shell.scripting import _ASSIGN

                match = _ASSIGN.match(stripped)
                assert match is not None
                name, value = match.group(1), match.group(2)
                self.env[name] = self.scripts._unquote(self.scripts.expand(value))
                self.last_status = 0
                return 0

            expanded = self.scripts.expand(stripped) if stripped else stripped
            if not expanded:
                return 0
            segments = split_pipeline(expanded)
        except ShellError as exc:
            print(colors.err(str(exc)))
            self.last_status = 1
            return 1

        current = None
        status = 0
        try:
            for index, segment in enumerate(segments):
                stage = parse_stage(segment)
                stdin_text = current
                for redirect in stage.redirects:
                    if redirect.mode == "<":
                        try:
                            stdin_text = self._kernel.filesystem.read(
                                redirect.path, self.path, user=self._current()
                            )
                        except NotFoundError:
                            raise ShellError(
                                f"termos: {redirect.path}: No such file or directory"
                            ) from None
                        except NotAFileError:
                            raise ShellError(f"termos: {redirect.path}: Is a directory") from None

                buffer = io.StringIO()
                with redirect_stdout(buffer):
                    status = self._dispatch(stage.argv, stdin_text)
                output = buffer.getvalue()

                wrote = False
                for redirect in stage.redirects:
                    if redirect.mode in {">", ">>"}:
                        existing = ""
                        if redirect.mode == ">>":
                            try:
                                existing = self._kernel.filesystem.read(
                                    redirect.path, self.path, user=self._current()
                                )
                            except NotFoundError:
                                existing = ""
                        self._kernel.filesystem.write(
                            redirect.path,
                            existing + output,
                            self.path,
                            user=self._current(),
                        )
                        wrote = True
                if wrote:
                    current = ""
                elif index == len(segments) - 1:
                    if output:
                        print(output, end="")
                    current = output
                else:
                    current = output
            self.last_status = status
            self.env["?"] = str(status)
            return status
        except ShellError as exc:
            print(colors.err(str(exc)))
            self.last_status = 1
            return 1
        except PermissionDeniedError:
            print(colors.err("Permission denied"))
            self.last_status = 1
            return 1
        except OutOfMemoryError:
            print(colors.err("TERMOS: Out of memory"))
            self.last_status = 1
            return 1
        except ProgramError as exc:
            print(colors.err(str(exc)))
            self.last_status = 1
            return 1
        except NetworkError as exc:
            print(colors.err(f"network: {exc}"))
            self.last_status = 1
            return 1
        except Exception as exc:  # noqa: BLE001 - keep the shell alive
            if self._kernel.debug:
                raise
            print(colors.err(f"termos: {exc}"))
            self.last_status = 1
            return 1

    def _dispatch(self, argv: list[str], stdin_text: str | None = None) -> int:
        """Run one argv list as a builtin, program, alias, or script."""
        if not argv:
            return 0
        name, args = argv[0], argv[1:]

        # Alias expansion (single shot).
        if name in self.aliases:
            aliased = self.parse(self.scripts.expand(self.aliases[name]))
            argv = aliased + args
            name, args = argv[0], argv[1:]

        previous = self._stdin
        self._stdin = stdin_text
        try:
            if is_script_path(name) or name.endswith(".sh"):
                return self._run_script_path(name, args)

            handler = self.commands.get(name)
            if handler is not None:
                handler(args)
                if name in {"test", "[", "sh", "source", "."}:
                    return self.last_status
                return 0

            if self._kernel.programs.has(name):
                code = self._kernel.run_program(self, name, args)
                return int(code)

            # Bare script name in cwd / PATH-like /bin
            for candidate in (name, f"./{name}", f"/bin/{name}"):
                if self._try_script(candidate, args):
                    return self.last_status

            raise CommandNotFoundError(name)
        except CommandNotFoundError as exc:
            print(colors.err(str(exc)))
            return 127
        finally:
            self._stdin = previous

    def _try_script(self, path: str, args: list[str]) -> bool:
        try:
            node = self._kernel.filesystem.resolve(path, self.path)
        except (NotFoundError, NotAFileError):
            return False
        from filesystem.file import File

        if not isinstance(node, File):
            return False
        if not can_execute_script(self, path):
            return False
        self.last_status = self.scripts.run_file(path, argv=args)
        return True

    def _run_script_path(self, path: str, args: list[str]) -> int:
        if not can_execute_script(self, path):
            # Readable scripts can still be run via explicit path if execute set;
            # otherwise require `sh`.
            try:
                node = self._kernel.filesystem.resolve(path, self.path)
                from filesystem.file import File

                if isinstance(node, File):
                    raise ShellError(f"termos: {path}: Permission denied")
            except (NotFoundError, NotAFileError):
                raise CommandNotFoundError(path) from None
            raise ShellError(f"termos: {path}: Permission denied")
        self.last_status = self.scripts.run_file(path, argv=args)
        return self.last_status

    @staticmethod
    def parse(line: str) -> list[str]:
        """Split a command line, honoring quotes and collapsing extra spaces."""
        try:
            return shlex.split(line, posix=True)
        except ValueError as exc:
            raise ShellError(f"termos: syntax error: {exc}") from exc

    def _enable_readline_history(self) -> None:
        try:
            import readline
        except ImportError:
            return
        readline.set_history_length(1000)
        readline.set_completer(Completer(self))
        try:
            readline.parse_and_bind("tab: complete")
        except Exception:
            pass

    def _cmd_help(self, _args: list[str]) -> None:
        sections = {
            "FILESYSTEM": ["ls", "cd", "pwd", "mkdir", "touch", "cat", "write", "rm", "rmdir", "tree", "df"],
            "PROCESS": ["ps", "top", "kill", "jobs", "scheduler", "sleep"],
            "MEMORY": ["free", "memory", "memmap"],
            "NETWORK": ["ifconfig", "ping", "netstat", "route"],
            "SYSTEM": ["sysinfo", "uptime", "monitor", "neofetch", "fortune", "dmesg", "demo", "verbose"],
            "USER": ["whoami", "id", "su", "passwd", "chmod", "chown", "users", "groups"],
            "TEXT": ["echo", "grep", "head", "tail", "wc"],
            "SHELL": ["help", "man", "history", "clear", "version", "exit", "run", "export", "env", "alias", "sh", "source"],
        }
        for title, names in sections.items():
            print(colors.sysmsg(title))
            for name in names:
                if name in self.commands or self._kernel.programs.has(name):
                    print(f"  {name}")
            print()

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
        for name, entry in entries:
            if isinstance(entry, Directory):
                print(colors.directory(name))
            else:
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
            if self._stdin is not None:
                text = self._stdin
                print(text, end="" if not text or text.endswith("\n") else "\n")
                return
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
        if contents and not contents.endswith("\n"):
            contents += "\n"
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

    def _cmd_df(self, _args: list[str]) -> None:
        snap = self._kernel.monitor.snapshot()
        used = float(snap["fs_used_mb"])
        free = float(snap["fs_free_mb"])
        total = used + free
        pct = int(round((used / total) * 100)) if total else 0
        print(f"{'Filesystem':<14}{'Size':<10}{'Used':<10}{'Avail':<10}{'Use%':<6}Mounted on")
        print(
            f"{'vfs':<14}"
            f"{total:.0f}MB{'':<6}"
            f"{used:.2f}MB{'':<4}"
            f"{free:.0f}MB{'':<5}"
            f"{pct}%{'':<4}/"
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
            _print_monitor(self._kernel.monitor.render(fancy=True))
            return
        try:
            while True:
                if os.name == "nt":
                    os.system("cls")
                else:
                    print("\033[2J\033[H", end="", flush=True)
                _print_monitor(self._kernel.monitor.render(fancy=True))
                print("\n(Ctrl+C to exit)")
                time.sleep(0.8)
        except KeyboardInterrupt:
            print()

    def _cmd_run(self, args: list[str]) -> None:
        if not args:
            raise ShellError("run: missing program")
        name, prog_args = args[0], args[1:]
        if not self._kernel.programs.has(name):
            raise CommandNotFoundError(name)
        self._kernel.run_program(self, name, prog_args)

    def _cmd_history(self, args: list[str]) -> None:
        if args and args[0] == "-c":
            self.history.clear()
            return
        for index, line in enumerate(self.history, start=1):
            print(f"{index:>4}  {line}")

    def _cmd_man(self, args: list[str]) -> None:
        if not args:
            raise ShellError("man: what manual page do you want?")
        try:
            print(self.man.get(args[0]))
        except NotFoundError:
            raise ShellError(f"man: no manual entry for {args[0]}") from None

    def _cmd_dmesg(self, _args: list[str]) -> None:
        text = self._kernel.logger.render()
        if text:
            print(colors.sysmsg(text))

    def _cmd_verbose(self, args: list[str]) -> None:
        if not args or args[0] not in {"on", "off"}:
            raise ShellError("verbose: usage: verbose on|off")
        self._kernel.verbose = args[0] == "on"
        print(f"verbose {'on' if self._kernel.verbose else 'off'}")

    def _cmd_demo(self, _args: list[str]) -> None:
        run_demo(self._kernel, self)

    def _cmd_grep(self, args: list[str]) -> None:
        if not args:
            raise ShellError("grep: missing pattern")
        pattern, files = args[0], args[1:]
        if files:
            for path in files:
                try:
                    text = self._kernel.filesystem.read(path, self.path, user=self._current())
                except NotFoundError:
                    raise ShellError(f"grep: {path}: No such file or directory") from None
                for line in text.splitlines():
                    if pattern in line:
                        print(line)
            return
        if self._stdin is None:
            raise ShellError("grep: missing file")
        for line in self._stdin.splitlines():
            if pattern in line:
                print(line)

    def _cmd_head(self, args: list[str]) -> None:
        count = 10
        path = None
        index = 0
        while index < len(args):
            if args[index] == "-n" and index + 1 < len(args):
                count = int(args[index + 1])
                index += 2
                continue
            path = args[index]
            index += 1
        text = self._read_text_or_stdin(path)
        for line in text.splitlines()[:count]:
            print(line)

    def _cmd_tail(self, args: list[str]) -> None:
        count = 10
        path = None
        index = 0
        while index < len(args):
            if args[index] == "-n" and index + 1 < len(args):
                count = int(args[index + 1])
                index += 2
                continue
            path = args[index]
            index += 1
        text = self._read_text_or_stdin(path)
        for line in text.splitlines()[-count:]:
            print(line)

    def _cmd_wc(self, args: list[str]) -> None:
        path = args[0] if args else None
        text = self._read_text_or_stdin(path)
        lines = text.splitlines()
        words = len(text.split())
        bytes_count = len(text.encode("utf-8"))
        print(f"{len(lines)} {words} {bytes_count}" + (f" {path}" if path else ""))

    def _cmd_export(self, args: list[str]) -> None:
        if not args:
            for key in sorted(self.env):
                if key.isdigit() or key in {"?", "#", "@", "*"}:
                    continue
                print(f"export {key}={self.env[key]}")
            return
        for item in args:
            if "=" in item:
                name, _, value = item.partition("=")
                self.env[name] = self.scripts._unquote(self.scripts.expand(value))
            elif item in self.env:
                pass
            else:
                self.env[item] = ""

    def _cmd_unset(self, args: list[str]) -> None:
        for name in args:
            self.env.pop(name, None)

    def _cmd_env(self, _args: list[str]) -> None:
        for key in sorted(self.env):
            if key.isdigit() or key in {"?", "#", "@", "*"}:
                continue
            print(f"{key}={self.env[key]}")

    def _cmd_set(self, _args: list[str]) -> None:
        self._cmd_env(_args)

    def _cmd_alias(self, args: list[str]) -> None:
        if not args:
            for name in sorted(self.aliases):
                print(f"alias {name}='{self.aliases[name]}'")
            return
        for item in args:
            if "=" not in item:
                if item in self.aliases:
                    print(f"alias {item}='{self.aliases[item]}'")
                continue
            name, _, value = item.partition("=")
            self.aliases[name] = self.scripts._unquote(value)

    def _cmd_unalias(self, args: list[str]) -> None:
        for name in args:
            self.aliases.pop(name, None)

    def _cmd_sh(self, args: list[str]) -> None:
        if not args:
            raise ShellError("sh: missing script")
        path, script_args = args[0], args[1:]
        self.last_status = self.scripts.run_file(path, argv=script_args)

    def _cmd_source(self, args: list[str]) -> None:
        if not args:
            raise ShellError("source: missing filename")
        self.last_status = self.scripts.run_file(args[0], argv=args[1:])

    def _cmd_test(self, args: list[str]) -> None:
        ok = self.scripts._test(" ".join(args))
        self.last_status = 0 if ok else 1

    def _cmd_test_bracket(self, args: list[str]) -> None:
        if args and args[-1] == "]":
            args = args[:-1]
        else:
            raise ShellError("[: missing `]'")
        self._cmd_test(args)

    def _read_text_or_stdin(self, path: str | None) -> str:
        if path:
            try:
                return self._kernel.filesystem.read(path, self.path, user=self._current())
            except NotFoundError:
                raise ShellError(f"{path}: No such file or directory") from None
        if self._stdin is not None:
            return self._stdin
        raise ShellError("missing file")

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


def re_full_assign(assign: str) -> bool:
    """Return True when the whole line is a NAME=value assignment."""
    from shell.scripting import _ASSIGN

    cleaned = ScriptEngine._strip_comment(assign.strip())
    if not cleaned or cleaned.startswith("#"):
        return False
    match = _ASSIGN.match(cleaned)
    if not match:
        return False
    return cleaned == match.group(0)


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
        print(
            rendered.replace("█", "#")
            .replace("░", "-")
            .replace("╔", "+")
            .replace("╗", "+")
            .replace("╚", "+")
            .replace("╝", "+")
            .replace("╠", "+")
            .replace("╣", "+")
            .replace("═", "-")
            .replace("║", "|")
        )


def _long_listing(name: str, node: Node) -> str:
    kind = "d" if isinstance(node, Directory) else "-"
    return f"{kind}{node.mode_string} {node.owner} {node.group_name} {node.size} {name}"
