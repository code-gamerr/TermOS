"""Built-in manual pages for TERMOS commands."""

from __future__ import annotations

from core.errors import NotFoundError

_MAN: dict[str, str] = {
    "ls": """LS(1)

NAME
    ls - list directory contents

SYNOPSIS
    ls [-l] [-a] [path]

DESCRIPTION
    Lists entries in the TERMOS virtual filesystem.

EXAMPLES
    ls
    ls -l
    ls -a /home""",
    "cd": """CD(1)

NAME
    cd - change the working directory

SYNOPSIS
    cd [directory]

DESCRIPTION
    Changes the current directory inside the virtual filesystem.
    Without arguments, returns to the user's home directory.""",
    "pwd": """PWD(1)

NAME
    pwd - print working directory

SYNOPSIS
    pwd

DESCRIPTION
    Prints the absolute path of the current directory.""",
    "mkdir": """MKDIR(1)

NAME
    mkdir - create a directory

SYNOPSIS
    mkdir <directory>

DESCRIPTION
    Creates a directory inside the TERMOS virtual filesystem.

EXAMPLES
    mkdir projects""",
    "touch": """TOUCH(1)

NAME
    touch - create an empty file

SYNOPSIS
    touch <file>

DESCRIPTION
    Creates a file or updates its modification time.""",
    "cat": """CAT(1)

NAME
    cat - concatenate and print files

SYNOPSIS
    cat <file...>
    cat < file

DESCRIPTION
    Prints file contents from the virtual filesystem.""",
    "write": """WRITE(1)

NAME
    write - write text to a file

SYNOPSIS
    write <file> <text...>

DESCRIPTION
    Creates or overwrites a file with the given text.""",
    "rm": """RM(1)

NAME
    rm - remove a file

SYNOPSIS
    rm <file>

DESCRIPTION
    Deletes a file from the virtual filesystem.""",
    "rmdir": """RMDIR(1)

NAME
    rmdir - remove an empty directory

SYNOPSIS
    rmdir <directory>

DESCRIPTION
    Removes an empty directory.""",
    "tree": """TREE(1)

NAME
    tree - display a directory tree

SYNOPSIS
    tree [path]

DESCRIPTION
    Prints a hierarchical view of the virtual filesystem.""",
    "ps": """PS(1)

NAME
    ps - report process status

SYNOPSIS
    ps

DESCRIPTION
    Lists simulated TERMOS processes.""",
    "kill": """KILL(1)

NAME
    kill - terminate a process

SYNOPSIS
    kill <pid>

DESCRIPTION
    Terminates a simulated process and releases its memory.""",
    "jobs": """JOBS(1)

NAME
    jobs - list active jobs

SYNOPSIS
    jobs

DESCRIPTION
    Shows sleeping or waiting shell jobs.""",
    "scheduler": """SCHEDULER(1)

NAME
    scheduler - show CPU scheduler state

SYNOPSIS
    scheduler

DESCRIPTION
    Displays the Round Robin ready queue and running process.""",
    "free": """FREE(1)

NAME
    free - display memory usage

SYNOPSIS
    free

DESCRIPTION
    Shows total, used, and free simulated RAM.""",
    "memory": """MEMORY(1)

NAME
    memory - memory manager summary

SYNOPSIS
    memory

DESCRIPTION
    Shows allocator strategy, usage, and fragmentation.""",
    "memmap": """MEMMAP(1)

NAME
    memmap - show the memory map

SYNOPSIS
    memmap

DESCRIPTION
    Lists simulated address blocks and owners.""",
    "whoami": """WHOAMI(1)

NAME
    whoami - print effective username

SYNOPSIS
    whoami""",
    "id": """ID(1)

NAME
    id - print user identity

SYNOPSIS
    id

DESCRIPTION
    Displays UID, GID, and group memberships.""",
    "su": """SU(1)

NAME
    su - switch user

SYNOPSIS
    su <username> [password]

DESCRIPTION
    Authenticates and switches the current TERMOS session user.""",
    "chmod": """CHMOD(1)

NAME
    chmod - change file mode bits

SYNOPSIS
    chmod <mode> <path>

DESCRIPTION
    Sets Unix-like permissions, e.g. 755 or 644.""",
    "chown": """CHOWN(1)

NAME
    chown - change file owner

SYNOPSIS
    chown <user[:group]> <path>

DESCRIPTION
    Changes ownership of a virtual filesystem node.""",
    "ping": """PING(1)

NAME
    ping - send simulated ICMP echo requests

SYNOPSIS
    ping <host>

DESCRIPTION
    Generates deterministic fake network replies.""",
    "ifconfig": """IFCONFIG(1)

NAME
    ifconfig - configure network interface

SYNOPSIS
    ifconfig

DESCRIPTION
    Displays the simulated eth0 interface.""",
    "netstat": """NETSTAT(1)

NAME
    netstat - network connection table

SYNOPSIS
    netstat""",
    "route": """ROUTE(1)

NAME
    route - show routing table

SYNOPSIS
    route""",
    "monitor": """MONITOR(1)

NAME
    monitor - system monitor dashboard

SYNOPSIS
    monitor [--live]

DESCRIPTION
    Shows CPU, memory, process, network, and filesystem metrics.""",
    "sysinfo": """SYSINFO(1)

NAME
    sysinfo - system information

SYNOPSIS
    sysinfo""",
    "uptime": """UPTIME(1)

NAME
    uptime - show how long TERMOS has been running

SYNOPSIS
    uptime""",
    "neofetch": """NEOFETCH(1)

NAME
    neofetch - styled system summary

SYNOPSIS
    neofetch""",
    "calc": """CALC(1)

NAME
    calc - evaluate arithmetic

SYNOPSIS
    calc <expression>

DESCRIPTION
    Safely evaluates +, -, *, /, and parentheses.

EXAMPLES
    calc 25 + 17""",
    "history": """HISTORY(1)

NAME
    history - command history

SYNOPSIS
    history
    history -c

DESCRIPTION
    Lists or clears the current shell session history.""",
    "man": """MAN(1)

NAME
    man - display manual pages

SYNOPSIS
    man <command>

DESCRIPTION
    Shows built-in documentation for TERMOS commands.""",
    "grep": """GREP(1)

NAME
    grep - print lines matching a pattern

SYNOPSIS
    grep <pattern> [file]
    command | grep <pattern>""",
    "head": """HEAD(1)

NAME
    head - output the first part of files

SYNOPSIS
    head [-n N] [file]""",
    "tail": """TAIL(1)

NAME
    tail - output the last part of files

SYNOPSIS
    tail [-n N] [file]""",
    "wc": """WC(1)

NAME
    wc - word, line, and byte counts

SYNOPSIS
    wc [file]
    command | wc""",
    "demo": """DEMO(1)

NAME
    demo - run the TERMOS system demonstration

SYNOPSIS
    demo

DESCRIPTION
    Exercises filesystem, processes, memory, programs, and networking.""",
    "dmesg": """DMESG(1)

NAME
    dmesg - print the kernel event log

SYNOPSIS
    dmesg""",
    "verbose": """VERBOSE(1)

NAME
    verbose - toggle internal system event output

SYNOPSIS
    verbose on
    verbose off""",
    "echo": """ECHO(1)

NAME
    echo - display a line of text

SYNOPSIS
    echo [text...]
    echo text > file
    echo text >> file""",
}


class ManPages:
    """Registry of built-in manual pages."""

    def get(self, name: str) -> str:
        try:
            return _MAN[name]
        except KeyError as exc:
            raise NotFoundError(name) from exc

    def has(self, name: str) -> bool:
        return name in _MAN
