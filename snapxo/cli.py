from datetime import datetime
from pathlib import Path

import click
from rich.console import Console

from . import __version__
from .archive.folder import resolve_many, resolve_one
from .archive.merge import merge_outputs
from .archive.rebuild import rebuild_folder
from .archive.verify import print_report, verify_folder, write_checksums
from .clock import UTC_NAME, is_known
from .config import Config
from .formats.dockergen import DEFAULT_PORT, compose_target, compose_up, write_compose
from .formats.pdfgen import render_pdfs
from .formats.spreadsheet import export_stats
from .formats.tables import FORMATS
from .pages.loose import write_loose_pages
from .pipeline import run_pipeline
from .selection import SOURCES, TYPES
from .selection import parse as parse_selection
from .tools.doctor import run_doctor

console = Console()


def _wizard_arguments(command: str | None = None) -> list[str]:
    from .wizard import NotATerminal, build_arguments, show_command

    try:
        args = build_arguments(command)
    except NotATerminal:
        console.print("[red]Interactive mode needs a terminal. Pass the flags instead, "
                      "see `snapxo --help`.[/red]")
        raise SystemExit(1) from None
    show_command(args)
    return args


PASS_THROUGH = ("--help", "-h", "--version", "-i", "--interactive")


class SnapxoGroup(click.Group):
    # Every run names a command. The old silent fallback to `organize` made a
    # typo look like an export path.

    def parse_args(self, ctx, args):
        if args and args[0] in ("-i", "--interactive"):
            args = _wizard_arguments()
        elif len(args) == 2 and args[0] in self.commands and args[1] in ("-i", "--interactive"):
            args = _wizard_arguments(args[0])
        if args and args[0] not in self.commands and args[0] not in PASS_THROUGH:
            _complain_about(args[0])
        return super().parse_args(ctx, args)

    def format_epilog(self, ctx, formatter):
        # click indents the epilog and rewraps it, the buffer keeps it flush left.
        if not self.epilog:
            return
        formatter.write_paragraph()
        for line in self.epilog.splitlines():
            formatter.write(line + "\n")


def _complain_about(first: str) -> None:
    # A path where a command belongs is the old shortcut, so it gets its own line.
    looks_like_a_path = first.lower().endswith(".zip") or Path(first).exists()
    console.print(f"[red]{first} is not a SnapXO command.[/red]")
    if looks_like_a_path:
        console.print(f"  To organize it:  [cyan]snapxo organize {first} -o ARCHIVE[/cyan]")
        console.print("  [dim]Earlier versions took a path without a command. They no longer "
                      "do, because a mistyped command looked like an export path.[/dim]")
    console.print()
    console.print("Run [cyan]snapxo --help[/cyan] for the commands, or "
                  "[cyan]snapxo -i[/cyan] to be asked instead.")
    raise SystemExit(2)


def _confirm_no_meta(yes: bool, dry_run: bool) -> None:
    # rebuild and merge have nothing else to work from, and the export is usually
    # deleted long before anyone finds out.
    console.print()
    console.print("[bold yellow]--no-meta leaves out the raw export.[/bold yellow]")
    console.print("  Without _meta/json/ this archive can never be rebuilt with a newer")
    console.print("  SnapXO, and it can never be merged with another one. Both need the")
    console.print("  original JSON, and there is no way to put it back afterwards.")
    console.print()

    if dry_run:
        console.print("[dim]Nothing is written on a dry run.[/dim]\n")
        return
    if yes:
        console.print("[dim]-y was given, carrying on.[/dim]\n")
        return

    if not console.is_interactive:
        console.print("[red]There is no terminal to confirm on. Pass -y if you meant it.[/red]")
        raise SystemExit(1)

    if not click.confirm("Continue without the raw export?", default=False):
        raise SystemExit(0)
    console.print()


def _check_timezone(name: str) -> None:
    if name and not is_known(name):
        console.print(f"[red]{name} is not a timezone this system knows. Try one like "
                      f"Europe/Vienna, or leave it out for {UTC_NAME}.[/red]")
        raise SystemExit(1)


def _require_output(output, optional: bool) -> None:
    if not output and not optional:
        raise click.UsageError("-o/--output is required, except with --dry-run")


def _is_iso_date(value: str) -> bool:
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return False
    return True


