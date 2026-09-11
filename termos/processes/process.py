"""Simulated process for TERMOS."""

from __future__ import annotations

import enum
import time


class ProcessState(enum.Enum):
    """Lifecycle states for a simulated process."""

    NEW = "NEW"
    READY = "READY"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    SLEEPING = "SLEEPING"
    TERMINATED = "TERMINATED"


class Process:
    """A simulated process. Not a real OS process."""

    def __init__(
        self,
        pid: int,
        name: str,
        uid: int,
        command: str,
        parent_pid: int = 0,
        priority: int = 0,
        memory_mb: float = 4.0,
    ) -> None:
        self.pid = pid
        self.name = name
        self.uid = uid
        self.command = command
        self.parent_pid = parent_pid
        self.priority = priority
        self.state = ProcessState.NEW
        self.cpu_usage = 0.0
        self.memory_mb = memory_mb
        self.start_time = time.time()
        self.exit_code: int | None = None

    def set_state(self, state: ProcessState) -> None:
        """Transition to ``state``."""
        self.state = state

    def terminate(self, exit_code: int = 0) -> None:
        """Mark the process as terminated."""
        self.state = ProcessState.TERMINATED
        self.exit_code = exit_code
        self.cpu_usage = 0.0
