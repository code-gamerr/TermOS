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
            "├── home\n"
            "│   └── root\n"
            "├── etc\n"
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