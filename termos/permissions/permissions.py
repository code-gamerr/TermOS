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
        return "".join(chars)

    @staticmethod
    def parse_mode(value: str) -> int:
        """Parse ``755``, ``0644``, or ``rwxr-xr-x`` into a mode integer."""
        text = value.strip()
        if text.isdigit():
            return int(text, 8) & 0o777
        if len(text) == 9 and all(ch in "rwx-" for ch in text):
            mode = 0
            for index, ch in enumerate(text):
                if ch == "-":
                    continue
                shift = 6 - (index // 3) * 3
                bit = {"r": READ, "w": WRITE, "x": EXECUTE}[ch]
                mode |= bit << shift
            return mode
        raise ValueError(f"invalid mode: {value}")

    @classmethod
    def check(cls, user: User, node: Node, access: int) -> None:
        """Raise ``PermissionDeniedError`` when ``user`` lacks ``access``."""
        if user.is_root:
            return
        mask = cls._effective_bits(user, node)
        if mask & access:
            return
        raise PermissionDeniedError("Permission denied")

    @classmethod
    def can_read(cls, user: User, node: Node) -> bool:
        return cls._allowed(user, node, READ)

    @classmethod
    def can_write(cls, user: User, node: Node) -> bool:
        return cls._allowed(user, node, WRITE)

    @classmethod
    def can_execute(cls, user: User, node: Node) -> bool:
        return cls._allowed(user, node, EXECUTE)

    @classmethod
    def require_read(cls, user: User, node: Node) -> None:
        cls.check(user, node, READ)

    @classmethod
    def require_write(cls, user: User, node: Node) -> None:
        cls.check(user, node, WRITE)

    @classmethod
    def require_execute(cls, user: User, node: Node) -> None:
        cls.check(user, node, EXECUTE)

    @staticmethod
    def _effective_bits(user: User, node: Node) -> int:
        mode = node.mode & 0o777
        if user.uid == node.uid:
            return (mode >> 6) & 0o7
        if user.gid == node.gid or any(
            group == node.group_name for group in user.groups
        ):
            return (mode >> 3) & 0o7
        return mode & 0o7

    @classmethod
    def _allowed(cls, user: User, node: Node, access: int) -> bool:
        try:
            cls.check(user, node, access)
            return True
        except PermissionDeniedError:
            return False
