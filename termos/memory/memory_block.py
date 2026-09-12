"""A single simulated RAM block."""

from __future__ import annotations

import time


class MemoryBlock:
    """One contiguous region in the simulated address space."""

    def __init__(
        self,
        start: int,
        size_mb: float,
        free: bool = True,
        owner: str = "-",
        pid: int | None = None,
    ) -> None:
        self.start = start
        self.size_mb = float(size_mb)
        self.free = free
        self.owner = owner
        self.pid = pid
        self.allocated_at = time.time()

    @property
    def end(self) -> int:
        """Exclusive end address."""
        from core.constants import MB_ADDRESS_UNIT

        return self.start + int(self.size_mb * MB_ADDRESS_UNIT)

    def format_address(self) -> str:
        """Return a hex address string."""
        return f"0x{self.start:X}"
