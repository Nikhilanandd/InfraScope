from __future__ import annotations

import importlib
import shutil
import subprocess
from typing import NamedTuple

from rich.console import Console

console = Console()


class DependencyInfo(NamedTuple):
    name: str
    binary: str | None = None
    python_package: str | None = None
    required: bool = False
    description: str = ""


COMMON_DEPENDENCIES: list[DependencyInfo] = [
    DependencyInfo("dmidecode", binary="dmidecode", description="DMI table decoder"),
    DependencyInfo("smartctl", binary="smartctl", description="SMART monitoring tool"),
    DependencyInfo("lshw", binary="lshw", description="Hardware lister"),
    DependencyInfo("lscpu", binary="lscpu", description="CPU architecture info"),
    DependencyInfo("lsblk", binary="lsblk", description="Block device listing"),
    DependencyInfo("hwinfo", binary="hwinfo", description="Hardware info tool"),
    DependencyInfo("nvme", binary="nvme", description="NVMe storage tool"),
    DependencyInfo("ip", binary="ip", description="IP network tool"),
    DependencyInfo("ethtool", binary="ethtool", description="Network interface tool"),
    DependencyInfo("fio", binary="fio", description="Storage benchmark tool"),
    DependencyInfo("sensors", binary="sensors", description="Temperature sensors"),
    DependencyInfo("inxi", binary="inxi", description="System information tool"),
    DependencyInfo("lspci", binary="lspci", description="PCI device lister"),
    DependencyInfo("lsusb", binary="lsusb", description="USB device lister"),
    DependencyInfo("iperf3", binary="iperf3", required=False, description="Network benchmark"),
]


def check_binary(name: str) -> bool:
    return shutil.which(name) is not None


def check_python_package(name: str) -> bool:
    try:
        importlib.import_module(name)
        return True
    except ImportError:
        return False


def check_dependencies(deps: list[DependencyInfo] | None = None) -> dict[str, bool]:
    if deps is None:
        deps = COMMON_DEPENDENCIES
    results: dict[str, bool] = {}
    for dep in deps:
        if dep.python_package:
            results[dep.name] = check_python_package(dep.python_package)
        elif dep.binary:
            results[dep.name] = check_binary(dep.binary)
        else:
            results[dep.name] = False
    return results


def get_missing_required(deps: list[DependencyInfo] | None = None) -> list[DependencyInfo]:
    if deps is None:
        deps = COMMON_DEPENDENCIES
    missing: list[DependencyInfo] = []
    for dep in deps:
        if not dep.required:
            continue
        if dep.python_package and not check_python_package(dep.python_package):
            missing.append(dep)
        elif dep.binary and not check_binary(dep.binary):
            missing.append(dep)
    return missing


def get_available_deps(deps: list[DependencyInfo] | None = None) -> list[str]:
    if deps is None:
        deps = COMMON_DEPENDENCIES
    available: list[str] = []
    for dep in deps:
        if dep.python_package and check_python_package(dep.python_package):
            available.append(dep.name)
        elif dep.binary and check_binary(dep.binary):
            available.append(dep.name)
    return available


def print_dependency_report() -> None:
    from rich.table import Table
    from rich import box

    table = Table(title="InfraScope Dependency Report", box=box.ROUNDED)
    table.add_column("Dependency", style="cyan")
    table.add_column("Type", style="yellow")
    table.add_column("Status", style="bold")
    table.add_column("Description")

    for dep in COMMON_DEPENDENCIES:
        dep_type = "Binary" if dep.binary else "Python"
        if dep.python_package:
            status = "OK" if check_python_package(dep.python_package) else "MISSING"
        elif dep.binary:
            status = "OK" if check_binary(dep.binary) else "MISSING"
        else:
            status = "UNKNOWN"
        style = "green" if status == "OK" else "red"
        table.add_row(
            dep.name,
            dep_type,
            f"[{style}]{status}[/{style}]",
            dep.description,
        )
    console.print(table)


def run_cmd(cmd: list[str], timeout: int = 15) -> str:
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return ""
