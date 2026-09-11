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
        self.assertIn("alice", self.users.get_group("users").members)

    def test_login_su(self) -> None:
        self.users.switch_user("guest", "guest")
        self.assertEqual(self.users.current.username, "guest")
        with self.assertRaises(AuthenticationError):
            self.users.switch_user("guest", "wrong")


class PermissionsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.kernel = Kernel()
        self.shell = Shell(self.kernel)
        self.root = self.kernel.users.get_user("root")
        self.guest = self.kernel.users.get_user("guest")

    def test_chmod_and_ls(self) -> None:
        self.shell.execute("touch secret.txt")
        self.shell.execute("chmod 600 secret.txt")
        node = self.kernel.filesystem.resolve("/home/root/secret.txt")
        self.assertEqual(node.mode, 0o600)
        self.assertEqual(Permissions.mode_to_string(node.mode), "rw-------")

        output = io.StringIO()
        with redirect_stdout(output):
            self.shell.execute("ls -l secret.txt")
        self.assertIn("-rw------- root root", output.getvalue())

    def test_chown(self) -> None:
        self.shell.execute("touch owned.txt")
        self.shell.execute("chown guest owned.txt")
        node = self.kernel.filesystem.resolve("/home/root/owned.txt")
        self.assertEqual(node.owner, "guest")
        self.assertEqual(node.uid, 1000)

    def test_denied_access_and_root_bypass(self) -> None:
        self.shell.execute("touch private.txt")
        self.shell.execute("chmod 600 private.txt")
        node = self.kernel.filesystem.resolve("/home/root/private.txt")

        with self.assertRaises(PermissionDeniedError):
            Permissions.require_read(self.guest, node)

        Permissions.require_read(self.root, node)

        self.shell.execute("su guest guest")
        output = io.StringIO()
        with redirect_stdout(output):
            self.shell.execute("cat /home/root/private.txt")
        self.assertIn("Permission denied", output.getvalue())
        self.assertEqual(self.shell.user, "guest")
        self.assertEqual(self.shell.path, "/home/guest")

        self.shell.execute("su root root")
        self.assertEqual(self.shell.user, "root")


class ShellUserCommandsTest(unittest.TestCase):
    def test_whoami_and_id(self) -> None:
        kernel = Kernel()
        shell = Shell(kernel)
        output = io.StringIO()
        with redirect_stdout(output):
            shell.execute("whoami")
            shell.execute("id")
        text = output.getvalue()
        self.assertIn("root", text)
        self.assertIn("uid=0(root)", text)
        self.assertIn("groups=root,admin", text)


if __name__ == "__main__":
    unittest.main()
