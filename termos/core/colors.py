"""ANSI color helpers for TERMOS. Disabled when stdout is not a TTY."""

from __future__ import annotations

import os
import sys


def _enabled() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def color(text: str, code: str) -> str:
    """Wrap ``text`` in an ANSI color when colors are enabled."""
    if not _enabled() or not text:
        return text
    return f"\033[{code}m{text}\033[0m"


def green(text: str) -> str:
    return color(text, "32")


def red(text: str) -> str:
    return color(text, "31")


def yellow(text: str) -> str:
    return color(text, "33")


def cyan(text: str) -> str:
    return color(text, "36")


def blue(text: str) -> str:
    return color(text, "34")


def bold(text: str) -> str:
    return color(text, "1")


def ok(text: str) -> str:
    return green(text)


def err(text: str) -> str:
    return red(text)


def warn(text: str) -> str:
    return yellow(text)


def sysmsg(text: str) -> str:
    return cyan(text)


def directory(text: str) -> str:
    return blue(bold(text)) if _enabled() else text
