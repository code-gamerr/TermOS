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

    @property
    def filesystem(self) -> FileSystem:
        """Return the kernel-owned virtual filesystem."""
        filesystem = self.components["filesystem"]
        if not isinstance(filesystem, FileSystem):
            raise TermOSError("filesystem is not available")
        return filesystem

    @property
    def is_running(self) -> bool:
        """Return whether the kernel has been booted and not shut down."""
        return self._running

    @property
    def uptime(self) -> float:
        """Seconds since boot, or 0 if the kernel is not running."""
        if self._booted_at is None:
            return 0.0
        return time.monotonic() - self._booted_at

    def boot(self) -> None:
        """Mark the kernel as running and start the uptime clock."""
        if self._running:
            raise TermOSError("kernel is already running")
        self._booted_at = time.monotonic()
        self._running = True

    def shutdown(self) -> None:
        """Stop the kernel. Safe to call more than once."""
        self._running = False
        self._booted_at = None

    def system_info(self) -> dict[str, Any]:
        """Return basic system information for the running kernel."""
        return {
            "name": self.name,
            "version": self.version,
            "hostname": self.hostname,
            "uptime_seconds": round(self.uptime, 3),
            "state": "running" if self._running else "halted",
            "components": {
                name: component is not None
                for name, component in self.components.items()
            },
        }
