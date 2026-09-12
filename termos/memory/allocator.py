"""First Fit and Best Fit allocation strategies."""

from __future__ import annotations

from memory.memory_block import MemoryBlock


class Allocator:
    """Chooses a free block for an allocation request."""

    def __init__(self, strategy: str = "first_fit") -> None:
        self.strategy = strategy.lower().replace("-", "_")

    def set_strategy(self, strategy: str) -> None:
        """Switch between first_fit and best_fit."""
        self.strategy = strategy.lower().replace("-", "_")

    def choose(self, blocks: list[MemoryBlock], size_mb: float) -> MemoryBlock | None:
        """Return a free block that can hold ``size_mb``, or None."""
        candidates = [block for block in blocks if block.free and block.size_mb >= size_mb]
        if not candidates:
            return None
        if self.strategy == "best_fit":
            return min(candidates, key=lambda block: block.size_mb)
        return candidates[0]
