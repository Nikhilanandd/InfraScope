from __future__ import annotations

import math
import time
from typing import Any

from infrascope.core.dependency import check_binary, run_cmd


class BenchmarkEngine:
    def __init__(self, iterations: int = 3):
        self.iterations = max(1, iterations)

    def run_cpu_benchmark(self) -> dict[str, Any]:
        results: dict[str, Any] = {}
        results["single_core"] = self._benchmark_single_core()
        results["multi_core"] = self._benchmark_multi_core()
        results["integer"] = self._benchmark_integer()
        results["float"] = self._benchmark_float()
        results["compression"] = self._benchmark_compression()
        results["encryption"] = self._benchmark_encryption()
        results["overall_score"] = self._calculate_overall_cpu_score(results)
        return results

    def _benchmark_single_core(self) -> float:
        scores = []
        for _ in range(self.iterations):
            start = time.perf_counter()
            result = 0
            for i in range(1_000_000):
                result += math.sin(i) * math.cos(i) + math.sqrt(i)
            elapsed = time.perf_counter() - start
            score = 1_000_000 / elapsed
            scores.append(score)
        return sum(scores) / len(scores)

    def _benchmark_multi_core(self) -> float:
        import multiprocessing
        scores = []
        for _ in range(min(self.iterations, 2)):
            start = time.perf_counter()
            with multiprocessing.Pool() as pool:
                results = pool.map(self._worker_task, range(500_000))
            elapsed = time.perf_counter() - start
            score = 500_000 / elapsed
            scores.append(score)
        return sum(scores) / len(scores) if scores else 0

    @staticmethod
    def _worker_task(n: int) -> float:
        result = 0.0
        for i in range(1000):
            result += math.sin(i * n) * math.cos(i) + math.sqrt(i + n)
        return result

    def _benchmark_integer(self) -> float:
        scores = []
        for _ in range(self.iterations):
            start = time.perf_counter()
            result = 0
            for i in range(5_000_000):
                result += (i * 7 + 13) % 256
                result ^= i << 2
                result &= 0xFFFFFFFF
            elapsed = time.perf_counter() - start
            score = 5_000_000 / elapsed
            scores.append(score)
        return sum(scores) / len(scores)

    def _benchmark_float(self) -> float:
        scores = []
        for _ in range(self.iterations):
            start = time.perf_counter()
            result = 0.0
            for i in range(2_000_000):
                result += math.sin(i * 0.001) * math.cos(i * 0.002)
                result += math.sqrt(i * 0.5) * math.exp(math.sin(i * 0.001))
            elapsed = time.perf_counter() - start
            score = 2_000_000 / elapsed
            scores.append(score)
        return sum(scores) / len(scores)

    def _benchmark_compression(self) -> float:
        import zlib
        import random
        data = bytes(random.randint(0, 255) for _ in range(10_000_000))
        scores = []
        for _ in range(self.iterations):
            start = time.perf_counter()
            compressed = zlib.compress(data, level=6)
            _ = zlib.decompress(compressed)
            elapsed = time.perf_counter() - start
            score = 20_000_000 / elapsed
            scores.append(score)
        return sum(scores) / len(scores)

    def _benchmark_encryption(self) -> float:
        import hashlib
        scores = []
        data = b"Benchmark data for InfraScope encryption test " * 10000
        for _ in range(self.iterations):
            start = time.perf_counter()
            for _ in range(100):
                hashlib.sha256(data).digest()
                hashlib.sha512(data).digest()
                hashlib.blake2b(data).digest()
            elapsed = time.perf_counter() - start
            score = 300 / elapsed
            scores.append(score)
        return sum(scores) / len(scores)

    def _calculate_overall_cpu_score(self, results: dict[str, Any]) -> float:
        base = 1000.0
        weights = {
            "single_core": 0.20,
            "multi_core": 0.30,
            "integer": 0.15,
            "float": 0.15,
            "compression": 0.10,
            "encryption": 0.10,
        }
        score = 0.0
        for key, weight in weights.items():
            val = results.get(key, 0)
            score += (val / base) * weight
        return score * 100

    def estimate_relative_performance(self, score: float) -> dict[str, str]:
        estimates: dict[str, str] = {}
        thresholds = [
            ("Ryzen 5 5600X", 850, 1050),
            ("Ryzen 7 5800X", 1050, 1300),
            ("Ryzen 9 5950X", 1300, 1600),
            ("Intel i5-13600K", 1000, 1250),
            ("Intel i7-13700K", 1250, 1500),
            ("Intel i9-13900K", 1500, 1800),
            ("Xeon Gold 6438M", 1800, 2200),
            ("EPYC 9654", 2200, 3000),
        ]
        for name, low, high in thresholds:
            if low <= score <= high:
                estimates[name] = "Comparable"
            elif score < low:
                ratio = score / low * 100
                estimates[name] = f"{ratio:.0f}%"
            else:
                ratio = score / high * 100
                estimates[name] = f"{ratio:.0f}%+"
        return estimates

    def run_storage_benchmark(self, device: str = "") -> dict[str, Any]:
        results: dict[str, Any] = {
            "sequential_read": 0,
            "sequential_write": 0,
            "random_read_iops": 0,
            "random_write_iops": 0,
        }
        if not check_binary("fio"):
            return self._estimate_storage_performance()
        return self._run_fio_benchmark(device)

    def _run_fio_benchmark(self, device: str = "") -> dict[str, Any]:
        results: dict[str, Any] = {}
        test_file = "/tmp/infrascope_fio_test" if not device else device

        try:
            seq_read = run_cmd([
                "fio", "--name=seq_read", f"--filename={test_file}",
                "--size=1G", "--rw=read", "--bs=1M", "--direct=1",
                "--iodepth=64", "--runtime=10", "--numjobs=1",
                "--output-format=json", "--group_reporting",
            ], timeout=30)
            if seq_read:
                import json
                data = json.loads(seq_read)
                jobs = data.get("jobs", [{}])
                if jobs:
                    results["sequential_read"] = jobs[0].get("read", {}).get("bw_bytes", 0)
                    results["sequential_read_iops"] = jobs[0].get("read", {}).get("iops", 0)
        except Exception:
            results["sequential_read"] = 0

        try:
            seq_write = run_cmd([
                "fio", "--name=seq_write", f"--filename={test_file}",
                "--size=1G", "--rw=write", "--bs=1M", "--direct=1",
                "--iodepth=64", "--runtime=10", "--numjobs=1",
                "--output-format=json", "--group_reporting",
            ], timeout=30)
            if seq_write:
                import json
                data = json.loads(seq_write)
                jobs = data.get("jobs", [{}])
                if jobs:
                    results["sequential_write"] = jobs[0].get("write", {}).get("bw_bytes", 0)
                    results["sequential_write_iops"] = jobs[0].get("write", {}).get("iops", 0)
        except Exception:
            results["sequential_write"] = 0

        try:
            rand_read = run_cmd([
                "fio", "--name=rand_read", f"--filename={test_file}",
                "--size=1G", "--rw=randread", "--bs=4K", "--direct=1",
                "--iodepth=32", "--runtime=10", "--numjobs=4",
                "--output-format=json", "--group_reporting",
            ], timeout=30)
            if rand_read:
                import json
                data = json.loads(rand_read)
                jobs = data.get("jobs", [{}])
                if jobs:
                    results["random_read_iops"] = jobs[0].get("read", {}).get("iops", 0)
                    results["random_read_bw"] = jobs[0].get("read", {}).get("bw_bytes", 0)
        except Exception:
            results["random_read_iops"] = 0

        try:
            rand_write = run_cmd([
                "fio", "--name=rand_write", f"--filename={test_file}",
                "--size=1G", "--rw=randwrite", "--bs=4K", "--direct=1",
                "--iodepth=32", "--runtime=10", "--numjobs=4",
                "--output-format=json", "--group_reporting",
            ], timeout=30)
            if rand_write:
                import json
                data = json.loads(rand_write)
                jobs = data.get("jobs", [{}])
                if jobs:
                    results["random_write_iops"] = jobs[0].get("write", {}).get("iops", 0)
                    results["random_write_bw"] = jobs[0].get("write", {}).get("bw_bytes", 0)
        except Exception:
            results["random_write_iops"] = 0

        # Cleanup
        if not device:
            run_cmd(["rm", "-f", test_file])

        return results

    def _estimate_storage_performance(self) -> dict[str, Any]:
        import psutil
        results: dict[str, Any] = {
            "sequential_read": 0,
            "sequential_write": 0,
            "random_read_iops": 0,
            "random_write_iops": 0,
            "estimated": True,
        }
        try:
            io_counters = psutil.disk_io_counters()
            if io_counters:
                results["read_bytes"] = io_counters.read_bytes
                results["write_bytes"] = io_counters.write_bytes
        except Exception:
            pass
        return results

    def run_network_benchmark(self, target: str = "localhost", port: int = 5201) -> dict[str, Any]:
        results: dict[str, Any] = {"bandwidth_mbps": 0, "latency_ms": 0}
        if check_binary("iperf3"):
            output = run_cmd([
                "iperf3", "-c", target, "-p", str(port),
                "-f", "m", "-O", "2", "-t", "5", "--json",
            ], timeout=15)
            if output:
                try:
                    import json
                    data = json.loads(output)
                    end = data.get("end", {})
                    streams = end.get("sum_received", end.get("sum", {}))
                    results["bandwidth_mbps"] = streams.get("bits_per_second", 0) / 1_000_000
                except (json.JSONDecodeError, AttributeError):
                    pass
        return results

    def run_memory_benchmark(self) -> dict[str, Any]:
        results: dict[str, Any] = {"bandwidth_mb_s": 0, "latency_ns": 0}
        import array
        import time

        size = 256 * 1024 * 1024
        try:
            arr = array.array("Q", [0]) * (size // 8)
            start = time.perf_counter()
            for i in range(len(arr)):
                arr[i] = i
            elapsed = time.perf_counter() - start
            results["bandwidth_mb_s"] = (size / (1024 * 1024)) / elapsed if elapsed > 0 else 0

            start = time.perf_counter()
            for _ in range(1000):
                _ = arr[0]
            latency = (time.perf_counter() - start) / 1000 * 1_000_000_000
            results["latency_ns"] = latency
        except (MemoryError, Exception):
            pass
        return results
