import shutil
from pathlib import Path

from rich.console import Console

from .. import __version__
from ..archive.manifest import build_media_id_map, load_manifest, manifest_to_file_index
from ..facts.mediacounts import summarize_folder
from ..facts.provenance import archive_facts, cover_page, fact_rows
from ..facts.series import build_series
from ..media.thumbs import build_thumbnails
from ..pages.conversations import generate_conversation_html, own_username_of, prepare_conversations
from ..pages.gallery import build_file_details, build_print_index
from ..pages.stats import generate_stats_html
from ..read.inspector import load_json_data
from ..snapchat import STATUS_TYPES
from ..tools.browser import PdfRenderer
from ..tools.deps import require_playwright
from ..tools.ffmpeg import FFmpeg
from .plaingallery import build_plain_gallery

console = Console()

PDF_DIR = "pdf"
# One level below the root, so the "../" in a chat page still reaches the media.
BUILD_DIR = "_pdfbuild"
FOOTER = f"Made with SnapXO {__version__}"


def pdf_dir(folder: Path) -> Path:
    return folder / PDF_DIR


def _message_range(messages: list[dict]) -> tuple[str, str]:
    stamps = sorted(stamp for stamp in
                    (str(message.get("timestamp", ""))[:10] for message in messages) if stamp)
    return (stamps[0], stamps[-1]) if stamps else ("", "")


def _chat_cover(chat: dict, own_username: str | None, facts: dict,
                attachments: int) -> tuple[str, str]:
    real = [m for m in chat["messages"] if m["media_type"].upper() not in STATUS_TYPES]
    first, last = _message_range(real)

    if chat["is_group"]:
        subtitle = f'Group chat with {len(chat["participants"])} people'
        parties = ", ".join(chat["participants"]) or "unknown"
    else:
        subtitle = "Conversation between two people"
        parties = f'{own_username or "you"} and {chat["contact"]}'

    rows = [("Between", parties)]
    if chat["secondary"] and not chat["is_group"]:
        rows.append(("Display name", chat["title"]))
    rows.append(("Messages", str(len(real))))
    rows.append(("Attachments", str(attachments)))
    if first and last:
        rows.append(("Conversation from", f"{first} to {last}"))
    rows.extend(fact_rows(facts))

    period = f"{first} to {last}" if first and last else ""
    return cover_page(chat["title"], subtitle, rows, __version__), period


def _render_gallery(folder: Path, out_dir: Path, file_index: list[dict], json_data: dict,
                    thumbs: dict[int, str], facts: dict, renderer) -> bool:
    rows = [("Files", str(len(file_index)))] + fact_rows(facts)
    cover = cover_page("Media gallery", "Every file in this archive, with its details",
                       rows, __version__)
    page = build_print_index(file_index, build_file_details(file_index, json_data), thumbs, cover)

    # Must sit in the output root, the media paths are relative to it.
    source = folder / "gallery_print.tmp.html"
    source.write_text(page, encoding="utf-8")
    try:
        return renderer.render(source, out_dir / "media-details.pdf",
                               header_left="Media gallery", footer_left=FOOTER)
    finally:
        source.unlink(missing_ok=True)


def _print_previews(file_index: list[dict], thumbs: dict[int, str]) -> dict[int, str]:
    previews = {}
    for position, entry in enumerate(file_index):
        picture = entry.get("medium") or entry.get("thumb") or thumbs.get(position)
        if picture:
            previews[position] = picture
    return previews


def _render_plain_gallery(folder: Path, out_dir: Path, file_index: list[dict],
                          thumbs: dict[int, str], facts: dict, renderer) -> bool:
    rows = [("Files", str(len(file_index)))] + fact_rows(facts)
    cover = cover_page("Memories", "The media on its own, nothing written over it",
                       rows, __version__)
    page = build_plain_gallery(file_index, _print_previews(file_index, thumbs), cover)

    source = folder / "memories_print.tmp.html"
    source.write_text(page, encoding="utf-8")
    try:
        return renderer.render(source, out_dir / "media-plain.pdf",
                               header_left="Memories", footer_left=FOOTER)
    finally:
        source.unlink(missing_ok=True)


