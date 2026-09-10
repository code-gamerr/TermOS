"""Shared TERMOS constants."""

OS_NAME = "TERMOS"
OS_VERSION = "1.0"
HOSTNAME = "termos"
DEFAULT_USER = "root"
DEFAULT_CWD = "~"
HOME_PATH = "/home/root"
ROOT_DIRECTORIES = ("bin", "home", "etc", "tmp", "var")

BOOT_WIDTH = 40

# Slots reserved for later parts. Values stay None until those managers exist.
COMPONENT_NAMES = (
    "filesystem",
    "process_manager",
    "memory_manager",
    "user_manager",
    "network_manager",
)
