"""Tests for networking and the system monitor."""

from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout

from kernel.kernel import Kernel
from network.network_manager import NetworkManager
from shell.shell import Shell


class NetworkManagerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.net = NetworkManager()

    def test_interface_and_ping(self) -> None:
        iface = self.net.primary()
        self.assertEqual(iface.name, "eth0")
        self.assertEqual(iface.ip, "10.0.0.2")
        lines = self.net.ping("10.0.0.1", count=2)
        self.assertEqual(self.net.tx, 2)
        self.assertEqual(self.net.rx, 2)
        self.assertIn("PING 10.0.0.1", lines[0])
        self.assertEqual(lines[1], "64 bytes")

    def test_netstat_and_route(self) -> None:
        table = self.net.netstat()
        self.assertIn("ESTABLISHED", table)
        self.assertIn("10.0.0.2:22", table)
        self.assertIn("default", self.net.route_table())


class MonitorIntegrationTest(unittest.TestCase):
    def test_monitor_tracks_live_metrics(self) -> None:
        kernel = Kernel()
        kernel.boot()
        shell = Shell(kernel)
        shell.execute("write demo.txt hello")
        before_tx = kernel.network.tx
        output = io.StringIO()
        with redirect_stdout(output):
            shell.execute("ping 10.0.0.1")
            shell.execute("monitor")
        self.assertGreater(kernel.network.tx, before_tx)
        text = output.getvalue()
        self.assertIn("TERMOS SYSTEM MONITOR", text)
        self.assertIn("NETWORK", text)
        snap = kernel.monitor.snapshot()
        self.assertGreaterEqual(snap["fs_used_mb"], 0)
        self.assertEqual(snap["processes_total"], 2)


if __name__ == "__main__":
    unittest.main()
