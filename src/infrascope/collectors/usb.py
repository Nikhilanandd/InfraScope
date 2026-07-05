from __future__ import annotations

import re
from typing import Any

from infrascope.collectors.base import BaseCollector, CollectorResult
from infrascope.core.dependency import check_binary, run_cmd


class USBCollector(BaseCollector):
    name = "usb"
    description = "USB device information"

    def collect(self) -> CollectorResult:
        data: dict[str, Any] = {}
        devices: list[dict[str, Any]] = []

        if check_binary("lsusb"):
            output = run_cmd(["lsusb"])
            if output:
                for line in output.split("\n"):
                    if not line.strip():
                        continue
                    m = re.match(r"Bus (\d+) Device (\d+): ID ([0-9a-fA-F]{4}):([0-9a-fA-F]{4})\s+(.*)", line)
                    if m:
                        device: dict[str, Any] = {
                            "bus": int(m.group(1)),
                            "device": int(m.group(2)),
                            "vendor_id": m.group(3),
                            "product_id": m.group(4),
                            "description": m.group(5).strip(),
                        }
                        detailed = self._get_usb_details(m.group(1), m.group(2))
                        device.update(detailed)
                        devices.append(device)

            verbose_output = run_cmd(["lsusb", "-v"])
            if verbose_output:
                current_bus = 0
                current_device = 0
                for line in verbose_output.split("\n"):
                    m = re.match(r"Bus (\d+) Device (\d+):", line)
                    if m:
                        current_bus = int(m.group(1))
                        current_device = int(m.group(2))
                    for dev in devices:
                        if dev["bus"] == current_bus and dev["device"] == current_device:
                            if "bcdUSB" in line:
                                m2 = re.search(r"(\d+[.]\d+)", line)
                                if m2:
                                    dev["usb_version"] = m2.group(1)
                            if "bMaxPower" in line:
                                m2 = re.search(r"(\d+)\s*mA", line)
                                if m2:
                                    dev["power_ma"] = int(m2.group(1))
                            if "bDeviceClass" in line:
                                parts = line.split()
                                if len(parts) >= 2:
                                    dev["device_class"] = parts[-1]

        elif check_binary("inxi"):
            output = run_cmd(["inxi", "-u", "-xx"])
            if output:
                current_device = {}
                for line in output.split("\n"):
                    if "USB" in line and ":" in line:
                        if current_device:
                            devices.append(current_device)
                        current_device = {"description": line.strip()}
                    elif current_device and ":" in line:
                        key, value = line.split(":", 1)
                        current_device[key.strip().lower()] = value.strip()
                if current_device:
                    devices.append(current_device)

        data["devices"] = devices
        data["device_count"] = len(devices)
        return CollectorResult(self.name, data)

    def _get_usb_details(self, bus: str, device: str) -> dict[str, Any]:
        details: dict[str, Any] = {}
        output = run_cmd(["lsusb", "-s", f"{bus}:{device}", "-v"])
        if output:
            for line in output.split("\n"):
                if "bcdUSB" in line:
                    m = re.search(r"(\d+[.]\d+)", line)
                    if m:
                        details["usb_version"] = m.group(1)
                if "bMaxPower" in line:
                    m = re.search(r"(\d+)\s*mA", line)
                    if m:
                        details["power_ma"] = int(m.group(1))
                if "idVendor" in line:
                    m = re.search(r"0x([0-9a-fA-F]+)", line)
                    if m:
                        details["vendor_id"] = m.group(1)
                if "idProduct" in line:
                    m = re.search(r"0x([0-9a-fA-F]+)", line)
                    if m:
                        details["product_id"] = m.group(1)
                if "bDeviceClass" in line:
                    m = re.search(r"\(([^)]+)\)", line)
                    if m:
                        details["device_class"] = m.group(1)
                if "iManufacturer" in line:
                    m = re.search(r"(\w+)$", line.strip())
                    if m and m.group(1) not in ("Unknown",):
                        details["manufacturer"] = m.group(1)
                if "iProduct" in line:
                    m = re.search(r"(\w.+)$", line.strip())
                    if m:
                        details["product"] = m.group(1)
        return details