def _render_stats(folder: Path, out_dir: Path, file_index: list[dict], json_data: dict,
                  facts: dict, renderer, stats_only: list[str] | None = None) -> bool:
    cover = cover_page("Statistics", "What this archive adds up to",
                       fact_rows(facts), __version__)
    generate_stats_html(json_data, summarize_folder(folder, file_index),
                        folder, file_index=file_index, filename="stats_print.tmp.html",
                        cover=cover, expanded=True, categories=stats_only or None)
    source = folder / "stats_print.tmp.html"
    try:
        return renderer.render(source, out_dir / "stats.pdf",
                               header_left="Statistics", footer_left=FOOTER)
    finally:
        source.unlink(missing_ok=True)


def _render_chats(folder: Path, out_dir: Path, json_data: dict, media_map: dict[str, dict],
                  facts: dict, renderer, chats_with: list[str] | None = None,
                  min_messages: int = 1) -> int:
    prepared, _ = prepare_conversations(json_data, conversations_for=chats_with or None,
                                        min_messages=min_messages)
    if not prepared:
        return 0

    own_username = own_username_of(json_data)
    build_dir = folder / BUILD_DIR
    build_dir.mkdir(exist_ok=True)
    target_dir = out_dir / "chats"
    target_dir.mkdir(parents=True, exist_ok=True)

    rendered = 0
    try:
        for chat in prepared:
            attachments = sum(1 for message in chat["messages"]
                              if (message.get("media_ids") or "").strip())
            cover, period = _chat_cover(chat, own_username, facts, attachments)
            page = generate_conversation_html(
                chat["contact"], chat["messages"], own_username, chat["is_group"],
                chat["conversation_title"], media_map=media_map, pdf_mode=True, cover=cover,
            )
            source = build_dir / f"{chat['safe_name']}.html"
            source.write_text(page, encoding="utf-8")
            if renderer.render(source, target_dir / f"{chat['safe_name']}.pdf",
                               header_left=chat["title"], header_right=period,
                               footer_left=FOOTER):
                rendered += 1
    finally:
        shutil.rmtree(build_dir, ignore_errors=True)
    return rendered


def render_pdfs(folder: Path, gallery: bool = True, stats: bool = True, chats: bool = True,
                memories: bool = True, chats_with: list[str] | None = None,
                min_messages: int = 1, stats_only: list[str] | None = None,
                target: Path | None = None, dry_run: bool = False) -> bool:
    manifest = load_manifest(folder)
    if not manifest:
        console.print(f"[red]{folder} has no _meta/manifest.json, so it is not a "
                      f"folder SnapXO produced.[/red]")
        return False

    file_index = manifest_to_file_index(manifest, folder)
    json_data = load_json_data(folder / "_meta")
    # Only the finished files move, the pages stay in the archive where the media is.
    out_dir = target or pdf_dir(folder)

    if dry_run:
        console.print(f"Would write PDFs to {out_dir}")
        return True

    require_playwright()
    # The 1280 px copies exist for the PDF alone, so this is where they are built.
    ff = FFmpeg()
    thumbs = build_thumbnails(file_index, folder, ff=ff if ff.check() else None,
                              with_medium=True)
    facts = archive_facts(folder, file_index, build_series(json_data, file_index))

    out_dir.mkdir(parents=True, exist_ok=True)
    with PdfRenderer() as renderer:
        if gallery and file_index and _render_gallery(folder, out_dir, file_index, json_data,
                                                      thumbs, facts, renderer):
            console.print(f"  Generated media-details.pdf in {out_dir}")
        if memories and file_index and _render_plain_gallery(folder, out_dir, file_index,
                                                             thumbs, facts, renderer):
            console.print(f"  Generated media-plain.pdf in {out_dir}")
        if stats and json_data and _render_stats(folder, out_dir, file_index, json_data,
                                                 facts, renderer, stats_only):
            console.print(f"  Generated stats.pdf in {out_dir}")
        if chats and json_data:
            count = _render_chats(folder, out_dir, json_data, build_media_id_map(file_index),
                                  facts, renderer, chats_with, min_messages)
            if count:
                console.print(f"  Generated {count} chat PDFs in {out_dir / 'chats'}")

    if not json_data:
        console.print(f"[yellow]{folder} has no _meta/json, so only the gallery could "
                      f"be rendered.[/yellow]")
    return True
