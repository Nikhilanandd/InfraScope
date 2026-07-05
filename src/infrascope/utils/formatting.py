from __future__ import annotations

from typing import Any

from rich import box
from rich.console import Console, Group
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table
from rich.text import Text


def create_progress(description: str = "Scanning...") -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=Console(),
    )


def health_badge(value: float, good_threshold: float = 70, warn_threshold: float = 40) -> Text:
    if value >= good_threshold:
        return Text(f"{value:.0f}%", style="bold green")
    if value >= warn_threshold:
        return Text(f"{value:.0f}%", style="bold yellow")
    return Text(f"{value:.0f}%", style="bold red")


def status_badge(status: str) -> Text:
    status_colors = {
        "excellent": "green",
        "good": "green",
        "acceptable": "yellow",
        "limited": "red",
        "not recommended": "red",
        "ok": "green",
        "warning": "yellow",
        "critical": "red",
        "healthy": "green",
        "degraded": "yellow",
        "failed": "red",
        "yes": "green",
        "no": "red",
        "detected": "green",
        "not detected": "yellow",
        "enabled": "green",
        "disabled": "yellow",
    }
    style = status_colors.get(status.lower().strip(), "white")
    return Text(f"  {status.upper()}  ", style=f"bold {style} on {style}_dim")


def gauge_bar(value: float, max_value: float, width: int = 20) -> str:
    ratio = min(value / max_value, 1.0) if max_value > 0 else 0
    filled = int(ratio * width)
    empty = width - filled
    bar = "█" * filled + "░" * empty
    return bar


def percent_bar(value: float, max_value: float = 100.0) -> Panel:
    ratio = min(value / max_value, 1.0) if max_value > 0 else 0
    percent = ratio * 100
    if percent >= 80:
        color = "red"
    elif percent >= 50:
        color = "yellow"
    else:
        color = "green"
    bar = gauge_bar(value, max_value)
    return Panel(
        f"[{color}]{bar}[/{color}] {percent:.1f}%",
        border_style=color,
        padding=(0, 1),
    )


def make_table(title: str, columns: list[str], rows: list[list[Any]]) -> Table:
    table = Table(title=title, box=box.ROUNDED, highlight=True)
    for col in columns:
        table.add_column(col, style="cyan" if col == columns[0] else "white")
    for row in rows:
        table.add_row(*[str(c) for c in row])
    return table


def format_dict_as_table(data: dict[str, Any], title: str = "") -> Table:
    table = Table(title=title, box=box.SIMPLE, highlight=True)
    table.add_column("Property", style="cyan bold")
    table.add_column("Value", style="white")
    for key, value in data.items():
        table.add_row(str(key), str(value))
    return table


def card(title: str, content: Any, border: str = "blue") -> Panel:
    return Panel(content, title=title, border_style=border, padding=(1, 2))


def section(title: str, content: Any) -> Group:
    return Group(Text(f"\n[bold cyan]═══ {title} ═══[/bold cyan]\n"), content)
