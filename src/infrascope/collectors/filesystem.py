from __future__ import annotations

import os
from typing import Any

import psutil

from infrascope.collectors.base import BaseCollector, CollectorResult
from infrascope.core.dependency import check_binary, run_cmd


class FilesystemCollector(BaseCollector):
    name = "filesystem"
    description = "Filesystem analysis"

    def collect(self) -> CollectorResult:
        data: dict[str, Any] = {}
        mounts: list[dict[str, Any]] = []

        partitions = psutil.disk_partitions()
        for part in partitions:
            mount: dict[str, Any] = {
                "device": part.device,
                "mountpoint": part.mountpoint,
                "fstype": part.fstype,
                "options": part.opts,
            }
            try:
                usage = psutil.disk_usage(part.mountpoint)
                mount["total"] = usage.total
                mount["used"] = usage.used
                mount["free"] = usage.free
                mount["percent_used"] = usage.percent
            except OSError:
                pass
            mount.update(self._get_mount_options(part.mountpoint, part.fstype))
            mounts.append(mount)

        data["mounts"] = mounts
        data["mount_count"] = len(mounts)

        data["fstab"] = self._parse_fstab()

        data["tmpfs"] = self._get_tmpfs_stats()
        data["overlay_stats"] = self._get_overlay_stats()

        return CollectorResult(self.name, data)

    def _get_mount_options(self, mountpoint: str, fstype: str) -> dict[str, Any]:
        info: dict[str, Any] = {
            "compression": False,
            "encryption": False,
            "noatime": False,
            "discard": False,
        }
        mountinfo_path = f"/proc/self/mountinfo"
        try:
            with open(mountinfo_path) as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 5 and parts[4] == mountpoint:
                        opts = parts[5] if len(parts) > 5 else ""
                        info["noatime"] = "noatime" in opts
                        info["discard"] = "discard" in opts
                        if "compress" in opts:
                            info["compression"] = True
                        if "encrypt" in opts:
                            info["encryption"] = True
                        break
        except OSError:
            pass
        return info

    def _parse_fstab(self) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        fstab_path = "/etc/fstab"
        if os.path.exists(fstab_path):
            try:
                with open(fstab_path) as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        parts = line.split()
                        if len(parts) >= 4:
                            entries.append({
                                "device": parts[0],
                                "mountpoint": parts[1],
                                "fstype": parts[2],
                                "options": parts[3],
                            })
            except OSError:
                pass
        return entries

    def _get_tmpfs_stats(self) -> list[dict[str, Any]]:
        stats: list[dict[str, Any]] = []
        tmpfs_mounts = [
            m for m in psutil.disk_partitions() if m.fstype == "tmpfs"
        ]
        for m in tmpfs_mounts:
            try:
                usage = psutil.disk_usage(m.mountpoint)
                stats.append({
                    "mountpoint": m.mountpoint,
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percent": usage.percent,
                })
            except OSError:
                pass
        return stats

    def _get_overlay_stats(self) -> dict[str, Any]:
        stats: dict[str, Any] = {"detected": False, "layers": 0}
        mountinfo = "/proc/self/mountinfo"
        if os.path.exists(mountinfo):
            try:
                with open(mountinfo) as f:
                    for line in f:
                        if "overlay" in line:
                            stats["detected"] = True
                            parts = line.split()
                            for part in parts:
                                if part.startswith("lowerdir="):
                                    stats["layers"] = len(part.split(":"))
                            break
            except OSError:
                pass
        return stats
