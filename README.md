# TERMOS

TERMOS is a simulated mini operating system that runs entirely inside a terminal. It is not a real kernel. It is a Python program that simulates a boot sequence, shell, virtual filesystem, users, permissions, processes, a CPU scheduler, memory, built-in programs, networking, and system monitoring.

## How to run

Requires Python 3.11+.

```bash
python termos/main.py
```

Or from the `termos` directory:

```bash
python main.py
```

Default passwords: `root` / `root`, `guest` / `guest`.

## Current features

- Boot + interactive shell
- In-memory VFS (`mkdir`, `cd`, `ls`, `cat`, `write`, `tree`, …)
- Users/groups + Unix-like permissions (`su`, `chmod`, `chown`, …)
- Process table + Round Robin scheduler (`ps`, `kill`, `scheduler`, …)
- Simulated 128 MB RAM with First Fit / Best Fit (`free`, `memory`, `memmap`)
- Built-in programs: `hello`, `calc`, `sysinfo`, `uptime`, `neofetch`, `editor`
- Simulated network: `ifconfig`, `ping`, `netstat`, `route`
- System monitor: `monitor`, `monitor --live`

Not implemented yet: persistence, virtual memory/paging, pipes/redirection polish extras from Part 8.

## Architecture

```
termos/
├── main.py
├── kernel/          Owns all subsystems
├── shell/
├── filesystem/
├── users/
├── permissions/
├── processes/
├── memory/
├── programs/
├── network/
├── monitor/
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
