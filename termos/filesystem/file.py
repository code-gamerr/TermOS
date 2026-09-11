"""In-memory file nodes."""

from __future__ import annotations

from filesystem.node import Node
from permissions.permissions import DEFAULT_FILE_MODE


class File(Node):
    """A regular file stored entirely in memory."""

    def __init__(
        self,
        name: str,
        parent: Node | None = None,
        contents: str = "",
        uid: int = 0,
        gid: int = 0,
        owner: str = "root",
        group: str = "root",
        mode: int = DEFAULT_FILE_MODE,
    ) -> None:
        super().__init__(name, parent, uid, gid, owner, group, mode)
        self._contents = contents

    @property
    def contents(self) -> str:
        """Return the file contents."""
        return self._contents

    @contents.setter
    def contents(self, value: str) -> None:
        self._contents = value
        self.touch_modified()

    @property
    def size(self) -> int:
        """Return the UTF-8 size of the contents."""
        return len(self._contents.encode("utf-8"))
