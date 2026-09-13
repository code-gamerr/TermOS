"""In-memory hierarchical filesystem. Never touches the host disk."""

from __future__ import annotations

from typing import TYPE_CHECKING

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
from permissions.permissions import DEFAULT_DIR_MODE, DEFAULT_FILE_MODE, Permissions

if TYPE_CHECKING:
    from users.user import User


class FileSystem:
    """Virtual filesystem owned by the kernel.

    Paths are resolved inside TERMOS memory only. ``~`` expands to ``self.home``.
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
        home.add(Directory("guest", home, uid=1000, gid=100, owner="guest", group="users"))
        from core.config import ConfigManager

        ConfigManager.install(self)

    def set_home(self, path: str) -> None:
        """Update the path that ``~`` expands to."""
        self.home = self.normalize(path)

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
        """Show the current home directory as ``~``."""
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

    def mkdir(self, path: str, cwd: str = "/", user: User | None = None) -> Directory:
        """Create a directory. Parents must already exist."""
        parent, name = self._parent_and_name(path, cwd)
        if user is not None:
            Permissions.require_write(user, parent)
        if name in parent.children:
            raise AlreadyExistsError(path)
        directory = Directory(
            name,
            parent,
            **self._owner_kwargs(user, DEFAULT_DIR_MODE),
        )
        parent.add(directory)
        return directory

    def touch(self, path: str, cwd: str = "/", user: User | None = None) -> File:
        """Create an empty file, or update the timestamp if it exists."""
        parent, name = self._parent_and_name(path, cwd)
        existing = parent.children.get(name)
        if existing is None:
            if user is not None:
                Permissions.require_write(user, parent)
            node = File(name, parent, **self._owner_kwargs(user, DEFAULT_FILE_MODE))
            parent.add(node)
            return node
        if not isinstance(existing, File):
            raise NotAFileError(path)
        if user is not None:
            Permissions.require_write(user, existing)
        existing.touch_modified()
        return existing

    def write(self, path: str, contents: str, cwd: str = "/", user: User | None = None) -> File:
        """Create or overwrite a file with ``contents``."""
        parent, name = self._parent_and_name(path, cwd)
        existing = parent.children.get(name)
        if existing is None:
            if user is not None:
                Permissions.require_write(user, parent)
            node = File(
                name,
                parent,
                contents,
                **self._owner_kwargs(user, DEFAULT_FILE_MODE),
            )
            parent.add(node)
            return node
        if not isinstance(existing, File):
            raise NotAFileError(path)
        if user is not None:
            Permissions.require_write(user, existing)
        existing.contents = contents
        return existing

    def read(self, path: str, cwd: str = "/", user: User | None = None) -> str:
        """Return file contents."""
        node = self.resolve(path, cwd)
        if not isinstance(node, File):
            raise NotAFileError(path)
        if user is not None:
            Permissions.require_read(user, node)
        return node.contents

    def remove(self, path: str, cwd: str = "/", user: User | None = None) -> None:
        """Delete a file. Directories must be removed with ``rmdir``."""
        parent, name = self._parent_and_name(path, cwd)
        existing = parent.children.get(name)
        if existing is None:
            raise NotFoundError(path)
        if isinstance(existing, Directory):
            raise NotAFileError(path)
        if user is not None:
            Permissions.require_write(user, parent)
        parent.remove(name)

    def rmdir(self, path: str, cwd: str = "/", user: User | None = None) -> None:
        """Remove an empty directory."""
        abs_path = self.abspath(path, cwd)
        if abs_path == "/":
            raise FileSystemError(path)
        node = self.resolve(path, cwd)
        if not isinstance(node, Directory):
            raise NotADirectoryError(path)
        if node.children:
            raise DirectoryNotEmptyError(path)
        if node.parent is None or not isinstance(node.parent, Directory):
            raise FileSystemError(path)
        if user is not None:
            Permissions.require_write(user, node.parent)
        node.parent.remove(node.name)

    def listdir(self, path: str, cwd: str = "/", user: User | None = None) -> Directory:
        """Return the directory at ``path``."""
        node = self.resolve(path, cwd)
        if not isinstance(node, Directory):
            raise NotADirectoryError(path)
        if user is not None:
            Permissions.require_read(user, node)
        return node

    def chmod(self, path: str, mode: int, cwd: str = "/", user: User | None = None) -> Node:
        """Change a node's permission bits. Owner or root only."""
        from core.errors import PermissionDeniedError

        node = self.resolve(path, cwd)
        if user is not None and not user.is_root and user.uid != node.uid:
            raise PermissionDeniedError("Permission denied")
        node.mode = mode & 0o777
        node.touch_modified()
        return node

    def chown(
        self,
        path: str,
        owner: str,
        group: str | None = None,
        cwd: str = "/",
        uid: int = 0,
        gid: int | None = None,
        user: User | None = None,
    ) -> Node:
        """Change a node's owner and optional group."""
        from core.errors import PermissionDeniedError

        node = self.resolve(path, cwd)
        if user is not None and not user.is_root:
            raise PermissionDeniedError("Permission denied")
        node.owner = owner
        node.uid = uid
        if group is not None and gid is not None:
            node.group_name = group
            node.gid = gid
        node.touch_modified()
        return node

    def tree(self, path: str = "/", cwd: str = "/") -> str:
        """Return a text tree starting at ``path``."""
        node = self.resolve(path, cwd)
        if not isinstance(node, Directory):
            return node.name
        label = "/" if node is self.root else node.name
        lines = [label]
        lines.extend(self._tree_lines(node, ""))
        return "\n".join(lines)

    def _owner_kwargs(self, user: User | None, mode: int) -> dict[str, object]:
        if user is None:
            return {"uid": 0, "gid": 0, "owner": "root", "group": "root", "mode": mode}
        return {
            "uid": user.uid,
            "gid": user.gid,
            "owner": user.username,
            "group": user.groups[0] if user.groups else "users",
            "mode": mode,
        }

    def _parent_and_name(self, path: str, cwd: str) -> tuple[Directory, str]:
        abs_path = self.abspath(path, cwd)
        if abs_path == "/":
            raise AlreadyExistsError(path)
        parent_path, name = abs_path.rsplit("/", 1)
        parent = self.resolve(parent_path or "/", "/")
        if not isinstance(parent, Directory):
            raise NotADirectoryError(path)
        return parent, name

    def _expand_home(self, path: str) -> str:
        if path == "~":
            return self.home
        if path.startswith("~/"):
            return self.home + "/" + path[2:]
        return path

    def _tree_lines(self, directory: Directory, prefix: str) -> list[str]:
        children = list(directory.children.values())
        lines: list[str] = []
        for index, child in enumerate(children):
            last = index == len(children) - 1
            branch = "└── " if last else "├── "
            lines.append(f"{prefix}{branch}{child.name}")
            if isinstance(child, Directory) and child.children:
                extension = "    " if last else "│   "
                lines.extend(self._tree_lines(child, prefix + extension))
        return lines
