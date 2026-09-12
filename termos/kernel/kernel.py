"""TERMOS kernel: boot state, uptime, and subsystem instances."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from core.constants import COMPONENT_NAMES, HOSTNAME, OS_NAME, OS_VERSION
from core.errors import NotFoundError, OutOfMemoryError, ProgramError, TermOSError
from filesystem.filesystem import FileSystem
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
        self.components: dict[str, Any] = {name: None for name in COMPONENT_NAMES}
        self.components["filesystem"] = FileSystem()
        self.components["user_manager"] = UserManager()
        self.components["process_manager"] = ProcessManager()
        self.components["memory_manager"] = MemoryManager()
        self.components["network_manager"] = NetworkManager()
        self.programs = ProgramRegistry()
        self.monitor = Monitor(self)
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

    def boot(self) -> None:
        """Start the kernel, reserve kernel RAM, and launch init + shell."""
        if self._running:
            raise TermOSError("kernel is already running")
        self._booted_at = time.monotonic()
        self._running = True
        self.memory.allocate(8, "kernel", pid=None)
        uid = self.users.current.uid if self.users.current else 0
        if not self.processes.processes:
            self.processes.bootstrap(uid=uid)

    def shutdown(self) -> None:
        self._running = False
        self._booted_at = None

    def run_program(self, shell: Shell, name: str, args: list[str], verbose: bool = True) -> int:
        """Create a process, allocate memory, schedule, run, then clean up."""
        try:
            program = self.programs.get(name)
        except NotFoundError as exc:
            raise NotFoundError(name) from exc

        user = self.users.require_current()
        if program.required_permissions == "root" and not user.is_root:
            raise ProgramError("Permission denied")

        if verbose:
            print(f"[EXEC] Starting {name}")
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
            if verbose:
                print("TERMOS: Out of memory")
            raise

        if verbose:
            print(f"[PROC] PID {process.pid} created")
            print(f"[MEM ] Allocating {program.memory_mb:g} MB")
            print(f"[CPU ] Scheduling PID {process.pid}")
            print(f"[EXEC] Running {name}")

        self.scheduler.running_pid = process.pid
        process.set_state(ProcessState.RUNNING)
        process.cpu_usage = min(99.9, process.cpu_usage + 4.0)

        try:
            code = program.run(self, shell, args)
        except Exception:
            self.processes.terminate(process.pid, exit_code=1)
            raise
        else:
            self.processes.terminate(process.pid, exit_code=code)
            if verbose:
                print(f"[EXEC] {name} finished")
                print(f"[MEM ] Released {program.memory_mb:g} MB")
            return code

    def system_info(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "hostname": self.hostname,
            "uptime_seconds": round(self.uptime, 3),
            "state": "running" if self._running else "halted",
            "user": self.users.current.username if self.users.current else None,
            "memory": self.memory.get_memory_stats(),
            "components": {
                name: component is not None
                for name, component in self.components.items()
            },
        }
