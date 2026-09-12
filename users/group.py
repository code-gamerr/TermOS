"""Unix-like group for TERMOS."""

from __future__ import annotations


class Group:
    """A named group with a numeric GID."""

    def __init__(self, name: str, gid: int) -> None:
        self.name = name
        self.gid = gid
        self.members: set[str] = set()

    def add_member(self, username: str) -> None:
        """Record a username as a member of this group."""
        self.members.add(username)
