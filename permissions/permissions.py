"""Centralized Unix-like permission checks for TERMOS."""

from __future__ import annotations

from typing import TYPE_CHECKING

from core.errors import PermissionDeniedError

if TYPE_CHECKING:
    from filesystem.node import Node
    from users.user import User

READ = 4
WRITE = 2
EXECUTE = 1

DEFAULT_FILE_MODE = 0o644
DEFAULT_DIR_MODE = 0o755


class Permissions:
    """All access decisions go through here. Root (UID 0) bypasses checks."""

    @staticmethod
    def mode_to_string(mode: int) -> str:
        """Convert a mode integer into ``rwxr-xr--`` style text."""
        bits = (
            (READ, "r"),
            (WRITE, "w"),
            (EXECUTE, "x"),
        )
        chars: list[str] = []
        for shift in (6, 3, 0):
            triplet = (mode >> shift) & 0o7
            for flag, letter in bits:
                chars.append(letter if triplet & flag else "-")