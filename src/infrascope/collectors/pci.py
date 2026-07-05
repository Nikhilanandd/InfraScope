from __future__ import annotations

import re
from typing import Any

from infrascope.collectors.base import BaseCollector, CollectorResult
from infrascope.core.dependency import check_binary, run_cmd


PCI_CLASSES: dict[str, str] = {
    "00": "Legacy",
    "01": "Storage",
    "02": "Network",
    "03": "Graphics",
    "04": "Audio",
    "05": "Bridge",
    "06": "Bridge",
    "07": "Bridge",
    "08": "Bridge",
    "09": "Communication",
    "0a": "Bridge",
    "0b": "Bridge",
    "0c": "Serial Bus",
    "0d": "Wireless",
    "0e": "I2O",
    "0f": "Satellite",
    "10": "Encryption",
    "11": "Data Acquisition",
    "12": "Processing Accelerator",
    "13": "FPGA",
    "40": "Co-Processor",
    "ff": "Unclassified",
}


class PCICollector(BaseCollector):
    name = "pci"
    description = "PCI device information"

    def collect(self) -> CollectorResult:
        data: dict[str, Any] = {}
        devices: list[dict[str, Any]] = []

        if check_binary("lspci"):
            output = run_cmd(["lspci", "-nnk"])
            if output:
                current_device: dict[str, Any] = {}
                for line in output.split("\n"):
                    if line and line[0].isdigit():
                        if current_device:
                            devices.append(current_device)
                        current_device = self._parse_pci_line(line)
                    elif line.strip().startswith("Subsystem"):
                        m = re.search(r"Subsystem:\s*(.+)", line)
                        if m:
                            current_device["subsystem"] = m.group(1).strip()
                    elif "Kernel driver in use" in line:
                        m = re.search(r"Kernel driver in use:\s*(.+)", line)
                        if m:
                            current_device["driver"] = m.group(1).strip()
                    elif "Kernel modules" in line:
                        m = re.search(r"Kernel modules:\s*(.+)", line)
                        if m:
                            current_device["kernel_modules"] = m.group(1).strip()
                if current_device:
                    devices.append(current_device)

            # Get verbose info
            verbose = run_cmd(["lspci", "-vvv"])
            if verbose:
                for i, dev in enumerate(devices):
                    pci_id = dev.get("pci_id", "")
                    if pci_id:
                        for line in verbose.split("\n"):
                            if pci_id in line and ":" in line.split(pci_id)[0] if pci_id in line else False:
                                pass
                            if dev.get("driver", "") in line or dev.get("pci_id", "") in line:
                                if "LnkSta:" in line:
                                    m = re.search(r"Speed\s+(\d+[.]?\d*)\s*GT/s", line)
                                    if m:
                                        dev["pcie_speed"] = m.group(1)
                                    m = re.search(r"Width\s+x(\d+)", line)
                                    if m:
                                        dev["pcie_width"] = f"x{m.group(1)}"
                                if "DevSta:" in line:
                                    if "URD" in line:
                                        dev["unsupported_request"] = True

        data["devices"] = devices
        data["device_count"] = len(devices)

        classified: dict[str, list[dict[str, Any]]] = {}
        for dev in devices:
            cls = dev.get("category", "Unclassified")
            if cls not in classified:
                classified[cls] = []
            classified[cls].append(dev)
        data["classified"] = classified

        return CollectorResult(self.name, data)

    def _parse_pci_line(self, line: str) -> dict[str, Any]:
        device: dict[str, Any] = {}
        parts = line.strip().split(None, 3)
        if parts:
            device["pci_id"] = parts[0]
        if len(parts) >= 2:
            device["class_code"] = parts[1].strip("[]")
            class_short = device["class_code"][:2]
            device["category"] = PCI_CLASSES.get(class_short, "Unclassified")
        description = parts[-1] if parts else ""
        m = re.search(r"\[([0-9a-fA-F]{4}:[0-9a-fA-F]{4})\]", description)
        if m:
            device["vendor_device_id"] = m.group(1)
            description = description.replace(m.group(0), "").strip()
        device["description"] = description.strip()
        return device
