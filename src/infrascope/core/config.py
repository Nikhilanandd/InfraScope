from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


CONFIG_DIRS = [
    Path.home() / ".config" / "infrascope",
    Path("/etc/infrascope"),
    Path.cwd() / ".infrascope",
]

CONFIG_FILE = "config.json"


class Config:
    """InfraScope configuration manager."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {
            "reports_dir": "reports",
            "benchmarks_dir": "benchmarks",
            "templates_dir": "templates",
            "color_output": True,
            "show_progress": True,
            "benchmark_iterations": 3,
            "timeout_seconds": 30,
            "log_level": "INFO",
        }
        self._loaded = False
        self.load()

    @property
    def reports_dir(self) -> Path:
        return Path(self._data.get("reports_dir", "reports"))

    @property
    def benchmarks_dir(self) -> Path:
        return Path(self._data.get("benchmarks_dir", "benchmarks"))

    @property
    def templates_dir(self) -> Path:
        return Path(self._data.get("templates_dir", "templates"))

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def load(self) -> None:
        for config_dir in CONFIG_DIRS:
            config_path = config_dir / CONFIG_FILE
            if config_path.exists():
                try:
                    with open(config_path) as f:
                        self._data.update(json.load(f))
                    self._loaded = True
                    break
                except (json.JSONDecodeError, OSError):
                    continue
        self._ensure_dirs()

    def save(self, path: Path | None = None) -> None:
        if path is None:
            path = CONFIG_DIRS[0] / CONFIG_FILE
            path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self._data, f, indent=2)

    def _ensure_dirs(self) -> None:
        for key in ("reports_dir", "benchmarks_dir"):
            path = Path(self._data.get(key, key.split("_")[0]))
            path.mkdir(parents=True, exist_ok=True)

    def to_dict(self) -> dict[str, Any]:
        return dict(self._data)
