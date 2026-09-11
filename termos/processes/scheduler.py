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
        if process.state == ProcessState.TERMINATED:
            return
        if pid not in self.ready and pid != self.running_pid:
            process.set_state(ProcessState.READY)
            self.ready.append(pid)

    def remove(self, pid: int) -> None:
        """Drop a process from the ready/running slots."""
        self.ready = deque(item for item in self.ready if item != pid)
        if self.running_pid == pid:
            self.running_pid = None

    def schedule(self) -> Process | None:
        """Context-switch: park the current runner and pick the next ready PID."""
        if self.running_pid is not None:
            current = self.process_manager.processes.get(self.running_pid)
            if current is not None and current.state == ProcessState.RUNNING:
                current.set_state(ProcessState.READY)
                self.ready.append(self.running_pid)
            self.running_pid = None

        while self.ready:
            pid = self.ready.popleft()
            process = self.process_manager.processes.get(pid)
            if process is None or process.state == ProcessState.TERMINATED:
                continue
            process.set_state(ProcessState.RUNNING)
            process.cpu_usage = min(99.9, process.cpu_usage + 0.4)
            self.running_pid = pid
            return process
        return None

    def tick(self) -> Process | None:
        """Advance one quantum."""
        return self.schedule()

    def status(self) -> dict[str, object]:
        """Return a snapshot for the ``scheduler`` command."""
        running = None
        if self.running_pid is not None:
            running = self.process_manager.processes.get(self.running_pid)
        ready_procs = [
            self.process_manager.processes[pid]
            for pid in self.ready
            if pid in self.process_manager.processes
        ]
        return {
            "algorithm": self.algorithm,
            "quantum_ms": self.quantum_ms,
            "running": running,
            "ready": ready_procs,
        }
