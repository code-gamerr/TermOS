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
        mem = kernel.memory.get_memory_stats()
        print("TERMOS SYSTEM INFORMATION")
        print("-------------------------")
        print(f"OS:          {kernel.name}")
        print(f"Version:     {kernel.version}")
        print("Kernel:      TERMOS Kernel")
        print("Shell:       termos-sh")
        print(f"Hostname:    {kernel.hostname}")
        print("CPU:         Simulated CPU")
        print(f"RAM:         {int(mem['total_mb'])} MB")
        print(f"Processes:   {len(kernel.processes.active())}")
        print(f"Users:       {len(kernel.users.users)}")
        print("Filesystem:  Virtual FS")
        iface = kernel.network.primary()
        print(f"Network:     {iface.name}")
        return 0
