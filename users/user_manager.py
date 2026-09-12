"""User and group accounts owned by the kernel."""

from __future__ import annotations

from core.errors import AlreadyExistsError, AuthenticationError, NotFoundError
from users.group import Group
from users.user import User


class UserManager:
    """Creates default accounts and tracks the current session user."""

    def __init__(self) -> None:
        self.groups: dict[str, Group] = {}
        self.users: dict[str, User] = {}
        self._by_uid: dict[int, User] = {}
        self._by_gid: dict[int, Group] = {}
        self.current: User | None = None
        self._seed_defaults()

    def _seed_defaults(self) -> None:
        self.add_group("root", 0)
        self.add_group("users", 100)
        self.add_group("admin", 10)

        root = self.add_user(
            "root",
            uid=0,
            gid=0,
            home="/home/root",
            password="root",
            groups=["root", "admin"],