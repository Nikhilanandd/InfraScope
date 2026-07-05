from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

from infrascope import __version__, __app_name__
from infrascope.collectors.base import CollectorRegistry
from infrascope.collectors.cpu import CPUCollector
from infrascope.collectors.memory import MemoryCollector
from infrascope.collectors.gpu import GPUCollector
from infrascope.collectors.storage import StorageCollector
from infrascope.collectors.network import NetworkCollector
from infrascope.collectors.motherboard import MotherboardCollector
from infrascope.collectors.cooling import CoolingCollector
from infrascope.collectors.power import PowerCollector
from infrascope.collectors.usb import USBCollector
from infrascope.collectors.pci import PCICollector
from infrascope.collectors.monitors import MonitorsCollector
from infrascope.collectors.audio import AudioCollector
from infrascope.collectors.virtualization import VirtualizationCollector
from infrascope.collectors.filesystem import FilesystemCollector
from infrascope.analyzers.scoring import ScoringAnalyzer
from infrascope.analyzers.bottlenecks import BottleneckDetector
from infrascope.analyzers.upgrades import UpgradeAdvisor
from infrascope.analyzers.workloads import WorkloadAnalyzer
from infrascope.analyzers.comparisons import ComparisonAnalyzer
from infrascope.analyzers.benchmark import BenchmarkEngine
from infrascope.reporting.terminal import TerminalReport
from infrascope.reporting.markdown import MarkdownReport
from infrascope.reporting.json_report import JSONReport
from infrascope.reporting.html_report import HTMLReport
from infrascope.reporting.csv_report import CSVReport
from infrascope.core.dependency import check_dependencies, print_dependency_report
from infrascope.core.config import Config
from infrascope.utils.system import get_os_info, get_uptime, get_load_average

console = Console()
config = Config()

app = typer.Typer(
    name="infrascope",
    help="Advanced Linux System Hardware & Performance Analyzer",
    add_completion=True,
    rich_markup_mode="rich",
)

collector_registry = CollectorRegistry()
collector_registry.register(CPUCollector())
collector_registry.register(MemoryCollector())
collector_registry.register(GPUCollector())
collector_registry.register(StorageCollector())
collector_registry.register(NetworkCollector())
collector_registry.register(MotherboardCollector())
collector_registry.register(CoolingCollector())
collector_registry.register(PowerCollector())
collector_registry.register(USBCollector())
collector_registry.register(PCICollector())
collector_registry.register(MonitorsCollector())
collector_registry.register(AudioCollector())
collector_registry.register(VirtualizationCollector())
collector_registry.register(FilesystemCollector())


def _run_collectors(names: list[str] | None = None) -> dict:
    results = {}
    collectors_to_run = names if names else collector_registry.available
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Scanning hardware...", total=len(collectors_to_run))
        for name in collectors_to_run:
            progress.update(task, description=f"[cyan]Collecting {name}...")
            collector = collector_registry.get(name)
            if collector:
                result = collector.run()
                results[name] = result.to_dict()
            progress.advance(task)
        progress.update(task, description="[green]Hardware scan complete!")
    return results


def _analyze_results(results: dict) -> dict:
    analysis = {}

    scorer = ScoringAnalyzer(results)
    scores = scorer.calculate_all()
    analysis["scores"] = scores.get("scores", {})
    analysis["scores"]["rating"] = scores.get("rating", "")

    bottleneck = BottleneckDetector(results)
    analysis["bottlenecks"] = bottleneck.detect_all()

    upgrade = UpgradeAdvisor(results)
    analysis["upgrades"] = upgrade.analyze_all()

    workload = WorkloadAnalyzer(results)
    analysis["workloads"] = workload.analyze_all()

    compare = ComparisonAnalyzer(results)
    analysis["comparisons"] = compare.compare_all()

    return analysis


def _full_scan() -> dict:
    collector_results = _run_collectors()
    analysis = _analyze_results(collector_results)
    collector_results.update(analysis)
    return collector_results


