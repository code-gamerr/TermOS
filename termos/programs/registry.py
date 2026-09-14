"""Registry of built-in TERMOS programs."""

from __future__ import annotations

from core.errors import NotFoundError
from programs.calculator import CalculatorProgram
from programs.editor import EditorProgram
from programs.fortune import FortuneProgram
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
            NeofetchProgram(),
            EditorProgram(),
            FortuneProgram(),
        ):
            self.register(program)

    def get(self, name: str) -> Program:
        """Return a program by name."""
        try:
            return self._programs[name]
        except KeyError as exc:
            raise NotFoundError(name) from exc

    def has(self, name: str) -> bool:
        """Return whether ``name`` is a registered program."""
        return name in self._programs

    def names(self) -> list[str]:
        """Return sorted program names."""
        return sorted(self._programs)
