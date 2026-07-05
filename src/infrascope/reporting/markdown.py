from __future__ import annotations

import os
from datetime import datetime
from typing import Any


class MarkdownReport:
    def __init__(self, results: dict[str, Any], output_dir: str = "reports"):
        self.results = results
        self.output_dir = output_dir

    def generate(self, filename: str | None = None) -> str:
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"infrascope_report_{timestamp}.md"

        os.makedirs(self.output_dir, exist_ok=True)
        filepath = os.path.join(self.output_dir, filename)

        content = self._build_content()
        with open(filepath, "w") as f:
            f.write(content)

        return filepath

    def _build_content(self) -> str:
        lines: list[str] = []
        lines.append("# InfraScope Hardware Report")
        lines.append(f"\n*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        lines.append("\n---\n")

        lines.append("## System Summary\n")
        scores = self.results.get("scores", {})
        lines.append(f"- **Overall Score**: {scores.get('overall', 'N/A')}/100")
        lines.append(f"- **Rating**: {scores.get('rating', 'N/A')}")
        lines.append(f"- **CPU**: {scores.get('cpu', 'N/A')}/100")
        lines.append(f"- **Memory**: {scores.get('memory', 'N/A')}/100")
        lines.append(f"- **GPU**: {scores.get('gpu', 'N/A')}/100")
        lines.append(f"- **Storage**: {scores.get('storage', 'N/A')}/100")
        lines.append(f"- **Network**: {scores.get('networking', 'N/A')}/100")
        lines.append(f"- **Thermals**: {scores.get('thermals', 'N/A')}/100")

        lines.append("\n---\n")

        cpu = self.results.get("cpu", {}).get("data", {})
        if cpu:
            lines.append("## CPU\n")
            lines.append(f"| Property | Value |")
            lines.append(f"| --- | --- |")
            lines.append(f"| Model | {cpu.get('brand', 'N/A')} |")
            lines.append(f"| Vendor | {cpu.get('vendor', 'N/A')} |")
            lines.append(f"| Architecture | {cpu.get('arch', 'N/A')} |")
            lines.append(f"| Class | {cpu.get('class', 'N/A')} |")
            lines.append(f"| Physical Cores | {cpu.get('physical_cores', 'N/A')} |")
            lines.append(f"| Logical Cores | {cpu.get('logical_cores', 'N/A')} |")
            lines.append(f"| Base Clock | {cpu.get('base_freq', 0) / 1_000_000:.2f} GHz |")
            lines.append(f"| Max Clock | {cpu.get('max_freq', 0) / 1_000_000:.2f} GHz |")
            lines.append(f"| SMT | {'Enabled' if cpu.get('smt_enabled') else 'Disabled'} |")
            lines.append(f"| L3 Cache | {cpu.get('l3_cache', 'N/A')} |")

        mem = self.results.get("memory", {}).get("data", {})
        if mem:
            lines.append("\n## Memory\n")
            total_gb = mem.get("total", 0) / (1024**3)
            lines.append(f"| Property | Value |")
            lines.append(f"| --- | --- |")
            lines.append(f"| Total RAM | {total_gb:.1f} GB |")
            lines.append(f"| Type | {mem.get('ddr_generation', 'N/A')} |")
            lines.append(f"| Frequency | {mem.get('frequency_mts', 0)} MHz |")
            lines.append(f"| ECC | {'Yes' if mem.get('ecc') else 'No'} |")
            lines.append(f"| Channels | {mem.get('channels', {}).get('mode', 'N/A')} |")
            lines.append(f"| Slots | {mem.get('slot_population', 'N/A')} |")

        gpu_data = self.results.get("gpu", {}).get("data", {})
        gpus = gpu_data.get("gpus", [])
        if gpus:
            lines.append("\n## GPU\n")
            for i, g in enumerate(gpus):
                lines.append(f"\n### GPU {i+1}: {g.get('model', 'Unknown')}")
                lines.append(f"| Property | Value |")
                lines.append(f"| --- | --- |")
                lines.append(f"| Vendor | {g.get('vendor', 'N/A')} |")
                lines.append(f"| VRAM | {g.get('vram_total_mb', 0) / 1024:.1f} GB |")
                lines.append(f"| CUDA Cores | {g.get('cuda_cores', 'N/A')} |")
                lines.append(f"| Tensor Cores | {g.get('tensor_cores', 'N/A')} |")
                lines.append(f"| Temperature | {g.get('temperature_c', 'N/A')} °C |")

        storage = self.results.get("storage", {}).get("data", {})
        disks = storage.get("disks", [])
        if disks:
            lines.append("\n## Storage\n")
            for disk in disks:
                size_gb = disk.get("size", 0) / (1024**3)
                lines.append(f"\n### /dev/{disk.get('name', '')}")
                lines.append(f"| Property | Value |")
                lines.append(f"| --- | --- |")
                lines.append(f"| Type | {disk.get('disk_type', 'N/A')} |")
                lines.append(f"| Size | {size_gb:.1f} GB |")
                lines.append(f"| SMART | {disk.get('smart_status', 'N/A')} |")
                if disk.get("remaining_life_pct"):
                    lines.append(f"| Life Remaining | {disk['remaining_life_pct']}% |")

        bottlenecks = self.results.get("bottlenecks", {})
        critical = bottlenecks.get("critical", [])
        if critical:
            lines.append("\n## Bottlenecks\n")
            for comp in critical:
                info = bottlenecks.get(comp, {})
                for detail in info.get("details", []):
                    lines.append(f"- **{comp.title()}**: {detail}")

        upgrades = self.results.get("upgrades", {})
        has_upgrades = any(u.get("needed") for u in upgrades.values())
        if has_upgrades:
            lines.append("\n## Recommended Upgrades\n")
            for comp, suggestion in upgrades.items():
                if suggestion.get("needed"):
                    lines.append(f"\n### {comp.upper()}")
                    lines.append(f"- Priority: {suggestion.get('priority', 'N/A')}")
                    for imp in suggestion.get("improvements", []):
                        lines.append(f"  - {imp}")

        workloads = self.results.get("workloads", {})
        if workloads:
            lines.append("\n## Workload Capability\n")
            lines.append("| Workload | Rating |")
            lines.append("| --- | --- |")
            for name, rating in sorted(workloads.items()):
                lines.append(f"| {name.replace('_', ' ').title()} | {rating} |")

        lines.append("\n---\n")
        lines.append("*Report generated by InfraScope v1.0.0*")

        return "\n".join(lines)
