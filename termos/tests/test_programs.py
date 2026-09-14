"""Tests for built-in programs and execution flow."""

from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout

from kernel.kernel import Kernel
from programs.calculator import safe_eval
from shell.shell import Shell


class CalculatorTest(unittest.TestCase):
    def test_safe_eval(self) -> None:
        self.assertEqual(safe_eval("25 + 17"), 42)
        self.assertEqual(safe_eval("(2 + 3) * 4"), 20)
        self.assertEqual(safe_eval("10 / 4"), 2.5)


class ProgramExecutionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.kernel = Kernel()
        self.kernel.boot()
        self.shell = Shell(self.kernel)

    def test_program_registration(self) -> None:
        for name in ("hello", "calc", "sysinfo", "uptime", "neofetch", "editor", "fortune"):
            self.assertTrue(self.kernel.programs.has(name))

    def test_execution_creates_process_and_frees_memory(self) -> None:
        before = self.kernel.memory.get_memory_stats()["used_mb"]
        output = io.StringIO()
        self.kernel.verbose = True
        with redirect_stdout(output):
            self.shell.execute("calc 2 + 2")
        text = output.getvalue()
        self.assertIn("[EXEC] Starting calc", text)
        self.assertIn("[PROC] PID", text)
        self.assertIn("[MEM ] Allocating", text)
        self.assertIn("4", text)
        after = self.kernel.memory.get_memory_stats()["used_mb"]
        self.assertEqual(before, after)
        self.assertEqual(len(self.kernel.processes.active()), 2)

    def test_unknown_program(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            self.shell.execute("calcx")
        self.assertIn("command not found: calcx", output.getvalue())

    def test_hello_and_sysinfo(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            self.shell.execute("hello")
            self.shell.execute("sysinfo")
            self.shell.execute("uptime")
            self.shell.execute("fortune")
            self.shell.execute("df")
        text = output.getvalue()
        self.assertIn("Hello from TERMOS!", text)
        self.assertIn("TERMOS SYSTEM INFORMATION", text)
        self.assertIn("Uptime:", text)
        self.assertTrue(len(text.strip()) > 40)
        self.assertIn("Filesystem", text)
        self.assertIn("vfs", text)


if __name__ == "__main__":
    unittest.main()