@app.command()
def scan() -> None:
    """Run a comprehensive hardware scan."""
    results = _full_scan()
    report = TerminalReport(results)
    report.display_header()
    report.display_summary()
    report.display_cpu()
    report.display_memory()
    report.display_gpu()
    report.display_storage()
    report.display_network()
    report.display_temperatures()


@app.command()
def full() -> None:
    """Display a complete system analysis report."""
    results = _full_scan()
    report = TerminalReport(results)
    report.display_full_report()


@app.command()
def cpu() -> None:
    """Display CPU information."""
    results = _run_collectors(["cpu"])
    analysis = _analyze_results(results)
    results.update(analysis)
    report = TerminalReport(results)
    report.display_header()
    report.display_cpu()


@app.command()
def ram() -> None:
    """Display memory/RAM information."""
    results = _run_collectors(["memory"])
    analysis = _analyze_results(results)
    results.update(analysis)
    report = TerminalReport(results)
    report.display_header()
    report.display_memory()


@app.command()
def gpu() -> None:
    """Display GPU information."""
    results = _run_collectors(["gpu"])
    analysis = _analyze_results(results)
    results.update(analysis)
    report = TerminalReport(results)
    report.display_header()
    report.display_gpu()


@app.command()
def storage() -> None:
    """Display storage device information."""
    results = _run_collectors(["storage"])
    analysis = _analyze_results(results)
    results.update(analysis)
    report = TerminalReport(results)
    report.display_header()
    report.display_storage()


@app.command()
def network() -> None:
    """Display network interface information."""
    results = _run_collectors(["network"])
    analysis = _analyze_results(results)
    results.update(analysis)
    report = TerminalReport(results)
    report.display_header()
    report.display_network()


@app.command()
def benchmark() -> None:
    """Run performance benchmarks."""
    engine = BenchmarkEngine(iterations=config.get("benchmark_iterations", 3))
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[yellow]Running benchmarks...", total=4)
        progress.update(task, description="[yellow]CPU benchmark...")
        cpu_scores = engine.run_cpu_benchmark()
        progress.advance(task)
        progress.update(task, description="[yellow]Memory benchmark...")
        mem_scores = engine.run_memory_benchmark()
        progress.advance(task)
        progress.update(task, description="[yellow]Storage benchmark...")
        storage_scores = engine.run_storage_benchmark()
        progress.advance(task)
        progress.update(task, description="[yellow]Analyzing results...")
        relative = engine.estimate_relative_performance(cpu_scores.get("overall_score", 0))
        progress.advance(task)
        progress.update(task, description="[green]Benchmarks complete!")

    from rich.table import Table
    from rich.panel import Panel
    from rich import box

    cpu_table = Table(box=box.ROUNDED)
    cpu_table.add_column("Metric", style="cyan bold")
    cpu_table.add_column("Score", style="white")
    for metric, score in cpu_scores.items():
        if metric != "overall_score":
            cpu_table.add_row(metric.replace("_", " ").title(), f"{score:.1f}")
    cpu_table.add_row("Overall CPU Score", f"{cpu_scores.get('overall_score', 0):.1f}")
    console.print(Panel(cpu_table, title="CPU Benchmark Results", border_style="yellow"))

    mem_table = Table(box=box.SIMPLE)
    mem_table.add_column("Metric", style="cyan bold")
    mem_table.add_column("Value", style="white")
    for metric, score in mem_scores.items():
        unit = "MB/s" if "bandwidth" in metric else "ns"
        mem_table.add_row(metric.replace("_", " ").title(), f"{score:.1f} {unit}")
    console.print(Panel(mem_table, title="Memory Benchmark Results", border_style="green"))

    if storage_scores:
        storage_table = Table(box=box.SIMPLE)
        storage_table.add_column("Metric", style="cyan bold")
        storage_table.add_column("Value", style="white")
        for metric, score in storage_scores.items():
            if isinstance(score, (int, float)):
                storage_table.add_row(metric.replace("_", " ").title(), f"{score:,.0f}")
        console.print(Panel(storage_table, title="Storage Benchmark Results", border_style="blue"))

    if relative:
        rel_table = Table(box=box.SIMPLE)
        rel_table.add_column("CPU", style="cyan bold")
        rel_table.add_column("Relative Performance", style="white")
        for name, est in relative.items():
            rel_table.add_row(name, est)
        console.print(Panel(rel_table, title="CPU Performance Comparison", border_style="blue"))


