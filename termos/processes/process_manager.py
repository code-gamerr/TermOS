"""Simulated process table and lifecycle."""

from __future__ import annotations

from collections import deque

from core.errors import NotFoundError, ProcessError
from processes.process import Process, ProcessState
from processes.scheduler import Scheduler


class ProcessManager:
    """Owns PIDs, the process table, and the Round Robin scheduler."""

    def __init__(self) -> None:
        self.processes: dict[int, Process] = {}
        self._next_pid = 1
        self.scheduler = Scheduler(self)
        self.jobs: list[int] = []

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
        """Allocate a PID and move the process into the ready queue."""
        pid = self._next_pid
        self._next_pid += 1
        process = Process(pid, name, uid, command, parent_pid, priority, memory_mb)
        self.processes[pid] = process
        process.set_state(ProcessState.READY)
        if auto_schedule:
            self.scheduler.enqueue(pid)
            if self.scheduler.running_pid is None:
                self.scheduler.schedule()
        return process

    def get(self, pid: int) -> Process:
        """Return a process by PID."""
        try:
            return self.processes[pid]
        except KeyError as exc:
            raise NotFoundError(str(pid)) from exc

    def terminate(self, pid: int, exit_code: int = 0) -> Process:
        """Terminate a process. Init (PID 1) cannot be killed."""
        if pid == 1:
            raise ProcessError("cannot kill init")
        process = self.get(pid)
        if process.state == ProcessState.TERMINATED:
            raise ProcessError(f"process {pid} already terminated")
        process.terminate(exit_code)
        self.scheduler.remove(pid)
        if pid in self.jobs:
            self.jobs.remove(pid)
        if self.scheduler.running_pid is None:
            self.scheduler.schedule()
        return process

    def sleep(self, pid: int) -> Process:
        """Move a process into the SLEEPING state."""
        process = self.get(pid)
        if process.state == ProcessState.TERMINATED:
            raise ProcessError(f"process {pid} is terminated")
        self.scheduler.remove(pid)
        process.set_state(ProcessState.SLEEPING)
        if pid not in self.jobs:
            self.jobs.append(pid)
        if self.scheduler.running_pid is None:
            self.scheduler.schedule()
        return process

    def wake(self, pid: int) -> Process:
        """Wake a sleeping process back onto the ready queue."""
        process = self.get(pid)
        if process.state not in {ProcessState.SLEEPING, ProcessState.WAITING}:
            return process
        if pid in self.jobs:
            self.jobs.remove(pid)
        self.scheduler.enqueue(pid)
        if self.scheduler.running_pid is None:
            self.scheduler.schedule()
        return process

    def list_processes(self) -> list[Process]:
        """Return living and recently terminated processes, ordered by PID."""
        return [self.processes[pid] for pid in sorted(self.processes)]

    def active(self) -> list[Process]:
        """Return non-terminated processes."""
        return [
            process
            for process in self.list_processes()
            if process.state != ProcessState.TERMINATED
        ]

    def bootstrap(self, uid: int = 0) -> tuple[Process, Process]:
        """Create the init and shell processes (PID 1 and 2)."""
        init = self.create("init", uid, "init", parent_pid=0, memory_mb=4.0)
        shell = self.create("shell", uid, "shell", parent_pid=init.pid, memory_mb=8.0)
        # Keep both "running" for the demo; shell is the interactive foreground.
        self.scheduler.running_pid = shell.pid
        shell.set_state(ProcessState.RUNNING)
        init.set_state(ProcessState.RUNNING)
        init.cpu_usage = 0.1
        shell.cpu_usage = 1.8
        self.scheduler.ready = deque(
            pid for pid in self.scheduler.ready if pid not in {init.pid, shell.pid}
        )
        return init, shell
