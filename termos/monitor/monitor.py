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
        used_bytes, _total = self._filesystem_usage()
        return {
            "cpu_percent": round(cpu, 1),
            "memory": mem,
            "processes_running": running,
            "processes_sleeping": sleeping,
            "processes_ready": ready,
            "processes_total": len(active),
            "network_rx": self.kernel.network.rx,
            "network_tx": self.kernel.network.tx,
            "fs_used_mb": round(used_bytes / (1024 * 1024), 2),
            "fs_free_mb": round(max(0.0, (128 * 1024 * 1024 - used_bytes) / (1024 * 1024)), 2),
            "uptime": self.kernel.uptime,
            "uptime_text": self.kernel.format_uptime(),
        }

    def render(self, fancy: bool = False) -> str:
        """Return a formatted monitor screen."""
        snap = self.snapshot()
        mem = snap["memory"]
        used_ratio = float(mem["used_mb"]) / float(mem["total_mb"]) if mem["total_mb"] else 0
        cpu_bar = _bar(float(snap["cpu_percent"]) / 100.0, 20)
        mem_bar = _bar(used_ratio, 20)
        if not fancy:
            return "\n".join(
                [
                    "TERMOS SYSTEM MONITOR",
                    "",
                    "CPU",
                    f"{cpu_bar}  {snap['cpu_percent']}%",
                    "",
                    "MEMORY",
                    f"{mem_bar}  {int(used_ratio * 100)}%",
                    "",
                    "PROCESSES",
                    (
                        f"Running: {snap['processes_running']}    "
                        f"Ready: {snap['processes_ready']}    "
                        f"Sleeping: {snap['processes_sleeping']}"
                    ),
                    "",
                    "NETWORK",
                    f"RX: {snap['network_rx']} packets    TX: {snap['network_tx']} packets",
                    "",
                    "FILESYSTEM",
                    f"Used: {snap['fs_used_mb']} MB",
                    f"Free: {snap['fs_free_mb']} MB",
                    "",
                    "UPTIME",
                    str(snap["uptime_text"]),
                ]
            )

        width = 46
        inner = width - 2

        def row(text: str = "") -> str:
            return "║" + text.ljust(inner)[:inner] + "║"

        lines = [
            "╔" + "═" * inner + "╗",
            row("TERMOS SYSTEM MONITOR".center(inner)),
            "╠" + "═" * inner + "╣",
            row("CPU"),
            row(f" {cpu_bar}  {snap['cpu_percent']}%"),
            row(),
            row("MEMORY"),
            row(f" {mem_bar}  {int(used_ratio * 100)}%"),
            row(),
            row("PROCESSES"),
            row(
                f" Running: {snap['processes_running']}  "
                f"Ready: {snap['processes_ready']}  "
                f"Sleeping: {snap['processes_sleeping']}"
            ),
            row(),
            row("NETWORK"),
            row(f" RX: {snap['network_rx']} packets   TX: {snap['network_tx']} packets"),
            row(),
            row("UPTIME"),
            row(f" {snap['uptime_text']}"),
            "╚" + "═" * inner + "╝",
        ]
        return "\n".join(lines)

    def _filesystem_usage(self) -> tuple[int, int]:
        used = _dir_bytes(self.kernel.filesystem.root)
        return used, 128 * 1024 * 1024


def _bar(ratio: float, width: int = 16) -> str:
    filled = max(0, min(width, int(round(ratio * width))))
    return "█" * filled + "░" * (width - filled)


def _dir_bytes(node: Directory) -> int:
    total = 0
    for child in node.children.values():
        if isinstance(child, File):
            total += child.size
        elif isinstance(child, Directory):
            total += _dir_bytes(child)
    return total
