from __future__ import annotations

import os
import re
from typing import Any

from infrascope.collectors.base import BaseCollector, CollectorResult
from infrascope.core.dependency import check_binary, run_cmd


class AudioCollector(BaseCollector):
    name = "audio"
    description = "Audio device information"

    def collect(self) -> CollectorResult:
        data: dict[str, Any] = {}
        devices: list[dict[str, Any]] = []

        if check_binary("aplay"):
            output = run_cmd(["aplay", "-l"])
            if output:
                for line in output.split("\n"):
                    m = re.match(r"card\s+(\d+):\s+(.*?)\s*\[(.*?)\]\s*,\s*device\s+(\d+):\s+(.*?)\s*\[(.*?)\]", line)
                    if m:
                        devices.append({
                            "card": int(m.group(1)),
                            "card_name": m.group(3),
                            "device": int(m.group(4)),
                            "device_name": m.group(6),
                            "type": "output",
                        })

        if check_binary("arecord"):
            output = run_cmd(["arecord", "-l"])
            if output:
                for line in output.split("\n"):
                    m = re.match(r"card\s+(\d+):\s+(.*?)\s*\[(.*?)\]\s*,\s*device\s+(\d+):\s+(.*?)\s*\[(.*?)\]", line)
                    if m:
                        devices.append({
                            "card": int(m.group(1)),
                            "card_name": m.group(3),
                            "device": int(m.group(4)),
                            "device_name": m.group(6),
                            "type": "input",
                        })

        # Get audio devices from ALSA
        if not devices and os.path.isdir("/proc/asound"):
            try:
                for card_dir in sorted(os.listdir("/proc/asound")):
                    if card_dir.startswith("card"):
                        card_id_path = os.path.join("/proc/asound", card_dir, "id")
                        if os.path.exists(card_id_path):
                            with open(card_id_path) as f:
                                card_name = f.read().strip()
                            devices.append({
                                "card_name": card_name,
                                "card_dir": card_dir,
                                "type": "unknown",
                            })
            except OSError:
                pass

        # Get HDMI and USB audio from PCI/USB
        lspci_output = run_cmd(["lspci", "-nnk"])
        if lspci_output:
            for block in lspci_output.split("\n\n"):
                if "Audio" in block or "HDMI" in block or "USB Audio" in block or "HDA" in block:
                    lines = block.strip().split("\n")
                    if lines:
                        audio_dev: dict[str, Any] = {"source": "PCI"}
                        first_line = lines[0]
                        audio_dev["pci_id"] = first_line.split()[0] if first_line else ""
                        rest = " ".join(first_line.split()[1:])
                        audio_dev["description"] = re.sub(r"\s*\[.*?\]\s*", " ", rest).strip()
                        for line in lines[1:]:
                            if "Kernel driver in use" in line:
                                audio_dev["driver"] = line.split(":")[1].strip() if ":" in line else ""
                        if not any(d.get("description") == audio_dev.get("description") for d in devices):
                            devices.append(audio_dev)

        # Detect HDMI audio
        hdmi_output = run_cmd(["ls", "-d", "/sys/class/drm/*/audio"])
        if hdmi_output:
            for audio_dev in devices:
                if "HDMI" in audio_dev.get("description", "").upper() or "HDMI" in audio_dev.get("card_name", "").upper():
                    audio_dev["hdmi"] = True

        # Detect USB audio
        for audio_dev in devices:
            desc = audio_dev.get("description", "").upper()
            card = audio_dev.get("card_name", "").upper()
            if "USB" in desc or "USB" in card:
                audio_dev["usb_audio"] = True

        data["devices"] = devices
        data["device_count"] = len(devices)
        data["has_hdmi_audio"] = any(d.get("hdmi") for d in devices)
        data["has_usb_audio"] = any(d.get("usb_audio") for d in devices)
        data["codecs"] = self._get_codecs()

        return CollectorResult(self.name, data)

    def _get_codecs(self) -> list[str]:
        codecs: list[str] = []
        if os.path.isdir("/proc/asound"):
            for card_dir in sorted(os.listdir("/proc/asound")):
                if card_dir.startswith("card"):
                    codec_path = os.path.join("/proc/asound", card_dir, "codec#0")
                    if os.path.exists(codec_path):
                        try:
                            with open(codec_path) as f:
                                for line in f:
                                    m = re.match(r"Codec:\s*(.+)", line)
                                    if m:
                                        codec = m.group(1).strip()
                                        if codec not in codecs:
                                            codecs.append(codec)
                        except OSError:
                            pass
        return codecs
