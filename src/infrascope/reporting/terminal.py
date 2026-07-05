from __future__ import annotations

from typing import Any

from rich import box
from rich.console import Console, Group
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text
from rich.layout import Layout
from rich.live import Live
from rich.columns import Columns

from infrascope.utils.formatting import (
    health_badge,
    percent_bar,
    status_badge,
    make_table,
    format_dict_as_table,
    card,
    gauge_bar,
)


class TerminalReport:
    def __init__(self, results: dict[str, Any], console: Console | None = None):
        self.results = results
        self.console = console or Console()

    def display_header(self) -> None:
        self.console.print()
        self.console.print(
            Panel(
                "[bold cyan]█╗███╗   ██╗███████╗██████╗  █████╗ ███████╗ ██████╗ ██████╗ ███████╗[/bold cyan]\n"
                "[bold cyan]██║████╗  ██║██╔════╝██╔══██╗██╔══██╗██╔════╝██╔════╝ ██╔══██╗██╔════╝[/bold cyan]\n"
                "[bold cyan]██║██╔██╗ ██║█████╗  ██████╔╝██║  ██║███████╗██║  ███╗██████╔╝█████╗  [/bold cyan]\n"
                "[bold cyan]██║██║╚██╗██║██╔══╝  ██╔══██╗██║  ██║╚════██║██║   ██║██╔═══╝ ██╔══╝  [/bold cyan]\n"
                "[bold cyan]██║██║ ╚████║██║     ██║  ██║╚█████╔╝███████║╚██████╔╝██║     ███████╗[/bold cyan]\n"
                "[bold cyan]╚═╝╚═╝  ╚═══╝╚═╝     ╚═╝  ╚═╝ ╚════╝ ╚══════╝ ╚═════╝ ╚═╝     ╚══════╝[/bold cyan]\n"
                "[bold white]        Advanced Linux System Hardware & Performance Analyzer[/bold white]",
                border_style="cyan",
                padding=(1, 2),
            )
        )
        self.console.print()

    def display_summary(self) -> None:
        scores = self.results.get("scores", {})
        overall = scores.get("overall", 0)
        rating = scores.get("rating", "Unknown")

        grid = Table.grid()
        grid.add_column()
        grid.add_row(
            Panel(
                f"[bold]Infrastructure Score:[/bold] {health_badge(overall)}\n"
                f"[bold]Rating:[/bold] {status_badge(rating)}",
                title="System Health Overview",
                border_style="green",
            )
        )

        import psutil
        uptime_seconds = 0
        try:
            with open("/proc/uptime") as f:
                uptime_seconds = float(f.read().split()[0])
        except OSError:
            pass
        days, remainder = divmod(uptime_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes = remainder // 60

        uptime_str = f"{int(days)}d {int(hours)}h {int(minutes)}m"
        load = ""
        try:
            import os
            load = f"{os.getloadavg()[0]:.1f}, {os.getloadavg()[1]:.1f}, {os.getloadavg()[2]:.1f}"
        except OSError:
            pass

        info_panel = Panel(
            f"[bold]Uptime:[/bold] {uptime_str}\n"
            f"[bold]Load Average:[/bold] {load}\n"
            f"[bold]Components Scored:[/bold] CPU: {health_badge(scores.get('cpu', 0))} | "
            f"Mem: {health_badge(scores.get('memory', 0))} | "
            f"GPU: {health_badge(scores.get('gpu', 0))} | "
            f"Disk: {health_badge(scores.get('storage', 0))} | "
            f"Net: {health_badge(scores.get('networking', 0))} | "
            f"Thermal: {health_badge(scores.get('thermals', 0))}",
            title="System Summary",
            border_style="blue",
        )
        self.console.print(grid)
        self.console.print(info_panel)

    def display_overall_score(self) -> None:
        scores = self.results.get("scores", {})
        overall = scores.get("overall", 0)
        rating = scores.get("rating", "Unknown")

        color = "green" if overall >= 70 else ("yellow" if overall >= 50 else "red")
        bar = gauge_bar(overall, 100, 40)
        self.console.print(
            Panel(
                f"\n[{color}]{bar}[/{color}]  [bold]{overall:.1f}/100[/bold]\n\n"
                f"[bold]Rating:[/bold] {status_badge(rating)}\n\n"
                f"[bold]CPU:[/bold]     {health_badge(scores.get('cpu', 0))}      "
                f"[bold]Memory:[/bold]  {health_badge(scores.get('memory', 0))}\n"
                f"[bold]GPU:[/bold]     {health_badge(scores.get('gpu', 0))}      "
                f"[bold]Storage:[/bold] {health_badge(scores.get('storage', 0))}\n"
                f"[bold]Network:[/bold] {health_badge(scores.get('networking', 0))}    "
                f"[bold]Thermal:[/bold] {health_badge(scores.get('thermals', 0))}",
                title="Overall Infrastructure Score",
                border_style=color,
                padding=(1, 2),
            )
        )

    def display_cpu(self) -> None:
        cpu = self.results.get("cpu", {}).get("data", {})
        if not cpu:
            self.console.print("[red]No CPU data available[/red]")
            return

        cores = cpu.get("physical_cores", 0)
        threads = cpu.get("logical_cores", 0)
        freq = cpu.get("current_freq", 0) / 1_000_000
        max_freq = cpu.get("max_freq", 0) / 1_000_000
        cpu_class = cpu.get("class", "Unknown")

        table = Table(box=box.ROUNDED)
        table.add_column("Property", style="cyan bold")
        table.add_column("Value", style="white")
        table.add_row("Vendor", cpu.get("vendor", "Unknown"))
        table.add_row("Model", cpu.get("brand", "Unknown"))
        table.add_row("Architecture", cpu.get("arch", ""))
        table.add_row("Class", status_badge(cpu_class))
        table.add_row("Physical Cores", str(cores))
        table.add_row("Logical Cores", str(threads))
        table.add_row("SMT/HyperThreading", "[green]Enabled[/green]" if cpu.get("smt_enabled") else "[yellow]Disabled[/yellow]")
        table.add_row("Base Frequency", f"{cpu.get('base_freq', 0)/1_000_000:.2f} GHz" if cpu.get("base_freq") else "N/A")
        table.add_row("Max Turbo Frequency", f"{max_freq:.2f} GHz")
        table.add_row("Current Frequency", f"{freq:.2f} GHz")
        table.add_row("L1 Cache", cpu.get("l1_cache", "N/A"))
        table.add_row("L2 Cache", cpu.get("l2_cache", "N/A"))
        table.add_row("L3 Cache", cpu.get("l3_cache", "N/A"))
        table.add_row("NUMA Nodes", str(cpu.get("numa_nodes", 1)))
        table.add_row("Sockets", str(cpu.get("sockets", 1)))
        table.add_row("Microcode", cpu.get("microcode", "N/A"))
        table.add_row("Governor", cpu.get("governor", "N/A"))
        table.add_row("Scaling Driver", cpu.get("scaling_driver", "N/A"))

        self.console.print(Panel(table, title="CPU Information", border_style="cyan"))

        flags = cpu.get("flags", [])
        isa = cpu.get("instruction_sets", {})
        isa_table = Table(box=box.SIMPLE)
        isa_table.add_column("Instruction Set", style="yellow")
        isa_table.add_column("Supported", style="bold")
        for isa_name, supported in isa.items():
            isa_table.add_row(isa_name, "[green]Yes[/green]" if supported else "[red]No[/red]")
        self.console.print(Panel(isa_table, title="Instruction Sets", border_style="yellow"))

        virt = cpu.get("virtualization", {})
        virt_table = Table(box=box.SIMPLE)
        virt_table.add_column("Technology", style="yellow")
        virt_table.add_column("Status")
        for vname, vsupported in virt.items():
            virt_table.add_row(vname, "[green]Supported[/green]" if vsupported else "[red]Not Supported[/red]")
        self.console.print(Panel(virt_table, title="Virtualization Support", border_style="green"))

    def display_memory(self) -> None:
        mem = self.results.get("memory", {}).get("data", {})
        if not mem:
            self.console.print("[red]No memory data available[/red]")
            return

        total_gb = mem.get("total", 0) / (1024**3)
        used_gb = mem.get("used", 0) / (1024**3)
        avail_gb = mem.get("available", 0) / (1024**3)

        table = Table(box=box.ROUNDED)
        table.add_column("Property", style="cyan bold")
        table.add_column("Value", style="white")
        table.add_row("Total RAM", f"{total_gb:.1f} GB")
        table.add_row("Used RAM", f"{used_gb:.1f} GB ({mem.get('percent_used', 0):.1f}%)")
        table.add_row("Available RAM", f"{avail_gb:.1f} GB")
        table.add_row("Type", mem.get("type", "Unknown"))
        table.add_row("DDR Generation", mem.get("ddr_generation", "Unknown"))
        table.add_row("Frequency", f"{mem.get('frequency_mts', 0)} MHz")
        table.add_row("Configured Speed", f"{mem.get('configured_speed_mts', 0)} MHz")
        table.add_row("Form Factor", mem.get("form_factor", "Unknown"))
        table.add_row("ECC", "[green]Yes[/green]" if mem.get("ecc") else "[yellow]No[/yellow]")
        table.add_row("Registered", "[green]Yes[/green]" if mem.get("registered") else "[yellow]No[/yellow]")
        table.add_row("Slots", mem.get("slot_population", "N/A"))
        table.add_row("Max Capacity", f"{mem.get('max_capacity', 0) / 1024:.0f} GB" if mem.get("max_capacity") else "N/A")
        table.add_row("Channels", mem.get("channels", {}).get("mode", "Unknown"))

        # Memory usage bar
        usage_pct = mem.get("percent_used", 0)
        self.console.print(Panel(table, title="Memory (RAM) Information", border_style="green"))
        self.console.print(percent_bar(usage_pct, 100))

        # Swap info
        swap_total = mem.get("swap_total", 0) / (1024**3)
        if swap_total > 0:
            swap_used = mem.get("swap_used", 0) / (1024**3)
            swap_table = Table(box=box.SIMPLE)
            swap_table.add_column("Property", style="yellow")
            swap_table.add_column("Value")
            swap_table.add_row("Total Swap", f"{swap_total:.1f} GB")
            swap_table.add_row("Used Swap", f"{swap_used:.1f} GB ({mem.get('swap_percent', 0):.1f}%)")
            self.console.print(Panel(swap_table, title="Swap", border_style="yellow"))

        # DIMMs
        dimms = mem.get("dimms", [])
        if dimms:
            dimm_table = Table(box=box.SIMPLE)
            dimm_table.add_column("Locator", style="cyan")
            dimm_table.add_column("Size", style="white")
            dimm_table.add_column("Type", style="white")
            dimm_table.add_column("Speed", style="white")
            dimm_table.add_column("Manufacturer", style="white")
            for d in dimms:
                size = d.get("size_mb", 0)
                size_str = f"{size} MB" if size < 1024 else f"{size/1024:.0f} GB"
                dimm_table.add_row(
                    d.get("locator", "N/A"),
                    size_str,
                    d.get("type", "N/A"),
                    f"{d.get('speed_mts', 0)} MT/s",
                    d.get("manufacturer", "N/A"),
                )
            self.console.print(Panel(dimm_table, title="Memory Modules (DIMMs)", border_style="blue"))

    def display_gpu(self) -> None:
        gpu = self.results.get("gpu", {}).get("data", {})
        gpus = gpu.get("gpus", [])
        if not gpus:
            self.console.print("[yellow]No dedicated GPU detected[/yellow]")
            return

        for i, g in enumerate(gpus):
            table = Table(box=box.ROUNDED)
            table.add_column("Property", style="cyan bold")
            table.add_column("Value", style="white")
            table.add_row("Vendor", g.get("vendor", "Unknown"))
            table.add_row("Model", g.get("model", "Unknown"))
            table.add_row("Driver", g.get("driver", "N/A"))
            table.add_row("VRAM", f"{g.get('vram_total_mb', 0) / 1024:.1f} GB")
            table.add_row("VRAM Utilization", f"{g.get('vram_utilization', 0):.1f}%")
            table.add_row("GPU Utilization", f"{g.get('gpu_utilization', 0):.1f}%")
            table.add_row("Temperature", f"{g.get('temperature_c', 'N/A')} °C")
            table.add_row("CUDA Cores", str(g.get("cuda_cores", "N/A")))
            table.add_row("Tensor Cores", str(g.get("tensor_cores", "N/A")))
            table.add_row("RT Cores", str(g.get("rt_cores", "N/A")))
            table.add_row("Power Draw", f"{g.get('power_watts', 'N/A')} W")

            pcie = g.get("pcie_info", {})
            if pcie:
                table.add_row("PCIe Speed", pcie.get("speed", "N/A"))
                table.add_row("PCIe Width", pcie.get("width", "N/A"))

            self.console.print(Panel(table, title=f"GPU {i+1}: {g.get('model', 'Unknown')}", border_style="magenta"))

            ai_cap = g.get("ai_capability", {})
            if ai_cap:
                ai_table = Table(box=box.SIMPLE)
                ai_table.add_column("Capability", style="yellow")
                ai_table.add_column("Supported", style="bold")
                for cap, supported in ai_cap.items():
                    ai_table.add_row(cap.replace("_", " ").title(), "[green]Yes[/green]" if supported else "[red]No[/red]")
                self.console.print(Panel(ai_table, title="AI/ML Capability", border_style="cyan"))

    def display_storage(self) -> None:
        storage = self.results.get("storage", {}).get("data", {})
        disks = storage.get("disks", [])
        if not disks:
            self.console.print("[red]No storage data available[/red]")
            return

        for disk in disks:
            size_gb = disk.get("size", 0) / (1024**3)
            table = Table(box=box.ROUNDED)
            table.add_column("Property", style="cyan bold")
            table.add_column("Value", style="white")
            table.add_row("Device", f"/dev/{disk.get('name', '')}")
            table.add_row("Model", disk.get("model", "N/A"))
            table.add_row("Type", disk.get("disk_type", "Unknown"))
            table.add_row("Size", f"{size_gb:.1f} GB")
            table.add_row("Rotational", "[red]Yes[/red]" if disk.get("rotational") else "[green]No[/green]")
            table.add_row("Transport", disk.get("tran", "N/A"))
            table.add_row("Scheduler", disk.get("scheduler", "N/A"))

            if disk.get("temperature_c"):
                table.add_row("Temperature", f"{disk['temperature_c']} °C")
            if disk.get("power_on_hours"):
                table.add_row("Power On Hours", str(disk["power_on_hours"]))
            if disk.get("remaining_life_pct"):
                life = disk["remaining_life_pct"]
                life_style = "green" if life > 80 else ("yellow" if life > 50 else "red")
                table.add_row("Remaining Life", f"[{life_style}]{life}%[/{life_style}]")
            if disk.get("smart_status"):
                status = disk["smart_status"]
                s_style = "green" if status == "PASSED" else "red"
                table.add_row("SMART Status", f"[{s_style}]{status}[/{s_style}]")
            if disk.get("pcie_version"):
                table.add_row("PCIe Version", str(disk["pcie_version"]))
            if disk.get("pcie_width"):
                table.add_row("PCIe Width", disk["pcie_width"])
            if disk.get("nvme_gen"):
                table.add_row("NVMe Generation", f"Gen{disk['nvme_gen']}")

            self.console.print(Panel(table, title=f"Storage: /dev/{disk.get('name', '')}", border_style="blue"))

        # Usage
        usage = storage.get("disk_usage", {})
        if usage:
            usage_table = Table(box=box.SIMPLE)
            usage_table.add_column("Mount", style="cyan")
            usage_table.add_column("Total", style="white")
            usage_table.add_column("Used", style="white")
            usage_table.add_column("Free", style="white")
            usage_table.add_column("Use%", style="bold")
            for mount, info in usage.items():
                total = info.get("total", 0)
                used = info.get("used", 0)
                free = info.get("free", 0)
                pct = info.get("percent", 0)
                pct_style = "green" if pct < 70 else ("yellow" if pct < 90 else "red")
                usage_table.add_row(
                    mount,
                    f"{total/(1024**3):.1f}G",
                    f"{used/(1024**3):.1f}G",
                    f"{free/(1024**3):.1f}G",
                    f"[{pct_style}]{pct:.1f}%[/{pct_style}]",
                )
            self.console.print(Panel(usage_table, title="Disk Usage", border_style="green"))

    def display_network(self) -> None:
        net = self.results.get("network", {}).get("data", {})
        interfaces = net.get("interfaces", [])
        if not interfaces:
            self.console.print("[red]No network data available[/red]")
            return

        for iface in interfaces:
            if iface.get("is_loopback"):
                continue
            table = Table(box=box.ROUNDED)
            table.add_column("Property", style="cyan bold")
            table.add_column("Value", style="white")
            table.add_row("Interface", iface.get("name", ""))
            table.add_row("State", "[green]Up[/green]" if iface.get("operstate") == "up" else "[red]Down[/red]")
            table.add_row("Speed", f"{iface.get('speed', 0)} Mbps" if iface.get("speed") else "N/A")
            table.add_row("MTU", str(iface.get("mtu", 1500)))
            table.add_row("Duplex", iface.get("duplex", "N/A"))
            table.add_row("Driver", iface.get("driver", "N/A"))
            table.add_row("Wireless", "[green]Yes[/green]" if iface.get("is_wireless") else "[red]No[/red]")

            addrs = iface.get("addresses", {})
            for family, addr_list in addrs.items():
                for addr in addr_list:
                    if ":" not in addr.get("address", "") or addr.get("address", "").count(":") <= 1:
                        table.add_row("IP", addr.get("address", ""))

            io = iface.get("io", {})
            if io:
                rx_mb = io.get("bytes_recv", 0) / (1024**2)
                tx_mb = io.get("bytes_sent", 0) / (1024**2)
                table.add_row("RX", f"{rx_mb:.1f} MB")
                table.add_row("TX", f"{tx_mb:.1f} MB")

            self.console.print(Panel(table, title=f"Network: {iface.get('name', '')}", border_style="blue"))

        route = net.get("route_info", {})
        if route.get("gateway"):
            route_table = Table(box=box.SIMPLE)
            route_table.add_column("Property", style="yellow")
            route_table.add_column("Value")
            route_table.add_row("Default Gateway", route["gateway"])
            self.console.print(Panel(route_table, title="Routing", border_style="green"))

    def display_temperatures(self) -> None:
        cool = self.results.get("cooling", {}).get("data", {})
        temps = cool.get("temperatures", [])
        if not temps:
            self.console.print("[yellow]No temperature data available[/yellow]")
            return

        temp_table = Table(box=box.ROUNDED)
        temp_table.add_column("Sensor", style="cyan")
        temp_table.add_column("Temperature", style="bold")
        temp_table.add_column("Status", style="bold")

        for t in temps:
            temp_c = t.get("temperature_c", 0)
            name = f"{t.get('chip', '')} - {t.get('feature', '')}"
            if temp_c >= 85:
                status = "[red]CRITICAL[/red]"
                style = "red"
            elif temp_c >= 70:
                status = "[yellow]WARM[/yellow]"
                style = "yellow"
            elif temp_c >= 55:
                status = "[cyan]MODERATE[/cyan]"
                style = "cyan"
            else:
                status = "[green]COOL[/green]"
                style = "green"
            temp_table.add_row(name, f"[{style}]{temp_c:.1f}°C[/{style}]", status)

        self.console.print(Panel(temp_table, title="Temperatures", border_style="red"))

        fans = cool.get("fans", [])
        if fans:
            fan_table = Table(box=box.SIMPLE)
            fan_table.add_column("Fan", style="cyan")
            fan_table.add_column("Speed (RPM)", style="white")
            for f in fans:
                fan_table.add_row(f.get("name", "Unknown"), str(f.get("rpm", 0)))
            self.console.print(Panel(fan_table, title="Fan Speeds", border_style="cyan"))

    def display_bottlenecks(self) -> None:
        bottlenecks = self.results.get("bottlenecks", {})
        if not bottlenecks:
            self.console.print("[yellow]No bottleneck data available[/yellow]")
            return

        critical = bottlenecks.get("critical", [])
        if critical:
            self.console.print(f"\n[bold red]Detected {len(critical)} critical bottleneck(s)![/bold red]\n")

        for component, info in bottlenecks.items():
            if component in ("critical", "count"):
                continue
            if isinstance(info, dict):
                severity = info.get("severity", "none")
                details = info.get("details", [])
                if severity == "none" and not details:
                    continue
                s_color = {
                    "critical": "red",
                    "high": "red",
                    "medium": "yellow",
                    "low": "cyan",
                    "none": "green",
                }.get(severity, "white")
                s_text = severity.upper()
                table = Table(box=box.SIMPLE)
                table.add_column("Component", style="cyan bold")
                table.add_column("Severity", style="bold")
                table.add_column("Details", style="white")
                for d in details:
                    table.add_row(
                        component.title(),
                        f"[{s_color}]{s_text}[/{s_color}]",
                        d,
                    )
                if details:
                    self.console.print(table)

        if not critical:
            self.console.print("[green]No critical bottlenecks detected. System is well-balanced.[/green]")

    def display_upgrades(self) -> None:
        upgrades = self.results.get("upgrades", {})
        if not upgrades:
            self.console.print("[yellow]No upgrade suggestions available[/yellow]")
            return

        for component, suggestion in upgrades.items():
            if not suggestion.get("needed"):
                continue
            priority = suggestion.get("priority", "low")
            p_color = {"critical": "red", "high": "yellow", "medium": "cyan"}.get(priority, "green")
            current = suggestion.get("current", {})
            recommended = suggestion.get("recommended", {})
            improvements = suggestion.get("improvements", [])

            content = f"[bold]Current:[/bold] "
            for k, v in current.items():
                content += f"{k.replace('_', ' ').title()}: {v}, "
            content = content.rstrip(", ") + "\n"
            content += f"[bold]Recommended:[/bold] "
            for k, v in recommended.items():
                content += f"{k.replace('_', ' ').title()}: {v}, "
            content = content.rstrip(", ") + "\n\n"
            content += "[bold]Expected Improvements:[/bold]\n"
            for imp in improvements:
                content += f"  [green]+[/green] {imp}\n"

            self.console.print(
                Panel(
                    content,
                    title=f"[{p_color}]Upgrade: {component.upper()}[/{p_color}]",
                    border_style=p_color,
                )
            )

    def display_workloads(self) -> None:
        workloads = self.results.get("workloads", {})
        if not workloads:
            self.console.print("[yellow]No workload data available[/yellow]")
            return

        table = Table(box=box.ROUNDED)
        table.add_column("Workload", style="cyan bold")
        table.add_column("Capability", style="bold")

        sorted_workloads = sorted(workloads.items(), key=lambda x: x[0])
        for name, rating in sorted_workloads:
            w_color = {
                "Excellent": "green",
                "Good": "green",
                "Acceptable": "yellow",
                "Limited": "red",
                "Not Recommended": "red",
            }.get(rating, "white")
            table.add_row(
                name.replace("_", " ").title(),
                f"[{w_color}]{rating}[/{w_color}]",
            )

        self.console.print(Panel(table, title="Workload Capability Assessment", border_style="blue"))

    def display_comparisons(self) -> None:
        comparisons = self.results.get("comparisons", {})
        if not comparisons:
            return

        for component, data in comparisons.items():
            table = Table(box=box.ROUNDED)
            table.add_column("Tier", style="cyan bold")
            table.add_column("Performance", style="bold")
            comparisons_list = data.get("comparisons", [])
            for comp in comparisons_list:
                pct = comp.get("percent", 0)
                p_color = "green" if pct >= 100 else ("yellow" if pct >= 50 else "red")
                table.add_row(
                    comp["tier"],
                    f"[{p_color}]{pct:.1f}%[/{p_color}]",
                )
            self.console.print(
                Panel(
                    table,
                    title=f"Comparison: {component.title()}",
                    border_style="blue",
                )
            )

    def display_motherboard(self) -> None:
        mobo = self.results.get("motherboard", {}).get("data", {})
        if not mobo:
            return
        table = make_table(
            "Motherboard Information",
            ["Property", "Value"],
            [
                ["Vendor", mobo.get("vendor", "N/A")],
                ["Model", mobo.get("model", "N/A")],
                ["Version", mobo.get("version", "N/A")],
                ["BIOS Vendor", mobo.get("bios_vendor", "N/A")],
                ["BIOS Version", mobo.get("bios_version", "N/A")],
                ["BIOS Date", mobo.get("bios_date", "N/A")],
                ["Form Factor", mobo.get("form_factor", "N/A")],
                ["Secure Boot", "[green]Enabled[/green]" if mobo.get("secure_boot") else "[yellow]Disabled[/yellow]"],
                ["TPM", "[green]Detected[/green]" if mobo.get("tpm") else "[yellow]Not Detected[/yellow]"],
            ],
        )
        self.console.print(table)

    def display_pci(self) -> None:
        pci = self.results.get("pci", {}).get("data", {})
        devices = pci.get("classified", {})
        if not devices:
            return
        for category, dev_list in devices.items():
            if not dev_list:
                continue
            table = Table(box=box.SIMPLE)
            table.add_column("PCI ID", style="cyan")
            table.add_column("Device", style="white")
            table.add_column("Driver", style="yellow")
            for dev in dev_list:
                table.add_row(
                    dev.get("pci_id", ""),
                    dev.get("description", ""),
                    dev.get("driver", ""),
                )
            self.console.print(Panel(table, title=f"PCI Devices: {category}", border_style="blue"))

    def display_usb(self) -> None:
        usb = self.results.get("usb", {}).get("data", {})
        devices = usb.get("devices", [])
        if not devices:
            return
        table = Table(box=box.ROUNDED)
        table.add_column("Device", style="cyan")
        table.add_column("USB Version", style="white")
        table.add_column("Power", style="white")
        for dev in devices:
            table.add_row(
                dev.get("description", "Unknown"),
                dev.get("usb_version", "N/A"),
                f"{dev.get('power_ma', 'N/A')} mA" if dev.get("power_ma") else "N/A",
            )
        self.console.print(Panel(table, title="USB Devices", border_style="green"))

    def display_virtualization(self) -> None:
        virt = self.results.get("virtualization", {}).get("data", {})
        if not virt:
            return
        table = Table(box=box.ROUNDED)
        table.add_column("Technology", style="cyan bold")
        table.add_column("Status", style="bold")
        detected = virt.get("detected", {})
        for tech, detected_bool in detected.items():
            table.add_row(
                tech.title(),
                "[green]Detected[/green]" if detected_bool else "[yellow]Not Detected[/yellow]",
            )
        if virt.get("hypervisor"):
            table.add_row("Hypervisor", virt["hypervisor"])
        if virt.get("container_runtime"):
            table.add_row("Container Runtime", virt["container_runtime"])
        self.console.print(Panel(table, title="Virtualization & Containers", border_style="cyan"))

    def display_monitors(self) -> None:
        monitors = self.results.get("monitors", {}).get("data", {})
        mon_list = monitors.get("monitors", [])
        if not mon_list:
            return
        table = Table(box=box.ROUNDED)
        table.add_column("Monitor", style="cyan")
        table.add_column("Resolution", style="white")
        table.add_column("Connected", style="bold")
        for m in mon_list:
            res = ""
            if m.get("current_width") and m.get("current_height"):
                res = f"{m['current_width']}x{m['current_height']}"
            if m.get("preferred_width") and m.get("preferred_height"):
                res = f"{m['preferred_width']}x{m['preferred_height']}"
            table.add_row(
                m.get("name", m.get("manufacturer", "Unknown")),
                res,
                "[green]Yes[/green]" if m.get("connected", True) else "[red]No[/red]",
            )
        self.console.print(Panel(table, title="Monitors", border_style="blue"))

    def display_full_report(self) -> None:
        self.display_header()
        self.display_summary()
        self.display_overall_score()
        self.display_cpu()
        self.display_memory()
        self.display_gpu()
        self.display_storage()
        self.display_motherboard()
        self.display_network()
        self.display_temperatures()
        self.display_bottlenecks()
        self.display_upgrades()
        self.display_workloads()
        self.display_comparisons()
        self.display_virtualization()
        self.display_pci()
        self.display_usb()
        self.display_monitors()
