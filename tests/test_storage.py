from __future__ import annotations

import pytest
from infrascope.collectors.storage import StorageCollector


class TestStorageCollector:
    def setup_method(self):
        self.collector = StorageCollector()

    def test_collector_name(self):
        assert self.collector.name == "storage"

    def test_collector_returns_result(self):
        result = self.collector.run()
        assert result.name == "storage"
        assert result.success

    def test_disk_detection(self):
        result = self.collector.run()
        disks = result.data.get("disks", [])
        assert len(disks) > 0

    def test_disk_has_name(self):
        result = self.collector.run()
        for disk in result.data.get("disks", []):
            assert "name" in disk

    def test_disk_has_size(self):
        result = self.collector.run()
        for disk in result.data.get("disks", []):
            assert disk.get("size", 0) > 0

    def test_partitions(self):
        result = self.collector.run()
        partitions = result.data.get("partitions", [])
        assert len(partitions) > 0

    def test_disk_usage(self):
        result = self.collector.run()
        usage = result.data.get("disk_usage", {})
        assert len(usage) > 0
