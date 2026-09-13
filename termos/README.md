# TERMOS

**Terminal Operating System Simulator**

TERMOS is a simulated mini operating system that runs entirely inside a terminal. It is a Python project for learning and demonstration — **not** a real kernel, and it does **not** replace or modify the host operating system.

All filesystem, processes, memory, users, permissions, and networking are simulated in memory.

## Why it exists

TERMOS was built as a TerminalCraft-style project to show how OS concepts connect: a shell, VFS, users, a scheduler, memory allocation, programs, and a fake network, all talking to each other.

## Quick start

Requires **Python 3.11+**.

```bash
cd termos
python main.py
```

Useful flags:

```bash
python main.py --no-boot
python main.py --verbose
python main.py --debug
python main.py --help
```

Default passwords: `root` / `root`, `guest` / `guest`.

## Features

- Boot sequence driven by real Kernel initialization
- Interactive shell with history, TAB completion, pipes, and redirection
- In-memory virtual filesystem (`/bin`, `/home`, `/etc`, `/tmp`, `/var`)
- Users, groups, and Unix-like permissions
- Process table + Round Robin scheduler
- Simulated 128 MB RAM (First Fit / Best Fit)
- Built-in programs: `hello`, `calc`, `sysinfo`, `uptime`, `neofetch`, `editor`
- Simulated network (`eth0`, `ping`, `netstat`, `route`)
- System monitor (`monitor`, `monitor --live`)
- Kernel log (`dmesg`), manuals (`man`), and `demo`

## Example session

```text
root@termos:~$ neofetch
root@termos:~$ mkdir projects
root@termos:~$ cd projects
root@termos:~/projects$ write hello.txt "Hello from TERMOS"
root@termos:~/projects$ echo "Second line" >> hello.txt
root@termos:~/projects$ cat hello.txt | grep TERMOS
root@termos:~/projects$ calc 25 + 17
root@termos:~/projects$ free
root@termos:~/projects$ ping 10.0.0.1
root@termos:~/projects$ demo
```

## Architecture

```text
termos/
├── main.py              Entry point + boot UX
├── kernel/              Lifecycle, logger, subsystem ownership
├── shell/               Prompt, parser, completion, man, demo
├── filesystem/          In-memory VFS
├── users/               Accounts and groups
├── permissions/         Central access checks
├── processes/           PIDs + Round Robin scheduler
├── memory/              Simulated RAM allocator
├── programs/            Controlled built-in programs
├── network/             Fake eth0 / packets / connections
├── monitor/             Live metrics dashboard
├── core/                Constants, errors, colors, config
└── tests/
```

The Kernel owns the managers. The Shell never creates its own filesystem, memory manager, or network stack.

## Commands

| Area | Commands |
|------|----------|
| Filesystem | `ls`, `cd`, `pwd`, `mkdir`, `touch`, `cat`, `write`, `rm`, `rmdir`, `tree` |
| Users | `whoami`, `id`, `su`, `passwd`, `chmod`, `chown`, `users`, `groups` |
| Processes | `ps`, `top`, `kill`, `jobs`, `scheduler`, `sleep` |
| Memory | `free`, `memory`, `memmap` |
| Network | `ifconfig`, `ping`, `netstat`, `route` |
| Programs | `hello`, `calc`, `sysinfo`, `uptime`, `neofetch`, `editor` |
| Shell polish | `help`, `man`, `history`, `grep`, `head`, `tail`, `wc`, `dmesg`, `verbose`, `demo`, `monitor` |

## Testing

```bash
cd termos
python -m unittest discover -s tests -v
```

## Design decisions

- Simulation only: no host disk writes, no real sockets, no OS process scheduling
- Permission checks stay centralized in `permissions.py`
- Program execution goes through `Kernel.run_program` (process + memory + scheduler)
- Config lives in the VFS at `/etc/termos.conf`

## Limitations

- No persistence across restarts
- No virtual memory / paging
- TAB completion needs `readline` (limited on some Windows setups)
- Networking replies are deterministic fakes
- The text editor is intentionally minimal

## License

Built for TerminalCraft / educational use.
