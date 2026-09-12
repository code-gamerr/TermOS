"""Tests for users, groups, and permissions."""

from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout

from core.errors import AuthenticationError, PermissionDeniedError
from kernel.kernel import Kernel
from permissions.permissions import Permissions
from shell.shell import Shell
from users.user_manager import UserManager


class UserManagerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.users = UserManager()

    def test_default_users_and_groups(self) -> None:
        self.assertIn("root", self.users.users)
        self.assertIn("guest", self.users.users)
        self.assertEqual(self.users.get_user("root").uid, 0)
        self.assertNotEqual(self.users.get_user("guest").uid, 0)
        self.assertEqual(set(self.users.groups), {"root", "users", "admin"})

    def test_user_creation(self) -> None:
        user = self.users.add_user("alice", uid=1001, gid=100, home="/home/alice", password="secret")
        self.assertEqual(user.username, "alice")