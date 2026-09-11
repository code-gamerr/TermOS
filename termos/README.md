# TERMOS

TERMOS is a simulated mini operating system that runs entirely inside a terminal. It is not a real kernel. It is a Python program that mimics boot, a shell, a virtual filesystem, users, permissions, processes, and a CPU scheduler.

## How to run

Requires Python 3.11+.

```bash
python termos/main.py
```

Or from the `termos` directory:

```bash
python main.py
```

Leave the shell with `exit` or Ctrl+D.

Default passwords: `root` / `root`, `guest` / `guest`.

## Current features

Part 1 — foundation and shell: boot sequence, kernel, interactive prompt, `help`, `version`, `clear`, `echo`, `exit`.

Part 2 — in-memory filesystem: `/bin`, `/home/root`, `/home/guest`, `/etc`, `/tmp`, `/var`, plus `mkdir`, `cd`, `pwd`, `ls`, `touch`, `cat`, `write`, `rm`, `rmdir`, `tree`.

Part 3 — users and permissions:

- Users `root` (UID 0) and `guest`
- Groups `root`, `users`, `admin`
- Unix-style modes (`rwxr-xr--`) with centralized checks in `permissions.py`
- `whoami`, `id`, `su`, `passwd`, `users`, `groups`, `chmod`, `chown`
- Access checks on `cat`, `write`, `cd`, and related file commands
- Root bypasses normal permission restrictions

Part 4 — processes and scheduler:

- Simulated process table (not real OS processes)
- PID 1 = `init`, PID 2 = `shell`
- Round Robin scheduler with ready queue and time slice
- `ps`, `top`, `kill`, `sleep`, `jobs`, `scheduler`

Not implemented yet: memory manager, programs/executables, networking, system monitor, persistence.

## Architecture

```
termos/
├── main.py
├── kernel/          Owns filesystem, users, processes
├── shell/           Prompt and commands
├── filesystem/      In-memory VFS
├── users/           Users and groups
├── permissions/     Central permission checks
├── processes/       Process table + Round Robin scheduler
└── core/            Constants and errors
```

## Tests

From the `termos` directory:

```bash
python -m unittest discover -s tests -v
```
