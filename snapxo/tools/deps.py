# A missing tool names the command that installs it on this machine.

import shutil
import sys

from rich.console import Console

console = Console()


def _platform() -> str:
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


def _linux_package_manager() -> tuple[str, str] | None:
    for manager, command in (
        ("apt", "sudo apt install"),
        ("dnf", "sudo dnf install"),
        ("pacman", "sudo pacman -S"),
        ("zypper", "sudo zypper install"),
        ("apk", "sudo apk add"),
        ("emerge", "sudo emerge"),
    ):
        if shutil.which(manager):
            return manager, command
    return None


def _windows_package_manager() -> tuple[str, str] | None:
    for manager, command in (
        ("winget", "winget install"),
        ("choco", "choco install"),
        ("scoop", "scoop install"),
    ):
        if shutil.which(manager):
            return manager, command
    return None


def ffmpeg_install_commands() -> list[str]:
    # Best guess for this system first.
    system = _platform()

    if system == "windows":
        found = _windows_package_manager()
        if found:
            manager, command = found
            package = "Gyan.FFmpeg" if manager == "winget" else "ffmpeg"
            return [f"{command} {package}"]
        return ["winget install Gyan.FFmpeg"]

    if system == "macos":
        return ["brew install ffmpeg"]

    found = _linux_package_manager()
    if found:
        _, command = found
        return [f"{command} ffmpeg"]
    return ["sudo apt install ffmpeg"]


def ffmpeg_missing_message() -> str:
    commands = ffmpeg_install_commands()
    lines = [
        "[bold red]ffmpeg is not installed.[/bold red]",
        "",
        "It is needed for video encoding, overlay burning and voice conversion.",
        "",
        "[bold]Install it, then run the command again:[/bold]",
    ]
    lines += [f"    [cyan]{c}[/cyan]" for c in commands]
    lines += [
        "",
        "Alternatives:",
        # The escaped bracket keeps rich from reading it as markup.
        '  - Get binaries through pip:  [cyan]pip install "snapxo\\[ffmpeg]"[/cyan]',
        "    (those builds usually have no hardware encoding, so it will be slower)",
        "  - Already installed elsewhere? Point at it with [cyan]--ffmpeg-path[/cyan] and [cyan]--ffprobe-path[/cyan]",
        "  - Skip video processing entirely with [cyan]--no-encode --no-overlay[/cyan]",
        "  - Or take the photos only, which needs no ffmpeg at all: [cyan]--types photos[/cyan]",
        "",
        "Download: [blue]https://ffmpeg.org/download.html[/blue]",
    ]
    return "\n".join(lines)


def playwright_missing_message(reason: str) -> str:
    # "package" is no pip install, "browser" is no Chromium.
    if reason == "package":
        lines = [
            "[bold red]Playwright is not installed.[/bold red]",
            "",
            "It renders the PDF versions of conversations and stats.",
            "",
            "[bold]Install it, then run the command again:[/bold]",
            "    [cyan]pip install playwright[/cyan]",
            "    [cyan]playwright install chromium[/cyan]",
        ]
    else:
        lines = [
            "[bold red]Playwright has no browser installed.[/bold red]",
            "",
            "The Python package is there, but Chromium itself still has to be downloaded.",
            "",
            "[bold]Run this, then try again:[/bold]",
            "    [cyan]playwright install chromium[/cyan]",
        ]

    if _platform() == "linux":
        lines += [
            "",
            "On Linux Chromium may also need system libraries:",
            "    [cyan]playwright install-deps chromium[/cyan]",
        ]

    lines += [
        "",
        "Or stay with the pages, which need nothing: [cyan]snapxo html FOLDER[/cyan]",
    ]
    return "\n".join(lines)


def require_ffmpeg(ff) -> None:
    if ff.check():
        return
    console.print()
    console.print(ffmpeg_missing_message())
    console.print()
    raise SystemExit(1)


def require_playwright() -> None:
    from .browser import playwright_status

    ok, reason = playwright_status()
    if ok:
        return
    console.print()
    console.print(playwright_missing_message(reason))
    console.print()
    raise SystemExit(1)
