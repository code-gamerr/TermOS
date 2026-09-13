"""Unix-like user account for TERMOS."""

from __future__ import annotations

import hashlib


class User:
    """A TERMOS user account.

    Passwords are stored as a simple SHA-256 hex digest. This is a simulator,
    not real authentication security.
    """

    def __init__(
        self,
        username: str,
        uid: int,
        gid: int,
        home: str,
        shell: str = "/bin/sh",
        password: str = "",
        groups: list[str] | None = None,
    ) -> None:
        self.username = username
        self.uid = uid
        self.gid = gid
        self.home = home
        self.shell = shell
        self.password_hash = self.hash_password(password)
        self.groups = list(groups or [])

    @staticmethod
    def hash_password(password: str) -> str:
        """Return a deterministic password representation."""
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    def check_password(self, password: str) -> bool:
        """Return whether ``password`` matches the stored hash."""
