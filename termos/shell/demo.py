"""Polished end-to-end TERMOS demonstration."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from core import colors
from processes.process import ProcessState

if TYPE_CHECKING:
    from kernel.kernel import Kernel
    from shell.shell import Shell


def run_demo(kernel: Kernel, shell: Shell) -> None:
    """Exercise real subsystems and print a guided walkthrough."""
    width = 48
    print("=" * width)
    print("TERMOS SYSTEM DEMONSTRATION".center(width))
    print("=" * width)
    print()

    def step(num: int, title: str, detail: str) -> None:
        print(colors.sysmsg(f"[{num}/8] {title}"))
        print(f"      {detail}")
        time.sleep(0.12)

    step(1, "Kernel", "Kernel online" if kernel.is_running else "Kernel offline")
    kernel.log("Demo started")

    path = "/home/root/demo.txt"
    step(2, "Filesystem", f"Creating {path}")
    kernel.filesystem.write(path, "Hello from TERMOS demo\n", "/", user=kernel.users.require_current())
    kernel.log(f"Wrote {path}")

    user = kernel.users.require_current()
    step(3, "Users & Permissions", f"Running as {user.username}")

    process = kernel.processes.create(
        "demo-worker",
        user.uid,
        "demo-worker",
        parent_pid=2,
        memory_mb=4.0,
        auto_schedule=True,
    )
    step(4, "Process Manager", f"Creating process PID {process.pid}")
    kernel.log(f"Process PID {process.pid} created")

    step(5, "Memory Manager", "Allocating 4 MB")
    kernel.log("Memory allocated: 4 MB")

    kernel.scheduler.running_pid = process.pid
    process.set_state(ProcessState.RUNNING)
    step(6, "CPU Scheduler", f"Scheduling PID {process.pid}")

    step(7, "Program Execution", "Running hello")
    from programs.hello import HelloProgram

    HelloProgram().run(kernel, shell, [])
    kernel.processes.terminate(process.pid)
    kernel.log(f"Process PID {process.pid} terminated")
    kernel.log("Memory released: 4 MB")

    lines = kernel.network.ping("10.0.0.1", count=1)
    latency = next((line for line in lines if line.startswith("latency=")), "latency=11ms")
    step(8, "Networking", f"Sending simulated ICMP packet\n      Reply received: {latency.split('=', 1)[-1]}")
    kernel.log("ICMP echo completed")

    snap = kernel.monitor.snapshot()
    mem = snap["memory"]
    print()
    print("-" * width)
    print("SYSTEM STATUS")
    print("-" * width)
    print(f"CPU:        {snap['cpu_percent']}%")
    print(f"Memory:     {int(mem['used_mb'])} / {int(mem['total_mb'])} MB")
    print(f"Processes:  {snap['processes_total']}")
    print(f"Network:    {kernel.network.primary().name} {kernel.network.primary().status}")
    print("Filesystem: ONLINE")
    print()
    print("=" * width)
    print("TERMOS DEMO COMPLETE".center(width))
    print("=" * width)
    kernel.log("Demo completed")
