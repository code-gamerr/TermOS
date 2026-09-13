"""Shell line parsing for pipes and redirections."""

from __future__ import annotations

from dataclasses import dataclass

from core.errors import ShellError


@dataclass
class Redirect:
    """Output or input redirection for one command stage."""

    mode: str  # '>', '>>', or '<'
    path: str


@dataclass
class Stage:
    """One pipeline stage."""

    argv: list[str]
    redirects: list[Redirect]


def split_pipeline(line: str) -> list[str]:
    """Split a command line on ``|`` while respecting quotes."""
    parts: list[str] = []
    buf: list[str] = []
    quote = ""
    for ch in line:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = ""
            continue
        if ch in {'"', "'"}:
            quote = ch
            buf.append(ch)
            continue
        if ch == "|":
            parts.append("".join(buf).strip())
            buf = []
            continue
        buf.append(ch)
    parts.append("".join(buf).strip())
    if any(not part for part in parts):
        raise ShellError("termos: invalid pipe")
    return parts


def parse_stage(segment: str) -> Stage:
    """Parse argv plus ``>``, ``>>``, and ``<`` redirects from one stage."""
    import shlex

    try:
        tokens = shlex.split(segment, posix=True)
    except ValueError as exc:
        raise ShellError(f"termos: syntax error: {exc}") from exc

    argv: list[str] = []
    redirects: list[Redirect] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token in {">", ">>", "<"}:
            if index + 1 >= len(tokens):
                raise ShellError("termos: syntax error near unexpected token `newline'")
            redirects.append(Redirect(token, tokens[index + 1]))
            index += 2
            continue
        if token.startswith(">>") and len(token) > 2:
            redirects.append(Redirect(">>", token[2:]))
            index += 1
            continue
        if token.startswith(">") and len(token) > 1 and not token.startswith(">>"):
            redirects.append(Redirect(">", token[1:]))
            index += 1
            continue
        if token.startswith("<") and len(token) > 1:
            redirects.append(Redirect("<", token[1:]))
            index += 1
            continue
        argv.append(token)
        index += 1

    if not argv:
        raise ShellError("termos: invalid command")
    return Stage(argv, redirects)
