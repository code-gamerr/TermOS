"""TAB completion against TERMOS commands and the virtual filesystem."""

from __future__ import annotations

from typing import TYPE_CHECKING

from filesystem.directory import Directory

if TYPE_CHECKING:
    from shell.shell import Shell


class Completer:
    """Readline completer backed by the TERMOS VFS and command table."""

    def __init__(self, shell: Shell) -> None:
        self.shell = shell
        self._matches: list[str] = []

    def __call__(self, text: str, state: int) -> str | None:
        if state == 0:
            self._matches = self._compute(text)
        if state < len(self._matches):
            return self._matches[state]
        return None

    def _compute(self, text: str) -> list[str]:
        line = ""
        try:
            import readline

            line = readline.get_line_buffer()
        except Exception:
            line = text

        stripped = line.lstrip()
        tokens = stripped.split()
        completing_command = not tokens or (len(tokens) == 1 and not stripped.endswith(" "))

        if completing_command:
            names = sorted(set(self.shell.commands) | set(self.shell._kernel.programs.names()))
            return [name for name in names if name.startswith(text)]

        return self._path_matches(text)

    def _path_matches(self, text: str) -> list[str]:
        fs = self.shell._kernel.filesystem
        cwd = self.shell.path
        if "/" in text:
            base, _, prefix = text.rpartition("/")
            search = fs.abspath(base or "/", cwd) if base != "" else (
                fs.abspath("/", cwd) if text.startswith("/") else cwd
            )
            if text.startswith("/") and base == "":
                search = "/"
                prefix = text.lstrip("/")
                # text like "/ho"
                if not text.endswith("/") and "/" not in text[1:]:
                    search = "/"
                    prefix = text[1:]
            try:
                node = fs.resolve(search if search else "/", cwd)
            except Exception:
                return []
            if not isinstance(node, Directory):
                return []
            matches = []
            for name in sorted(node.children):
                if not name.startswith(prefix):
                    continue
                child = node.children[name]
                suffix = "/" if isinstance(child, Directory) else ""
                if text.startswith("/"):
                    shown = f"{search.rstrip('/')}/{name}{suffix}" if search != "/" else f"/{name}{suffix}"
                elif base:
                    shown = f"{base}/{name}{suffix}"
                else:
                    shown = f"{name}{suffix}"
                matches.append(shown)
            return matches

        try:
            node = fs.resolve(cwd, "/")
        except Exception:
            return []
        if not isinstance(node, Directory):
            return []
        matches = []
        for name in sorted(node.children):
            if name.startswith(text):
                child = node.children[name]
                matches.append(name + ("/" if isinstance(child, Directory) else ""))
        return matches
