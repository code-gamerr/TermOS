"""Simple line editor backed by the virtual filesystem."""

from __future__ import annotations

from typing import TYPE_CHECKING

from core.errors import NotAFileError, NotFoundError, ProgramError
from programs.program import Program

if TYPE_CHECKING:
    from kernel.kernel import Kernel
    from shell.shell import Shell


class EditorProgram(Program):
    name = "editor"
    description = "Edit a file in the virtual filesystem"
    memory_mb = 6.0

    def run(self, kernel: Kernel, shell: Shell, args: list[str]) -> int:
        if not args:
            raise ProgramError("editor: missing filename")
        path = args[0]
        user = kernel.users.require_current()
        try:
            existing = kernel.filesystem.read(path, shell.path, user=user)
            lines = existing.splitlines()
        except NotFoundError:
            lines = []
        except NotAFileError as exc:
            raise ProgramError(f"editor: {path}: Is a directory") from exc

        print(f"Editing {path} (type text, single '.' to save, '.q' to quit)")
        if lines:
            for line in lines:
                print(line)
        buffer: list[str] = list(lines)
        while True:
            try:
                line = input()
            except EOFError:
                line = "."
            if line == ".q":
                print("editor: discarded changes")
                return 1
            if line == ".":
                break
            buffer.append(line)

        text = "\n".join(buffer)
        if text:
            text += "\n"
        kernel.filesystem.write(path, text, shell.path, user=user)
        print(f"editor: wrote {path}")
        return 0