@app.command()
def health() -> None:
    """Display system health overview."""
    results = _full_scan()
    report = TerminalReport(results)
    report.display_header()
    report.display_overall_score()
    report.display_temperatures()
    report.display_bottlenecks()
    report.display_upgrades()


@app.command()
def temperatures() -> None:
    """Display temperature and cooling information."""
    results = _run_collectors(["cooling"])
    analysis = _analyze_results(results)
    results.update(analysis)
    report = TerminalReport(results)
    report.display_header()
    report.display_temperatures()


@app.command()
def bottlenecks() -> None:
    """Detect and display system bottlenecks."""
    results = _run_collectors()
    analysis = _analyze_results(results)
    results.update(analysis)
    report = TerminalReport(results)
    report.display_header()
    report.display_overall_score()
    report.display_bottlenecks()


@app.command()
def upgrades() -> None:
    """Show recommended hardware upgrades."""
    results = _run_collectors()
    analysis = _analyze_results(results)
    results.update(analysis)
    report = TerminalReport(results)
    report.display_header()
    report.display_upgrades()


@app.command()
def workloads() -> None:
    """Assess system capability for various workloads."""
    results = _run_collectors(["cpu", "memory", "gpu", "storage"])
    analysis = _analyze_results(results)
    results.update(analysis)
    report = TerminalReport(results)
    report.display_header()
    report.display_workloads()


@app.command()
def compare() -> None:
    """Compare system against standard tiers."""
    results = _run_collectors(["cpu", "memory", "gpu", "storage"])
    analysis = _analyze_results(results)
    results.update(analysis)
    report = TerminalReport(results)
    report.display_header()
    report.display_comparisons()


@app.command()
def score() -> None:
    """Display performance scores."""
    results = _run_collectors()
    analysis = _analyze_results(results)
    results.update(analysis)
    report = TerminalReport(results)
    report.display_header()
    report.display_overall_score()


@app.command()
def summary() -> None:
    """Display a brief system summary."""
    results = _full_scan()
    report = TerminalReport(results)
    report.display_header()
    report.display_summary()
    report.display_overall_score()


