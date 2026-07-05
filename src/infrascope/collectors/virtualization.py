from __future__ import annotations

import os
import re
from typing import Any

from infrascope.collectors.base import BaseCollector, CollectorResult
from infrascope.core.dependency import check_binary, run_cmd


class VirtualizationCollector(BaseCollector):
    name = "virtualization"
    description = "Virtualization environment detection"

    def collect(self) -> CollectorResult:
        data: dict[str, Any] = {
            "is_virtual_machine": False,
            "hypervisor": "",
            "detected": {},
            "container_runtime": "",
            "orchestrator": "",
        }

        data["detected"]["kvm"] = self._check_kvm()
        data["detected"]["vmware"] = self._check_vmware()
        data["detected"]["virtualbox"] = self._check_virtualbox()
        data["detected"]["hyperv"] = self._check_hyperv()
        data["detected"]["docker"] = self._check_docker()
        data["detected"]["podman"] = self._check_podman()
        data["detected"]["lxc"] = self._check_lxc()
        data["detected"]["kubernetes"] = self._check_kubernetes()
        data["detected"]["wsl"] = self._check_wsl()

        # Determine hypervisor
        hypervisors = []
        for hv in ["kvm", "vmware", "virtualbox", "hyperv", "wsl"]:
            if data["detected"][hv]:
                hypervisors.append(hv)
        data["hypervisor"] = ", ".join(hypervisors) if hypervisors else ""

        # Container runtimes
        containers = []
        for cr in ["docker", "podman", "lxc"]:
            if data["detected"][cr]:
                containers.append(cr)
        data["container_runtime"] = ", ".join(containers) if containers else ""

        if data["detected"]["kubernetes"]:
            data["orchestrator"] = "Kubernetes"
        elif data["detected"]["docker"]:
            data["orchestrator"] = "Docker Compose (potential)"

        # Systemd container detection
        data["is_virtual_machine"] = bool(data["hypervisor"]) or self._check_systemd_container()

        return CollectorResult(self.name, data)

    def _check_kvm(self) -> bool:
        if os.path.exists("/sys/devices/virtual/misc/kvm"):
            return True
        output = run_cmd(["systemd-detect-virt", "-v"])
        if "kvm" in output.lower():
            return True
        cpuinfo = run_cmd(["grep", "-c", "hypervisor", "/proc/cpuinfo"])
        try:
            return int(cpuinfo.strip()) > 0
        except ValueError:
            pass
        return False

    def _check_vmware(self) -> bool:
        output = run_cmd(["systemd-detect-virt", "-v"])
        if "vmware" in output.lower():
            return True
        try:
            with open("/proc/cpuinfo") as f:
                content = f.read()
            if "VMware" in content or "VMW" in content:
                return True
        except OSError:
            pass
        if check_binary("vmware"):
            return True
        return False

    def _check_virtualbox(self) -> bool:
        output = run_cmd(["systemd-detect-virt", "-v"])
        if "oracle" in output.lower() or "virtualbox" in output.lower():
            return True
        if check_binary("VBoxControl") or check_binary("VBoxService"):
            return True
        try:
            with open("/proc/cpuinfo") as f:
                if "VirtualBox" in f.read():
                    return True
        except OSError:
            pass
        return False

    def _check_hyperv(self) -> bool:
        output = run_cmd(["systemd-detect-virt", "-v"])
        if "hyper-v" in output.lower() or "microsoft" in output.lower():
            return True
        try:
            with open("/proc/cpuinfo") as f:
                if "Hyper-V" in f.read() or "hyperv" in f.read():
                    return True
        except OSError:
            pass
        return False

    def _check_wsl(self) -> bool:
        if "WSL" in os.uname().release or "microsoft" in os.uname().release.lower():
            return True
        try:
            with open("/proc/version") as f:
                if "Microsoft" in f.read() or "WSL" in f.read():
                    return True
        except OSError:
            pass
        return False

    def _check_docker(self) -> bool:
        if os.path.exists("/.dockerenv"):
            return True
        if check_binary("docker"):
            output = run_cmd(["docker", "info", "--format", "{{.ServerVersion}}"], timeout=5)
            if output:
                return True
        if os.path.isdir("/proc/1/cgroup"):
            try:
                with open("/proc/1/cgroup") as f:
                    content = f.read()
                if "docker" in content:
                    return True
            except OSError:
                pass
        return False

    def _check_podman(self) -> bool:
        if check_binary("podman"):
            output = run_cmd(["podman", "version"], timeout=5)
            return bool(output)
        return False

    def _check_lxc(self) -> bool:
        if os.path.exists("/dev/lxd/sock"):
            return True
        try:
            with open("/proc/1/environ") as f:
                if "lxc" in f.read():
                    return True
        except OSError:
            pass
        output = run_cmd(["systemd-detect-virt", "-c"])
        if "lxc" in output.lower():
            return True
        return False

    def _check_kubernetes(self) -> bool:
        if check_binary("kubectl"):
            output = run_cmd(["kubectl", "version", "--short"], timeout=5)
            if output:
                return True
        if os.path.isdir("/etc/kubernetes"):
            return True
        if check_binary("k3s"):
            return True
        if os.path.isdir("/var/lib/kubelet"):
            return True
        return False

    def _check_systemd_container(self) -> bool:
        output = run_cmd(["systemd-detect-virt"])
        if output and "none" not in output.lower():
            return True
        return False
