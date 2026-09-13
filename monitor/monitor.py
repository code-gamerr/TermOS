"""System monitor that reads live TERMOS simulation metrics."""

from __future__ import annotations

from typing import TYPE_CHECKING

from filesystem.directory import Directory
from filesystem.file import File
from processes.process import ProcessState

if TYPE_CHECKING:
    from kernel.kernel import Kernel


class Monitor:
    """Aggregates CPU, memory, process, network, and filesystem metrics."""

    def __init__(self, kernel: Kernel) -> None:
        self.kernel = kernel

    def snapshot(self) -> dict[str, object]:
        """Collect a one-shot metrics snapshot."""
        mem = self.kernel.memory.get_memory_stats()
        active = self.kernel.processes.active()
        running = sum(1 for p in active if p.state == ProcessState.RUNNING)
        sleeping = sum(
            1 for p in active if p.state in {ProcessState.SLEEPING, ProcessState.WAITING}
        )
        ready = sum(1 for p in active if p.state == ProcessState.READY)
        cpu = 0.0
        if active:
            cpu = min(100.0, sum(p.cpu_usage for p in active) * 3.0)
        used_bytes, total_bytes = self._filesystem_usage()
        return {
            "cpu_percent": round(cpu, 1),