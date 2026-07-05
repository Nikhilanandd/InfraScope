from __future__ import annotations

import os
from datetime import datetime
from typing import Any


class HTMLReport:
    def __init__(self, results: dict[str, Any], output_dir: str = "reports"):
        self.results = results
        self.output_dir = output_dir

    def generate(self, filename: str | None = None) -> str:
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"infrascope_report_{timestamp}.html"

        os.makedirs(self.output_dir, exist_ok=True)
        filepath = os.path.join(self.output_dir, filename)

        html = self._build_html()
        with open(filepath, "w") as f:
            f.write(html)

        return filepath

    def _build_html(self) -> str:
        scores = self.results.get("scores", {})
        overall = scores.get("overall", 0)
        rating = scores.get("rating", "N/A")

        color = "#22c55e" if overall >= 70 else ("#eab308" if overall >= 50 else "#ef4444")

        cpu_data = self.results.get("cpu", {}).get("data", {})
        mem_data = self.results.get("memory", {}).get("data", {})
        gpu_data = self.results.get("gpu", {}).get("data", {})
        storage_data = self.results.get("storage", {}).get("data", {})

        cpu_html = ""
        if cpu_data:
            cpu_html = self._table("CPU", [
                ("Model", cpu_data.get("brand", "N/A")),
                ("Cores", f"{cpu_data.get('physical_cores', 0)}P / {cpu_data.get('logical_cores', 0)}L"),
                ("Frequency", f"{cpu_data.get('max_freq', 0) / 1_000_000:.2f} GHz"),
                ("Class", cpu_data.get("class", "N/A")),
            ])

        mem_html = ""
        if mem_data:
            mem_html = self._table("Memory", [
                ("Total", f"{mem_data.get('total', 0) / (1024**3):.1f} GB"),
                ("Type", mem_data.get("ddr_generation", "N/A")),
                ("Frequency", f"{mem_data.get('frequency_mts', 0)} MHz"),
                ("Channels", mem_data.get("channels", {}).get("mode", "N/A")),
            ])

        gpu_html = ""
        gpus = gpu_data.get("gpus", [])
        if gpus:
            g = gpus[0]
            gpu_html = self._table("GPU", [
                ("Model", g.get("model", "N/A")),
                ("VRAM", f"{g.get('vram_total_mb', 0) / 1024:.1f} GB"),
                ("CUDA Cores", str(g.get("cuda_cores", "N/A"))),
            ])

        storage_html = ""
        disks = storage_data.get("disks", [])
        if disks:
            rows = []
            for d in disks:
                rows.append(("{}/{}".format(d.get("name", ""), d.get("disk_type", "N/A")),
                            "{:.1f} GB".format(d.get("size", 0) / (1024**3))))
            storage_html = self._table("Storage", rows)

        workloads = self.results.get("workloads", {})
        workloads_html = ""
        if workloads:
            rows = []
            for name, rating in sorted(workloads.items()):
                rows.append((name.replace("_", " ").title(), rating))
            workloads_html = self._table("Workload Capability", rows)

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>InfraScope Report</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
       background: #0f172a; color: #e2e8f0; padding: 2rem; }}
.container {{ max-width: 1200px; margin: 0 auto; }}
h1 {{ color: #06b6d4; font-size: 2rem; margin-bottom: 0.5rem; }}
h2 {{ color: #38bdf8; margin: 2rem 0 1rem; border-bottom: 1px solid #334155; padding-bottom: 0.5rem; }}
.score {{ font-size: 4rem; font-weight: bold; text-align: center; padding: 2rem; }}
.score-bar {{ height: 20px; background: #1e293b; border-radius: 10px; margin: 1rem 0; overflow: hidden; }}
.score-fill {{ height: 100%; border-radius: 10px; background: {color}; width: {overall}%; }}
.rating {{ text-align: center; font-size: 1.5rem; color: {color}; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1rem; }}
.card {{ background: #1e293b; border-radius: 8px; padding: 1.5rem; border: 1px solid #334155; }}
.card h3 {{ color: #38bdf8; margin-bottom: 1rem; }}
table {{ width: 100%; border-collapse: collapse; }}
td {{ padding: 0.5rem; border-bottom: 1px solid #334155; }}
td:first-child {{ color: #94a3b8; font-weight: 500; }}
td:last-child {{ text-align: right; }}
.meta {{ color: #64748b; font-size: 0.875rem; text-align: center; margin-top: 2rem; }}
</style>
</head>
<body>
<div class="container">
  <h1>InfraScope Hardware Report</h1>
  <p style="color: #94a3b8;">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
  <div class="score">{overall}/100</div>
  <div class="score-bar"><div class="score-fill"></div></div>
  <div class="rating">{rating}</div>
  <h2>Component Scores</h2>
  <div class="grid">
    <div class="card"><h3>CPU</h3><div style="font-size:2rem;color:{"#22c55e" if scores.get("cpu", 0)>=70 else "#eab308" if scores.get("cpu", 0)>=50 else "#ef4444"}">{scores.get("cpu", 0)}/100</div></div>
    <div class="card"><h3>Memory</h3><div style="font-size:2rem;color:{"#22c55e" if scores.get("memory", 0)>=70 else "#eab308" if scores.get("memory", 0)>=50 else "#ef4444"}">{scores.get("memory", 0)}/100</div></div>
    <div class="card"><h3>GPU</h3><div style="font-size:2rem;color:{"#22c55e" if scores.get("gpu", 0)>=70 else "#eab308" if scores.get("gpu", 0)>=50 else "#ef4444"}">{scores.get("gpu", 0)}/100</div></div>
    <div class="card"><h3>Storage</h3><div style="font-size:2rem;color:{"#22c55e" if scores.get("storage", 0)>=70 else "#eab308" if scores.get("storage", 0)>=50 else "#ef4444"}">{scores.get("storage", 0)}/100</div></div>
  </div>
  <h2>Hardware</h2>
  <div class="grid">
    {cpu_html}
    {mem_html}
    {gpu_html}
    {storage_html}
  </div>
  {self._bottlenecks_section()}
  <h2>Workload Capability</h2>
  <div class="grid">{workloads_html}</div>
  <div class="meta">Report generated by InfraScope v1.0.0</div>
</div>
</body>
</html>"""

    def _table(self, title: str, rows: list[tuple[str, str]]) -> str:
        trs = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in rows)
        return f'<div class="card"><h3>{title}</h3><table>{trs}</table></div>'

    def _bottlenecks_section(self) -> str:
        bottlenecks = self.results.get("bottlenecks", {})
        critical = bottlenecks.get("critical", [])
        if not critical:
            return ""
        items = "".join(
            f"<li style='color:#ef4444'>{bottlenecks.get(comp, {}).get('details', ['No details'])[0]}</li>"
            for comp in critical
        )
        return f"<h2>Bottlenecks</h2><ul style='background:#1e293b;padding:1rem 2rem;border-radius:8px;'>{items}</ul>"
