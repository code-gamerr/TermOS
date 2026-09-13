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