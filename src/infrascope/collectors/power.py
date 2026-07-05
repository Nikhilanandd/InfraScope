from __future__ import annotations

import os
from typing import Any

from infrascope.collectors.base import BaseCollector, CollectorResult
from infrascope.core.dependency import check_binary, run_cmd


class PowerCollector(BaseCollector):
    name = "power"
    description = "Power supply and power management information"

    def collect(self) -> CollectorResult:
        data: dict[str, Any] = {}
        data["ac_adapter"] = self._get_ac_adapter()
        data["batteries"] = self._get_batteries()
        data["power_supplies"] = self._get_power_supplies()
        data["governors"] = self._get_cpu_governors()
        data["energy_info"] = self._get_energy_info()
        return CollectorResult(self.name, data)

    def _get_ac_adapter(self) -> dict[str, Any]:
        info: dict[str, Any] = {"connected": False, "online": False}
        for ac_path in ["/sys/class/power_supply/AC*/online", "/sys/class/power_supply/ADP*/online"]:
            import glob
            for path in glob.glob(ac_path):
                try:
                    with open(path) as f:
                        info["online"] = f.read().strip() == "1"
                    info["connected"] = True
                    break
                except OSError:
                    pass
        return info

    def _get_batteries(self) -> list[dict[str, Any]]:
        batteries: list[dict[str, Any]] = []
        import glob
        for bat_path in glob.glob("/sys/class/power_supply/BAT*"):
            bat: dict[str, Any] = {}
            try:
                with open(os.path.join(bat_path, "capacity")) as f:
                    bat["capacity_pct"] = int(f.read().strip())
            except (OSError, ValueError):
                pass
            try:
                with open(os.path.join(bat_path, "energy_full")) as f:
                    bat["energy_full_uw"] = int(f.read().strip())
            except (OSError, ValueError):
                pass
            try:
                with open(os.path.join(bat_path, "energy_now")) as f:
                    bat["energy_now_uw"] = int(f.read().strip())
            except (OSError, ValueError):
                pass
            try:
                with open(os.path.join(bat_path, "voltage_now")) as f:
                    bat["voltage_uv"] = int(f.read().strip())
            except (OSError, ValueError):
                pass
            try:
                with open(os.path.join(bat_path, "status")) as f:
                    bat["status"] = f.read().strip()
            except OSError:
                pass
            try:
                with open(os.path.join(bat_path, "model_name")) as f:
                    bat["model"] = f.read().strip()
            except OSError:
                pass
            try:
                with open(os.path.join(bat_path, "manufacturer")) as f:
                    bat["manufacturer"] = f.read().strip()
            except OSError:
                pass
            try:
                with open(os.path.join(bat_path, "technology")) as f:
                    bat["technology"] = f.read().strip()
            except OSError:
                pass
            if bat:
                batteries.append(bat)
        return batteries

    def _get_power_supplies(self) -> list[dict[str, Any]]:
        supplies: list[dict[str, Any]] = []
        import glob
        for ps_path in glob.glob("/sys/class/power_supply/*"):
            name = os.path.basename(ps_path)
            if name.startswith(("AC", "ADP", "BAT")):
                continue
            info: dict[str, Any] = {"name": name}
            try:
                with open(os.path.join(ps_path, "type")) as f:
                    info["type"] = f.read().strip()
            except OSError:
                pass
            try:
                with open(os.path.join(ps_path, "power_now")) as f:
                    info["power_uw"] = int(f.read().strip())
            except (OSError, ValueError):
                pass
            try:
                with open(os.path.join(ps_path, "status")) as f:
                    info["status"] = f.read().strip()
            except OSError:
                pass
            supplies.append(info)
        return supplies

    def _get_cpu_governors(self) -> dict[str, Any]:
        governors: dict[str, Any] = {"current": "", "available": [], "driver": ""}
        try:
            with open("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor") as f:
                governors["current"] = f.read().strip()
        except OSError:
            pass
        try:
            path = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_available_governors"
            with open(path) as f:
                governors["available"] = f.read().strip().split()
        except OSError:
            pass
        try:
            with open("/sys/devices/system/cpu/cpu0/cpufreq/scaling_driver") as f:
                governors["driver"] = f.read().strip()
        except OSError:
            pass
        return governors

    def _get_energy_info(self) -> dict[str, Any]:
        info: dict[str, Any] = {}
        try:
            with open("/sys/class/powercap/intel-rapl/intel-rapl:0/energy_uj") as f:
                info["energy_uj"] = int(f.read().strip())
        except OSError:
            pass
        try:
            with open("/sys/class/powercap/intel-rapl/intel-rapl:0/name") as f:
                info["rapl_domain"] = f.read().strip()
        except OSError:
            pass
        return info
