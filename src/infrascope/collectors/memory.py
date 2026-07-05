from __future__ import annotations

import os
import re
from typing import Any

import psutil

from infrascope.collectors.base import BaseCollector, CollectorResult
from infrascope.core.dependency import check_binary, run_cmd
from infrascope.utils.system import parse_meminfo, read_sysfs


class MemoryCollector(BaseCollector):
    name = "memory"
    description = "Memory (RAM) information"

    def collect(self) -> CollectorResult:
        data: dict[str, Any] = {}
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()

        data["total"] = mem.total
        data["available"] = mem.available
        data["used"] = mem.used
        data["free"] = mem.free
        data["percent_used"] = mem.percent
        data["buffers"] = 0
        data["cached"] = 0

        meminfo = parse_meminfo()
        if "Buffers" in meminfo:
            data["buffers"] = meminfo["Buffers"]
        if "Cached" in meminfo:
            data["cached"] = meminfo["Cached"]

        data["swap_total"] = swap.total
        data["swap_used"] = swap.used
        data["swap_free"] = swap.free
        data["swap_percent"] = swap.percent
        data["swap_in"] = swap.sin
        data["swap_out"] = swap.sout

        hugepages = self._get_hugepages()
        data["hugepages"] = hugepages

        dimm_info = self._get_dimm_info()
        data.update(dimm_info)

        data["channels"] = self._detect_memory_channels()
        data["numa_info"] = self._get_numa_memory()

        return CollectorResult(self.name, data)

    def _get_hugepages(self) -> dict[str, Any]:
        hugepages: dict[str, Any] = {}
        hugepages["total"] = read_sysfs("/proc/sys/vm/nr_hugepages")
        hugepages["size_kb"] = read_sysfs("/proc/sys/vm/hugepagesize")
        try:
            hugepages["total"] = int(hugepages["total"]) if hugepages["total"] else 0
            hugepages["size_kb"] = int(hugepages["size_kb"]) if hugepages["size_kb"] else 0
        except ValueError:
            hugepages["total"] = 0
            hugepages["size_kb"] = 0
        hugepages["enabled"] = hugepages["total"] > 0
        hugepages["total_bytes"] = hugepages["total"] * hugepages["size_kb"] * 1024
        return hugepages

    def _get_dimm_info(self) -> dict[str, Any]:
        info: dict[str, Any] = {
            "dimm_count": 0,
            "dimm_slots": 0,
            "dimms": [],
            "max_capacity": 0,
            "type": "unknown",
            "type_detail": "unknown",
            "form_factor": "unknown",
        }
        if not check_binary("dmidecode"):
            return info
        output = run_cmd(["dmidecode", "-t", "memory"])
        if not output:
            return info

        dimms: list[dict[str, Any]] = []
        current_dimm: dict[str, Any] = {}
        slot_count = 0

        for line in output.split("\n"):
            if "Memory Device" in line and ":" not in line.split("Memory Device")[0]:
                if current_dimm:
                    dimms.append(current_dimm)
                current_dimm = {}
            elif ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()
                if "Number Of Devices" in key:
                    try:
                        slot_count = int(value)
                    except ValueError:
                        pass
                elif key == "Total Width":
                    if "Unknown" not in value:
                        try:
                            current_dimm["width"] = int(value.split()[0])
                        except (ValueError, IndexError):
                            pass
                elif key == "Data Width":
                    if "Unknown" not in value:
                        try:
                            current_dimm["data_width"] = int(value.split()[0])
                        except (ValueError, IndexError):
                            pass
                elif key == "Size":
                    if "No Module Installed" not in value and "Unknown" not in value:
                        try:
                            parts = value.split()
                            size = int(parts[0])
                            if len(parts) > 1 and parts[1].upper() == "GB":
                                size *= 1024
                            current_dimm["size_mb"] = size
                        except (ValueError, IndexError):
                            pass
                elif key == "Type":
                    if value and "Unknown" not in value:
                        current_dimm["type"] = value
                        if "DDR" in value:
                            info["type"] = value
                elif key == "Type Detail":
                    if value and "Unknown" not in value:
                        current_dimm["type_detail"] = value
                elif key == "Speed":
                    if "Unknown" not in value and "Not Installed" not in value:
                        try:
                            current_dimm["speed_mts"] = int(value.split()[0])
                        except (ValueError, IndexError):
                            pass
                elif key == "Manufacturer":
                    if value and "Not Specified" not in value and "Unknown" not in value:
                        current_dimm["manufacturer"] = value
                elif key == "Serial Number":
                    if value and "Not Specified" not in value and "Unknown" not in value:
                        current_dimm["serial"] = value
                elif key == "Part Number":
                    if value and "Not Specified" not in value and "Unknown" not in value and "NO DIMM" not in value.upper():
                        current_dimm["part_number"] = value
                elif key == "Locator":
                    current_dimm["locator"] = value
                elif key == "Bank Locator":
                    current_dimm["bank"] = value
                elif key == "Configured Memory Speed":
                    if "Unknown" not in value:
                        try:
                            current_dimm["configured_speed_mts"] = int(value.split()[0])
                        except (ValueError, IndexError):
                            pass
                elif key == "Form Factor":
                    if value and "Unknown" not in value:
                        current_dimm["form_factor"] = value
                        info["form_factor"] = value
                elif "Maximum Capacity" in key:
                    try:
                        parts = value.split()
                        cap = int(parts[0])
                        if len(parts) > 1 and parts[1].upper() == "TB":
                            cap *= 1024 * 1024
                        elif len(parts) > 1 and parts[1].upper() == "GB":
                            cap *= 1024
                        info["max_capacity"] = cap
                    except (ValueError, IndexError):
                        pass
                elif key == "Error Information Type":
                    current_dimm["ecc"] = value if "None" not in value else "None"
                elif "Operational Memory" in key:
                    if "Unknown" not in value:
                        current_dimm["operational_memory"] = value
                elif key == "Attributes":
                    if "Unknown" not in value:
                        current_dimm["attributes"] = value
                elif key == "Extended Size":
                    if "Unknown" not in value:
                        try:
                            parts = value.split()
                            size = int(parts[0])
                            if len(parts) > 1 and parts[1].upper() == "GB":
                                size *= 1024
                            current_dimm["extended_size_mb"] = size
                        except (ValueError, IndexError):
                            pass
                elif key == "Configured Voltage":
                    if "Unknown" not in value:
                        try:
                            current_dimm["voltage"] = value
                        except (ValueError, IndexError):
                            pass
                elif key == "Minimum Voltage":
                    if "Unknown" not in value:
                        current_dimm["min_voltage"] = value
                elif key == "Maximum Voltage":
                    if "Unknown" not in value:
                        current_dimm["max_voltage"] = value

        if current_dimm and current_dimm.get("size_mb", 0) > 0:
            dimms.append(current_dimm)

        if slot_count == 0:
            slot_count = len(dimms) if dimms else 1
            if slot_count == 0:
                slot_count = 2

        ecc = any(d.get("ecc", "") not in ("", "None") for d in dimms)
        registered = any("Registered" in d.get("type_detail", "") for d in dimms)
        buffered = any("Buffered" in d.get("type_detail", "") for d in dimms)
        total_installed = sum(d.get("size_mb", 0) for d in dimms)

        # Determine DDR generation
        ddr_gen = "unknown"
        dimm_types = [d.get("type", "") for d in dimms]
        for t in dimm_types:
            m = re.search(r"DDR(\d)", t)
            if m:
                ddr_gen = f"DDR{m.group(1)}"
                break

        freq = 0
        for d in dimms:
            if d.get("speed_mts", 0) > freq:
                freq = d["speed_mts"]

        configured_freq = 0
        for d in dimms:
            if d.get("configured_speed_mts", 0) > configured_freq:
                configured_freq = d["configured_speed_mts"]

        info["dimms"] = dimms
        info["dimm_count"] = len(dimms)
        info["dimm_slots"] = slot_count
        info["total_installed_mb"] = total_installed
        info["ecc"] = ecc
        info["registered"] = registered
        info["buffered"] = buffered
        info["ddr_generation"] = ddr_gen
        info["frequency_mts"] = freq or 0
        info["configured_speed_mts"] = configured_freq or freq
        info["slot_population"] = f"{len(dimms)}/{slot_count}"

        return info

    def _detect_memory_channels(self) -> dict[str, Any]:
        channels: dict[str, Any] = {"mode": "unknown", "channels": 1, "interleaved": False}

        try:
            with open("/sys/devices/system/edac/mc/mc0/rank_count") as f:
                channels["edac_detected"] = True
        except OSError:
            channels["edac_detected"] = False

        dimm_data = self._get_dimm_info()
        dimms = dimm_data.get("dimms", [])
        populated = [d for d in dimms if d.get("size_mb", 0) > 0]

        if len(populated) >= 4 and all(d.get("size_mb") == populated[0].get("size_mb") for d in populated[:4]):
            channels["channels"] = 4
            channels["mode"] = "Quad"
            channels["interleaved"] = True
        elif len(populated) >= 3 and all(d.get("size_mb") == populated[0].get("size_mb") for d in populated[:3]):
            channels["channels"] = 3
            channels["mode"] = "Triple"
            channels["interleaved"] = True
        elif len(populated) >= 2 and all(d.get("size_mb") == populated[0].get("size_mb") for d in populated[:2]):
            channels["channels"] = 2
            channels["mode"] = "Dual"
            channels["interleaved"] = True
        elif len(populated) == 1:
            channels["channels"] = 1
            channels["mode"] = "Single"
            channels["interleaved"] = False
        else:
            channels["channels"] = max(len(populated), 1)
            channels["mode"] = "Single"
            channels["interleaved"] = False

        return channels

    def _get_numa_memory(self) -> list[dict[str, Any]]:
        numa_info: list[dict[str, Any]] = []
        if not os.path.isdir("/sys/devices/system/node"):
            return numa_info
        for node_dir in sorted(os.listdir("/sys/devices/system/node/")):
            if node_dir.startswith("node"):
                meminfo_path = f"/sys/devices/system/node/{node_dir}/meminfo"
                if os.path.exists(meminfo_path):
                    node_data: dict[str, Any] = {"node": node_dir}
                    try:
                        with open(meminfo_path) as f:
                            for line in f:
                                parts = line.split(":")
                                if len(parts) == 2:
                                    key = parts[0].strip()
                                    val_str = parts[1].strip().split()[0] if parts[1].strip() else "0"
                                    try:
                                        node_data[key] = int(val_str) * 1024
                                    except ValueError:
                                        node_data[key] = 0
                    except OSError:
                        pass
                    numa_info.append(node_data)
        return numa_info
