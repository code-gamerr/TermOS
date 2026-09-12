"""Neofetch-style system banner."""

from __future__ import annotations

from typing import TYPE_CHECKING

from programs.program import Program

if TYPE_CHECKING:
    from kernel.kernel import Kernel
    from shell.shell import Shell


class NeofetchProgram(Program):
    name = "neofetch"
    description = "Show a styled TERMOS summary"
    memory_mb = 3.0

    def run(self, kernel: Kernel, shell: Shell, args: list[str]) -> int:
        mem = kernel.memory.get_memory_stats()
        user = kernel.users.require_current().username
        banner = (
            "████████████████\n"
            "██    TERMOS  ██\n"
            "████████████████"
        )
        try:
            print(banner)
        except UnicodeEncodeError:
            print("################\n##   TERMOS   ##\n################")
        print()
        print(f"OS:         {kernel.name} {kernel.version}")
        print("Kernel:     TERMOS Kernel")
        print("Shell:      termos-sh")
        print(f"User:       {user}")
        print(f"Hostname:   {kernel.hostname}")
        print("CPU:        Simulated CPU")
        print(f"Memory:     {int(mem['used_mb'])}MB / {int(mem['total_mb'])}MB")
        print(f"Processes:  {len(kernel.processes.active())}")
        print("Filesystem: VFS")
        print(f"Network:    {kernel.network.primary().name}")
        return 0
