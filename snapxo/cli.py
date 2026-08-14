from datetime import datetime
from pathlib import Path

import click
from rich.console import Console

from . import __version__
from .config import Config
from .doctor import run_doctor
from .merge import merge_outputs
from .pipeline import run_pipeline
from .verify import print_report, verify_folder, write_checksums

console = Console()


class DefaultGroup(click.Group):
    # Falls back to `organize` so invocations without a subcommand keep working:
    #   snapxo export.zip -o ./out    ->  organize
    #   snapxo merge a b -o ./merged  ->  merge
    default_command = "organize"

    def parse_args(self, ctx, args):
        if args and args[0] not in self.commands and args[0] not in ("--help", "-h", "--version"):
            args = [self.default_command] + args
        return super().parse_args(ctx, args)

    def format_epilog(self, ctx, formatter):
        # click indents the epilog by two columns and rewraps it; write the
        # lines straight into the buffer instead to keep them flush left.
        if not self.epilog:
            return
        formatter.write_paragraph()
        for line in self.epilog.splitlines():
            formatter.write(line + "\n")


def _require_output(output, optional: bool) -> None:
    # Only needed when something is actually written.
    if not output and not optional:
        raise click.UsageError("-o/--output is required, except with --info or --dry-run")


def _is_iso_date(value: str) -> bool:
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return False
    return True


GROUP_EPILOG = """\
Try:
snapxo organize --help    all options for organizing an export
snapxo merge --help       options for merging finished output folders
snapxo verify --help      check a finished folder against its manifest
snapxo doctor             check whether ffmpeg and the PDF browser are there\
"""


@click.group(cls=DefaultGroup, epilog=GROUP_EPILOG)
@click.version_option(version=__version__)
def main():
    """Organize Snapchat data exports."""


@main.command("merge")
@click.argument("folders", nargs=-1, required=True, type=click.Path(exists=True, file_okay=False))
@click.option("-o", "--output", type=click.Path(),
              help="Target directory for the merged export (not needed for --dry-run)")
@click.option("--hardlink", is_flag=True, help="Link files instead of copying (same drive only, no extra space)")
@click.option("--delete-sources", is_flag=True, help="Delete the input folders after a verified merge")
@click.option("-y", "--yes", is_flag=True, help="Don't ask before deleting the input folders")
@click.option("--folder-structure", type=click.Choice(["year", "year-month"]), default="year", show_default=True,
              help="One folder per year, or one per month")
@click.option("--conversation-format", type=click.Choice(["html", "pdf"]), default="html", show_default=True,
              help="Rebuild the conversations as HTML pages or PDFs (PDF needs `playwright install chromium`)")
@click.option("--index-format", type=click.Choice(["html", "pdf"]), default="html", show_default=True,
              help="Also render the media gallery to index.pdf (PDF needs `playwright install chromium`)")
@click.option("--verify/--no-verify", default=True, show_default=True,
              help="Check the input folders against their manifests before merging")
@click.option("--skip-damaged", is_flag=True,
              help="With --no-verify: leave damaged files out instead of taking them along marked")
@click.option("--dry-run", is_flag=True, help="Show what would happen, without writing anything")
def merge_command(folders, output, hardlink, delete_sources, yes, folder_structure, conversation_format,
                  index_format, verify, skip_damaged, dry_run):
    """Merge finished output folders into one.

    FOLDERS can be any number of output folders, or a parent folder containing
    them. Deduplicates by content, renumbers everything chronologically and
    rebuilds conversations, stats, map and index. Media is never re-encoded.

    Every input folder is checked against its manifest first; damaged files stop
    the merge unless --no-verify is given, which takes them along marked as
    damaged. Only --dry-run works without -o.
    """
    _require_output(output, dry_run)
    if delete_sources and not verify:
        # Unchecked inputs plus deleted originals is the one way to lose data for good.
        raise click.UsageError("--delete-sources cannot be combined with --no-verify")
    if skip_damaged and verify:
        raise click.UsageError("--skip-damaged only applies together with --no-verify")

    inputs = [Path(f) for f in folders]

    merge_outputs(
        inputs=inputs,
        output=Path(output) if output else None,
        hardlink=hardlink,
        delete_sources=delete_sources,
        yes=yes,
        folder_structure=folder_structure,
        conversation_format=conversation_format,
        index_format=index_format,
        verify=verify,
        skip_damaged=skip_damaged,
        dry_run=dry_run,
    )


