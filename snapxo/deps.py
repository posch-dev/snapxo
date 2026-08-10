# Checks for external tools. A missing one should say what is missing, print the
# command that fixes it on this machine, and stop before any long work is done.

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
    # Returns (manager, install command prefix) for whatever this distro uses.
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
    # Install commands for ffmpeg, best guess for this system first.
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
        # \[ escapes the bracket so rich prints it instead of reading it as markup
        '  - Get binaries through pip:  [cyan]pip install "snapxo\\[ffmpeg]"[/cyan]',
        "    (those builds usually have no hardware encoding, so it will be slower)",
        "  - Already installed elsewhere? Point at it with [cyan]--ffmpeg-path[/cyan] and [cyan]--ffprobe-path[/cyan]",
        "  - Skip video processing entirely with [cyan]--no-encode --no-overlay[/cyan]",
        "",
        "Download: [blue]https://ffmpeg.org/download.html[/blue]",
    ]
    return "\n".join(lines)


def playwright_missing_message(reason: str) -> str:
    # `reason` is "package" (no pip install) or "browser" (no Chromium).
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
        "Or skip PDFs and generate HTML instead: [cyan]--conversation-format html[/cyan]",
    ]
    return "\n".join(lines)


def require_ffmpeg(ff) -> None:
    # Abort with instructions if ffmpeg or ffprobe cannot be run.
    if ff.check():
        return
    console.print()
    console.print(ffmpeg_missing_message())
    console.print()
    raise SystemExit(1)


def require_playwright() -> None:
    # Abort with instructions if PDFs cannot be rendered.
    from .pdf import playwright_status

    ok, reason = playwright_status()
    if ok:
        return
    console.print()
    console.print(playwright_missing_message(reason))
    console.print()
    raise SystemExit(1)
