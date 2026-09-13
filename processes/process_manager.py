"""Simulated process table and lifecycle."""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING

from core.errors import NotFoundError, OutOfMemoryError, ProcessError
from processes.process import Process, ProcessState
from processes.scheduler import Scheduler

if TYPE_CHECKING:
    from memory.memory_manager import MemoryManager


class ProcessManager:
    """Owns PIDs, the process table, and the Round Robin scheduler."""

    def __init__(self) -> None:
        self.processes: dict[int, Process] = {}
        self._next_pid = 1
        self.scheduler = Scheduler(self)
        self.jobs: list[int] = []
        self.memory: MemoryManager | None = None
        self.verbose = False

    def create(
        self,
        name: str,
        uid: int,
        command: str,
        parent_pid: int = 1,
        priority: int = 0,
        memory_mb: float = 4.0,
        auto_schedule: bool = True,
    ) -> Process: