"""TERMOS entry point."""

from __future__ import annotations

import argparse
import sys
import time

from core import colors
from core.constants import OS_NAME
from kernel.kernel import Kernel
from shell.shell import Shell


def display_boot(kernel: Kernel) -> None:
    """Print the polished boot banner using real kernel init results."""
    width = 47
    print("=" * width)
    print(colors.bold(f"{kernel.name} v{kernel.version}".center(width)))
    print("Terminal Operating System".center(width))
    print("=" * width)
    print()

    steps = kernel.boot()
    for label, ok, detail in steps:
        if ok:
            print(f"{colors.ok('[ OK ]')} {label}")
        else:
            print(f"{colors.err('[FAIL]')} {label}: {detail}")
        time.sleep(0.05)

    print()
    print("-" * width)
    if kernel.is_running:
        print("System initialization complete.")
        print(f"Welcome to {kernel.name}.")
    else:
        print(colors.err("System initialization failed."))
    print("-" * width)
    print()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="TERMOS — Terminal Operating System Simulator")
    parser.add_argument("--no-boot", action="store_true", help="skip the animated boot sequence")
    parser.add_argument("--debug", action="store_true", help="show Python tracebacks on errors")
    parser.add_argument("--verbose", action="store_true", help="enable kernel event output")
    return parser


def main(argv: list[str] | None = None) -> None:
    """Boot TERMOS and run the interactive shell."""
    if sys.version_info < (3, 11):
        print(f"{OS_NAME} requires Python 3.11 or newer.", file=sys.stderr)
        raise SystemExit(1)

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")

    args = build_parser().parse_args(argv)
    kernel = Kernel()
    kernel.debug = args.debug
    kernel.verbose = args.verbose

    if args.no_boot:
        kernel.boot()
        print(f"Welcome to {kernel.name}.")
        print()
    else:
        display_boot(kernel)

    if not kernel.is_running:
        raise SystemExit(1)

    try:
        Shell(kernel).run()
    finally:
        kernel.shutdown()
        print(f"{kernel.name} halted.")


if __name__ == "__main__":
    main()