@app.command()
def topology() -> None:
    """Display system topology."""
    results = _run_collectors(["cpu", "memory", "pci", "storage", "network", "usb"])
    report = TerminalReport(results)
    report.display_header()

    console.print("[bold cyan]System Topology Overview[/bold cyan]")
    console.print()

    os_info = get_os_info()
    from rich.table import Table
    from rich.panel import Panel
    from rich import box

    t = Table(box=box.ROUNDED)
    t.add_column("Layer", style="cyan bold")
    t.add_column("Components", style="white")
    cpu_data = results.get("cpu", {}).get("data", {})
    t.add_row("CPU", f"{cpu_data.get('brand', 'N/A')} ({cpu_data.get('physical_cores', 0)}C/{cpu_data.get('logical_cores', 0)}T)")
    mem_data = results.get("memory", {}).get("data", {})
    t.add_row("Memory", f"{mem_data.get('total', 0) / (1024**3):.1f} GB ({mem_data.get('channels', {}).get('mode', 'N/A')} channel)")
    pci_data = results.get("pci", {}).get("data", {})
    t.add_row("PCI Devices", f"{pci_data.get('device_count', 0)} devices")

    storage_data = results.get("storage", {}).get("data", {})
    disk_count = len(storage_data.get("disks", []))
    t.add_row("Storage", f"{disk_count} devices")

    net_data = results.get("network", {}).get("data", {})
    if_count = len([i for i in net_data.get("interfaces", []) if not i.get("is_loopback")])
    t.add_row("Network", f"{if_count} interfaces")

    usb_data = results.get("usb", {}).get("data", {})
    t.add_row("USB", f"{usb_data.get('device_count', 0)} devices")

    t.add_row("OS", f"{os_info.get('distro', os_info.get('system', 'N/A'))} ({os_info.get('release', '')})")
    t.add_row("Kernel", os_info.get("release", "N/A"))
    t.add_row("Uptime", get_uptime())

    console.print(Panel(t, title="Infrastructure Topology", border_style="cyan"))

    gpu_data = results.get("gpu", {}).get("data", {})
    gpus = gpu_data.get("gpus", [])
    gpu_str = f"GPU: {gpus[0].get('model', 'N/A')[:20]}" if gpus else "No GPU"

    # Simple ASCII topology
    console.print()
    console.print("[bold]Logical Topology:[/bold]")
    console.print()
    console.print("  ┌─────────────────────────────────────┐")
    console.print("  │          [cyan]Operating System[/cyan]          │")
    console.print(f"  │  {os_info.get('distro', 'Linux'):33s} │")
    console.print("  └───────────┬─────────────────────────┘")
    console.print("              │")
    console.print("  ┌───────────┴─────────────────────────┐")
    console.print(f"  │          [green]CPU: {cpu_data.get('physical_cores', 0)}C/{cpu_data.get('logical_cores', 0)}T[/green]          │")
    console.print("  └─────┬─────┬─────┬─────┬────────────┘")
    console.print("        │     │     │     │")
    console.print("  ┌─────┘     │     │     └─────┐")
    console.print(f"  │  [yellow]Memory: {mem_data.get('total', 0) / (1024**3):.1f} GB[/yellow]  │  [magenta]{gpu_str}[/magenta] │")
    console.print(f"  │  {mem_data.get('channels', {}).get('mode', 'N/A')} channel {mem_data.get('frequency_mts', 0)} MHz  │  │")
    console.print("  └──────────────┘  └──────────────┘")
    console.print()


@app.command()
def inventory() -> None:
    """Generate a hardware inventory in table format."""
    results = _run_collectors()
    report = TerminalReport(results)
    report.display_header()

    from rich.table import Table
    from rich.panel import Panel
    from rich import box

    # Hardware inventory table
    inv_table = Table(box=box.ROUNDED)
    inv_table.add_column("Component", style="cyan bold")
    inv_table.add_column("Vendor/Model", style="white")
    inv_table.add_column("Specification", style="white")
    inv_table.add_column("Status", style="bold")

    cpu_data = results.get("cpu", {}).get("data", {})
    inv_table.add_row("CPU", cpu_data.get("brand", "N/A"),
                      f"{cpu_data.get('physical_cores', 0)}C/{cpu_data.get('logical_cores', 0)}T @ {cpu_data.get('max_freq', 0)/1_000_000:.1f}GHz",
                      cpu_data.get("class", "N/A"))

    mem_data = results.get("memory", {}).get("data", {})
    inv_table.add_row("Memory", mem_data.get("ddr_generation", "N/A"),
                      f"{mem_data.get('total', 0) / (1024**3):.1f} GB @ {mem_data.get('frequency_mts', 0)} MHz",
                      f"{mem_data.get('channels', {}).get('mode', 'N/A')} Channel")

    gpu_data = results.get("gpu", {}).get("data", {})
    gpus = gpu_data.get("gpus", [])
    if gpus:
        g = gpus[0]
        inv_table.add_row("GPU", g.get("vendor", "N/A"),
                          f"{g.get('model', 'N/A')} ({g.get('vram_total_mb', 0) / 1024:.1f} GB)",
                          "Active" if g.get("gpu_utilization", 0) is not None else "N/A")
    else:
        inv_table.add_row("GPU", "N/A", "Integrated", "N/A")

    storage_data = results.get("storage", {}).get("data", {})
    for disk in storage_data.get("disks", []):
        inv_table.add_row("Storage", f"/dev/{disk.get('name', '')}",
                          f"{disk.get('disk_type', 'N/A')} ({disk.get('size', 0) / (1024**3):.1f} GB)",
                          disk.get("smart_status", "N/A"))

    mobo_data = results.get("motherboard", {}).get("data", {})
    inv_table.add_row("Motherboard", mobo_data.get("vendor", "N/A"),
                      mobo_data.get("model", "N/A"),
                      mobo_data.get("version", "N/A"))

    net_data = results.get("network", {}).get("data", {})
    for iface in net_data.get("interfaces", []):
        if not iface.get("is_loopback"):
            inv_table.add_row("Network", iface.get("name", ""),
                              f"{iface.get('speed', 0)} Mbps",
                              iface.get("operstate", "N/A"))

    console.print(Panel(inv_table, title="Hardware Inventory", border_style="green"))


