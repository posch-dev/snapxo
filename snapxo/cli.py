from pathlib import Path

import click

from . import __version__
from .config import Config
from .merge import merge_outputs
from .pipeline import run_pipeline


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


GROUP_EPILOG = """\
Try:
snapxo organize --help    all options for organizing an export
snapxo merge --help       options for merging finished output folders\
"""


@click.group(cls=DefaultGroup, epilog=GROUP_EPILOG)
@click.version_option(version=__version__)
def main():
    """Organize Snapchat data exports."""


@main.command("merge")
@click.argument("folders", nargs=-1, required=True, type=click.Path(exists=True, file_okay=False))
@click.option("-o", "--output", required=True, type=click.Path(), help="Target directory for the merged export")
@click.option("--hardlink", is_flag=True, help="Link files instead of copying (same drive only, no extra space)")
@click.option("--delete-sources", is_flag=True, help="Delete the input folders after a verified merge")
@click.option("-y", "--yes", is_flag=True, help="Don't ask before deleting the input folders")
@click.option("--folder-structure", type=click.Choice(["year", "year-month"]), default="year", show_default=True,
              help="One folder per year, or one per month")
@click.option("--conversation-format", type=click.Choice(["html", "pdf"]), default="html", show_default=True,
              help="Rebuild the conversations as HTML pages or PDFs (PDF needs `playwright install chromium`)")
@click.option("--dry-run", is_flag=True, help="Show what would happen, without writing anything")
def merge_command(folders, output, hardlink, delete_sources, yes, folder_structure, conversation_format, dry_run):
    """Merge finished output folders into one.

    FOLDERS can be any number of output folders, or a parent folder containing
    them. Deduplicates by content, renumbers everything chronologically and
    rebuilds conversations, stats, map and index. Media is never re-encoded.
    """
    inputs = [Path(f) for f in folders]

    merge_outputs(
        inputs=inputs,
        output=Path(output),
        hardlink=hardlink,
        delete_sources=delete_sources,
        yes=yes,
        folder_structure=folder_structure,
        conversation_format=conversation_format,
        dry_run=dry_run,
    )


@main.command("organize")
@click.argument("input", nargs=-1, required=True, type=click.Path(exists=True))
@click.option("-o", "--output", required=True, type=click.Path(), help="Directory the archive is written to")
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
@click.option("--only-stickers", is_flag=True, help="Only stickers")
# Skip
@click.option("--no-encode", is_flag=True, help="Don't encode videos to H.265")
@click.option("--no-overlay", is_flag=True, help="Don't burn overlays onto media")
@click.option("--no-exif", is_flag=True, help="Don't write EXIF/GPS into images")
@click.option("--no-dedup", is_flag=True, help="Don't remove duplicate media")
@click.option("--no-index", is_flag=True, help="Don't generate index.html (media gallery)")
@click.option("--no-conversations", is_flag=True, help="Don't generate conversations")
@click.option("--no-stats", is_flag=True, help="Don't generate stats.html")
@click.option("--no-map", is_flag=True, help="Don't generate map.html")
@click.option("--no-stickers", is_flag=True, help="Don't export stickers")
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
def organize(input, output, yes, info, dry_run,
         only_media, only_memories, only_chat_media, only_voice, only_photos, only_videos,
         only_conversations, only_stats, only_map, only_stickers,
         no_encode, no_overlay, no_exif, no_dedup, no_index,
         no_conversations, no_stats, no_map, no_stickers, no_meta,
         no_hwaccel, crf, ffmpeg_path, ffprobe_path,
         folder_structure, conversation_format,
         conversations_for, conversations_min_messages,
         stats_only_categories,
         resume, verbose, clean):
    """Organize Snapchat data exports.

    INPUT can be ZIP file(s), a directory containing ZIPs, or an already-extracted
    export directory. The archive is written to the -o/--output directory, which is
    created if it doesn't exist and reused if it does.
    """
    config = Config(
        inputs=[Path(i) for i in input],
        output=Path(output),
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
        only_stickers=only_stickers,
        no_encode=no_encode,
        no_overlay=no_overlay,
        no_exif=no_exif,
        no_dedup=no_dedup,
        no_index=no_index,
        no_conversations=no_conversations,
        no_stats=no_stats,
        no_map=no_map,
        no_stickers=no_stickers,
        no_meta=no_meta,
        no_hwaccel=no_hwaccel,
        crf=crf,
        ffmpeg_path=ffmpeg_path,
        ffprobe_path=ffprobe_path,
        folder_structure=folder_structure,
        conversation_format=conversation_format,
        conversations_for=conversations_for.split(",") if conversations_for else [],
        conversations_min_messages=conversations_min_messages,
        stats_only_categories=stats_only_categories.split(",") if stats_only_categories else [],
        resume=resume,
        verbose=verbose,
        clean=clean,
    )

    run_pipeline(config)
