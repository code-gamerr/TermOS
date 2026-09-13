"""TERMOS kernel: boot state, uptime, and subsystem instances."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from core.config import ConfigManager
from core.constants import COMPONENT_NAMES, HOSTNAME, OS_NAME, OS_VERSION
from core.errors import NotFoundError, OutOfMemoryError, ProgramError, TermOSError
from filesystem.filesystem import FileSystem
from kernel.logger import KernelLogger
from memory.memory_manager import MemoryManager
from monitor.monitor import Monitor
from network.network_manager import NetworkManager
from processes.process import ProcessState
from processes.process_manager import ProcessManager
from programs.registry import ProgramRegistry
from users.user_manager import UserManager

if TYPE_CHECKING:
    from shell.shell import Shell


class Kernel:
    """Owns OS identity, lifecycle, and subsystem instances."""

    def __init__(self) -> None:
        self.name = OS_NAME
        self.version = OS_VERSION
        self.hostname = HOSTNAME
        self._booted_at: float | None = None
        self._running = False
        self.debug = False
        self.verbose = False
        self.logger = KernelLogger()
        self.components: dict[str, Any] = {name: None for name in COMPONENT_NAMES}
        self.components["filesystem"] = FileSystem()
        self.components["user_manager"] = UserManager()
        self.components["process_manager"] = ProcessManager()
        self.components["memory_manager"] = MemoryManager()
        self.components["network_manager"] = NetworkManager()
        self.programs = ProgramRegistry()
        self.monitor = Monitor(self)
        self.config = ConfigManager()
        self.config.load_from_fs(self.filesystem)
        self.hostname = self.config.get("hostname", HOSTNAME)
        allocator = self.config.get("memory_allocator", "first_fit")
        self.memory.set_allocator(allocator)
        self.processes.memory = self.memory
        self.filesystem.set_home(self.users.current.home if self.users.current else "/home/root")

    @property
    def filesystem(self) -> FileSystem:
        filesystem = self.components["filesystem"]
        if not isinstance(filesystem, FileSystem):
            raise TermOSError("filesystem is not available")
        return filesystem

    @property
    def users(self) -> UserManager:
        manager = self.components["user_manager"]
        if not isinstance(manager, UserManager):
            raise TermOSError("user manager is not available")
        return manager

    @property
    def processes(self) -> ProcessManager:
        manager = self.components["process_manager"]
        if not isinstance(manager, ProcessManager):
            raise TermOSError("process manager is not available")
        return manager

    @property
    def memory(self) -> MemoryManager:
        manager = self.components["memory_manager"]
        if not isinstance(manager, MemoryManager):
            raise TermOSError("memory manager is not available")
        return manager

    @property
    def network(self) -> NetworkManager:
        manager = self.components["network_manager"]
        if not isinstance(manager, NetworkManager):
            raise TermOSError("network manager is not available")
        return manager

    @property
    def scheduler(self):
        return self.processes.scheduler

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def uptime(self) -> float:
        if self._booted_at is None:
            return 0.0
        return time.monotonic() - self._booted_at

    def log(self, message: str) -> None:
        """Append a kernel log entry and optionally echo it."""
        self.logger.log(message)
        if self.verbose:
            from core import colors

            print(colors.sysmsg(f"[KERN] {message}"))

    def boot(self) -> list[tuple[str, bool, str]]:
        """Initialize subsystems and return ``(label, ok, detail)`` steps."""
        if self._running:
            raise TermOSError("kernel is already running")

        steps: list[tuple[str, bool, str]] = []
        self._booted_at = time.monotonic()
        self.logger.start(self._booted_at)
        self.log("TERMOS kernel starting")

        def record(label: str, ok: bool, detail: str = "") -> None:
            steps.append((label, ok, detail))
            if ok:
                self.log(detail or label)

        try:
            record("BIOS initialization", True, "BIOS initialization")
            record("Loading TERMOS kernel", True, "Kernel loaded")
            self.memory.allocate(8, "kernel", pid=None)
            record("Initializing memory manager", True, "Memory manager initialized")
            record("Mounting virtual filesystem", True, "Virtual filesystem mounted")
            record("Loading users and permissions", True, "User manager initialized")
            uid = self.users.current.uid if self.users.current else 0
            if not self.processes.processes:
                self.processes.bootstrap(uid=uid)
            record("Starting process scheduler", True, "Scheduler started")
            iface = self.network.primary()
            record(
                "Initializing network interface",
                True,
                f"Network interface {iface.name} initialized",
            )
            record(
                "Loading system programs",
                True,
                f"Loaded {len(self.programs.names())} system programs",
            )
            record("Starting terminal shell", True, "Shell started")
            self._running = True
        except Exception as exc:  # noqa: BLE001 - boot must report failure
            record("System initialization", False, str(exc))
            self._running = False
            if self.debug:
                raise
        return steps

    def shutdown(self) -> None:
        self.log("Kernel shutting down")
        self._running = False
        self._booted_at = None

    def run_program(self, shell: Shell, name: str, args: list[str], verbose: bool | None = None) -> int:
        """Create a process, allocate memory, schedule, run, then clean up."""
        show = self.verbose if verbose is None else verbose
        try:
            program = self.programs.get(name)
        except NotFoundError as exc:
            raise NotFoundError(name) from exc

        user = self.users.require_current()
        if program.required_permissions == "root" and not user.is_root:
            raise ProgramError("Permission denied")

        if show:
            from core import colors

            print(colors.sysmsg(f"[EXEC] Starting {name}"))
        try:
            process = self.processes.create(
                name,
                user.uid,
                " ".join([name, *args]).strip(),
                parent_pid=2,
                memory_mb=program.memory_mb,
                auto_schedule=True,
            )
        except OutOfMemoryError:
            if show:
                print("TERMOS: Out of memory")
            raise

        self.log(f"Process PID {process.pid} created")
        self.log(f"Memory allocated: {program.memory_mb:g} MB")
        if show:
            from core import colors

            print(colors.sysmsg(f"[PROC] PID {process.pid} created"))
            print(colors.sysmsg(f"[MEM ] Allocating {program.memory_mb:g} MB"))
            print(colors.sysmsg(f"[CPU ] Scheduling PID {process.pid}"))
            print(colors.sysmsg(f"[EXEC] Running {name}"))

        self.scheduler.running_pid = process.pid
        process.set_state(ProcessState.RUNNING)
        process.cpu_usage = min(99.9, process.cpu_usage + 4.0)

        try:
            code = program.run(self, shell, args)
        except Exception:
            self.processes.terminate(process.pid, exit_code=1)
            self.log(f"Process PID {process.pid} terminated")
            self._restore_shell_process()
            raise
        else:
            self.processes.terminate(process.pid, exit_code=code)
            self.log(f"Process PID {process.pid} terminated")
            self.log(f"Memory released: {program.memory_mb:g} MB")
            self._restore_shell_process()
            if show:
                from core import colors

                print(colors.sysmsg(f"[EXEC] {name} finished"))
                print(colors.sysmsg(f"[MEM ] Released {program.memory_mb:g} MB"))
            return code

    def _restore_shell_process(self) -> None:
        """Keep PID 2 (shell) marked running after a foreground program exits."""
        try:
            shell_proc = self.processes.get(2)
        except NotFoundError:
            return
        if shell_proc.state != ProcessState.TERMINATED:
            shell_proc.set_state(ProcessState.RUNNING)
            self.scheduler.running_pid = 2

    def format_uptime(self) -> str:
        seconds = int(self.uptime)
        hours, rem = divmod(seconds, 3600)
        minutes, secs = divmod(rem, 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def system_info(self) -> dict[str, Any]:
        mem = self.memory.get_memory_stats()
        return {
            "name": self.name,
            "version": self.version,
            "hostname": self.hostname,
            "uptime_seconds": round(self.uptime, 3),
            "uptime": self.format_uptime(),
            "state": "running" if self._running else "halted",
            "user": self.users.current.username if self.users.current else None,
            "memory": mem,
            "scheduler": self.scheduler.algorithm,
            "allocator": mem["allocator"],
            "components": {
                name: component is not None
                for name, component in self.components.items()
            },
        }
