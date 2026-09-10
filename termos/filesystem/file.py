"""In-memory file nodes."""

from __future__ import annotations

from filesystem.node import Node


class File(Node):
    """A regular file stored entirely in memory."""

    def __init__(
        self,
        name: str,
        parent: Node | None = None,
        contents: str = "",
        owner: str = "root",
    ) -> None:
        super().__init__(name, parent, owner)
        self.mode = "rw-r--r--"
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
