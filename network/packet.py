"""Simulated network packet."""

from __future__ import annotations

import time


class Packet:
    """One simulated network packet."""

    def __init__(
        self,
        source: str,
        destination: str,
        protocol: str,
        size: int = 64,
        ttl: int = 64,
    ) -> None:
        self.source = source
        self.destination = destination
        self.protocol = protocol.upper()
        self.size = size
        self.ttl = ttl
        self.timestamp = time.time()
