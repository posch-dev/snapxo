# snapxo -i. Every answer defaults to the plain command, so pressing Enter
# through the whole thing changes nothing.

from pathlib import Path

from rich.columns import Columns
from rich.console import Console
from rich.prompt import Confirm, IntPrompt, Prompt

from .clock import COMMON_ZONES, UTC_NAME, is_known
from .formats.dockergen import DEFAULT_PORT
from .selection import SOURCES, TYPES

console = Console()

COMMANDS = [
    ("info", "Look at a Snapchat export without converting it"),
    ("organize", "Turn a Snapchat export into an archive"),
    ("rebuild", "Bring a finished archive up to date"),
    ("html", "Write the one page per topic versions"),
    ("pdf", "Render a finished archive to PDFs"),
    ("spreadsheet", "Write the statistics to a spreadsheet"),
    ("merge", "Merge several finished archives into one"),
    ("docker", "Serve a finished archive over HTTP"),
    ("verify", "Check a finished archive against its manifest"),
    ("doctor", "Check whether the external tools are in place"),
]

SOURCE_LABELS = {"memories": "Memories, the ones you saved yourself",
                 "chat": "Chat media, everything sent in a conversation"}
TYPE_LABELS = {"photos": "Photos", "videos": "Videos", "voice": "Voice messages"}


class NotATerminal(Exception):
    pass


def require_terminal() -> None:
    # rich decides, because rich prompts. isatty() still reports a terminal under
    # Git Bash with stdin redirected.
    if not console.is_interactive:
        raise NotATerminal


def _numbered_menu(question: str, entries: list[str], default: int) -> int:
    console.print(f"\n[bold]{question}[/bold]")
    for number, entry in enumerate(entries, 1):
        console.print(f"  [yellow]{number:2d}[/yellow] {entry}")
    console.print("  [yellow] 0[/yellow] Cancel")

    choice = IntPrompt.ask("\nPick a number", default=default)
    if choice == 0:
        raise SystemExit(0)
    if not 1 <= choice <= len(entries):
        console.print("[red]No such option.[/red]")
        raise SystemExit(1)
    return choice


def pick_command() -> str:
    labels = [description for _name, description in COMMANDS]
    return COMMANDS[_numbered_menu("What would you like to do?", labels, 2) - 1][0]


def ask_existing_folder(question: str) -> Path:
    while True:
        folder = Path(Prompt.ask(question).strip().strip('"'))
        if folder.is_dir():
            return folder
        console.print(f"[red]{folder} is not a folder.[/red]")


def ask_names(question: str, names: tuple[str, ...], labels: dict[str, str]) -> list[str]:
    console.print(f"\n[bold]{question}[/bold]")
    for number, name in enumerate(names, 1):
        console.print(f"  [yellow]{number:2d}[/yellow] {labels[name]}")
    console.print("  [dim]Enter for all of them[/dim]")

    response = Prompt.ask("\nNumbers, comma separated", default="").strip()
    if not response:
        return []

    try:
        wanted = {int(part.strip()) for part in response.split(",") if part.strip()}
    except ValueError:
        console.print("[red]Those are not numbers.[/red]")
        raise SystemExit(1) from None

    picked = [name for number, name in enumerate(names, 1) if number in wanted]
    if not picked:
        console.print("[red]Nothing picked.[/red]")
        raise SystemExit(1)
    return [] if len(picked) == len(names) else picked


def ask_timezone() -> str:
    # Filled downwards, so the regions stay together in a column.
    console.print("\n[bold]Which timezone should the timestamps be shown in?[/bold]")
    console.print(Columns(
        [f"[yellow]{number:2d}[/yellow] {zone}" for number, zone in enumerate(COMMON_ZONES, 1)],
        padding=(0, 2), column_first=True,
    ))
    console.print("  [yellow] 0[/yellow] Type one myself, or any other IANA name")

    choice = IntPrompt.ask("\nPick a number", default=len(COMMON_ZONES))
    if 1 <= choice <= len(COMMON_ZONES):
        return COMMON_ZONES[choice - 1]

    while True:
        typed = Prompt.ask("Timezone", default=UTC_NAME).strip()
        if is_known(typed):
            return typed
        console.print(f"[red]{typed} is not a timezone this system knows.[/red]")


def _maybe_timezone(args: list[str], question: str) -> None:
    if Confirm.ask(question, default=False):
        args += ["--timezone", ask_timezone()]


def ask_info() -> list[str]:
    source = Prompt.ask("Export ZIP or folder").strip().strip('"')
    return ["info", source]


