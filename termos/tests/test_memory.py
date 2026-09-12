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

    def test_best_fit(self) -> None:
        self.mem.set_allocator("best_fit")
        self.mem.allocate(20, "big", pid=1)
        hole = self.mem.allocate(10, "mid", pid=2)
        self.mem.allocate(30, "tail", pid=3)
        self.mem.free(hole.start)
        # free map: 20 used, 10 free, 30 used, 68 free -> best fit for 8 is the 10 hole
        chosen = self.mem.allocate(8, "fit", pid=4)
        self.assertEqual(chosen.start, hole.start)

    def test_fragmentation_and_oom(self) -> None:
        self.mem.allocate(50, "a", pid=1)
        mid = self.mem.allocate(20, "b", pid=2)
        self.mem.allocate(40, "c", pid=3)
        self.mem.free(mid.start)
        self.assertGreater(self.mem.fragmentation(), 0)
        with self.assertRaises(OutOfMemoryError):
            self.mem.allocate(30, "too-big", pid=4)

    def test_process_memory_accounting(self) -> None:
        self.mem.allocate(4, "PID 7", pid=7)
        self.mem.allocate(4, "PID 7", pid=7)
        freed = self.mem.free_process_memory(7)
        self.assertEqual(freed, 8)
        self.assertEqual(self.mem.get_memory_stats()["used_mb"], 0)


class KernelMemoryIntegrationTest(unittest.TestCase):
    def test_boot_reserves_memory_and_shell_commands(self) -> None:
        kernel = Kernel()
        kernel.boot()
        stats = kernel.memory.get_memory_stats()
        self.assertEqual(stats["used_mb"], 8 + 8 + 12)

        shell = Shell(kernel)
        output = io.StringIO()
        with redirect_stdout(output):
            shell.execute("free")
            shell.execute("memory")
            shell.execute("memmap")
        text = output.getvalue()
        self.assertIn("128MB", text)
        self.assertIn("First Fit", text)
        self.assertIn("kernel", text)


if __name__ == "__main__":
    unittest.main()
