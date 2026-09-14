"""Tests for the TERMOS shell scripting engine."""

from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout

from kernel.kernel import Kernel
from shell.shell import Shell


class ScriptingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.kernel = Kernel()
        self.kernel.boot()
        self.shell = Shell(self.kernel)

    def test_variables_and_export(self) -> None:
        self.shell.execute("NAME=TERMOS")
        self.assertEqual(self.shell.env["NAME"], "TERMOS")
        output = io.StringIO()
        with redirect_stdout(output):
            self.shell.execute("echo Hello $NAME")
            self.shell.execute("export CITY=Delhi")
            self.shell.execute("echo $CITY")
        text = output.getvalue()
        self.assertIn("Hello TERMOS", text)
        self.assertIn("Delhi", text)

    def test_if_for_and_status(self) -> None:
        script = "\n".join(
            [
                'MSG="ok"',
                "if [ -d /home ]",
                "then",
                '  echo "home-yes"',
                "else",
                '  echo "home-no"',
                "fi",
                "for x in a b c",
                "do",
                '  echo "item:$x"',
                "done",
                "false_cmd_should_fail",
            ]
        )
        # Write and run with sh (false command will 127)
        self.kernel.filesystem.write("/tmp/demo.sh", script + "\n", "/")
        self.kernel.filesystem.chmod("/tmp/demo.sh", 0o755, "/")
        output = io.StringIO()
        with redirect_stdout(output):
            status = self.shell.execute("sh /tmp/demo.sh")
        text = output.getvalue()
        self.assertIn("home-yes", text)
        self.assertIn("item:a", text)
        self.assertIn("item:c", text)
        self.assertEqual(status, 127)

    def test_builtin_scripts_and_args(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            self.shell.execute("sh /bin/hello.sh Friend")
            self.shell.execute("sh /bin/countdown.sh")
            self.shell.execute("sh /bin/args.sh one two")
            self.shell.execute("/bin/hello.sh Neo")
        text = output.getvalue()
        self.assertIn("Hello, Friend from TERMOS scripting!", text)
        self.assertIn("liftoff", text)
        self.assertIn("argc=2", text)
        self.assertIn("Hello, Neo from TERMOS scripting!", text)

    def test_alias_and_source(self) -> None:
        self.shell.execute("alias greet='echo hi'")
        output = io.StringIO()
        with redirect_stdout(output):
            self.shell.execute("greet")
        self.assertIn("hi", output.getvalue())

        self.kernel.filesystem.write("/tmp/rc.sh", "export FROM_RC=1\n", "/")
        self.shell.execute("source /tmp/rc.sh")
        self.assertEqual(self.shell.env.get("FROM_RC"), "1")

    def test_test_builtin(self) -> None:
        self.assertEqual(self.shell.execute("test -d /home"), 0)
        self.assertEqual(self.shell.execute("test -f /home"), 1)
        self.assertEqual(self.shell.execute("[ -n hello ]"), 0)


if __name__ == "__main__":
    unittest.main()
