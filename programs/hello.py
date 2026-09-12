"""Hello world program."""

from __future__ import annotations

from typing import TYPE_CHECKING

from programs.program import Program

if TYPE_CHECKING:
    from kernel.kernel import Kernel
    from shell.shell import Shell


class HelloProgram(Program):
    name = "hello"
    description = "Print a greeting"
    memory_mb = 2.0

    def run(self, kernel: Kernel, shell: Shell, args: list[str]) -> int:
        print("Hello from TERMOS!")
        return 0
