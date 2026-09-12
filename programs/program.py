"""Base class for built-in TERMOS programs."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kernel.kernel import Kernel
    from shell.shell import Shell


class Program(ABC):
    """Controlled program abstraction. No arbitrary user code execution."""

    name: str = ""
    description: str = ""
    version: str = "1.0"
    required_permissions: str = "user"
    memory_mb: float = 4.0

    @abstractmethod
    def run(self, kernel: Kernel, shell: Shell, args: list[str]) -> int:
        """Execute the program. Return an exit code."""
