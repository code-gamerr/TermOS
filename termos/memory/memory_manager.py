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
        for block in self.blocks:
            if block.start == address and not block.free:
                block.free = True
                block.owner = "-"
                block.pid = None
                self._coalesce()
                return
        raise NotFoundError(hex(address))

    def free_process_memory(self, pid: int) -> float:
        """Release every block owned by ``pid``. Return MB freed."""
        freed = 0.0
        for block in self.blocks:
            if block.pid == pid and not block.free:
                freed += block.size_mb
                block.free = True
                block.owner = "-"
                block.pid = None
        if freed:
            self._coalesce()
        return freed

    def get_memory_stats(self) -> dict[str, float | str | int]:
        """Return aggregate memory statistics."""
        used = sum(block.size_mb for block in self.blocks if not block.free)
        free = self.total_mb - used
        return {
            "total_mb": self.total_mb,
            "used_mb": used,
            "free_mb": free,
            "allocations": self.allocations,
            "fragmentation": self.fragmentation(),
            "allocator": self.allocator.strategy.replace("_", " ").title(),
        }

    def get_memory_map(self) -> list[MemoryBlock]:
        """Return the current block list in address order."""
        return list(self.blocks)

    def fragmentation(self) -> float:
        """Percent of free memory that is not in the largest free hole."""
        free_blocks = [block.size_mb for block in self.blocks if block.free]
        free_total = sum(free_blocks)
        if free_total <= 0:
            return 0.0
        largest = max(free_blocks)
        return round((1.0 - (largest / free_total)) * 100.0, 1)

    def set_allocator(self, strategy: str) -> None:
        """Configure First Fit or Best Fit."""
        self.allocator.set_strategy(strategy)

    def _coalesce(self) -> None:
        merged: list[MemoryBlock] = []
        for block in self.blocks:
            if merged and merged[-1].free and block.free:
                merged[-1].size_mb += block.size_mb
            else:
                merged.append(block)
        self.blocks = merged
