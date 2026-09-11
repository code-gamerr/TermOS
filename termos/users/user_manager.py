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
        )
        self.add_user(
            "guest",
            uid=1000,
            gid=100,
            home="/home/guest",
            password="guest",
            groups=["users"],
        )
        self.current = root

    def add_group(self, name: str, gid: int) -> Group:
        """Create a group."""
        if name in self.groups or gid in self._by_gid:
            raise AlreadyExistsError(name)
        group = Group(name, gid)
        self.groups[name] = group
        self._by_gid[gid] = group
        return group

    def add_user(
        self,
        username: str,
        uid: int,
        gid: int,
        home: str,
        password: str = "",
        shell: str = "/bin/sh",
        groups: list[str] | None = None,
    ) -> User:
        """Create a user and attach them to their groups."""
        if username in self.users or uid in self._by_uid:
            raise AlreadyExistsError(username)
        if gid not in self._by_gid:
            raise NotFoundError(str(gid))
        primary = self._by_gid[gid]
        memberships = list(dict.fromkeys([primary.name, *(groups or [])]))
        for group_name in memberships:
            if group_name not in self.groups:
                raise NotFoundError(group_name)
        user = User(username, uid, gid, home, shell, password, memberships)
        self.users[username] = user
        self._by_uid[uid] = user
        for group_name in memberships:
            self.groups[group_name].add_member(username)
        return user

    def get_user(self, username: str) -> User:
        """Return a user by name."""
        try:
            return self.users[username]
        except KeyError as exc:
            raise NotFoundError(username) from exc

    def get_user_by_uid(self, uid: int) -> User:
        """Return a user by UID."""
        try:
            return self._by_uid[uid]
        except KeyError as exc:
            raise NotFoundError(str(uid)) from exc

    def get_group(self, name: str) -> Group:
        """Return a group by name."""
        try:
            return self.groups[name]
        except KeyError as exc:
            raise NotFoundError(name) from exc

    def get_group_by_gid(self, gid: int) -> Group:
        """Return a group by GID."""
        try:
            return self._by_gid[gid]
        except KeyError as exc:
            raise NotFoundError(str(gid)) from exc

    def switch_user(self, username: str, password: str) -> User:
        """Authenticate and set the current session user."""
        user = self.get_user(username)
        if not user.check_password(password):
            raise AuthenticationError("Authentication failure")
        self.current = user
        return user

    def require_current(self) -> User:
        """Return the current user or raise if unset."""
        if self.current is None:
            raise AuthenticationError("No current user")
        return self.current