def ask_organize() -> list[str]:
    source = Prompt.ask("Export ZIP or folder").strip().strip('"')
    output = Prompt.ask("Where should the archive go").strip().strip('"')
    args = ["organize", source, "-o", output]

    # Media first: answering "photos only" makes the encoding question pointless.
    sources = ask_names("Which media should be copied?", SOURCES, SOURCE_LABELS)
    if sources:
        args += ["--media", ",".join(sources)]
    kinds = ask_names("Which kinds?", TYPES, TYPE_LABELS)
    if kinds:
        args += ["--types", ",".join(kinds)]

    wants_videos = not kinds or "videos" in kinds
    if wants_videos and not Confirm.ask(
            "Encode videos to H.265 (slow, saves a lot of space)", default=True):
        args.append("--no-encode")
    if not Confirm.ask("Burn overlays onto the media", default=True):
        args.append("--no-overlay")
    if not Confirm.ask("Remove duplicates", default=True):
        args.append("--no-dedup")
    if Confirm.ask("Keep Snapchat's own HTML pages as well", default=False):
        args.append("--keep-raw-html")
    _maybe_timezone(args, "Convert the timestamps out of UTC into your timezone")

    args.append("--yes")
    return args


def ask_rebuild() -> list[str]:
    args = ["rebuild", str(ask_existing_folder("Which archive"))]
    _maybe_timezone(args, "Show the timestamps in a different timezone")
    return args


def ask_html() -> list[str]:
    args = ["html", str(ask_existing_folder("Which archive"))]
    if Confirm.ask("Only some contacts", default=False):
        args += ["--chats-with", Prompt.ask("Names, comma separated").strip()]
    least = IntPrompt.ask("Leave out conversations shorter than how many messages", default=1)
    if least > 1:
        args += ["--min-messages", str(least)]
    _maybe_timezone(args, "Show the timestamps in a different timezone")
    return args


PDF_PARTS = [
    ("--media-details", "The media with every detail beside each file"),
    ("--media-plain", "The picture book, media and dates and nothing else"),
    ("--stats", "The statistics"),
    ("--chats", "The conversations"),
]


def ask_pdf() -> list[str]:
    args = ["pdf", str(ask_existing_folder("Which archive"))]
    if Confirm.ask("Render all of it", default=True):
        return args

    picked = ask_names("Which parts?", tuple(flag for flag, _ in PDF_PARTS),
                       dict(PDF_PARTS))
    args += picked or [flag for flag, _ in PDF_PARTS]
    return args


def ask_spreadsheet() -> list[str]:
    args = ["spreadsheet", str(ask_existing_folder("Which archive"))]
    chosen = _numbered_menu("Which format?", [
        "XLSX, with real Excel charts you can edit",
        "ODS, OpenDocument, needs nothing extra",
        "CSV, one file per table",
    ], 1)
    args += ["--format", ["xlsx", "ods", "csv"][chosen - 1]]
    if Confirm.ask("Write it somewhere other than inside the archive", default=False):
        args += ["-o", Prompt.ask("Where").strip().strip('"')]
    return args


def ask_docker() -> list[str]:
    args = ["docker", str(ask_existing_folder("Which archive"))]
    console.print("[yellow]The archive is served on every network interface.[/yellow]")
    args.append("--password" if Confirm.ask("Protect it with a password", default=True)
                else "--no-auth")
    args += ["--port", str(IntPrompt.ask("Host port", default=DEFAULT_PORT))]
    if Confirm.ask("Start it now with docker compose up", default=False):
        args.append("--up")
    return args


def ask_merge() -> list[str]:
    folders = []
    while True:
        folders.append(str(ask_existing_folder(f"Archive {len(folders) + 1}")))
        if len(folders) >= 2 and not Confirm.ask("Add another", default=False):
            break
    args = ["merge", *folders]
    args += ["-o", Prompt.ask("Where should the merged archive go").strip().strip('"')]
    if Confirm.ask("[red]Delete the source folders after a verified merge[/red]", default=False):
        args.append("--delete-sources")
    return args


def ask_verify() -> list[str]:
    args = ["verify", str(ask_existing_folder("Which archive"))]
    if Confirm.ask("Read every file and compare checksums (slow)", default=False):
        args.append("--hash")
    return args


ASKERS = {
    "info": ask_info,
    "organize": ask_organize,
    "rebuild": ask_rebuild,
    "html": ask_html,
    "pdf": ask_pdf,
    "spreadsheet": ask_spreadsheet,
    "merge": ask_merge,
    "docker": ask_docker,
    "verify": ask_verify,
    "doctor": lambda: ["doctor"],
}


def build_arguments(command: str | None = None) -> list[str]:
    # The argv the plain command takes, so the wizard runs the same code path.
    require_terminal()
    return ASKERS[command or pick_command()]()


def show_command(args: list[str]) -> None:
    printable = " ".join(f'"{part}"' if " " in part else part for part in args)
    console.print(f"\n[dim]Same as:[/dim] [bold]snapxo {printable}[/bold]\n")
