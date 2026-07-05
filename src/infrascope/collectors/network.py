from __future__ import annotations

import os
import re
from typing import Any

import psutil

from infrascope.collectors.base import BaseCollector, CollectorResult
from infrascope.core.dependency import check_binary, run_cmd


class NetworkCollector(BaseCollector):
    name = "network"
    description = "Network interface and connectivity information"

    def collect(self) -> CollectorResult:
        data: dict[str, Any] = {}
        interfaces: list[dict[str, Any]] = []

        for iface_name, iface_addrs in psutil.net_if_addrs().items():
            iface = self._collect_interface(iface_name)
            iface["addresses"] = {}
            for addr in iface_addrs:
                family = str(addr.family)
                if family not in iface["addresses"]:
                    iface["addresses"][family] = []
                entry: dict[str, Any] = {"address": addr.address}
                if addr.netmask:
                    entry["netmask"] = addr.netmask
                if addr.broadcast:
                    entry["broadcast"] = addr.broadcast
                if hasattr(addr, 'ptp') and addr.ptp:
                    entry["ptp"] = addr.ptp
                iface["addresses"][family].append(entry)

            io_counters = psutil.net_io_counters(pernic=True)
            if iface_name in io_counters:
                counter = io_counters[iface_name]
                iface["io"] = {
                    "bytes_sent": counter.bytes_sent,
                    "bytes_recv": counter.bytes_recv,
                    "packets_sent": counter.packets_sent,
                    "packets_recv": counter.packets_recv,
                    "errin": counter.errin,
                    "errout": counter.errout,
                    "dropin": counter.dropin,
                    "dropout": counter.dropout,
                }

            iface.update(self._get_ethtool_info(iface_name))
            interfaces.append(iface)

        data["interfaces"] = interfaces
        data["interface_count"] = len(interfaces)

        data["route_info"] = self._get_routing_info()
        data["dns_info"] = self._get_dns_info()
        data["connections"] = self._get_connections()

        data["wifi_info"] = self._get_wifi_info()

        return CollectorResult(self.name, data)

    def _collect_interface(self, name: str) -> dict[str, Any]:
        iface: dict[str, Any] = {
            "name": name,
            "is_loopback": name == "lo",
            "is_wireless": self._is_wireless(name),
            "is_bridge": self._is_bridge(name),
            "is_bond": self._is_bond(name),
            "speed": self._get_interface_speed(name),
            "mtu": self._get_mtu(name),
            "state": self._get_interface_state(name),
            "mac": "",
            "driver": self._get_interface_driver(name),
            "pcie_info": self._get_iface_pcie_info(name),
        }

        operstate = self._read_sysfs_net(name, "operstate")
        iface["operstate"] = operstate if operstate else "unknown"

        addr_len = self._read_sysfs_net(name, "addr_len")
        iface["addr_len"] = addr_len

        duplex = self._read_sysfs_net(name, "duplex")
        iface["duplex"] = duplex

        ifname = self._read_sysfs_net(name, "ifindex")
        try:
            iface["ifindex"] = int(ifname) if ifname else 0
        except ValueError:
            iface["ifindex"] = 0

        return iface

    def _read_sysfs_net(self, iface: str, attr: str) -> str:
        path = f"/sys/class/net/{iface}/{attr}"
        try:
            with open(path) as f:
                return f.read().strip()
        except OSError:
            return ""

    def _is_wireless(self, iface: str) -> bool:
        return os.path.isdir(f"/sys/class/net/{iface}/wireless")

    def _is_bridge(self, iface: str) -> bool:
        return os.path.isdir(f"/sys/class/net/{iface}/bridge")

    def _is_bond(self, iface: str) -> bool:
        bond_path = f"/sys/class/net/{iface}/bonding"
        return os.path.isdir(bond_path)

    def _get_interface_speed(self, iface: str) -> int:
        speed_str = self._read_sysfs_net(iface, "speed")
        try:
            return int(speed_str)
        except (ValueError, TypeError):
            return 0

    def _get_mtu(self, iface: str) -> int:
        mtu_str = self._read_sysfs_net(iface, "mtu")
        try:
            return int(mtu_str)
        except (ValueError, TypeError):
            return 1500

    def _get_interface_state(self, iface: str) -> str:
        return self._read_sysfs_net(iface, "carrier") or "0"

    def _get_interface_driver(self, iface: str) -> str:
        driver_path = f"/sys/class/net/{iface}/device/driver"
        if os.path.isdir(driver_path):
            try:
                return os.path.basename(os.readlink(driver_path))
            except OSError:
                pass
        uevent_path = f"/sys/class/net/{iface}/device/uevent"
        if os.path.exists(uevent_path):
            try:
                with open(uevent_path) as f:
                    for line in f:
                        if line.startswith("DRIVER="):
                            return line.split("=", 1)[1].strip()
            except OSError:
                pass
        return ""

    def _get_iface_pcie_info(self, iface: str) -> dict[str, Any]:
        info: dict[str, Any] = {"pcie": False}
        device_path = f"/sys/class/net/{iface}/device"
        if not os.path.isdir(device_path):
            return info
        try:
            if os.path.exists(os.path.join(device_path, "vendor")):
                with open(os.path.join(device_path, "vendor")) as f:
                    info["vendor_id"] = f.read().strip()
            if os.path.exists(os.path.join(device_path, "device")):
                with open(os.path.join(device_path, "device")) as f:
                    info["device_id"] = f.read().strip()
            if os.path.exists(os.path.join(device_path, "class")):
                with open(os.path.join(device_path, "class")) as f:
                    info["class_id"] = f.read().strip()

            current_speed = os.path.join(device_path, "current_link_speed")
            if os.path.exists(current_speed):
                with open(current_speed) as f:
                    info["pcie_speed"] = f.read().strip()
                info["pcie"] = True
            current_width = os.path.join(device_path, "current_link_width")
            if os.path.exists(current_width):
                with open(current_width) as f:
                    info["pcie_width"] = f.read().strip()
                info["pcie"] = True
        except OSError:
            pass
        return info

    def _get_ethtool_info(self, iface: str) -> dict[str, Any]:
        info: dict[str, Any] = {}
        if not check_binary("ethtool"):
            return info

        output = run_cmd(["ethtool", iface])
        if output:
            for line in output.split("\n"):
                if "Speed:" in line:
                    info["advertised_speed"] = line.split(":")[1].strip() if ":" in line else ""
                elif "Duplex:" in line:
                    info["advertised_duplex"] = line.split(":")[1].strip() if ":" in line else ""
                elif "Auto-negotiation:" in line:
                    info["autoneg"] = line.split(":")[1].strip() if ":" in line else ""
                elif "Port:" in line:
                    info["port_type"] = line.split(":")[1].strip() if ":" in line else ""
                elif "Link detected:" in line:
                    info["link_detected"] = line.split(":")[1].strip() if ":" in line else ""

        # Offload info
        offload = run_cmd(["ethtool", "-k", iface])
        if offload:
            offloads: dict[str, str] = {}
            for line in offload.split("\n"):
                if ":" in line and "fixed" not in line:
                    key, value = line.split(":", 1)
                    offloads[key.strip()] = value.strip()
            info["offload"] = offloads

        # Ring info
        ring = run_cmd(["ethtool", "-g", iface])
        if ring:
            rings: dict[str, str] = {}
            for line in ring.split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    rings[key.strip()] = value.strip()
            info["ring"] = rings

        return info

    def _get_routing_info(self) -> dict[str, Any]:
        info: dict[str, Any] = {"gateway": "", "routes": []}
        if not check_binary("ip"):
            return info
        output = run_cmd(["ip", "route", "show", "default"])
        if output:
            for line in output.split("\n"):
                if "default via" in line:
                    parts = line.split()
                    if len(parts) >= 3:
                        info["gateway"] = parts[2]

        route_output = run_cmd(["ip", "route", "show"])
        if route_output:
            for line in route_output.split("\n"):
                if line.strip():
                    info["routes"].append(line.strip())
        return info

    def _get_dns_info(self) -> dict[str, Any]:
        info: dict[str, Any] = {"nameservers": [], "search_domains": []}
        resolv = "/etc/resolv.conf"
        if os.path.exists(resolv):
            try:
                with open(resolv) as f:
                    for line in f:
                        if line.startswith("nameserver"):
                            parts = line.split()
                            if len(parts) >= 2:
                                info["nameservers"].append(parts[1])
                        elif line.startswith("search"):
                            parts = line.split()
                            if len(parts) >= 2:
                                info["search_domains"] = parts[1:]
            except OSError:
                pass
        return info

    def _get_connections(self) -> int:
        try:
            connections = psutil.net_connections(kind="inet")
            return len(connections)
        except (psutil.AccessDenied, Exception):
            return 0

    def _get_wifi_info(self) -> dict[str, Any]:
        info: dict[str, Any] = {"connected": False, "ssid": "", "signal": 0, "frequency": ""}
        if not check_binary("iwconfig") and not check_binary("iw"):
            return info

        iw_output = run_cmd(["iwconfig"])
        if iw_output:
            for line in iw_output.split("\n"):
                m = re.search(r'ESSID:"([^"]*)"', line)
                if m:
                    info["ssid"] = m.group(1)
                    info["connected"] = bool(info["ssid"])
                m = re.search(r"Signal level=(-?\d+)", line)
                if m:
                    info["signal"] = int(m.group(1))
                m = re.search(r"Frequency[:=](\d+[.]?\d*)", line)
                if m:
                    info["frequency"] = f"{m.group(1)} GHz"

        if not info["connected"]:
            iw_output = run_cmd(["iw", "dev"])
            if iw_output:
                current_iface = ""
                for line in iw_output.split("\n"):
                    if "Interface" in line:
                        current_iface = line.split()[-1]
                    if "ssid" in line and current_iface:
                        m = re.search(r"ssid (.+)", line)
                        if m:
                            info["ssid"] = m.group(1).strip()
                            info["connected"] = True
                    m = re.search(r"signal: (-?\d+)", line)
                    if m:
                        info["signal"] = int(m.group(1))
        return info