GROUP_EPILOG = """\
Try:
snapxo info EXPORT            what a Snapchat export contains, writes nothing
snapxo organize --help        all options for turning one into an archive
snapxo rebuild --help         bring a finished archive up to date
snapxo html --help            the one page per topic versions
snapxo pdf --help             the same, rendered for printing
snapxo spreadsheet --help     the statistics as a table
snapxo merge --help           fold several archives into one
snapxo docker --help          serve an archive over HTTP
snapxo verify --help          check an archive against its manifest
snapxo doctor                 check whether ffmpeg and the PDF browser are there
snapxo -i                     answer questions instead of reading the flags\
"""


@click.group(cls=SnapxoGroup, epilog=GROUP_EPILOG)
@click.version_option(version=__version__)
def main():
    """Turn a Snapchat data export into an offline archive you can browse on any device."""


@main.command("merge")
@click.argument("folders", nargs=-1, required=True, type=click.Path(exists=True, file_okay=False))
@click.option("-o", "--output", type=click.Path(),
              help="Target directory for the merged export (not needed for --dry-run)")
@click.option("--hardlink", is_flag=True, help="Link files instead of copying (same drive only, no extra space)")
@click.option("--delete-sources", is_flag=True, help="Delete the input folders after a verified merge")
@click.option("-y", "--yes", is_flag=True, help="Don't ask before deleting the input folders")
@click.option("--folder-structure", type=click.Choice(["year", "year-month"]), default="year", show_default=True,
              help="One folder per year, or one per month")
@click.option("--verify/--no-verify", default=True, show_default=True,
              help="Check the input folders against their manifests before merging")
@click.option("--skip-damaged", is_flag=True,
              help="With --no-verify: leave damaged files out instead of taking them along marked")
@click.option("--dry-run", is_flag=True, help="Show what would happen, without it happening")
def merge_command(folders, output, hardlink, delete_sources, yes, folder_structure,
                  verify, skip_damaged, dry_run):
    """Merge finished output folders into one.

    FOLDERS can be any number of output folders, or a parent folder holding
    them. Pointing at _meta or at a year folder works too, SnapXO looks around
    for the archive itself. Deduplicates by content, renumbers everything
    chronologically and rebuilds the pages afterwards, so a `rebuild` run after
    a merge is not needed. Media is never re-encoded.

    Every input folder is checked against its manifest first; damaged files stop
    the merge unless --no-verify is given, which takes them along marked as
    damaged. Only --dry-run works without -o.
    """
    _require_output(output, dry_run)
    if delete_sources and not verify:
        # Unchecked inputs plus deleted originals loses data for good.
        raise click.UsageError("--delete-sources cannot be combined with --no-verify")
    if skip_damaged and verify:
        raise click.UsageError("--skip-damaged only applies together with --no-verify")

    inputs = resolve_many([Path(f) for f in folders])
    if not inputs:
        raise SystemExit(1)

    merge_outputs(
        inputs=inputs,
        output=Path(output) if output else None,
        hardlink=hardlink,
        delete_sources=delete_sources,
        yes=yes,
        folder_structure=folder_structure,
        verify=verify,
        skip_damaged=skip_damaged,
        dry_run=dry_run,
    )


@main.command("rebuild")
@click.argument("folder", type=click.Path(exists=True, file_okay=False))
@click.option("--timezone", default="", metavar="ZONE",
              help="Show timestamps in this timezone instead of the one stored in the archive")
@click.option("--dry-run", is_flag=True, help="Show what would happen, without it happening")
@click.option("-v", "--verbose", is_flag=True, help="Print every file as it is processed")
def rebuild_command(folder, timezone, dry_run, verbose):
    """Rebuild the pages, the map and the thumbnails of a finished output folder.

    Reads _meta/manifest.json and _meta/json/, then writes the pages again. This
    is how a folder organized with an older version picks up new page features
    without the original export, which is usually long deleted. Your media files
    are never touched. `merge` already does this at the end, so it is not needed
    after a merge.
    """
    _check_timezone(timezone)
    archive = resolve_one(Path(folder))
    if archive is None or not rebuild_folder(archive, timezone=timezone,
                                             dry_run=dry_run, verbose=verbose):
        raise SystemExit(1)


@main.command("html")
@click.argument("folder", type=click.Path(exists=True, file_okay=False))
@click.option("--chats-with", type=str, default=None, metavar="NAME,NAME",
              help="Only these contacts, by the name Snapchat exported")
