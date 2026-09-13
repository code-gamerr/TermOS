"""System information program."""

from __future__ import annotations

from typing import TYPE_CHECKING

from programs.program import Program

if TYPE_CHECKING:
    from kernel.kernel import Kernel
    from shell.shell import Shell


class SysInfoProgram(Program):
    name = "sysinfo"
    description = "Show TERMOS system information"
    memory_mb = 3.0

    def run(self, kernel: Kernel, shell: Shell, args: list[str]) -> int:
        info = kernel.system_info()
        mem = info["memory"]
        user = kernel.users.require_current()
        print("TERMOS SYSTEM INFORMATION")
        print("-------------------------")
        print(f"OS:           {kernel.name}")
        print(f"Version:      {kernel.version}")
        print("Kernel:       TERMOS Kernel")
        print(f"Hostname:     {kernel.hostname}")
        print(f"Shell:        {kernel.config.get('shell', 'termos-sh')}")
        print(f"User:         {user.username}")
        print("CPU:          Simulated CPU")
        print(f"Memory:       {int(mem['used_mb'])} MB / {int(mem['total_mb'])} MB")
        print(f"Processes:    {len(kernel.processes.active())}")
        print("Filesystem:   Virtual FS")
        print(f"Network:      {kernel.network.primary().name}")
        print(f"Scheduler:    {info['scheduler']}")
        print(f"Allocator:    {info['allocator']}")
        print(f"Uptime:       {info['uptime']}")
        return 0
