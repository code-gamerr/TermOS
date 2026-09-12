"""Simulated network interface."""

from __future__ import annotations


class Interface:
    """A virtual NIC such as eth0."""

    def __init__(
        self,
        name: str = "eth0",
        ip: str = "10.0.0.2",
        netmask: str = "255.255.255.0",
        gateway: str = "10.0.0.1",
        mac: str = "02:00:00:00:00:01",
        status: str = "UP",
    ) -> None:
        self.name = name
        self.ip = ip
        self.netmask = netmask
        self.gateway = gateway
        self.mac = mac
        self.status = status