@click.option("--min-messages", type=int, default=1, show_default=True,
              help="Leave out conversations with fewer messages than this")
@click.option("--stats-only", type=str, default=None, metavar="CAT,CAT",
              help="Only these statistics categories, by their JSON file name (e.g. account,friends)")
@click.option("--timezone", default="", metavar="ZONE",
              help="Show timestamps in this timezone instead of the one stored in the archive")
@click.option("--dry-run", is_flag=True, help="Show what would happen, without it happening")
@click.option("-v", "--verbose", is_flag=True, help="Print every file as it is processed")
def html_command(folder, chats_with, min_messages, stats_only, timezone, dry_run, verbose):
    """Write the one page per topic versions beside index.html.

    gallery.html, chats.html, stats.html and one file per chat in
    conversations/. index.html holds all of it as well, so these are for handing
    a single page on without the rest of the archive. `snapxo pdf` renders the
    same thing for printing and takes the same three filters.
    """
    _check_timezone(timezone)
    archive = resolve_one(Path(folder))
    if archive is None or not write_loose_pages(
        archive,
        chats_with=chats_with.split(",") if chats_with else None,
        min_messages=min_messages,
        stats_only=stats_only.split(",") if stats_only else None,
        timezone=timezone,
        dry_run=dry_run,
        verbose=verbose,
    ):
        raise SystemExit(1)


@main.command("pdf")
@click.argument("folder", type=click.Path(exists=True, file_okay=False))
@click.option("--media-details", is_flag=True, help="Only the media with every detail beside each file")
@click.option("--media-plain", is_flag=True, help="Only the picture book, media and dates and nothing else")
@click.option("--stats", is_flag=True, help="Only the statistics")
@click.option("--chats", is_flag=True, help="Only the conversations")
@click.option("--chats-with", type=str, default=None, metavar="NAME,NAME",
              help="Only these contacts, by the name Snapchat exported")
@click.option("--min-messages", type=int, default=1, show_default=True,
              help="Leave out conversations with fewer messages than this")
@click.option("--stats-only", type=str, default=None, metavar="CAT,CAT",
              help="Only these statistics categories, by their JSON file name (e.g. account,friends)")
@click.option("-o", "--output", type=click.Path(),
              help="Directory to write the PDFs into, instead of pdf/ inside the archive")
@click.option("--dry-run", is_flag=True, help="Show what would happen, without it happening")
def pdf_command(folder, media_details, media_plain, stats, chats,
                chats_with, min_messages, stats_only, output, dry_run):
    """Render a finished output folder to PDFs under pdf/.

    Without a selection all four are rendered. --media-details and --media-plain
    are the same files twice: once with the filename, date, size and dimensions
    beside each one, once as a plain picture book with only the date. A PDF
    carries its pictures inside it, so -o can put them anywhere. The HTML pages
    are never replaced, a PDF is an addition. Needs
    `playwright install chromium`.
    """
    archive = resolve_one(Path(folder))
    if archive is None:
        raise SystemExit(1)

    nothing_picked = not (media_details or media_plain or stats or chats)
    ok = render_pdfs(
        archive,
        gallery=media_details or nothing_picked,
        memories=media_plain or nothing_picked,
        stats=stats or nothing_picked,
        chats=chats or nothing_picked,
        chats_with=chats_with.split(",") if chats_with else None,
        min_messages=min_messages,
        stats_only=stats_only.split(",") if stats_only else None,
        target=Path(output) if output else None,
        dry_run=dry_run,
    )
    if not ok:
        raise SystemExit(1)


@main.command("spreadsheet")
@click.argument("folder", type=click.Path(exists=True, file_okay=False))
@click.option("--format", "spreadsheet_format", type=click.Choice(list(FORMATS)),
              default="xlsx", show_default=True, help="Spreadsheet format to write")
@click.option("-o", "--output", type=click.Path(),
              help="Write it somewhere other than spreadsheet/ inside the archive")
@click.option("--dry-run", is_flag=True, help="Show what would happen, without it happening")
def spreadsheet_command(folder, spreadsheet_format, output, dry_run):
    """Write the statistics to a spreadsheet.

    The numbers behind the charts, not your chats or media. XLSX carries real
    Excel charts you can still edit, which needs `pip install "snapxo[spreadsheet]"`.
    ODS and CSV need nothing and carry the numbers. The same tables sit behind
    the export buttons in index.html.
    """
    archive = resolve_one(Path(folder))
    if archive is None or not export_stats(archive, spreadsheet_format=spreadsheet_format,
                                           target=Path(output) if output else None,
                                           dry_run=dry_run):
        raise SystemExit(1)


