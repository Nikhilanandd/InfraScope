from __future__ import annotations

import os
import platform
import subprocess
from typing import Any


def get_os_info() -> dict[str, str]:
    info: dict[str, str] = {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "hostname": platform.node(),
        "distro": "",
        "distro_version": "",
    }
    os_release = "/etc/os-release"
    if os.path.exists(os_release):
        try:
            with open(os_release) as f:
                for line in f:
                    if line.startswith("PRETTY_NAME="):
                        info["distro"] = line.split("=", 1)[1].strip().strip('"')
                    elif line.startswith("VERSION_ID="):
                        info["distro_version"] = line.split("=", 1)[1].strip().strip('"')
        except OSError:
            pass
    if not info["distro"]:
        info["distro"] = f"{info['system']} {info['release']}"
    return info


def get_kernel_params() -> dict[str, str]:
    params: dict[str, str] = {}
    try:
        with open("/proc/cmdline") as f:
            params["cmdline"] = f.read().strip()
    except OSError:
        params["cmdline"] = ""
    return params


def get_uptime() -> str:
    try:
        with open("/proc/uptime") as f:
            uptime_seconds = float(f.read().split()[0])
        days, remainder = divmod(uptime_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        parts = []
        if days > 0:
            parts.append(f"{int(days)}d")
        if hours > 0:
            parts.append(f"{int(hours)}h")
        if minutes > 0:
            parts.append(f"{int(minutes)}m")
        parts.append(f"{int(seconds)}s")
        return " ".join(parts)
    except (OSError, ValueError):
        return "unknown"


def get_load_average() -> tuple[float, float, float]:
    try:
        return os.getloadavg()
    except OSError:
        return (0.0, 0.0, 0.0)


def get_process_count() -> int:
    try:
        result = subprocess.run(
            ["ps", "-e", "--no-headers", "-o", "pid"],
            capture_output=True, text=True, timeout=10,
        )
        return len(result.stdout.strip().split("\n")) if result.stdout.strip() else 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return 0


def bytes_to_human(size: int | float, suffix: str = "B") -> str:
    for unit in ("", "K", "M", "G", "T", "P"):
        if abs(size) < 1024.0:
            return f"{size:3.1f} {unit}{suffix}"
        size /= 1024.0
    return f"{size:.1f} P{suffix}"


def hz_to_human(hz: float) -> str:
    if hz >= 1_000_000_000:
        return f"{hz / 1_000_000_000:.2f} GHz"
    if hz >= 1_000_000:
        return f"{hz / 1_000_000:.2f} MHz"
    if hz >= 1_000:
        return f"{hz / 1_000:.2f} KHz"
    return f"{hz:.2f} Hz"


def read_sysfs(path: str) -> str:
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return ""


def read_int_from_sysfs(path: str, default: int = 0) -> int:
    val = read_sysfs(path)
    try:
        return int(val)
    except ValueError:
        return default


def parse_meminfo() -> dict[str, int]:
    info: dict[str, int] = {}
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                parts = line.split(":")
                if len(parts) == 2:
                    key = parts[0].strip()
                    value_str = parts[1].strip().split()[0] if parts[1].strip() else "0"
                    try:
                        info[key] = int(value_str) * 1024
                    except ValueError:
                        info[key] = 0
    except OSError:
        pass
    return info


def parse_cpuinfo() -> list[dict[str, str]]:
    processors: list[dict[str, str]] = []
    current: dict[str, str] = {}
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                line = line.strip()
                if not line:
                    if current:
                        processors.append(current)
                        current = {}
                elif ":" in line:
                    key, value = line.split(":", 1)
                    current[key.strip()] = value.strip()
        if current:
            processors.append(current)
    except OSError:
        pass
    return processors
