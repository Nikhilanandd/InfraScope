from __future__ import annotations

import os
import re
from typing import Any

from infrascope.collectors.base import BaseCollector, CollectorResult
from infrascope.core.dependency import check_binary, run_cmd


class MonitorsCollector(BaseCollector):
    name = "monitors"
    description = "Display/monitor information"

    def collect(self) -> CollectorResult:
        data: dict[str, Any] = {}
        monitors: list[dict[str, Any]] = []

        monitors = self._get_monitors_from_edid()
        if not monitors:
            monitors = self._get_monitors_from_xrandr()
        if not monitors:
            monitors = self._get_monitors_from_sysfs()

        data["monitors"] = monitors
        data["monitor_count"] = len(monitors)
        return CollectorResult(self.name, data)

    def _get_monitors_from_edid(self) -> list[dict[str, Any]]:
        monitors: list[dict[str, Any]] = []
        for drm_path in ["/sys/class/drm/"]:
            if not os.path.isdir(drm_path):
                continue
            for card in sorted(os.listdir(drm_path)):
                if card.startswith("card"):
                    for connector in sorted(os.listdir(os.path.join(drm_path, card))):
                        edid_path = os.path.join(drm_path, card, connector, "edid")
                        if os.path.exists(edid_path):
                            try:
                                with open(edid_path, "rb") as f:
                                    edid_data = f.read()
                                if len(edid_data) >= 128:
                                    monitor = self._parse_edid(edid_data)
                                    if monitor:
                                        monitors.append(monitor)
                            except (OSError, PermissionError):
                                pass
        return monitors

    def _parse_edid(self, data: bytes) -> dict[str, Any]:
        monitor: dict[str, Any] = {}
        try:
            # Manufacturer
            mfg_id = ((data[8] & 0x7F) << 8) | (data[9] & 0x7F)
            mfg_str = ""
            for i in range(3):
                c = (mfg_id >> ((2 - i) * 5)) & 0x1F
                mfg_str += chr(ord("A") + c - 1)
            monitor["manufacturer"] = mfg_str

            # Product code
            monitor["product_code"] = (data[10] << 8) | data[11]

            # Serial
            serial = (data[12] << 8) | data[13]
            monitor["serial"] = serial if serial > 0 else ""

            # Week/Year
            monitor["manufacture_week"] = data[16]
            monitor["manufacture_year"] = 1990 + data[17] if data[17] <= 0x15 else 2000 + (data[17] - 0x10)

            # Dimensions
            monitor["width_cm"] = data[21]
            monitor["height_cm"] = data[22]

            # Parse detailed timings from EDID descriptor blocks
            for i in range(4):
                offset = 54 + i * 18
                if offset + 18 > len(data):
                    break
                tag = data[offset + 3]
                if tag == 0xFC:  # Monitor name
                    name_bytes = data[offset + 5 : offset + 18]
                    name = name_bytes.split(b"\n")[0].strip().decode("ascii", errors="ignore").strip()
                    if name:
                        monitor["name"] = name
                elif tag == 0xFF:  # Serial
                    serial_bytes = data[offset + 5 : offset + 18]
                    serial_str = serial_bytes.split(b"\n")[0].strip().decode("ascii", errors="ignore").strip()
                    if serial_str:
                        monitor["serial_str"] = serial_str
                elif tag == 0xFD:  # Range limits
                    pass
                elif tag == 0xFC:
                    pass

            # Preferred resolution
            if data[54] & 0x80:
                h_active = ((data[56] & 0xF0) << 4) | data[54]
                v_active = ((data[59] & 0xF0) << 4) | data[55]
                if h_active > 0 and v_active > 0:
                    monitor["preferred_width"] = h_active
                    monitor["preferred_height"] = v_active
                    refresh = data[57] if data[57] > 1 else 60
                    monitor["preferred_refresh"] = refresh

        except (IndexError, ValueError, UnicodeDecodeError):
            pass
        return monitor

    def _get_monitors_from_xrandr(self) -> list[dict[str, Any]]:
        monitors: list[dict[str, Any]] = []
        output = run_cmd(["xrandr", "--current"])
        if output:
            current_monitor: dict[str, Any] = {}
            for line in output.split("\n"):
                m = re.match(r"(\S+) connected", line)
                if m:
                    if current_monitor:
                        monitors.append(current_monitor)
                    current_monitor = {"name": m.group(1), "connected": True}
                    m2 = re.search(r"(\d+)mm x (\d+)mm", line)
                    if m2:
                        current_monitor["width_mm"] = int(m2.group(1))
                        current_monitor["height_mm"] = int(m2.group(2))
                elif "disconnected" in line and not current_monitor:
                    m = re.match(r"(\S+) disconnected", line)
                    if m:
                        current_monitor = {"name": m.group(1), "connected": False}
                        monitors.append(current_monitor)
                        current_monitor = {}
                elif current_monitor and "*" in line:
                    m2 = re.search(r"(\d+)x(\d+)", line)
                    if m2:
                        current_monitor["current_width"] = int(m2.group(1))
                        current_monitor["current_height"] = int(m2.group(2))
                    m3 = re.search(r"(\d+[.]?\d*)\s*\*", line)
                    if m3:
                        current_monitor["current_refresh"] = float(m3.group(1))
                elif current_monitor and line.strip().startswith(" ") and "x" in line:
                    m2 = re.search(r"(\d+)x(\d+)", line)
                    if m2:
                        if "modes" not in current_monitor:
                            current_monitor["modes"] = []
                        current_monitor["modes"].append(f"{m2.group(1)}x{m2.group(2)}")
            if current_monitor:
                monitors.append(current_monitor)
        return monitors

    def _get_monitors_from_sysfs(self) -> list[dict[str, Any]]:
        monitors: list[dict[str, Any]] = []
        for drm_path in ["/sys/class/drm/card*/"]:
            import glob
            for card_dir in glob.glob(drm_path):
                for connector in sorted(os.listdir(card_dir)):
                    if "status" in connector:
                        continue
                    connector_path = os.path.join(card_dir, connector)
                    if os.path.isdir(connector_path):
                        status_path = os.path.join(connector_path, "status")
                        if os.path.exists(status_path):
                            try:
                                with open(status_path) as f:
                                    if f.read().strip() == "connected":
                                        mon: dict[str, Any] = {"connector": connector, "connected": True}
                                        modes_path = os.path.join(connector_path, "modes")
                                        if os.path.exists(modes_path):
                                            with open(modes_path) as f:
                                                modes = f.read().strip().split("\n")
                                                if modes and modes[0]:
                                                    mon["modes"] = modes
                                                    first_mode = modes[0]
                                                    m = re.search(r"(\d+)x(\d+)", first_mode)
                                                    if m:
                                                        mon["current_width"] = int(m.group(1))
                                                        mon["current_height"] = int(m.group(2))
                                        edid_path = os.path.join(connector_path, "edid")
                                        if os.path.exists(edid_path):
                                            try:
                                                with open(edid_path, "rb") as f:
                                                    edid_data = f.read()
                                                if len(edid_data) >= 128:
                                                    mfg_id = ((edid_data[8] & 0x7F) << 8) | (edid_data[9] & 0x7F)
                                                    mfg_str = ""
                                                    for i in range(3):
                                                        c = (mfg_id >> ((2 - i) * 5)) & 0x1F
                                                        mfg_str += chr(ord("A") + c - 1)
                                                    mon["manufacturer"] = mfg_str
                                            except (OSError, PermissionError):
                                                pass
                                        monitors.append(mon)
                            except OSError:
                                pass
        return monitors