@main.command("docker")
@click.argument("folder", type=click.Path(exists=True, file_okay=False))
@click.option("--password", "ask_password", is_flag=True,
              help="Protect the site with a password (you are prompted for it)")
@click.option("--no-auth", is_flag=True, help="Serve without any password")
@click.option("--port", type=int, default=DEFAULT_PORT, show_default=True, help="Host port")
@click.option("-o", "--output", type=click.Path(),
              help="Directory to write the compose file into, instead of the archive")
@click.option("--append", "append_to", type=click.Path(exists=True, dir_okay=False),
              help="Add the service to an existing compose file instead")
@click.option("--up", is_flag=True, help="Run `docker compose up -d` afterwards")
@click.option("--dry-run", is_flag=True, help="Show what would happen, without it happening")
def docker_command(folder, ask_password, no_auth, port, output, append_to, up, dry_run):
    """Write a docker-compose.yml that serves a finished folder over HTTP.

    Serves the archive read-only with nginx, so you can reach it from a phone
    or laptop on your network. It listens on every interface, which is the
    point, so you have to say whether it is protected: --password prompts for
    one, --no-auth serves it openly.
    """
    if ask_password == no_auth:
        console.print("[red]Pick one: --password to protect the archive, or --no-auth "
                      "to serve it openly. It listens on the whole network either way.[/red]")
        raise SystemExit(1)

    archive = resolve_one(Path(folder))
    if archive is None:
        raise SystemExit(1)

    password = click.prompt("Password", hide_input=True, confirmation_prompt=True) if ask_password else None

    target = Path(output) if output else None
    if not write_compose(archive, target=target, port=port, password=password,
                         append_to=Path(append_to) if append_to else None, dry_run=dry_run):
        raise SystemExit(1)

    if up and not dry_run:
        compose_up(compose_target(archive, target, Path(append_to) if append_to else None), port)


@main.command("verify")
@click.argument("folders", nargs=-1, required=True, type=click.Path(exists=True, file_okay=False))
@click.option("--hash", "with_hash", is_flag=True,
              help="Read every file and compare it to the stored checksums (slow)")
@click.option("--update", is_flag=True, help="Write the current state as the new baseline")
def verify_command(folders, with_hash, update):
    """Check a finished output folder against its manifest.

    FOLDERS can be output folders or a parent folder holding them. Without
    --hash only existence and size are checked, which takes seconds and already
    finds a half-copied or partly deleted folder. With --hash every file is read
    and compared to _meta/checksums.json, which is what detects bit rot. The
    first --hash run writes that baseline.
    """
    archives = resolve_many([Path(f) for f in folders])
    if not archives:
        raise SystemExit(1)

    failed = False
    for path in archives:
        report, computed = verify_folder(path, hashes=with_hash)
        print_report(report)

        if computed and (update or not report.has_baseline):
            if write_checksums(path, computed):
                console.print(f"  Wrote checksums for {len(computed)} files")
        failed = failed or not report.ok

    if failed:
        raise SystemExit(1)


@main.command("doctor")
def doctor_command():
    """Check whether the external tools are in place."""
    if not run_doctor():
        raise SystemExit(1)


@main.command("info")
@click.argument("input", nargs=-1, required=True, type=click.Path(exists=True))
@click.option("-v", "--verbose", is_flag=True, help="Print every file as it is inspected")
def info_command(input, verbose):
    """Show what a Snapchat export contains, without writing anything.

    INPUT can be ZIP file(s), a folder holding them, or an already extracted
    export. Counts the media, lists the JSON files Snapchat included and says
    how much space the whole thing takes. Nothing is written, so no -o.
    """
    run_pipeline(Config(inputs=[Path(i) for i in input], info=True, verbose=verbose))


@main.command("organize")
@click.argument("input", nargs=-1, required=True, type=click.Path(exists=True))
@click.option("-o", "--output", type=click.Path(),
              help="Directory the archive is written to (not needed for --info and --dry-run)")
# Mode
@click.option("-y", "--yes", is_flag=True, help="Organize everything without asking")
@click.option("--dry-run", is_flag=True, help="Show what would happen, without it happening")
# Which media are copied
@click.option("--media", "media", default="", metavar="SOURCE,SOURCE",
              help="Where the media come from: memories, chat (default: both)")
