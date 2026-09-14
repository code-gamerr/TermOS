"""Fortune — random TERMOS tips for demos."""

from __future__ import annotations

import hashlib
import time
from typing import TYPE_CHECKING

from programs.program import Program

if TYPE_CHECKING:
    from kernel.kernel import Kernel
    from shell.shell import Shell

_FORTUNES = (
    "TERMOS: where every filesystem fits in RAM and none of it is real.",
    "root@termos:~$ — with great UID 0 comes great responsibility.",
    "Round Robin never sleeps. Your shell process might.",
    "Permission denied is just TERMOS's way of saying 'nice try, guest'.",
    "128 MB ought to be enough for anybody. In a simulator.",
    "dmesg never lies. It just timestamps everything at 00:00:00 if you're fast.",
    "Pipes in TERMOS: no subprocesses were harmed in the making of this pipeline.",
    "neofetch: because every fake OS deserves a banner.",
    "First Fit is fast. Best Fit is polite. Out of memory is honest.",
    "demo is the shortest path from 'what is this?' to 'okay, wow'.",
)


class FortuneProgram(Program):
    name = "fortune"
    description = "Print a random TERMOS tip"
    memory_mb = 1.0

    def run(self, kernel: Kernel, shell: Shell, args: list[str]) -> int:
        seed = f"{time.time_ns()}:{kernel.uptime}:{len(kernel.logger.entries)}"
        index = int(hashlib.md5(seed.encode()).hexdigest(), 16) % len(_FORTUNES)
        print(_FORTUNES[index])
        return 0
