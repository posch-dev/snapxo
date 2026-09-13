import importlib.util
from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console

from ..formats.pdfgen import CHATS, MEDIA_DETAILS, MEDIA_PLAIN, pdf_dir, render_pdfs
from ..formats.spreadsheet import export_stats, spreadsheet_dir
from ..formats.tables import FORMATS
from ..pages.loose import write_loose_pages
from ..tools.browser import playwright_status
from ..tools.doctor import print_browser_help, status_line

console = Console()

LOOSE_PAGES = ("gallery.html", "chats.html", "stats.html")
PDF_FLAGS = {"gallery": "--media-details", "memories": "--media-plain", "stats": "--stats", "chats": "--chats"}


@dataclass
class Outputs:
    pdfs: list[str] = field(default_factory=list)
    spreadsheets: list[str] = field(default_factory=list)
    pages: bool = False

    def __bool__(self) -> bool:
        return bool(self.pdfs or self.spreadsheets or self.pages)

    def commands(self, archive: Path) -> list[str]:
        commands = []
        if self.pdfs:
            commands.append(f"snapxo pdf {archive} {' '.join(PDF_FLAGS[kind] for kind in self.pdfs)}")
        commands += [f"snapxo spreadsheet {archive} --format {name}" for name in self.spreadsheets]
        if self.pages:
            commands.append(f"snapxo html {archive}")
        return commands


def found_outputs(archive: Path) -> Outputs:
    pdf = pdf_dir(archive)
    present = {
        # Before 2.0.1 the media PDFs were one file each.
        "gallery": (pdf / MEDIA_DETAILS).is_dir() or (pdf / f"{MEDIA_DETAILS}.pdf").is_file(),
        "memories": (pdf / MEDIA_PLAIN).is_dir() or (pdf / f"{MEDIA_PLAIN}.pdf").is_file(),
        "stats": (pdf / "stats.pdf").is_file(),
        "chats": (pdf / CHATS).is_dir(),
    }
    folder = spreadsheet_dir(archive)
    written = {path.suffix.lstrip(".") for path in folder.glob("snapxo-*")} if folder.is_dir() else set()
    return Outputs(
        pdfs=[kind for kind, found in present.items() if found],
        spreadsheets=[name for name in FORMATS if name in written],
        pages=any((archive / name).is_file() for name in LOOSE_PAGES) or (archive / "conversations").is_dir(),
    )


def check_tools(outputs: Outputs) -> bool:
    browser_ok, reason = playwright_status() if outputs.pdfs else (True, "")
    openpyxl_ok = "xlsx" not in outputs.spreadsheets or importlib.util.find_spec("openpyxl") is not None
    if browser_ok and openpyxl_ok:
        return True

    console.print("[red]--refresh cannot redo everything this archive has. Nothing has been written.[/red]")
    if not browser_ok:
        status_line("missing", "PDF browser", f"for pdf/, playwright {reason}")
    if not openpyxl_ok:
        status_line("missing", "openpyxl", "for the xlsx spreadsheet")
    console.print()
    if not browser_ok:
        print_browser_help(reason)
    if not openpyxl_ok:
        console.print("[bold]XLSX spreadsheets need openpyxl:[/bold]")
        console.print('    [cyan]pip install "snapxo[spreadsheet]"[/cyan]')
    console.print("Or leave out --refresh and bring these up to date by hand afterwards.")
    return False


def _refresh_spreadsheet(archive: Path, name: str) -> bool:
    # Rewritten files get a new inode, the ones left untouched are the outdated ones.
    folder = spreadsheet_dir(archive)
    before = {path: path.stat().st_ino for path in folder.glob(f"snapxo-*.{name}")}
    if not export_stats(archive, spreadsheet_format=name):
        return False
    for path, inode in before.items():
        if path.exists() and path.stat().st_ino == inode:
            path.unlink()
    return True


def _pdfs_rendered(archive: Path, kinds: list[str]) -> bool:
    try:
        return render_pdfs(archive, **{kind: kind in kinds for kind in PDF_FLAGS})
    except SystemExit:
        return False


def refresh_outputs(archive: Path, outputs: Outputs) -> bool:
    failed = []
    if outputs.pdfs and not _pdfs_rendered(archive, outputs.pdfs):
        failed.append(outputs.commands(archive)[0])
    for name in outputs.spreadsheets:
        if not _refresh_spreadsheet(archive, name):
            failed.append(f"snapxo spreadsheet {archive} --format {name}")
    if outputs.pages and not write_loose_pages(archive):
        failed.append(f"snapxo html {archive}")

    if failed:
        console.print(f"[yellow]{archive} is complete, but these could not be refreshed and are "
                      f"still the old ones:[/yellow]")
        for command in failed:
            console.print(f"  [cyan]{command}[/cyan]")
    return not failed
