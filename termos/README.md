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

Part 2 — in-memory filesystem:

- Hierarchical filesystem that never touches the host disk
- Initial tree: `/bin`, `/home/root`, `/etc`, `/tmp`, `/var`
- Path resolution for absolute paths, relative paths, `.`, `..`, and `~`
- Commands: `mkdir`, `cd`, `pwd`, `ls`, `ls -l`, `ls -a`, `touch`, `cat`, `write`, `rm`, `rmdir`, `tree`
- Owner and permission fields are stored only; they are not enforced

Not implemented yet: persistence, users, permissions enforcement, processes, scheduler, memory manager, networking, and system monitoring.

## Architecture

```
termos/
├── main.py              Boot display and process entry
├── kernel/kernel.py     OS lifecycle; owns the filesystem
├── shell/shell.py       Prompt, parsing, history, built-ins
├── filesystem/          In-memory files, directories, path resolution
└── core/
    ├── constants.py     Shared names and reserved component slots
    └── errors.py        Shell, kernel, and filesystem errors
```

`main.py` starts the kernel, prints the boot sequence, and runs the shell. The kernel owns the `FileSystem` instance. The shell uses that filesystem for the working directory and file commands. Nothing is written to the host disk, and nothing is saved after shutdown.

## Tests

From the `termos` directory:

```bash
python -m unittest tests.test_filesystem
```