@app.command()
def doctor(
    fix: bool = typer.Option(False, "--fix", help="Attempt to fix detected issues"),
) -> None:
    """Check system health and diagnose issues."""
    console.print(f"[bold cyan]{__app_name__} Doctor[/bold cyan]")
    console.print()

    # Check dependencies
    print_dependency_report()

    results = _run_collectors()
    analysis = _analyze_results(results)
    results.update(analysis)

    bottlenecks = results.get("bottlenecks", {})
    critical = bottlenecks.get("critical", [])
    if critical:
        console.print(f"\n[bold red]Found {len(critical)} critical issues![/bold red]")
    else:
        console.print("\n[green]No critical issues detected.[/green]")

    if fix:
        console.print("\n[yellow]Auto-fix mode: Attempting fixes...[/yellow]")
        governors_path = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"
        if os.path.exists(governors_path):
            try:
                with open(governors_path) as f:
                    current = f.read().strip()
                if current in ("powersave", "conservative"):
                    try:
                        for cpu_dir in os.listdir("/sys/devices/system/cpu/"):
                            if cpu_dir.startswith("cpu") and cpu_dir[3:].isdigit():
                                gov_path = f"/sys/devices/system/cpu/{cpu_dir}/cpufreq/scaling_governor"
                                if os.path.exists(gov_path):
                                    with open(gov_path, "w") as gf:
                                        gf.write("performance")
                        console.print("[green]✓ CPU governor set to 'performance'[/green]")
                    except PermissionError:
                        console.print("[red]✗ Need root to change CPU governor[/red]")
            except OSError:
                pass
        console.print("[green]✓ Doctor check complete[/green]")

    report = TerminalReport(results)
    report.display_overall_score()


@app.command()
def report(
    markdown: bool = typer.Option(False, "--md", "-m", help="Generate Markdown report"),
    json: bool = typer.Option(False, "--json", "-j", help="Generate JSON report"),
    html: bool = typer.Option(False, "--html", "-h", help="Generate HTML report"),
    csv: bool = typer.Option(False, "--csv", "-c", help="Generate CSV report"),
    output_dir: str = typer.Option("reports", "--output", "-o", help="Output directory"),
) -> None:
    """Generate hardware analysis reports."""
    results = _full_scan()

    generated = []
    if markdown or not any([markdown, json, html, csv]):
        md = MarkdownReport(results, output_dir)
        path = md.generate()
        generated.append(("Markdown", path))
        console.print(f"[green]✓[/green] Markdown report: [cyan]{path}[/cyan]")

    if json:
        js = JSONReport(results, output_dir)
        path = js.generate()
        generated.append(("JSON", path))
        console.print(f"[green]✓[/green] JSON report: [cyan]{path}[/cyan]")

    if html:
        h = HTMLReport(results, output_dir)
        path = h.generate()
        generated.append(("HTML", path))
        console.print(f"[green]✓[/green] HTML report: [cyan]{path}[/cyan]")

    if csv:
        c = CSVReport(results, output_dir)
        path = c.generate()
        generated.append(("CSV", path))
        console.print(f"[green]✓[/green] CSV report: [cyan]{path}[/cyan]")

    if not generated:
        console.print("[yellow]No report format selected. Use --md, --json, --html, or --csv[/yellow]")


