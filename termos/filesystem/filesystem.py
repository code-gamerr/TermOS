"""In-memory hierarchical filesystem. Never touches the host disk."""

from __future__ import annotations

from core.constants import HOME_PATH, ROOT_DIRECTORIES
from core.errors import (
    AlreadyExistsError,
    DirectoryNotEmptyError,
    FileSystemError,
    NotADirectoryError,
    NotAFileError,
    NotFoundError,
)
from filesystem.directory import Directory
from filesystem.file import File
from filesystem.node import Node


class FileSystem:
    """Virtual filesystem owned by the kernel.

    Paths are resolved inside TERMOS memory only. ``~`` means ``/home/root``.
    """

    def __init__(self) -> None:
        self.root = Directory("")
        self.home = HOME_PATH
        for name in ROOT_DIRECTORIES:
            self.root.add(Directory(name, self.root))
        home = self.root.get("home")
        if not isinstance(home, Directory):
            raise FileSystemError(HOME_PATH)
        home.add(Directory("root", home))

    def normalize(self, path: str) -> str:
        """Collapse ``.``, ``..``, and repeated slashes into an absolute path."""
        parts: list[str] = []
        for part in path.split("/"):
            if part in ("", "."):
                continue
            if part == "..":
                if parts:
                    parts.pop()
                continue
            parts.append(part)
        return "/" + "/".join(parts)

    def abspath(self, path: str, cwd: str = "/") -> str:
        """Resolve ``path`` against ``cwd``, including ``~``."""
        path = self._expand_home(path)
        if not path.startswith("/"):
            base = cwd if cwd.startswith("/") else "/" + cwd
            path = f"{base.rstrip('/')}/{path}"
        return self.normalize(path)

    def display_path(self, path: str) -> str:
        """Show the home directory as ``~``."""
        abs_path = self.normalize(path)
        if abs_path == self.home:
            return "~"
        prefix = self.home + "/"
        if abs_path.startswith(prefix):
            return "~/" + abs_path[len(prefix):]
        return abs_path

    def resolve(self, path: str, cwd: str = "/") -> Node:
        """Return the node at ``path``."""
        abs_path = self.abspath(path, cwd)
        if abs_path == "/":
            return self.root
        node: Node = self.root
        for part in abs_path.strip("/").split("/"):
            if not isinstance(node, Directory):
                raise NotADirectoryError(path)
            child = node.children.get(part)
            if child is None:
                raise NotFoundError(path)
            node = child
        return node

    def mkdir(self, path: str, cwd: str = "/") -> Directory:
        """Create a directory. Parents must already exist."""