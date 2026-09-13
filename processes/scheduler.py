"""Simulated Round Robin CPU scheduler."""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING

from processes.process import Process, ProcessState

if TYPE_CHECKING:
    from processes.process_manager import ProcessManager


class Scheduler:
    """Round Robin scheduler over simulated processes.

    Does not schedule real Python threads or OS processes.
    """

    def __init__(self, process_manager: ProcessManager, quantum_ms: int = 100) -> None:
        self.process_manager = process_manager
        self.quantum_ms = quantum_ms
        self.algorithm = "Round Robin"
        self.ready: deque[int] = deque()
        self.running_pid: int | None = None

    def enqueue(self, pid: int) -> None:
        """Place a process on the ready queue."""
        process = self.process_manager.get(pid)