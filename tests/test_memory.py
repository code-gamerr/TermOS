"""Tests for the simulated memory manager."""

from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout

from core.errors import OutOfMemoryError
from kernel.kernel import Kernel
from memory.memory_manager import MemoryManager
from shell.shell import Shell


class MemoryManagerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.mem = MemoryManager(total_mb=128, strategy="first_fit")

    def test_allocation_and_free(self) -> None:
        block = self.mem.allocate(8, "kernel")
        self.assertFalse(block.free)
        self.assertEqual(block.owner, "kernel")
        self.mem.free(block.start)
        self.assertTrue(self.mem.blocks[0].free)
        self.assertEqual(self.mem.blocks[0].size_mb, 128)

    def test_first_fit(self) -> None:
        self.mem.set_allocator("first_fit")
        a = self.mem.allocate(10, "a", pid=1)
        b = self.mem.allocate(10, "b", pid=2)
        self.mem.free(a.start)
        chosen = self.mem.allocate(8, "c", pid=3)
        self.assertEqual(chosen.start, a.start)
