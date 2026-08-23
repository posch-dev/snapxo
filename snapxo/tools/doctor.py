import shutil
from pathlib import Path

from rich.console import Console

from ..read.zips import GIB
from .browser import playwright_status
from .deps import ffmpeg_install_commands
from .ffmpeg import FFmpeg

console = Console()


def _line(state: str, label: str, detail: str = "") -> None:
    # Padded before the markup, rich would otherwise count the tags as width.
    color = {"ok": "green", "missing": "red"}.get(state, "yellow")
    console.print(f"  [{color}]{state:<9}[/{color}] {label:<20}" + (f" [dim]{detail}[/dim]" if detail else ""))


def run_doctor() -> bool:
    console.rule("[bold yellow]Tools[/bold yellow]")

    ff = FFmpeg()
    has_ffmpeg = ff.check()
    _line("ok" if has_ffmpeg else "missing", "ffmpeg / ffprobe", ff.ffmpeg if has_ffmpeg else "")
    if has_ffmpeg:
        _line("ok" if ff.qsv_available else "software", "hardware encoding",
              "Intel QSV" if ff.qsv_available else "falling back to libx265")

    browser_ok, reason = playwright_status()
    _line("ok" if browser_ok else "missing", "PDF browser", "" if browser_ok else f"playwright {reason}")

    console.rule("[bold yellow]Space[/bold yellow]")
    here = Path.cwd()
    free = shutil.disk_usage(str(here)).free
    console.print(f"  {free / GIB:.1f} GB free on {here.anchor or here}")
    console.print("  [dim]A full export needs room for the ZIP, the extracted copy and the output[/dim]")

    if has_ffmpeg and browser_ok:
        console.print("\n[green]Everything is in place.[/green]")
        return True

    console.print()
    if not has_ffmpeg:
        console.print("[bold]ffmpeg is needed for videos, overlays and voice messages:[/bold]")
        for command in ffmpeg_install_commands():
            console.print(f"    [cyan]{command}[/cyan]")
        console.print("    [dim]or run with --types photos, which needs no ffmpeg[/dim]")
    if not browser_ok:
        console.print("[bold]`snapxo pdf` needs Chromium:[/bold]")
        if reason == "package":
            console.print("    [cyan]pip install playwright[/cyan]")
        console.print("    [cyan]playwright install chromium[/cyan]")
        console.print("    [dim]or use `snapxo html`, which needs nothing[/dim]")
    return False
