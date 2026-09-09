# TERMOS

TERMOS is a simulated mini operating system that runs entirely inside a terminal. It is not a real kernel. It is a Python program that mimics boot, a shell, and (in later parts) a virtual machine: filesystem, users, processes, memory, and networking.

## How to run

Requires Python 3.11+.

From the project root:

```bash
python termos/main.py
```

Or from the `termos` directory:

```bash
python main.py
```

Leave the shell with `exit` or Ctrl+D.

## Current features

Part 1 — foundation and shell:

- Boot sequence
- Kernel with name, version, uptime, boot, shutdown, and system info
- Interactive shell prompt: `root@termos:~$`
- Commands: `help`, `version`, `clear`, `echo`, `exit`
- Quoted arguments and extra-space handling (`echo "hello world"`)
- In-memory command history (arrow-key recall when `readline` is available)
- Unknown-command errors

Not implemented yet: filesystem, processes, users, permissions, scheduler, memory manager, networking, built-in programs, and system monitoring.

## Architecture

```
termos/
├── main.py              Boot display and process entry
├── kernel/kernel.py     OS lifecycle and component slots
├── shell/shell.py       Prompt, parsing, history, built-ins
└── core/
    ├── constants.py     Shared names and reserved component slots
    └── errors.py        Shell and kernel errors
```

`main.py` starts the kernel, prints the boot sequence, and runs the shell. The kernel does not own I/O. The shell parses lines with the standard-library `shlex` module and dispatches to a command table, so later parts can register commands without rewriting the loop.

Future subsystems (filesystem, process manager, memory manager, user manager, network manager) attach to `Kernel.components`. Those slots are empty in this part.