@main.command("verify")
@click.argument("folders", nargs=-1, required=True, type=click.Path(exists=True, file_okay=False))
@click.option("--hash", "with_hash", is_flag=True,
              help="Read every file and compare it to the stored checksums (slow)")
@click.option("--update", is_flag=True, help="Write the current state as the new baseline")
def verify_command(folders, with_hash, update):
    """Check a finished output folder against its manifest.

    Without --hash only existence and size are checked, which takes seconds and
    already finds a half-copied or partly deleted folder. With --hash every file
    is read and compared to _meta/checksums.json, which is what detects bit rot.
    The first --hash run writes that baseline.
    """
    failed = False
    for folder in folders:
        path = Path(folder)
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


@main.command("organize")
@click.argument("input", nargs=-1, required=True, type=click.Path(exists=True))
@click.option("-o", "--output", type=click.Path(),
              help="Directory the archive is written to (not needed for --info and --dry-run)")
# Mode
@click.option("-y", "--yes", is_flag=True, help="Organize everything without asking")
@click.option("--info", is_flag=True, help="Only show what the export contains, then exit")
@click.option("--dry-run", is_flag=True, help="Show what would happen, without writing anything")
# Filter
@click.option("--only-media", is_flag=True, help="Only media (Memories + chat media + voice)")
@click.option("--only-memories", is_flag=True, help="Only Memories")
@click.option("--only-chat-media", is_flag=True, help="Only chat media")
@click.option("--only-voice", is_flag=True, help="Only voice messages")
@click.option("--only-photos", is_flag=True, help="Only photos")
@click.option("--only-videos", is_flag=True, help="Only videos")
@click.option("--only-conversations", is_flag=True, help="Only conversations")
@click.option("--only-stats", is_flag=True, help="Only stats.html")
@click.option("--only-map", is_flag=True, help="Only map.html")
@click.option("--since", type=str, default=None, metavar="YYYY-MM-DD", help="Only media and messages from this day on")
@click.option("--until", type=str, default=None, metavar="YYYY-MM-DD", help="Only media and messages up to this day")
# Skip
@click.option("--no-encode", is_flag=True, help="Don't encode videos to H.265")
@click.option("--no-overlay", is_flag=True, help="Don't burn overlays onto media")
@click.option("--no-exif", is_flag=True, help="Don't write EXIF/GPS into images")
@click.option("--no-dedup", is_flag=True, help="Don't remove duplicate media")
@click.option("--no-index", is_flag=True, help="Don't generate index.html (media gallery)")
@click.option("--no-conversations", is_flag=True, help="Don't generate conversations")
@click.option("--no-stats", is_flag=True, help="Don't generate stats.html")
@click.option("--no-map", is_flag=True, help="Don't generate map.html")
@click.option("--no-meta", is_flag=True, help="Don't copy the raw JSON/HTML export to _meta/")
# Encoding
@click.option("--no-hwaccel", is_flag=True, help="Force software encoding (no QSV/NVENC)")
@click.option("--crf", type=int, default=23, show_default=True, help="Video quality, lower is better (0-51)")
@click.option("--ffmpeg-path", type=click.Path(), default="ffmpeg", show_default=True,
              help="Path to the ffmpeg binary")
@click.option("--ffprobe-path", type=click.Path(), default="ffprobe", show_default=True,
              help="Path to the ffprobe binary")
# Output format
@click.option("--folder-structure", type=click.Choice(["year", "year-month"]), default="year", show_default=True,
              help="One folder per year, or one per month")
