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