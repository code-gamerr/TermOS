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
        self.assertIn(worker.state, {ProcessState.READY, ProcessState.RUNNING})
        self.pm.terminate(worker.pid)
        self.assertEqual(worker.state, ProcessState.TERMINATED)

    def test_scheduler_queue_and_state_transitions(self) -> None:
        self.pm.bootstrap()
        a = self.pm.create("a", uid=0, command="a", auto_schedule=True)
        b = self.pm.create("b", uid=0, command="b", auto_schedule=True)
        self.assertIn(a.pid, list(self.pm.scheduler.ready) + [self.pm.scheduler.running_pid])
        self.assertIn(b.pid, list(self.pm.scheduler.ready) + [self.pm.scheduler.running_pid])

        self.pm.sleep(a.pid)
        self.assertEqual(a.state, ProcessState.SLEEPING)
        self.pm.wake(a.pid)
        self.assertIn(a.state, {ProcessState.READY, ProcessState.RUNNING})

        running = self.pm.scheduler.tick()
        self.assertIsNotNone(running)
        self.assertEqual(running.state, ProcessState.RUNNING)


class ShellProcessCommandsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.kernel = Kernel()
        self.kernel.boot()
        self.shell = Shell(self.kernel)

    def test_shell_process_exists(self) -> None:
        shell_proc = self.kernel.processes.get(2)
        self.assertEqual(shell_proc.name, "shell")
        self.assertEqual(shell_proc.state, ProcessState.RUNNING)

    def test_ps_kill_scheduler(self) -> None:
        worker = self.kernel.processes.create("demo", uid=0, command="demo")
        output = io.StringIO()
        with redirect_stdout(output):
            self.shell.execute("ps")
            self.shell.execute("scheduler")
            self.shell.execute(f"kill {worker.pid}")
        text = output.getvalue()
        self.assertIn("init", text)
        self.assertIn("shell", text)
        self.assertIn("Round Robin", text)
        self.assertIn(f"[ OK ] Process {worker.pid} terminated.", text)
        self.assertEqual(worker.state, ProcessState.TERMINATED)


if __name__ == "__main__":
    unittest.main()
