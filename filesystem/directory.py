"""In-memory directory nodes."""

from __future__ import annotations

from core.errors import AlreadyExistsError, NotFoundError
from filesystem.node import Node
from permissions.permissions import DEFAULT_DIR_MODE


class Directory(Node):
    """A directory that owns its child nodes."""

    def __init__(
        self,
        name: str,
        parent: Node | None = None,
        uid: int = 0,
        gid: int = 0,
        owner: str = "root",
        group: str = "root",
        mode: int = DEFAULT_DIR_MODE,
    ) -> None:
        super().__init__(name, parent, uid, gid, owner, group, mode)
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