@app.command()
def export(
    format: str = typer.Argument("json", help="Export format (json, csv)"),
    output: str = typer.Option("export", "--output", "-o", help="Output file/directory"),
) -> None:
    """Export system data to an external format."""
    results = _full_scan()
    if format == "json":
        exporter = JSONReport(results, output)
        path = exporter.generate()
    elif format == "csv":
        exporter = CSVReport(results, output)
        path = exporter.generate()
    else:
        console.print(f"[red]Unknown format: {format}[/red]")
        return
    console.print(f"[green]✓[/green] Data exported: [cyan]{path}[/cyan]")


@app.command()
def version() -> None:
    """Show InfraScope version."""
    console.print(f"[bold cyan]{__app_name__}[/bold cyan] v{__version__}")


@app.command()
def deps() -> None:
    """Check system dependencies for InfraScope."""
    print_dependency_report()


@app.command()
def monitor(
    live: bool = typer.Option(False, "--live", "-l", help="Enable live monitoring"),
    interval: float = typer.Option(2.0, "--interval", "-i", help="Update interval in seconds"),
) -> None:
    """Monitor system performance in real-time."""
    if live:
        from rich.live import Live
        from rich.layout import Layout
        from rich.table import Table
        from rich.panel import Panel

        def generate_display() -> Layout:
            layout = Layout()
            layout.split_column(
                Layout(name="header", size=3),
                Layout(name="body"),
            )
            layout["body"].split_row(
                Layout(name="left"),
                Layout(name="right"),
            )

            import psutil
            cpu_pct = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory()
            load = get_load_average()

            header = Table.grid()
            header.add_column()
            header.add_row(
                f"[bold cyan]InfraScope Monitor[/bold cyan] | "
                f"CPU: {cpu_pct:.1f}% | "
                f"RAM: {mem.percent:.1f}% | "
                f"Load: {load[0]:.1f}, {load[1]:.1f}, {load[2]:.1f} | "
                f"[green]● Live[/green] (interval: {interval}s)"
            )
            layout["header"].update(Panel(header, border_style="cyan"))

            # CPU per-core
            cpu_table = Table(box=None)
            cpu_table.add_column("Core", style="cyan")
            cpu_table.add_column("Usage", style="bold")
            cpu_per_core = psutil.cpu_percent(percpu=True)
            for i, p in enumerate(cpu_per_core):
                color = "green" if p < 50 else ("yellow" if p < 80 else "red")
                bar = "█" * int(p / 5) + "░" * (20 - int(p / 5))
                cpu_table.add_row(f"Core {i}", f"[{color}]{bar}[/{color}] {p:.1f}%")
            layout["left"].update(Panel(cpu_table, title="CPU Cores"))

            # Processes
            proc_table = Table(box=None)
            proc_table.add_column("PID", style="dim")
            proc_table.add_column("Name", style="cyan")
            proc_table.add_column("CPU%", style="bold")
            proc_table.add_column("MEM%", style="bold")
            for p in sorted(psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]),
                           key=lambda p: p.info["cpu_percent"] or 0, reverse=True)[:10]:
                try:
                    proc_table.add_row(
                        str(p.info["pid"]),
                        p.info["name"][:20] if p.info["name"] else "",
                        f"{p.info['cpu_percent'] or 0:.1f}",
                        f"{p.info['memory_percent'] or 0:.1f}",
                    )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            layout["right"].update(Panel(proc_table, title="Top Processes"))

            return layout

        try:
            with Live(generate_display(), refresh_per_second=int(1 / interval), console=console) as live:
                import time
                while True:
                    time.sleep(interval)
                    live.update(generate_display())
        except KeyboardInterrupt:
            console.print("\n[yellow]Monitoring stopped[/yellow]")
    else:
        import psutil
        from rich.table import Table
        from rich import box
        from rich.layout import Layout

        cpu_pct = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        table = Table(box=box.ROUNDED)
        table.add_column("Metric", style="cyan bold")
        table.add_column("Value", style="white")
        table.add_column("Status", style="bold")

        table.add_row("CPU Usage", f"{cpu_pct:.1f}%",
                      "[green]Good[/green]" if cpu_pct < 70 else ("[yellow]High[/yellow]" if cpu_pct < 90 else "[red]Critical[/red]"))
        table.add_row("Memory Usage", f"{mem.percent:.1f}% ({mem.used / (1024**3):.1f}/{mem.total / (1024**3):.1f} GB)",
                      "[green]Good[/green]" if mem.percent < 70 else ("[yellow]High[/yellow]" if mem.percent < 90 else "[red]Critical[/red]"))
        table.add_row("Disk Usage (/)", f"{disk.percent:.1f}% ({disk.used / (1024**3):.1f}/{disk.total / (1024**3):.1f} GB)",
                      "[green]Good[/green]" if disk.percent < 70 else ("[yellow]High[/yellow]" if disk.percent < 90 else "[red]Critical[/red]"))

        temps = []
        cool_data = _run_collectors(["cooling"]).get("cooling", {}).get("data", {})
        for t in cool_data.get("temperatures", []):
            tc = t.get("temperature_c", 0)
            temps.append(tc)
        if temps:
            max_temp = max(temps)
            table.add_row("Max Temperature", f"{max_temp:.1f}°C",
                          "[green]Cool[/green]" if max_temp < 60 else ("[yellow]Warm[/yellow]" if max_temp < 80 else "[red]Hot[/red]"))

        console.print(Panel(table, title="System Monitor Snapshot", border_style="cyan"))


