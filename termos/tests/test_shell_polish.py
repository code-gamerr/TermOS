"""Phase 8 shell polish tests: pipes, redirection, history, man, demo."""

from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout

from kernel.kernel import Kernel
from shell.completion import Completer
from shell.parser import parse_stage, split_pipeline
from shell.shell import Shell


class ParserTest(unittest.TestCase):
    def test_pipes_and_redirects(self) -> None:
        self.assertEqual(split_pipeline('echo a | grep a'), ["echo a", "grep a"])
        stage = parse_stage('echo hello > out.txt')
        self.assertEqual(stage.argv, ["echo", "hello"])
        self.assertEqual(stage.redirects[0].mode, ">")
        self.assertEqual(stage.redirects[0].path, "out.txt")


class ShellPolishTest(unittest.TestCase):
    def setUp(self) -> None:
        self.kernel = Kernel()
        self.kernel.boot()
        self.shell = Shell(self.kernel)

    def test_history_and_man(self) -> None:
        self.shell.execute("pwd")
        self.shell.history.append("pwd")
        output = io.StringIO()
        with redirect_stdout(output):
            self.shell.execute("history")
            self.shell.execute("man mkdir")
            self.shell.execute("dmesg")
        text = output.getvalue()
        self.assertIn("pwd", text)
        self.assertIn("MKDIR(1)", text)
        self.assertIn("TERMOS kernel starting", text)

    def test_redirect_and_pipe(self) -> None:
        self.shell.execute('echo hello > note.txt')
        self.shell.execute('echo world >> note.txt')
        output = io.StringIO()
        with redirect_stdout(output):
            self.shell.execute("cat note.txt")
            self.shell.execute("cat note.txt | grep hello")
            self.shell.execute("cat note.txt | wc")
        text = output.getvalue()
        self.assertIn("hello", text)
        self.assertIn("world", text)
        self.assertIn("2 ", text)

    def test_input_redirect(self) -> None:
        self.shell.execute('write data.txt "alpha\\nbeta"')
        # write puts literal text; use two writes via redirect instead
        self.shell.execute('echo alpha > data.txt')
        self.shell.execute('echo beta >> data.txt')
        output = io.StringIO()
        with redirect_stdout(output):
            self.shell.execute("cat < data.txt")
        self.assertIn("alpha", output.getvalue())

    def test_completion_commands(self) -> None:
        completer = Completer(self.shell)
        matches = completer._compute("me")
        self.assertTrue(any(item.startswith("mem") for item in matches))

    def test_demo(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            self.shell.execute("demo")
        text = output.getvalue()
        self.assertIn("TERMOS SYSTEM DEMONSTRATION", text)
        self.assertIn("DEMO COMPLETE", text)
        self.assertTrue(self.kernel.filesystem.resolve("/home/root/demo.txt"))


if __name__ == "__main__":
    unittest.main()
