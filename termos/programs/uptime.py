"""Uptime program."""

from __future__ import annotations

from typing import TYPE_CHECKING

from programs.program import Program

if TYPE_CHECKING:
    from kernel.kernel import Kernel
    from shell.shell import Shell


class UptimeProgram(Program):
    name = "uptime"
    description = "Show kernel uptime"
    memory_mb = 2.0

    def run(self, kernel: Kernel, shell: Shell, args: list[str]) -> int:
        seconds = int(kernel.uptime)
        hours, rem = divmod(seconds, 3600)
        minutes, secs = divmod(rem, 60)
        print(f"Uptime: {hours:02d}:{minutes:02d}:{secs:02d}")
        return 0
