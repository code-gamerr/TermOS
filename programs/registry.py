"""Registry of built-in TERMOS programs."""

from __future__ import annotations

from core.errors import NotFoundError
from programs.calculator import CalculatorProgram
from programs.editor import EditorProgram
from programs.hello import HelloProgram
from programs.neofetch import NeofetchProgram
from programs.program import Program
from programs.sysinfo import SysInfoProgram
from programs.uptime import UptimeProgram


class ProgramRegistry:
    """Maps program names to Program instances."""

    def __init__(self) -> None:
        self._programs: dict[str, Program] = {}
        self.register_defaults()

    def register(self, program: Program) -> None:
        """Add or replace a program."""
        self._programs[program.name] = program

    def register_defaults(self) -> None:
        """Install the built-in programs."""
        for program in (
            HelloProgram(),
            CalculatorProgram(),
            SysInfoProgram(),
            UptimeProgram(),