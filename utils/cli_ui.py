from __future__ import annotations

import logging
import os
from typing import Any, Mapping, Optional, Sequence

try:
    from rich import box
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    _console = Console()
    _RICH_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised only without optional UI packages
    _console = None
    _RICH_AVAILABLE = False

logger = logging.getLogger("inventory_app")


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def is_rich_available() -> bool:
    return _RICH_AVAILABLE


def _fallback(message: str, level: int = logging.INFO) -> None:

    logger.log(level, message)


def print_banner(title: str, subtitle: str = "") -> None:
    
    if _RICH_AVAILABLE:
        text = f"[bold cyan]{title}[/bold cyan]"
        if subtitle:
            text += f"\n[dim]{subtitle}[/dim]"
        _console.print(Panel.fit(text, border_style="cyan", box=box.ROUNDED))
    else:
        _fallback("=" * 60)
        _fallback(title.center(60))
        if subtitle:
            _fallback(subtitle.center(60))
        _fallback("=" * 60)


def print_success(message: str) -> None:
   
    if _RICH_AVAILABLE:
        _console.print(f"[bold green]✔ {message}[/bold green]")
    else:
        _fallback(f"[OK] {message}")


def print_error(message: str) -> None:
 
    if _RICH_AVAILABLE:
        _console.print(f"[bold red]✘ {message}[/bold red]")
    else:
        _fallback(f"[ERROR] {message}", logging.ERROR)


def print_warning(message: str) -> None:

    if _RICH_AVAILABLE:
        _console.print(f"[bold yellow]⚠ {message}[/bold yellow]")
    else:
        _fallback(f"[WARNING] {message}", logging.WARNING)


def print_info(message: str) -> None:
  
    if _RICH_AVAILABLE:
        _console.print(f"[bold blue]ℹ {message}[/bold blue]")
    else:
        _fallback(f"[INFO] {message}")


def print_table(
    title: str,
    columns: Sequence[Any],
    rows: Sequence[Sequence[Any]],
    row_styles: Optional[Sequence[Optional[str]]] = None,
) -> None:
    if not rows:
        print_warning(f"No records found for '{title}'.")
        return

    if _RICH_AVAILABLE:
        table = Table(title=title, box=box.SIMPLE_HEAVY, header_style="bold magenta")
        for col in columns:
            table.add_column(str(col))
        for index, row in enumerate(rows):
            style = row_styles[index] if row_styles and index < len(row_styles) else None
            table.add_row(*[str(cell) for cell in row], style=style)
        _console.print(table)
        return

    try:
        from tabulate import tabulate
        _fallback(f"\n{title}")
        _fallback(tabulate(rows, headers=columns, tablefmt="grid"))
    except ImportError:
        _fallback(f"\n{title}")
        _print_plain_grid_table(columns, rows)


def _print_plain_grid_table(columns: Sequence[Any], rows: Sequence[Sequence[Any]]) -> None:
    str_rows = [[str(cell) for cell in row] for row in rows]
    headers = [str(col) for col in columns]
    widths = [len(header) for header in headers]
    for row in str_rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))

    def border(left: str, mid: str, right: str, fill: str = "─") -> str:
        return left + mid.join(fill * (width + 2) for width in widths) + right

    def render_row(cells: Sequence[str]) -> str:
        padded = [f" {cell.ljust(widths[i])} " for i, cell in enumerate(cells)]
        return "│" + "│".join(padded) + "│"

    _fallback(border("┌", "┬", "┐"))
    _fallback(render_row(headers))
    _fallback(border("├", "┼", "┤"))
    for row in str_rows:
        _fallback(render_row(row))
    _fallback(border("└", "┴", "┘"))


def print_menu(title: str, options: Mapping[str, str]) -> None:
    if _RICH_AVAILABLE:
        _console.print(f"[bold cyan]{title}[/bold cyan]")
        for key, label in options.items():
            _console.print(f"  [bold yellow]{key}[/bold yellow]. {label}")
    else:
        _fallback(title)
        for key, label in options.items():
            _fallback(f"  {key}. {label}")


def pause() -> None:
    input("\nPress Enter to continue...")
