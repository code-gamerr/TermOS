"""In-memory directory nodes."""

from __future__ import annotations

from core.errors import AlreadyExistsError, NotFoundError
from filesystem.node import Node


class Directory(Node):
    """A directory that owns its child nodes."""

    def __init__(self, name: str, parent: Node | None = None, owner: str = "root") -> None:
        super().__init__(name, parent, owner)
        self.mode = "rwxr-xr-x"
        self.children: dict[str, Node] = {}

    @property
    def is_dir(self) -> bool:
        return True

    def add(self, node: Node) -> None:
        """Attach a child and set its parent."""
        if node.name in self.children:
            raise AlreadyExistsError(node.name)
        node.parent = self
        self.children[node.name] = node
        self.touch_modified()

    def get(self, name: str) -> Node:
        """Return a direct child, or raise if it is missing."""
        try:
            return self.children[name]
        except KeyError as exc:
            raise NotFoundError(name) from exc

    def remove(self, name: str) -> Node:
        """Detach a direct child."""
        node = self.get(name)
        del self.children[name]
        node.parent = None
        self.touch_modified()
        return node
