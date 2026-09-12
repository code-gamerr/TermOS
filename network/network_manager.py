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