from __future__ import annotations

import os
from typing import Any

from infrascope.collectors.base import BaseCollector, CollectorResult
from infrascope.core.dependency import check_binary, run_cmd


class MotherboardCollector(BaseCollector):
    name = "motherboard"
    description = "Motherboard (mainboard) information"

    def collect(self) -> CollectorResult:
        data: dict[str, Any] = {
            "vendor": "",
            "model": "",
            "version": "",
            "serial": "",
            "bios_vendor": "",
            "bios_version": "",
            "bios_date": "",
            "uefi": False,
            "chipset": "",
            "socket": "",
            "form_factor": "",
            "secure_boot": False,
            "tpm": False,
        }

        if check_binary("dmidecode"):
            data.update(self._get_dmidecode_info())
        elif check_binary("inxi"):
            data.update(self._get_inxi_info())

        data["secure_boot"] = self._check_secure_boot()
        data["tpm"] = self._check_tpm()

        return CollectorResult(self.name, data)

    def _get_dmidecode_info(self) -> dict[str, Any]:
        info: dict[str, Any] = {}

        # Baseboard info
        output = run_cmd(["dmidecode", "-t", "baseboard"])
        if output:
            for line in output.split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    key = key.strip()
                    value = value.strip()
                    if "Manufacturer" in key:
                        info["vendor"] = value
                    elif "Product Name" in key:
                        info["model"] = value
                    elif "Version" in key:
                        info["version"] = value
                    elif "Serial Number" in key:
                        info["serial"] = value
                    elif "Asset Tag" in key:
                        info["asset_tag"] = value
                    elif "Location In Chassis" in key:
                        info["location"] = value

        # BIOS info
        bios_output = run_cmd(["dmidecode", "-t", "bios"])
        if bios_output:
            for line in bios_output.split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    key = key.strip()
                    value = value.strip()
                    if "Vendor" in key:
                        info["bios_vendor"] = value
                    elif "Version" in key and "BIOS" in key:
                        info["bios_version"] = value
                    elif "Release Date" in key:
                        info["bios_date"] = value
                    elif "UEFI" in key or "uefi" in key:
                        info["uefi"] = "supported" in value.lower() or "yes" in value.lower()
                    elif "BIOS Revision" in key:
                        info["bios_revision"] = value
                    elif "Firmware Revision" in key:
                        info["firmware_revision"] = value

        # System info for form factor
        chassis_output = run_cmd(["dmidecode", "-t", "chassis"])
        if chassis_output:
            for line in chassis_output.split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    if "Type" in key:
                        info["form_factor"] = value.strip()
                        break

        # Processor info for socket
        cpu_output = run_cmd(["dmidecode", "-t", "processor"])
        if cpu_output:
            for line in cpu_output.split("\n"):
                if "Upgrade" in line and "Socket" in line:
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        info["socket"] = parts[1].strip()
                        break
                if "Socket Designation" in line:
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        socket_val = parts[1].strip()
                        if socket_val and "UEFI" not in socket_val:
                            info.setdefault("socket", socket_val)

        return info

    def _get_inxi_info(self) -> dict[str, Any]:
        info: dict[str, Any] = {}
        output = run_cmd(["inxi", "-M", "-x"])
        if output:
            for line in output.split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    key = key.strip().lower()
                    value = value.strip()
                    if "system" in key or "board" in key:
                        continue
                    if "type" in key:
                        info["form_factor"] = value
                    elif "serial" in key:
                        info["serial"] = value
                    elif "bios" in key:
                        info["bios_vendor"] = value
                    elif "chipset" in key:
                        info["chipset"] = value
        return info

    def _check_secure_boot(self) -> bool:
        for path in ["/sys/firmware/efi/efivars/SecureBoot-*", "/sys/firmware/secureboot"]:
            output = run_cmd(["ls", path])
            if output:
                return True
        mok_output = run_cmd(["mokutil", "--sb-state"])
        if mok_output:
            return "enabled" in mok_output.lower()
        return False

    def _check_tpm(self) -> bool:
        if os.path.exists("/sys/class/tpm"):
            return True
        output = run_cmd(["ls", "/dev/tpm*"])
        if output:
            return True
        output = run_cmd(["dmesg", "|", "grep", "-i", "tpm"])
        if "tpm" in output.lower():
            return True
        return False
