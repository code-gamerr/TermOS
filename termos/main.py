"""TERMOS entry point."""

from __future__ import annotations

import sys
import time

from core.constants import BOOT_WIDTH, OS_NAME
from kernel.kernel import Kernel
from shell.shell import Shell


def display_boot(kernel: Kernel) -> None:
    """Print the boot banner and start the kernel."""
    title = f"{kernel.name} v{kernel.version}"
    print("=" * BOOT_WIDTH)
    print(title.center(BOOT_WIDTH))
    print("=" * BOOT_WIDTH)
    print()

    steps = (
        ("Loading kernel", kernel.boot),
        ("Initializing system", None),
        ("Starting shell", None),
    )
    for label, action in steps:
        if action is not None:
            action()
        print(f"[ OK ] {label}")
        time.sleep(0.08)

    print()
    print(f"Welcome to {kernel.name}.")
    print()


def main() -> None:
    """Boot TERMOS and run the interactive shell."""
    if sys.version_info < (3, 11):
        print(f"{OS_NAME} requires Python 3.11 or newer.", file=sys.stderr)
        raise SystemExit(1)

    kernel = Kernel()
    display_boot(kernel)
    try:
        Shell(kernel).run()
    finally:
        kernel.shutdown()
        print(f"{kernel.name} halted.")


if __name__ == "__main__":
    main()