@click.option("--types", "types", default="", metavar="KIND,KIND",
              help="What they are: photos, videos, voice (default: all three)")
@click.option("--since", type=str, default=None, metavar="YYYY-MM-DD", help="Only media and messages from this day on")
@click.option("--until", type=str, default=None, metavar="YYYY-MM-DD", help="Only media and messages up to this day")
# Skip
@click.option("--no-encode", is_flag=True, help="Don't encode videos to H.265")
@click.option("--no-overlay", is_flag=True, help="Don't burn overlays onto media")
@click.option("--no-exif", is_flag=True, help="Don't write EXIF/GPS into images")
@click.option("--no-dedup", is_flag=True, help="Don't remove duplicate media")
@click.option("--no-meta", is_flag=True, help="Don't copy the raw export to _meta/ (costs you rebuild and merge)")
@click.option("--timezone", default="", metavar="ZONE",
              help="Convert every timestamp to this timezone, e.g. Europe/Vienna (default: UTC)")
# Encoding
@click.option("--software-encoding", is_flag=True, help="Encode on the CPU, ignoring QSV and NVENC")
@click.option("--crf", type=int, default=23, show_default=True, help="Video quality, lower is better (0-51)")
@click.option("--ffmpeg-path", type=click.Path(), default="ffmpeg", show_default=True,
              help="Path to the ffmpeg binary")
@click.option("--ffprobe-path", type=click.Path(), default="ffprobe", show_default=True,
              help="Path to the ffprobe binary")
# Output layout
@click.option("--folder-structure", type=click.Choice(["year", "year-month"]), default="year", show_default=True,
              help="One folder per year, or one per month")
# System
@click.option("--resume/--no-resume", default=True, show_default=True,
              help="Pick up where an interrupted run left off, instead of copying and encoding again")
@click.option("-v", "--verbose", is_flag=True, help="Print every file as it is processed")
@click.option("--keep-raw-html", is_flag=True,
              help="Keep Snapchat's own HTML pages in _meta/html/, which are dropped by default")
@click.option("--no-checksums", is_flag=True,
              help="Skip fingerprinting the archive, which is what `snapxo verify` compares against")
def organize(input, output, yes, dry_run,
         media, types, since, until,
         no_encode, no_overlay, no_exif, no_dedup, no_meta, timezone,
         software_encoding, crf, ffmpeg_path, ffprobe_path,
         folder_structure,
         resume, verbose, keep_raw_html, no_checksums):
    """Turn an export into an archive folder.

    INPUT can be ZIP file(s), a directory containing ZIPs, or an already-extracted
    export directory. The archive is written to the -o/--output directory, which is
    created if it doesn't exist and reused if it does. Only --dry-run works
    without -o, since it writes nothing. To look at an export first without
    converting it, use `snapxo info`.

    The pages always come as one index.html, so there is nothing to pick there.
    What can be picked is which media are copied, along two axes: --media says
    where they came from, --types says what they are. Both default to everything,
    and both only ever apply to files, never to the chats or the statistics.
    """
    _require_output(output, dry_run)
    for name, value in (("--since", since), ("--until", until)):
        if value and not _is_iso_date(value):
            raise click.UsageError(f"{name} must be a date like 2026-07-20")

    try:
        sources = parse_selection(media, SOURCES, "--media")
        kinds = parse_selection(types, TYPES, "--types")
    except ValueError as problem:
        raise click.UsageError(str(problem)) from None

    if no_meta:
        _confirm_no_meta(yes, dry_run)

    config = Config(
        inputs=[Path(i) for i in input],
        output=Path(output) if output else None,
        yes=yes,
        dry_run=dry_run,
        media_sources=sources,
        media_types=kinds,
        since=since,
        until=until,
        no_encode=no_encode,
        no_overlay=no_overlay,
        no_exif=no_exif,
        no_dedup=no_dedup,
        no_meta=no_meta,
        timezone=timezone,
        software_encoding=software_encoding,
        crf=crf,
        ffmpeg_path=ffmpeg_path,
        ffprobe_path=ffprobe_path,
        folder_structure=folder_structure,
        resume=resume,
        verbose=verbose,
        keep_raw_html=keep_raw_html,
        no_checksums=no_checksums,
    )

    run_pipeline(config)
