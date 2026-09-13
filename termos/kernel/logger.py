"""Central kernel event log for ``dmesg``."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LogEntry:
    """One timestamped kernel message."""

    seconds: float
    message: str

    def format(self) -> str:
        total = int(self.seconds)
        hours, rem = divmod(total, 3600)
        minutes, secs = divmod(rem, 60)
        return f"[{hours:02d}:{minutes:02d}:{secs:02d}] {self.message}"


class KernelLogger:
    """Stores system events relative to kernel boot time."""

    def __init__(self) -> None:
        self.entries: list[LogEntry] = []
        self._boot_monotonic: float | None = None

    def start(self, boot_monotonic: float) -> None:
        """Mark the boot clock used for timestamps."""
        self._boot_monotonic = boot_monotonic

    def log(self, message: str, now: float | None = None) -> None:
        """Append a kernel log line."""
        import time

        base = self._boot_monotonic if self._boot_monotonic is not None else time.monotonic()
        stamp = (now if now is not None else time.monotonic()) - base
        self.entries.append(LogEntry(max(0.0, stamp), message))

    def render(self) -> str:
        """Return the full dmesg text."""
        return "\n".join(entry.format() for entry in self.entries)
