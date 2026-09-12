"""Shared metadata for virtual filesystem nodes."""

from __future__ import annotations

import time

from permissions.permissions import DEFAULT_DIR_MODE, DEFAULT_FILE_MODE, Permissions


class Node:
    """A named entry in the in-memory filesystem."""

    def __init__(
        self,
        name: str,
        parent: Node | None = None,
        uid: int = 0,
        gid: int = 0,
        owner: str = "root",
        group: str = "root",
        mode: int = DEFAULT_FILE_MODE,
    ) -> None:
        now = time.time()
        self.name = name
        self.parent = parent
        self.uid = uid
        self.gid = gid
        self.owner = owner
        self.group_name = group
        self.mode = mode & 0o777
        self.created_at = now
        self.modified_at = now

    @property
    def is_dir(self) -> bool:
        """Return whether this node is a directory."""
        return False

    @property
    def size(self) -> int:
        """Return the size in bytes."""
        return 0

    @property
    def mode_string(self) -> str:
        """Return the permission string without the type prefix."""
        return Permissions.mode_to_string(self.mode)
    def touch_modified(self) -> None:
        """Update the modification timestamp."""
        self.modified_at = time.time()
