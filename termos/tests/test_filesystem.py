"""Tests for the in-memory filesystem."""

from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout

from core.errors import AlreadyExistsError, DirectoryNotEmptyError, NotAFileError, NotFoundError
from filesystem.file import File
from filesystem.filesystem import FileSystem
from kernel.kernel import Kernel
from shell.shell import Shell


class FileSystemTest(unittest.TestCase):
    def setUp(self) -> None:
        self.fs = FileSystem()

    def test_initial_tree(self) -> None:
        self.assertEqual(
            self.fs.tree(),
            "/\n"
            "├── bin\n"
            "│   ├── hello.sh\n"
            "│   ├── greet.sh\n"
            "│   ├── countdown.sh\n"
            "│   ├── syscheck.sh\n"
            "│   └── args.sh\n"
            "├── home\n"
            "│   ├── root\n"
            "│   └── guest\n"
            "├── etc\n"
            "│   └── termos.conf\n"
            "├── tmp\n"
            "└── var",
        )

    def test_directory_creation(self) -> None:
        self.fs.mkdir("projects", "/home/root")
        node = self.fs.resolve("/home/root/projects")
        self.assertTrue(node.is_dir)
        self.assertIs(node.parent, self.fs.resolve("/home/root"))

    def test_file_creation_write_read_delete(self) -> None:
        self.fs.mkdir("/home/root/projects")
        created = self.fs.touch("/home/root/projects/hello.txt")
        self.assertIsInstance(created, File)
        self.assertEqual(created.size, 0)

        written = self.fs.write("/home/root/projects/hello.txt", "hello world")
        self.assertEqual(written.size, 11)
        self.assertEqual(self.fs.read("/home/root/projects/hello.txt"), "hello world")

        self.fs.remove("/home/root/projects/hello.txt")
        with self.assertRaises(NotFoundError):
            self.fs.read("/home/root/projects/hello.txt")

    def test_path_resolution(self) -> None:
        self.assertEqual(
            self.fs.normalize("/home/user/../user/test.txt"),
            "/home/user/test.txt",
        )
        self.fs.mkdir("/home/user")
        self.fs.touch("/home/user/test.txt")
        node = self.fs.resolve("/home/user/../user/test.txt")
        self.assertEqual(node.name, "test.txt")
        self.assertIs(node, self.fs.resolve("/home/user/test.txt"))

    def test_relative_paths_and_parent_navigation(self) -> None:
        self.fs.mkdir("projects", "/home/root")
        self.fs.write("projects/hello.txt", "hello world", "/home/root")

        node = self.fs.resolve("./projects/../projects/hello.txt", "/home/root")
        self.assertEqual(self.fs.read("projects/hello.txt", "/home/root"), "hello world")
        self.assertIs(node, self.fs.resolve("/home/root/projects/hello.txt"))

        parent = self.fs.resolve("..", "/home/root/projects")
        self.assertEqual(self.fs.abspath(".", "/home/root/projects"), "/home/root/projects")
        self.assertIs(parent, self.fs.resolve("/home/root"))
        self.assertIs(self.fs.resolve("..", "/"), self.fs.root)

    def test_mkdir_existing_and_rmdir(self) -> None:
        self.fs.mkdir("/tmp/work")
        with self.assertRaises(AlreadyExistsError):
            self.fs.mkdir("/tmp/work")
        with self.assertRaises(DirectoryNotEmptyError):
            self.fs.rmdir("/tmp")
        self.fs.rmdir("/tmp/work")
        with self.assertRaises(NotFoundError):
            self.fs.resolve("/tmp/work")

    def test_cannot_remove_directory_with_rm(self) -> None:
        with self.assertRaises(NotAFileError):
            self.fs.remove("/tmp")


class ShellFilesystemTest(unittest.TestCase):
    def setUp(self) -> None:
        self.kernel = Kernel()
        self.shell = Shell(self.kernel)

    def test_kernel_owns_the_filesystem(self) -> None:
        self.assertIs(self.shell._kernel.filesystem, self.kernel.components["filesystem"])
        self.assertEqual(self.shell.path, "/home/root")
        self.assertEqual(self.shell.cwd, "~")

    def test_shell_file_commands(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            self.shell.execute("mkdir projects")
            self.shell.execute("cd projects")
            self.shell.execute("touch hello.txt")
            self.shell.execute('write hello.txt "hello world"')
            self.shell.execute("cat hello.txt")
            self.shell.execute("cd missing")
            self.shell.execute("cat missing.txt")
            self.shell.execute("cd ..")
            self.shell.execute("mkdir projects")

        self.assertEqual(self.shell.path, "/home/root")
        self.assertEqual(
            self.kernel.filesystem.read("/home/root/projects/hello.txt"),
            "hello world\n",
        )
        text = output.getvalue()
        self.assertIn("hello world", text)
        self.assertIn("cd: missing: No such directory", text)
        self.assertIn("cat: missing.txt: No such file or directory", text)
        self.assertIn("mkdir: cannot create directory: File exists", text)

        self.shell.execute("rm projects/hello.txt")
        with self.assertRaises(NotFoundError):
            self.kernel.filesystem.resolve("/home/root/projects/hello.txt")


if __name__ == "__main__":
    unittest.main()
