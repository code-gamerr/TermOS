"""Tests for the process manager and Round Robin scheduler."""

from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout

from kernel.kernel import Kernel
from processes.process import ProcessState
from processes.process_manager import ProcessManager
from shell.shell import Shell


class ProcessManagerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.pm = ProcessManager()

    def test_pid_allocation_and_bootstrap(self) -> None:
        init, shell = self.pm.bootstrap()
        self.assertEqual(init.pid, 1)
        self.assertEqual(shell.pid, 2)
        self.assertEqual(init.name, "init")
        self.assertEqual(shell.name, "shell")
        self.assertEqual(init.state, ProcessState.RUNNING)
        self.assertEqual(shell.state, ProcessState.RUNNING)

    def test_process_creation_and_termination(self) -> None:
        self.pm.bootstrap()
        worker = self.pm.create("worker", uid=0, command="worker")
        self.assertEqual(worker.pid, 3)