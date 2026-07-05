from __future__ import annotations

import os
import re
from typing import Any

from infrascope.collectors.base import BaseCollector, CollectorResult
from infrascope.core.dependency import check_binary, run_cmd


class CoolingCollector(BaseCollector):
    name = "cooling"
    description = "Cooling and thermal information"

    def collect(self) -> CollectorResult:
        data: dict[str, Any] = {}
        data["temperatures"] = self._get_temperatures()
        data["fans"] = self._get_fan_speeds()
        data["thermal_zones"] = self._get_thermal_zones()
        data["cooling_devices"] = self._get_cooling_devices()
        data["throttling_risk"] = self._estimate_throttling_risk(data)
        data["cooling_efficiency"] = self._estimate_cooling_efficiency(data)

        return CollectorResult(self.name, data)

    def _get_temperatures(self) -> list[dict[str, Any]]:
        temps: list[dict[str, Any]] = []
        if check_binary("sensors"):
            output = run_cmd(["sensors", "-u"])
            if output:
                current_chip = ""
                current_feature = ""
                for line in output.split("\n"):
                    if line.startswith("Adapter:"):
                        continue
                    if line.startswith("  "):
                        if ":" in line:
                            key, value = line.split(":", 1)
                            key = key.strip()
                            value = value.strip()
                            if key == "temp1_input":
                                try:
                                    temp_c = float(value)
                                    temps.append({
                                        "chip": current_chip,
                                        "feature": current_feature or f"temp1",
                                        "temperature_c": temp_c,
                                    })
                                except ValueError:
                                    pass
                    else:
                        parts = line.split("-")
                        if len(parts) >= 2:
                            current_chip = line.strip()
                            current_feature = ""
                        elif ":" in line:
                            current_feature = line.split(":")[0].strip()

        if not temps:
            for path in ["/sys/class/thermal/thermal_zone*/temp"]:
                import glob
                for zone_path in glob.glob("/sys/class/thermal/thermal_zone*/temp"):
                    try:
                        with open(zone_path) as f:
                            temp_raw = f.read().strip()
                            temp_c = int(temp_raw) / 1000.0
                        zone_name = ""
                        name_path = zone_path.replace("/temp", "/type")
                        if os.path.exists(name_path):
                            with open(name_path) as f:
                                zone_name = f.read().strip()
                        temps.append({
                            "chip": f"thermal_zone_{zone_path.split('thermal_zone_')[1].split('/')[0]}" if "thermal_zone_" in zone_path else "unknown",
                            "feature": zone_name,
                            "temperature_c": temp_c,
                        })
                    except (OSError, ValueError, IndexError):
                        pass

        # CPU and GPU temps from other sysfs paths
        for hwmon_path in self._find_hwmon_paths():
            name = ""
            try:
                with open(os.path.join(hwmon_path, "name")) as f:
                    name = f.read().strip()
            except OSError:
                continue
            for entry in os.listdir(hwmon_path):
                if entry.startswith("temp") and entry.endswith("_input"):
                    try:
                        with open(os.path.join(hwmon_path, entry)) as f:
                            temp_c = int(f.read().strip()) / 1000.0
                        label_path = os.path.join(hwmon_path, entry.replace("_input", "_label"))
                        label = name
                        if os.path.exists(label_path):
                            with open(label_path) as f:
                                label = f.read().strip()
                        temps.append({
                            "chip": name,
                            "feature": label or f"temp{entry[4:5]}",
                            "temperature_c": temp_c,
                        })
                    except (OSError, ValueError):
                        pass

        return temps

    def _find_hwmon_paths(self) -> list[str]:
        paths: list[str] = []
        base = "/sys/class/hwmon/"
        if os.path.isdir(base):
            for hwmon in sorted(os.listdir(base)):
                hwmon_path = os.path.join(base, hwmon)
                if os.path.isdir(hwmon_path):
                    paths.append(hwmon_path)
        return paths

    def _get_fan_speeds(self) -> list[dict[str, Any]]:
        fans: list[dict[str, Any]] = []
        for hwmon_path in self._find_hwmon_paths():
            try:
                with open(os.path.join(hwmon_path, "name")) as f:
                    name = f.read().strip()
            except OSError:
                continue
            for entry in os.listdir(hwmon_path):
                if entry.startswith("fan") and entry.endswith("_input"):
                    try:
                        with open(os.path.join(hwmon_path, entry)) as f:
                            rpm = int(f.read().strip())
                        label_path = os.path.join(hwmon_path, entry.replace("_input", "_label"))
                        label = name
                        if os.path.exists(label_path):
                            with open(label_path) as f:
                                label = f.read().strip()
                        fans.append({
                            "chip": name,
                            "name": label,
                            "rpm": rpm,
                        })
                    except (OSError, ValueError):
                        pass

        if not fans and check_binary("sensors"):
            output = run_cmd(["sensors"])
            if output:
                for line in output.split("\n"):
                    m = re.search(r"(\d+)\s+RPM", line)
                    if m:
                        fans.append({
                            "chip": "sensors",
                            "name": line.split(":")[0].strip() if ":" in line else "Fan",
                            "rpm": int(m.group(1)),
                        })
        return fans

    def _get_thermal_zones(self) -> list[dict[str, Any]]:
        zones: list[dict[str, Any]] = []
        import glob
        for zone_path in glob.glob("/sys/class/thermal/thermal_zone*"):
            try:
                zone_num = zone_path.split("thermal_zone")[1]
                type_val = ""
                temp_val = 0
                policy = ""
                with open(os.path.join(zone_path, "type")) as f:
                    type_val = f.read().strip()
                with open(os.path.join(zone_path, "temp")) as f:
                    temp_val = int(f.read().strip()) / 1000.0
                policy_path = os.path.join(zone_path, "policy")
                if os.path.exists(policy_path):
                    with open(policy_path) as f:
                        policy = f.read().strip()
                zones.append({
                    "zone": f"thermal_zone{zone_num}",
                    "type": type_val,
                    "temperature_c": temp_val,
                    "policy": policy,
                })
            except (OSError, ValueError, IndexError):
                pass
        return zones

    def _get_cooling_devices(self) -> list[dict[str, Any]]:
        devices: list[dict[str, Any]] = []
        import glob
        for dev_path in glob.glob("/sys/class/thermal/cooling_device*"):
            try:
                dev_num = dev_path.split("cooling_device")[1]
                type_val = ""
                max_state = 0
                cur_state = 0
                with open(os.path.join(dev_path, "type")) as f:
                    type_val = f.read().strip()
                with open(os.path.join(dev_path, "max_state")) as f:
                    max_state = int(f.read().strip())
                with open(os.path.join(dev_path, "cur_state")) as f:
                    cur_state = int(f.read().strip())
                devices.append({
                    "device": f"cooling_device{dev_num}",
                    "type": type_val,
                    "max_state": max_state,
                    "current_state": cur_state,
                })
            except (OSError, ValueError, IndexError):
                pass
        return devices

    def _estimate_throttling_risk(self, data: dict[str, Any]) -> str:
        temps = data.get("temperatures", [])
        max_temp = max((t.get("temperature_c", 0) for t in temps), default=0)
        if max_temp >= 95:
            return "Critical"
        if max_temp >= 85:
            return "High"
        if max_temp >= 75:
            return "Moderate"
        if max_temp >= 60:
            return "Low"
        return "None"

    def _estimate_cooling_efficiency(self, data: dict[str, Any]) -> str:
        risk = data.get("throttling_risk", "None")
        fans = data.get("fans", [])
        if risk == "None" and len(fans) > 0:
            return "Excellent"
        if risk == "Low":
            return "Good"
        if risk == "Moderate":
            return "Adequate"
        if risk == "High":
            return "Poor"
        if risk == "Critical":
            return "Critical"
        return "Unknown"