@app.command()
def help() -> None:
    """Show detailed help information."""
    console.print("[bold cyan]InfraScope - Advanced Linux Hardware Analyzer[/bold cyan]")
    console.print()
    console.print("[bold]Commands:[/bold]")
    console.print("  scan          Run a comprehensive hardware scan")
    console.print("  full          Display a complete system analysis report")
    console.print("  cpu           Display CPU information")
    console.print("  ram           Display memory/RAM information")
    console.print("  gpu           Display GPU information")
    console.print("  storage       Display storage device information")
    console.print("  network       Display network interface information")
    console.print("  benchmark     Run performance benchmarks")
    console.print("  compare       Compare system against standard tiers")
    console.print("  health        Display system health overview")
    console.print("  temperatures  Display temperature and cooling information")
    console.print("  bottlenecks   Detect and display system bottlenecks")
    console.print("  upgrades      Show recommended hardware upgrades")
    console.print("  workloads     Assess system capability for various workloads")
    console.print("  score         Display performance scores")
    console.print("  summary       Display a brief system summary")
    console.print("  monitor       Monitor system performance in real-time")
    console.print("  topology      Display system topology")
    console.print("  inventory     Generate a hardware inventory")
    console.print("  doctor        Check system health and diagnose issues")
    console.print("  doctor --fix  Attempt to fix detected issues")
    console.print("  report        Generate hardware analysis reports")
    console.print("  report --md   Generate Markdown report")
    console.print("  report --json Generate JSON report")
    console.print("  report --html Generate HTML report")
    console.print("  report --csv  Generate CSV report")
    console.print("  export        Export system data (json/csv)")
    console.print("  deps          Check system dependencies")
    console.print("  version       Show InfraScope version")
    console.print()
    console.print("[bold]Examples:[/bold]")
    console.print("  infrascope scan")
    console.print("  infrascope full")
    console.print("  infrascope cpu")
    console.print("  infrascope benchmark")
    console.print("  infrascope report --html")
    console.print("  infrascope doctor --fix")
    console.print("  infrascope monitor --live")


if __name__ == "__main__":
    app()
