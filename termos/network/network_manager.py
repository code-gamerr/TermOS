"""Simulated network stack for TERMOS. No real sockets."""

from __future__ import annotations

import hashlib

from core.errors import NetworkError
from network.connection import Connection
from network.interface import Interface
from network.packet import Packet


class NetworkManager:
    """Owns interfaces, packets, and fake connections."""

    def __init__(self) -> None:
        self.interfaces = {"eth0": Interface()}
        self.packets: list[Packet] = []
        self.connections: list[Connection] = [
            Connection("TCP", "10.0.0.2:22", "10.0.0.1:5321", "ESTABLISHED"),
        ]
        self.rx = 0
        self.tx = 0
        self.routes = [
            {"destination": "default", "gateway": "10.0.0.1", "iface": "eth0"},
            {"destination": "10.0.0.0/24", "gateway": "*", "iface": "eth0"},
        ]

    def primary(self) -> Interface:
        """Return the primary interface."""
        return self.interfaces["eth0"]

    def ifconfig(self) -> str:
        """Format interface information."""
        lines: list[str] = []
        for iface in self.interfaces.values():
            lines.extend(
                [
                    iface.name,
                    f"  inet {iface.ip}",
                    f"  netmask {iface.netmask}",
                    f"  gateway {iface.gateway}",
                    f"  mac {iface.mac}",
                    f"  status {iface.status}",
                ]
            )
        return "\n".join(lines)

    def ping(self, host: str, count: int = 4) -> list[str]:
        """Simulate ICMP echo replies with deterministic latency."""
        iface = self.primary()
        if iface.status != "UP":
            raise NetworkError("network is down")
        lines = [f"PING {host}"]
        for index in range(count):
            packet = Packet(iface.ip, host, "ICMP", size=64)
            self.packets.append(packet)
            self.tx += 1
            reply = Packet(host, iface.ip, "ICMP", size=64)
            self.packets.append(reply)
            self.rx += 1
            latency = 8 + (int(hashlib.md5(f"{host}:{index}".encode()).hexdigest(), 16) % 10)
            lines.append("64 bytes")
            lines.append(f"latency={latency}ms")
        return lines

    def netstat(self) -> str:
        """Format the connection table."""
        lines = [f"{'PROTO':<6} {'LOCAL':<16} {'REMOTE':<16} STATE"]
        for conn in self.connections:
            lines.append(f"{conn.protocol:<6} {conn.local:<16} {conn.remote:<16} {conn.state}")
        return "\n".join(lines)

    def route_table(self) -> str:
        """Format the routing table."""
        lines = [f"{'DESTINATION':<16} {'GATEWAY':<12} IFACE"]
        for route in self.routes:
            lines.append(f"{route['destination']:<16} {route['gateway']:<12} {route['iface']}")
        return "\n".join(lines)
