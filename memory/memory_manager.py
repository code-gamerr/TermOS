"""Simulated RAM manager for TERMOS. Never touches host memory."""

from __future__ import annotations

from core.constants import DEFAULT_ALLOCATOR, MB_ADDRESS_UNIT, TOTAL_RAM_MB
from core.errors import NotFoundError, OutOfMemoryError
from memory.allocator import Allocator
from memory.memory_block import MemoryBlock


class MemoryManager:
    """Owns the simulated 128 MB address space and allocation strategy."""

    def __init__(self, total_mb: int = TOTAL_RAM_MB, strategy: str = DEFAULT_ALLOCATOR) -> None:
        self.total_mb = float(total_mb)
        self.allocator = Allocator(strategy)
        self.allocations = 0
        self.blocks: list[MemoryBlock] = [MemoryBlock(0, self.total_mb, free=True)]

    def allocate(self, size_mb: float, owner: str, pid: int | None = None) -> MemoryBlock:
        """Allocate ``size_mb`` using the configured strategy."""
        if size_mb <= 0:
            raise OutOfMemoryError("TERMOS: Out of memory")
        target = self.allocator.choose(self.blocks, size_mb)
        if target is None:
            raise OutOfMemoryError("TERMOS: Out of memory")

        index = self.blocks.index(target)
        if target.size_mb > size_mb:
            leftover = MemoryBlock(target.start + int(size_mb * MB_ADDRESS_UNIT), target.size_mb - size_mb)
            target.size_mb = size_mb
            self.blocks.insert(index + 1, leftover)

        target.free = False
        target.owner = owner
        target.pid = pid
        target.allocated_at = __import__("time").time()
        self.allocations += 1
        return target

    def free(self, address: int) -> None:
        """Free the block starting at ``address`` and coalesce neighbors."""