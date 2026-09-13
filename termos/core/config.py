"""Virtual configuration for TERMOS (/etc/termos.conf)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from filesystem.filesystem import FileSystem

DEFAULT_CONFIG = {
    "hostname": "termos",
    "memory": "128MB",
    "scheduler": "round_robin",
    "memory_allocator": "first_fit",
    "shell": "termos-sh",
    "network_interface": "eth0",
}

CONFIG_PATH = "/etc/termos.conf"


class ConfigManager:
    """Reads and writes the in-memory ``/etc/termos.conf`` file."""

    def __init__(self, values: dict[str, str] | None = None) -> None:
        self.values = dict(DEFAULT_CONFIG)
        if values:
            self.values.update(values)

    @classmethod
    def install(cls, filesystem: FileSystem) -> ConfigManager:
        """Write the default config into the virtual filesystem."""
        manager = cls()
        body = "\n".join(f"{key}={value}" for key, value in manager.values.items()) + "\n"
        filesystem.write(CONFIG_PATH, body, "/")
        return manager

    def load_from_fs(self, filesystem: FileSystem) -> None:
        """Reload settings from the virtual config file."""
        try:
            text = filesystem.read(CONFIG_PATH, "/")
        except Exception:
            return
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            self.values[key.strip()] = value.strip()

    def get(self, key: str, default: str = "") -> str:
        return self.values.get(key, default)
