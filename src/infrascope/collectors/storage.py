from __future__ import annotations

import os
import re
from typing import Any

import psutil

from infrascope.collectors.base import BaseCollector, CollectorResult
from infrascope.core.dependency import check_binary, run_cmd


class StorageCollector(BaseCollector):
    name = "storage"
    description = "Storage device information"

    def collect(self) -> CollectorResult:
        data: dict[str, Any] = {}
        disks: list[dict[str, Any]] = []

        lsblk_disks = self._get_lsblk_disks()
        disks.extend(lsblk_disks)

        for disk in disks:
            disk_name = disk.get("name", "")
            if disk_name:
                smart_info = self._get_smart_info(disk_name)
                disk.update(smart_info)

                nvme_info = self._get_nvme_info(disk_name)
                disk.update(nvme_info)

                disk["disk_type"] = self._classify_disk(disk)

        data["disks"] = disks
        data["disk_count"] = len(disks)

        partitions = psutil.disk_partitions()
        data["partitions"] = [
            {
                "device": p.device,
                "mountpoint": p.mountpoint,
                "fstype": p.fstype,
                "opts": p.opts,
            }
            for p in partitions
        ]

        disk_usage = {}
        for p in partitions:
            try:
                usage = psutil.disk_usage(p.mountpoint)
                disk_usage[p.mountpoint] = {
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percent": usage.percent,
                }
            except OSError:
                pass
        data["disk_usage"] = disk_usage

        data["io_counters"] = self._get_io_counters()

        data["lvm_info"] = self._get_lvm_info()
        data["raid_info"] = self._get_raid_info()
        data["loop_devices"] = self._get_loop_devices()

        return CollectorResult(self.name, data)

    def _get_lsblk_disks(self) -> list[dict[str, Any]]:
        disks: list[dict[str, Any]] = []
        output = run_cmd(["lsblk", "-d", "-o", "NAME,SIZE,TYPE,MOUNTPOINT,MODEL,ROTA,TRAN,SCHED,ALIGNMENT,MIN-IO,OPT-IO,PHY-SEC,LOG-SEC", "-J"])
        if output:
            try:
                import json
                data = json.loads(output)
                for device in data.get("blockdevices", []):
                    if device.get("type") in ("disk", "nvme"):
                        disk: dict[str, Any] = {
                            "name": device.get("name", ""),
                            "size": self._parse_size(device.get("size", "0")),
                            "type": device.get("type", ""),
                            "model": device.get("model", ""),
                            "rotational": device.get("rota", 0) == 1,
                            "tran": device.get("tran", ""),
                            "scheduler": device.get("sched", ""),
                            "phy_sec": device.get("phy-sec", 0),
                            "log_sec": device.get("log-sec", 0),
                        }
                        disks.append(disk)
            except (json.JSONDecodeError, Exception):
                pass
        if not disks:
            output = run_cmd(["lsblk", "-d", "-o", "NAME,SIZE,TYPE,ROTA,TRAN"])
            if output:
                for line in output.split("\n")[1:]:
                    parts = line.split()
                    if len(parts) >= 3 and parts[2] in ("disk", "nvme"):
                        disk = {
                            "name": parts[0],
                            "size": self._parse_size(parts[1]),
                            "type": parts[2],
                            "rotational": len(parts) > 3 and parts[3] == "1",
                            "tran": parts[4] if len(parts) > 4 else "",
                        }
                        disks.append(disk)
        return disks

    def _parse_size(self, size_str: str) -> int:
        try:
            size_str = size_str.strip()
            if size_str.endswith("G"):
                return int(float(size_str[:-1]) * 1024**3)
            if size_str.endswith("T"):
                return int(float(size_str[:-1]) * 1024**4)
            if size_str.endswith("M"):
                return int(float(size_str[:-1]) * 1024**2)
            if size_str.endswith("K"):
                return int(float(size_str[:-1]) * 1024)
            if size_str.endswith("B"):
                return int(float(size_str[:-1]))
            return int(size_str)
        except (ValueError, AttributeError):
            return 0

    def _get_smart_info(self, disk: str) -> dict[str, Any]:
        info: dict[str, Any] = {}
        if not check_binary("smartctl"):
            return info
        output = run_cmd(["smartctl", "-A", f"/dev/{disk}"])
        if not output:
            return info

        for line in output.split("\n"):
            if "Temperature_Celsius" in line:
                parts = line.split()
                if len(parts) >= 10:
                    try:
                        info["temperature_c"] = int(parts[9])
                    except ValueError:
                        pass
            if "Power_On_Hours" in line or "Power-On Hours" in line:
                parts = line.split()
                if len(parts) >= 10:
                    try:
                        info["power_on_hours"] = int(parts[9])
                    except ValueError:
                        pass
            if "Total_LBAs_Written" in line:
                parts = line.split()
                if len(parts) >= 10:
                    try:
                        info["total_lba_written"] = int(parts[9])
                    except ValueError:
                        pass
            if "Wear_Leveling_Count" in line or "Wear Leveling Count" in line:
                parts = line.split()
                if len(parts) >= 10:
                    try:
                        info["wear_leveling"] = int(parts[9])
                        wear = info["wear_leveling"]
                        info["remaining_life_pct"] = max(0, 100 - wear)
                    except ValueError:
                        pass
            if "Reallocated_Sector_Ct" in line:
                parts = line.split()
                if len(parts) >= 10:
                    try:
                        info["reallocated_sectors"] = int(parts[9])
                    except ValueError:
                        pass
            if "Reported_Uncorrect" in line or "Reported Uncorrect" in line:
                parts = line.split()
                if len(parts) >= 10:
                    try:
                        info["uncorrectable_errors"] = int(parts[9])
                    except ValueError:
                        pass
            if "Media_Wearout_Indicator" in line:
                parts = line.split()
                if len(parts) >= 10:
                    try:
                        info["media_wearout"] = int(parts[9])
                        info["remaining_life_pct"] = info["media_wearout"]
                    except ValueError:
                        pass
            if "Percentage Used" in line:
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        pct = int(parts[2].rstrip("%"))
                        info["remaining_life_pct"] = max(0, 100 - pct)
                    except ValueError:
                        pass
            if "Available Spare" in line:
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        info["available_spare_pct"] = int(parts[2].rstrip("%"))
                    except ValueError:
                        pass
            if "Critical Warning" in line:
                info["critical_warning"] = line.split(":")[1].strip() if ":" in line else ""

        if "remaining_life_pct" not in info:
            info["remaining_life_pct"] = 100

        # SMART status
        status_output = run_cmd(["smartctl", "-H", f"/dev/{disk}"])
        if status_output:
            for line in status_output.split("\n"):
                if "SMART overall-health" in line or "SMART Health Status" in line:
                    info["smart_status"] = "PASSED" if "PASSED" in line else "FAILED"
                    break

        return info

    def _get_nvme_info(self, disk: str) -> dict[str, Any]:
        info: dict[str, Any] = {}
        if not os.path.exists(f"/sys/block/{disk}/queue"):
            return info

        try:
            rotational_path = f"/sys/block/{disk}/queue/rotational"
            if os.path.exists(rotational_path):
                with open(rotational_path) as f:
                    is_rotational = f.read().strip() == "1"
                if is_rotational:
                    info["media_type"] = "HDD"
                    return info
        except OSError:
            pass

        nvme_path = f"/sys/block/{disk}/device"
        if os.path.isdir(nvme_path):
            try:
                if os.path.exists(os.path.join(nvme_path, "samsung")):
                    info["vendor"] = "Samsung"
                elif os.path.exists(os.path.join(nvme_path, "wdc")):
                    info["vendor"] = "WD"
                elif os.path.exists(os.path.join(nvme_path, "intel")):
                    info["vendor"] = "Intel"
                elif os.path.exists(os.path.join(nvme_path, "micron")):
                    info["vendor"] = "Micron"
                elif os.path.exists(os.path.join(nvme_path, "kingston")):
                    info["vendor"] = "Kingston"
            except OSError:
                pass

            model_path = os.path.join(nvme_path, "model")
            if os.path.exists(model_path):
                try:
                    with open(model_path) as f:
                        info["model"] = f.read().strip()
                except OSError:
                    pass

            pcie_link = self._get_nvme_pcie_info(disk)
            info.update(pcie_link)

        # NVMe gen detection
        model = info.get("model", "").upper()
        if any(x in model for x in ["PC801", "PC811", "990 PRO", "T700", "GEN5", "E26"]):
            info["nvme_gen"] = 5
        elif any(x in model for x in ["980 PRO", "SN850", "KC3000", "T500", "P44 PRO", "GEN4", "E18", "SE10"]):
            info["nvme_gen"] = 4
        elif info.get("pcie_version", 0) >= 5:
            info["nvme_gen"] = 5
        elif info.get("pcie_version", 0) >= 4:
            info["nvme_gen"] = 4
        elif info.get("pcie_version", 0) >= 3:
            info["nvme_gen"] = 3
        elif info.get("pcie_version", 0) >= 2:
            info["nvme_gen"] = 2
        elif info.get("pcie_version", 0) >= 1:
            info["nvme_gen"] = 1
        elif "NVMe" in model:
            info["nvme_gen"] = 3
        else:
            info["nvme_gen"] = 0

        info["media_type"] = "NVMe"
        return info

    def _get_nvme_pcie_info(self, disk: str) -> dict[str, Any]:
        info: dict[str, Any] = {"pcie_version": 0, "pcie_lanes": 0, "pcie_width": "unknown"}
        nvme_device_path = f"/sys/block/{disk}/device/device"
        if not os.path.isdir(nvme_device_path):
            nvme_device_path = f"/sys/block/{disk}/device"
            if not os.path.isdir(nvme_device_path):
                return info

        try:
            current_link_speed = os.path.join(nvme_device_path, "current_link_speed")
            if os.path.exists(current_link_speed):
                with open(current_link_speed) as f:
                    speed_str = f.read().strip()
                    m = re.search(r"(\d+[.]?\d*)\s*GT/s", speed_str)
                    if m:
                        speed = float(m.group(1))
                        if speed >= 32:
                            info["pcie_version"] = 5
                        elif speed >= 16:
                            info["pcie_version"] = 4
                        elif speed >= 8:
                            info["pcie_version"] = 3
                        elif speed >= 5:
                            info["pcie_version"] = 2
                        else:
                            info["pcie_version"] = 1
                    info["pcie_speed"] = speed_str

            current_link_width = os.path.join(nvme_device_path, "current_link_width")
            if os.path.exists(current_link_width):
                with open(current_link_width) as f:
                    width = f.read().strip()
                    try:
                        info["pcie_lanes"] = int(width)
                        info["pcie_width"] = f"x{width}"
                    except ValueError:
                        pass

            max_link_speed = os.path.join(nvme_device_path, "max_link_speed")
            if os.path.exists(max_link_speed):
                with open(max_link_speed) as f:
                    info["max_pcie_speed"] = f.read().strip()

            max_link_width = os.path.join(nvme_device_path, "max_link_width")
            if os.path.exists(max_link_width):
                with open(max_link_width) as f:
                    width = f.read().strip()
                    try:
                        info["max_pcie_width"] = f"x{width}"
                    except ValueError:
                        pass
        except OSError:
            pass
        return info

    def _get_io_counters(self) -> dict[str, Any]:
        counters: dict[str, Any] = {}
        for disk_name in os.listdir("/sys/block/"):
            if disk_name.startswith(("sd", "nvme", "hd", "vd", "mmc")):
                try:
                    stat_path = f"/sys/block/{disk_name}/stat"
                    if os.path.exists(stat_path):
                        with open(stat_path) as f:
                            parts = f.read().strip().split()
                            if len(parts) >= 15:
                                counters[disk_name] = {
                                    "read_ios": int(parts[0]),
                                    "read_merges": int(parts[1]),
                                    "read_sectors": int(parts[2]),
                                    "read_ticks": int(parts[3]),
                                    "write_ios": int(parts[4]),
                                    "write_merges": int(parts[5]),
                                    "write_sectors": int(parts[6]),
                                    "write_ticks": int(parts[7]),
                                    "in_flight": int(parts[8]),
                                    "io_ticks": int(parts[9]),
                                    "time_in_queue": int(parts[10]),
                                }
                except (OSError, ValueError, IndexError):
                    pass
        return counters

    def _classify_disk(self, disk: dict[str, Any]) -> str:
        if disk.get("media_type") == "NVMe":
            gen = disk.get("nvme_gen", 0)
            if gen >= 5:
                return "NVMe Gen5"
            if gen >= 4:
                return "NVMe Gen4"
            if gen >= 3:
                return "NVMe Gen3"
            return "NVMe"
        if disk.get("rotational"):
            return "HDD"
        tran = disk.get("tran", "").lower()
        if "usb" in tran:
            return "USB"
        if "sata" in tran or not disk.get("rotational"):
            return "SATA SSD"
        return "Unknown"

    def _get_lvm_info(self) -> dict[str, Any]:
        info: dict[str, Any] = {"detected": False, "pv_count": 0, "vg_count": 0, "lv_count": 0}
        output = run_cmd(["lvm", "pvs", "--reportformat=json", "--units=b"], timeout=10)
        if output and "report" in output:
            info["detected"] = True
            try:
                import json
                data = json.loads(output)
                info["pv_count"] = len(data.get("report", [{}])[0].get("pv", []))
            except (json.JSONDecodeError, IndexError):
                pass
        vg_output = run_cmd(["lvm", "vgs", "--reportformat=json", "--units=b"], timeout=10)
        if vg_output and "report" in vg_output:
            try:
                import json
                data = json.loads(vg_output)
                info["vg_count"] = len(data.get("report", [{}])[0].get("vg", []))
            except (json.JSONDecodeError, IndexError):
                pass
        lv_output = run_cmd(["lvm", "lvs", "--reportformat=json", "--units=b"], timeout=10)
        if lv_output and "report" in lv_output:
            try:
                import json
                data = json.loads(lv_output)
                info["lv_count"] = len(data.get("report", [{}])[0].get("lv", []))
            except (json.JSONDecodeError, IndexError):
                pass
        return info

    def _get_raid_info(self) -> dict[str, Any]:
        info: dict[str, Any] = {"detected": False, "level": "", "devices": [], "status": ""}
        mdstat = "/proc/mdstat"
        if os.path.exists(mdstat):
            try:
                with open(mdstat) as f:
                    content = f.read()
                if "md" in content and "active" in content:
                    info["detected"] = True
                    for line in content.split("\n"):
                        if " : " in line:
                            parts = line.split(" : ")
                            info["status"] = parts[1].strip()
                            if "raid" in parts[1]:
                                m = re.search(r"raid(\d+)", parts[1])
                                if m:
                                    info["level"] = f"RAID {m.group(1)}"
            except OSError:
                pass
        return info

    def _get_loop_devices(self) -> list[dict[str, Any]]:
        devices: list[dict[str, Any]] = []
        output = run_cmd(["losetup", "-l", "-O", "NAME,SIZE,BACK-FILE", "--json"], timeout=10)
        if output:
            try:
                import json
                data = json.loads(output)
                for device in data.get("loopdevices", []):
                    devices.append({
                        "name": device.get("name", ""),
                        "size": device.get("size", 0),
                        "back_file": device.get("back-file", ""),
                    })
            except (json.JSONDecodeError, Exception):
                pass
        return devices