@click.option("--conversation-format", type=click.Choice(["html", "pdf"]), default="html", show_default=True,
              help="Write the conversations as HTML pages or PDFs (PDF needs `playwright install chromium`)")
@click.option("--index-format", type=click.Choice(["html", "pdf"]), default="html", show_default=True,
              help="Also render the media gallery to index.pdf (PDF needs `playwright install chromium`)")
@click.option("--stats-format", type=click.Choice(["html", "pdf"]), default="html", show_default=True,
              help="Also render the statistics to stats.pdf (PDF needs `playwright install chromium`)")
# Conversations
@click.option("--conversations-for", type=str, default=None, metavar="NAME,NAME",
              help="Only these contacts, by the name Snapchat exported")
@click.option("--conversations-min-messages", type=int, default=1, show_default=True,
              help="Skip conversations with fewer messages than this")
# Media is embedded automatically, matched exactly via the Media IDs field
# Stats
@click.option("--stats-only-categories", type=str, default=None, metavar="CAT,CAT",
              help="Only these stats categories, by their JSON file name (e.g. account,friends)")
# System
@click.option("--resume/--no-resume", default=True, show_default=True,
              help="Pick up where an interrupted run left off, instead of copying and encoding again")
@click.option("-v", "--verbose", is_flag=True, help="Print every file as it is processed")
@click.option("--clean", is_flag=True, help="Delete the bulky raw HTML export (keeps manifest and JSON data)")
@click.option("--checksums", is_flag=True, help="Fingerprint the finished archive for later `snapxo verify` runs")
def organize(input, output, yes, info, dry_run,
         only_media, only_memories, only_chat_media, only_voice, only_photos, only_videos,
         only_conversations, only_stats, only_map, since, until,
         no_encode, no_overlay, no_exif, no_dedup, no_index,
         no_conversations, no_stats, no_map, no_meta,
         no_hwaccel, crf, ffmpeg_path, ffprobe_path,
         folder_structure, conversation_format, index_format, stats_format,
         conversations_for, conversations_min_messages,
         stats_only_categories,
         resume, verbose, clean, checksums):
    """Organize Snapchat data exports.

    INPUT can be ZIP file(s), a directory containing ZIPs, or an already-extracted
    export directory. The archive is written to the -o/--output directory, which is
    created if it doesn't exist and reused if it does. Only --info and --dry-run
    work without -o, since they write nothing.
    """
    _require_output(output, info or dry_run)
    for name, value in (("--since", since), ("--until", until)):
        if value and not _is_iso_date(value):
            raise click.UsageError(f"{name} must be a date like 2026-07-20")

    config = Config(
        inputs=[Path(i) for i in input],
        output=Path(output) if output else None,
        yes=yes,
        info=info,
        dry_run=dry_run,
        only_media=only_media,
        only_memories=only_memories,
        only_chat_media=only_chat_media,
        only_voice=only_voice,
        only_photos=only_photos,
        only_videos=only_videos,
        only_conversations=only_conversations,
        only_stats=only_stats,
        only_map=only_map,
        since=since,
        until=until,
        no_encode=no_encode,
        no_overlay=no_overlay,
        no_exif=no_exif,
        no_dedup=no_dedup,
        no_index=no_index,
        no_conversations=no_conversations,
        no_stats=no_stats,
        no_map=no_map,
        no_meta=no_meta,
        no_hwaccel=no_hwaccel,
        crf=crf,
        ffmpeg_path=ffmpeg_path,
        ffprobe_path=ffprobe_path,
        folder_structure=folder_structure,
        conversation_format=conversation_format,
        index_format=index_format,
        stats_format=stats_format,
        conversations_for=conversations_for.split(",") if conversations_for else [],
        conversations_min_messages=conversations_min_messages,
        stats_only_categories=stats_only_categories.split(",") if stats_only_categories else [],
        resume=resume,
        verbose=verbose,
        clean=clean,
        checksums=checksums,
    )

    run_pipeline(config)
