"""Shared metadata for virtual filesystem nodes."""

from __future__ import annotations

import time


class Node:
    """A named entry in the in-memory filesystem.

    Permissions and owner are stored only. They are not enforced yet.
    """

    def __init__(self, name: str, parent: Node | None = None, owner: str = "root") -> None:
        now = time.time()
        self.name = name
        self.parent = parent
        self.owner = owner
        self.mode = "rwxr-xr-x"
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

    def touch_modified(self) -> None:
        """Update the modification timestamp."""
        self.modified_at = time.time()
