"""TERMOS shell scripting engine.

Supports a practical subset of sh:
- variables, export, $VAR / ${VAR} / $? / $# / $0 / $1 / $@
- comments (#)
- if / elif / else / fi  with  [ tests ]
- for ...; do ... done
- while ...; do ... done
- break / continue
- source / .
- exit status codes inside scripts
"""

from __future__ import annotations

import re
import shlex
from typing import TYPE_CHECKING

from core.errors import NotAFileError, NotFoundError, ShellError
from filesystem.directory import Directory
from filesystem.file import File
from permissions.permissions import Permissions

if TYPE_CHECKING:
    from shell.shell import Shell

_ASSIGN = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$")
_VAR = re.compile(
    r"\$(\{([A-Za-z0-9_@#\?\*]+)(:-([^}]*))?\}|([A-Za-z0-9_@#\?\*]+))"
)


class ScriptEngine:
    """Line-oriented shell script interpreter bound to a Shell instance."""

    def __init__(self, shell: Shell) -> None:
        self.shell = shell
        self._break = False
        self._continue = False
        self._return_code: int | None = None

    def run_text(self, text: str, argv: list[str] | None = None, name: str = "sh") -> int:
        """Execute a script body with positional parameters."""
        args = list(argv or [])
        previous = {
            "0": self.shell.env.get("0", "termos-sh"),
            "#": self.shell.env.get("#", "0"),
            "@": self.shell.env.get("@", ""),
            "*": self.shell.env.get("*", ""),
        }
        positional = {str(i): value for i, value in enumerate(args, start=1)}
        self.shell.env["0"] = name
        self.shell.env["#"] = str(len(args))
        self.shell.env["@"] = " ".join(args)
        self.shell.env["*"] = " ".join(args)
        for key in list(self.shell.env):
            if key.isdigit() and key != "0":
                del self.shell.env[key]
        self.shell.env.update(positional)

        self._break = False
        self._continue = False
        self._return_code = None
        try:
            lines = text.splitlines()
            status, _ = self._run_lines(lines, 0, len(lines))
            if self._return_code is not None:
                status = self._return_code
            self.shell.last_status = status
            return status
        finally:
            for key in list(self.shell.env):
                if key.isdigit() and key != "0":
                    del self.shell.env[key]
            self.shell.env["0"] = previous["0"]
            self.shell.env["#"] = previous["#"]
            self.shell.env["@"] = previous["@"]
            self.shell.env["*"] = previous["*"]

    def run_file(self, path: str, argv: list[str] | None = None) -> int:
        """Load a script from the virtual filesystem and run it."""
        try:
            text = self.shell._kernel.filesystem.read(
                path, self.shell.path, user=self.shell._current()
            )
        except NotFoundError as exc:
            raise ShellError(f"sh: {path}: No such file or directory") from exc
        except NotAFileError as exc:
            raise ShellError(f"sh: {path}: Is a directory") from exc
        return self.run_text(text, argv=argv, name=path)

    def expand(self, text: str) -> str:
        """Expand shell variables inside ``text`` (quote-aware)."""
        if not text:
            return text
        out: list[str] = []
        index = 0
        in_single = False
        in_double = False
        while index < len(text):
            ch = text[index]
            if ch == "'" and not in_double:
                in_single = not in_single
                out.append(ch)
                index += 1
                continue
            if ch == '"' and not in_single:
                in_double = not in_double
                out.append(ch)
                index += 1
                continue
            if in_single or ch != "$":
                out.append(ch)
                index += 1
                continue
            match = _VAR.match(text, index)
            if not match:
                out.append(ch)
                index += 1
                continue
            name = match.group(2) or match.group(5)
            default = match.group(4)
            value = self._lookup(name)
            if default is not None and value == "":
                value = default
            out.append(value)
            index = match.end()
        return "".join(out)

    def _lookup(self, name: str) -> str:
        if name == "?":
            return str(self.shell.last_status)
        if name == "#":
            return self.shell.env.get("#", "0")
        if name in {"@", "*"}:
            return self.shell.env.get(name, "")
        if name == "$":
            return "2"
        return self.shell.env.get(name, self.shell.aliases.get(name, ""))

    def _run_lines(self, lines: list[str], start: int, end: int) -> tuple[int, int]:
        status = 0
        index = start
        while index < end:
            if self._return_code is not None:
                return self._return_code, index
            if self._break or self._continue:
                return status, index

            raw = lines[index].rstrip()
            stripped = raw.strip()
            index += 1
            if not stripped or stripped.startswith("#"):
                continue

            # Strip trailing comments outside quotes.
            stripped = self._strip_comment(stripped)
            if not stripped:
                continue

            lowered = stripped.lower()
            if lowered.startswith("if "):
                status, index = self._run_if(lines, index - 1, end)
                continue
            if lowered.startswith("for "):
                status, index = self._run_for(lines, index - 1, end)
                continue
            if lowered.startswith("while "):
                status, index = self._run_while(lines, index - 1, end)
                continue
            if stripped in {"break", "break;"}:
                self._break = True
                return status, index
            if stripped in {"continue", "continue;"}:
                self._continue = True
                return status, index
            if stripped.startswith("exit"):
                status = self._handle_exit(stripped)
                self._return_code = status
                return status, index

            assign = _ASSIGN.match(stripped)
            if assign and not self._looks_like_command(stripped):
                name, value = assign.group(1), assign.group(2)
                self.shell.env[name] = self._unquote(self.expand(value))
                status = 0
                self.shell.last_status = 0
                continue

            status = self.shell.execute_line(self.expand(stripped), from_script=True)
        return status, index

    def _looks_like_command(self, stripped: str) -> bool:
        # export FOO=bar is a command; FOO=bar is an assignment.
        return stripped.split(None, 1)[0] in {
            "export",
            "alias",
            "env",
            "set",
            "unset",
            "echo",
        }

    def _handle_exit(self, stripped: str) -> int:
        parts = stripped.split()
        if len(parts) == 1:
            return self.shell.last_status
        try:
            return int(parts[1])
        except ValueError:
            return 1

    def _run_if(self, lines: list[str], start: int, end: int) -> tuple[int, int]:
        header = lines[start].strip()
        if not header.lower().startswith("if "):
            raise ShellError("sh: syntax error near `if'")
        condition = header[3:].strip()
        if condition.endswith(";"):
            condition = condition[:-1].strip()
        if condition.lower().endswith("then"):
            condition = condition[: -len("then")].strip()
            if condition.endswith(";"):
                condition = condition[:-1].strip()

        body_start = start + 1
        if body_start < end and lines[body_start].strip().lower() == "then":
            body_start += 1

        # Split into branches: list of (condition|None for else, start, end)
        branches: list[tuple[str | None, int, int]] = []
        cursor = body_start
        branch_cond: str | None = condition
        branch_start = body_start
        depth = 0
        index = body_start
        while index < end:
            word = lines[index].strip().lower()
            if word.startswith("if "):
                depth += 1
            elif word == "fi" or word.startswith("fi;"):
                if depth == 0:
                    branches.append((branch_cond, branch_start, index))
                    return self._exec_if_branches(lines, branches), index + 1
                depth -= 1
            elif depth == 0 and (word.startswith("elif ") or word == "else" or word.startswith("else;")):
                branches.append((branch_cond, branch_start, index))
                if word.startswith("elif "):
                    branch_cond = lines[index].strip()[5:].strip()
                    if branch_cond.endswith(";"):
                        branch_cond = branch_cond[:-1].strip()
                    if branch_cond.lower().endswith("then"):
                        branch_cond = branch_cond[: -len("then")].strip()
                    branch_start = index + 1
                    if branch_start < end and lines[branch_start].strip().lower() == "then":
                        branch_start += 1
                        index = branch_start - 1
                else:
                    branch_cond = None
                    branch_start = index + 1
            index += 1
        raise ShellError("sh: syntax error: missing `fi'")

    def _exec_if_branches(
        self, lines: list[str], branches: list[tuple[str | None, int, int]]
    ) -> int:
        for cond, start, end in branches:
            if cond is None or self._truthy(cond):
                status, _ = self._run_lines(lines, start, end)
                return status
        return 0

    def _run_for(self, lines: list[str], start: int, end: int) -> tuple[int, int]:
        header = lines[start].strip()
        # for name in a b c; do
        match = re.match(
            r"^for\s+([A-Za-z_][A-Za-z0-9_]*)\s+in\s+(.*)$",
            header,
            flags=re.IGNORECASE,
        )
        if not match:
            raise ShellError("sh: syntax error near `for'")
        var = match.group(1)
        rest = match.group(2).strip()
        if rest.lower().endswith("; do"):
            rest = rest[: -len("; do")].strip()
        elif rest.lower().endswith("do"):
            rest = rest[: -len("do")].strip()
            if rest.endswith(";"):
                rest = rest[:-1].strip()
        words = self._split_words(self.expand(rest))
        if rest.strip() in {'"$@"', "$@", '"$*"', "$*"}:
            words = self.shell.env.get("@", "").split() if self.shell.env.get("@") else []
        body_start = start + 1
        if body_start < end and lines[body_start].strip().lower() in {"do", "do;"}:
            body_start += 1
        body_end = self._find_done(lines, body_start, end)
        status = 0
        for word in words:
            if self._return_code is not None:
                return self._return_code, body_end + 1
            self.shell.env[var] = word
            self._break = False
            self._continue = False
            status, _ = self._run_lines(lines, body_start, body_end)
            if self._break:
                self._break = False
                break
            if self._continue:
                self._continue = False
                continue
        return status, body_end + 1

    def _run_while(self, lines: list[str], start: int, end: int) -> tuple[int, int]:
        header = lines[start].strip()
        if not header.lower().startswith("while "):
            raise ShellError("sh: syntax error near `while'")
        condition = header[6:].strip()
        if condition.lower().endswith("; do"):
            condition = condition[: -len("; do")].strip()
        elif condition.lower().endswith("do"):
            condition = condition[: -len("do")].strip()
            if condition.endswith(";"):
                condition = condition[:-1].strip()
        body_start = start + 1
        if body_start < end and lines[body_start].strip().lower() in {"do", "do;"}:
            body_start += 1
        body_end = self._find_done(lines, body_start, end)
        status = 0
        guard = 0
        while self._truthy(condition):
            guard += 1
            if guard > 10000:
                raise ShellError("sh: while loop exceeded iteration limit")
            self._break = False
            self._continue = False
            status, _ = self._run_lines(lines, body_start, body_end)
            if self._return_code is not None:
                return self._return_code, body_end + 1
            if self._break:
                self._break = False
                break
            if self._continue:
                self._continue = False
                continue
        return status, body_end + 1

    def _find_done(self, lines: list[str], start: int, end: int) -> int:
        depth = 0
        for index in range(start, end):
            word = lines[index].strip().lower()
            if word.startswith("for ") or word.startswith("while "):
                depth += 1
            elif word in {"done", "done;"}:
                if depth == 0:
                    return index
                depth -= 1
        raise ShellError("sh: syntax error: missing `done'")

    def _truthy(self, condition: str) -> bool:
        condition = condition.strip()
        if condition.startswith("[") and condition.endswith("]"):
            return self._test(condition[1:-1].strip())
        if condition.startswith("test "):
            return self._test(condition[5:].strip())
        # Fallback: run as command, success if exit 0.
        status = self.shell.execute_line(self.expand(condition), from_script=True)
        return status == 0

    def _test(self, expr: str) -> bool:
        tokens = self._split_words(self.expand(expr))
        if not tokens:
            return False
        if tokens[0] == "!" and len(tokens) > 1:
            return not self._test(" ".join(tokens[1:]))
        if len(tokens) == 1:
            return bool(tokens[0])
        if len(tokens) == 2:
            op, arg = tokens
            if op == "-z":
                return arg == ""
            if op == "-n":
                return arg != ""
            if op == "-e":
                return self._path_exists(arg)
            if op == "-f":
                return self._path_is_file(arg)
            if op == "-d":
                return self._path_is_dir(arg)
            return bool(arg)
        if len(tokens) == 3:
            left, op, right = tokens
            if op in {"=", "=="}:
                return left == right
            if op == "!=":
                return left != right
            try:
                a, b = int(left), int(right)
            except ValueError:
                return False
            if op == "-eq":
                return a == b
            if op == "-ne":
                return a != b
            if op == "-lt":
                return a < b
            if op == "-le":
                return a <= b
            if op == "-gt":
                return a > b
            if op == "-ge":
                return a >= b
        return False

    def _path_exists(self, path: str) -> bool:
        try:
            self.shell._kernel.filesystem.resolve(path, self.shell.path)
            return True
        except (NotFoundError, NotAFileError):
            return False

    def _path_is_file(self, path: str) -> bool:
        try:
            node = self.shell._kernel.filesystem.resolve(path, self.shell.path)
        except (NotFoundError, NotAFileError):
            return False
        return isinstance(node, File)

    def _path_is_dir(self, path: str) -> bool:
        try:
            node = self.shell._kernel.filesystem.resolve(path, self.shell.path)
        except (NotFoundError, NotAFileError):
            return False
        return isinstance(node, Directory)

    @staticmethod
    def _split_words(text: str) -> list[str]:
        try:
            return shlex.split(text, posix=True)
        except ValueError:
            return text.split()

    @staticmethod
    def _unquote(value: str) -> str:
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            return value[1:-1]
        return value

    @staticmethod
    def _strip_comment(line: str) -> str:
        in_single = False
        in_double = False
        for index, ch in enumerate(line):
            if ch == "'" and not in_double:
                in_single = not in_single
            elif ch == '"' and not in_single:
                in_double = not in_double
            elif ch == "#" and not in_single and not in_double:
                return line[:index].rstrip()
        return line


def is_script_path(name: str) -> bool:
    """Return whether ``name`` looks like a filesystem script path."""
    return name.startswith(("./", "/", "../")) or ("/" in name and not name.startswith("-"))


def can_execute_script(shell: Shell, path: str) -> bool:
    """Return whether the current user may execute ``path`` as a script."""
    try:
        node = shell._kernel.filesystem.resolve(path, shell.path)
    except (NotFoundError, NotAFileError):
        return False
    if not isinstance(node, File):
        return False
    return Permissions.can_execute(shell._current(), node)
