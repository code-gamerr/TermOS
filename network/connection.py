"""Simulated network connection."""

from __future__ import annotations


class Connection:
    """A simulated TCP/UDP connection entry."""

    def __init__(
        self,
        protocol: str,
        local: str,
        remote: str,
        state: str = "ESTABLISHED",
    ) -> None:
        self.protocol = protocol.upper()
        self.local = local
        self.remote = remote
        self.state = state
