import shutil
from pathlib import Path

from rich.console import Console
from rich.progress import Progress

from .. import __version__
from ..archive.manifest import build_media_id_map, load_manifest, manifest_to_file_index
from ..facts.mediacounts import summarize_folder
from ..facts.provenance import archive_facts, cover_page, fact_rows
from ..facts.series import build_series
from ..media.thumbs import build_thumbnails
from ..pages.conversations import generate_conversation_html, own_username_of, prepare_conversations
from ..pages.gallery import build_file_details, build_print_index
from ..pages.stats import generate_stats_html
from ..parts.messages import _media_rel_path, resolve_media
from ..read.inspector import load_json_data
from ..snapchat import STATUS_TYPES
from ..tools.browser import PdfRenderer
from ..tools.deps import require_playwright
from ..tools.ffmpeg import FFmpeg
from .pdfparts import MB, plan_parts, render_group
from .plaingallery import build_plain_gallery

console = Console()

PDF_DIR = "pdf"
MEDIA_DETAILS = "media-details"
MEDIA_PLAIN = "media-plain"
CHATS = "chats"
# One level below the root, so the "../" in a chat page still reaches the media.
BUILD_DIR = "_pdfbuild"
FOOTER = f"Made with SnapXO {__version__}"
# What a tile or a message adds to a PDF beyond its embedded image, measured
# with Chromium, which embeds a JPEG byte for byte.
PLAIN_TILE_BYTES = 2 * 1024
DETAILS_TILE_BYTES = 4 * 1024
MESSAGE_BYTES = 512


def pdf_dir(folder: Path) -> Path:
    return folder / PDF_DIR


def _file_size(folder: Path, rel: str | None) -> int:
    try:
        return (folder / rel).stat().st_size if rel else 0
    except OSError:
        return 0


def _render_page(renderer, page: str, source: Path, pdf_path: Path,
                 header_left: str, header_right: str = "") -> bool:
    source.write_text(page, encoding="utf-8")
    if not renderer.render(source, pdf_path, header_left=header_left,
                           header_right=header_right, footer_left=FOOTER):
        console.print(f"    [yellow]Kept the page it failed on: {source}[/yellow]")
        return False
    source.unlink(missing_ok=True)
    return True


def _note_foreign_folders(kind_dir: Path, expected: set[str]) -> None:
    if not kind_dir.is_dir():
        return
    for child in sorted(kind_dir.iterdir()):
        if child.is_dir() and not child.name.startswith(".") and child.name not in expected:
            console.print(f"  [yellow]{child} is not in this archive, left as it is[/yellow]")


class _PartProgress:
    # Positions are absolute within a group, so a group split again rewinds
    # instead of counting its parts twice.

    def __init__(self, progress: Progress, label: str, estimates: dict[str, list[int]]):
        self.progress = progress
        self.label = label
        self.estimates = estimates
        self.planned = {group: len(plan_parts(sizes)) for group, sizes in estimates.items()}
        self.finished_bytes = 0
        self.finished_parts = 0
        self.task = progress.add_task(f"{label:<13}", total=max(1, sum(map(sum, estimates.values()))))

    def part_done(self, group: str, chosen: list[int], number: int, total: int, pdf_path: Path):
        self.planned[group] = total
        done = self.finished_bytes + sum(self.estimates[group][:chosen[-1] + 1])
        size = pdf_path.stat().st_size / MB if pdf_path.is_file() else 0
        self.progress.update(self.task, completed=done, description=(
            f"{self.label:<13} {self.finished_parts + number}/{sum(self.planned.values())} · "
            f"{group} part {number} of {total} · {size:.0f} MB"))

    def group_done(self, group: str):
        self.finished_bytes += sum(self.estimates[group])
        self.finished_parts += self.planned[group]
        self.progress.update(self.task, completed=self.finished_bytes)


def _message_range(messages: list[dict]) -> tuple[str, str]:
    stamps = sorted(stamp for stamp in
                    (str(message.get("timestamp", ""))[:10] for message in messages) if stamp)
    return (stamps[0], stamps[-1]) if stamps else ("", "")


def _period(first: str, last: str) -> str:
    return f"{first} to {last}" if first and last else ""


def _chat_cover(chat: dict, messages: list[dict], own_username: str | None, facts: dict,
                number: int, total: int) -> tuple[str, str]:
    real = [m for m in messages if m["media_type"].upper() not in STATUS_TYPES]
    attachments = sum(1 for m in messages if (m.get("media_ids") or "").strip())
    whole = sum(1 for m in chat["messages"] if m["media_type"].upper() not in STATUS_TYPES)
    first, last = _message_range(real)

    if chat["is_group"]:
        subtitle = f'Group chat with {len(chat["participants"])} people'
        parties = ", ".join(chat["participants"]) or "unknown"
    else:
        subtitle = "Conversation between two people"
        parties = f'{own_username or "you"} and {chat["contact"]}'

    rows = [("Part", f"{number} of {total}"), ("Between", parties)]
    if chat["secondary"] and not chat["is_group"]:
        rows.append(("Display name", chat["title"]))
    rows.append(("Messages", f"{len(real):,} in this part, {whole:,} in the chat"))
    rows.append(("Attachments", str(attachments)))
    if first and last:
        rows.append(("Conversation from", f"{first} to {last}"))
    rows.extend(fact_rows(facts))

    period = _period(first, last)
    subtitle = f"{subtitle} · Part {number} of {total}"
    return cover_page(chat["title"], subtitle, rows, __version__), period


def _media_years(file_index: list[dict]) -> dict[str, list[int]]:
    years: dict[str, list[int]] = {}
    for position in sorted(range(len(file_index)), key=lambda p: str(file_index[p].get("date", ""))):
        entry = file_index[position]
        year = str(entry.get("subfolder") or entry.get("year") or "unknown")[:4]
        years.setdefault(year, []).append(position)
    return dict(sorted(years.items()))


def _render_media(kind: str, title: str, subtitle: str, folder: Path, out_dir: Path,
                  file_index: list[dict], pictures: dict[int, str], tile_bytes: int,
                  build_page, facts: dict, renderer, progress: Progress) -> bool:
    kind_dir = out_dir / kind
    years = _media_years(file_index)
    _note_foreign_folders(kind_dir, set(years))
    estimates_by_year = {year: [_file_size(folder, pictures.get(p)) + tile_bytes for p in positions]
                         for year, positions in years.items()}
    tracker = _PartProgress(progress, title, estimates_by_year)
    all_rendered = True

    for year, positions in years.items():
        estimates = estimates_by_year[year]

        def render_part(chosen: list[int], number: int, total: int, pdf_path: Path,
                        year=year, positions=positions) -> bool:
            picked = [positions[i] for i in chosen]
            period = _period(str(file_index[picked[0]].get("date", ""))[:10],
                             str(file_index[picked[-1]].get("date", ""))[:10])
            rows = [("Part", f"{number} of {total} for {year}"),
                    ("Files in this part", f"{len(picked):,} (files {chosen[0] + 1:,} to "
                                           f"{chosen[-1] + 1:,} of {len(positions):,} in {year})"),
                    ("Files in archive", f"{len(file_index):,}")] + fact_rows(facts)
            heading = f"{subtitle} · Part {number} of {total}" + (f" · {period}" if period else "")
            cover = cover_page(f"{title} {year}", heading, rows, __version__)
            # Must sit in the output root, the media paths are relative to it.
            rendered = _render_page(renderer, build_page(picked, cover),
                                    folder / f"{kind}-{year}_print.tmp.html", pdf_path,
                                    f"{title} {year} · Part {number}/{total}", period)
            tracker.part_done(year, chosen, number, total, pdf_path)
            return rendered

        if not render_group(kind_dir / year, f"{kind}-{year}", estimates, render_part):
            all_rendered = False
        tracker.group_done(year)

    if all_rendered:
        (out_dir / f"{kind}.pdf").unlink(missing_ok=True)
    return all_rendered


def _print_previews(file_index: list[dict], thumbs: dict[int, str]) -> dict[int, str]:
    previews = {}
    for position, entry in enumerate(file_index):
        picture = entry.get("medium") or entry.get("thumb") or thumbs.get(position)
        if picture:
            previews[position] = picture
    return previews


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


def _message_bytes(folder: Path, message: dict, media_map: dict[str, dict]) -> int:
    size = MESSAGE_BYTES
    for entry in resolve_media(message, media_map):
        if entry.get("type") == "image":
            size += _file_size(folder, entry.get("medium") or _media_rel_path(entry))
        elif entry.get("type") == "video":
            size += _file_size(folder, entry.get("thumb"))
    return size


def _render_chats(folder: Path, out_dir: Path, json_data: dict, media_map: dict[str, dict],
                  facts: dict, renderer, progress: Progress,
                  chats_with: list[str] | None = None, min_messages: int = 1) -> int:
    prepared, _ = prepare_conversations(json_data, conversations_for=chats_with or None,
                                        min_messages=min_messages)
    if not prepared:
        return 0

    own_username = own_username_of(json_data)
    build_dir = folder / BUILD_DIR
    build_dir.mkdir(exist_ok=True)
    target_dir = out_dir / CHATS
    target_dir.mkdir(parents=True, exist_ok=True)
    if not chats_with:
        _note_foreign_folders(target_dir, {chat["safe_name"] for chat in prepared})

    estimates_by_chat = {chat["safe_name"]: [_message_bytes(folder, message, media_map)
                                             for message in chat["messages"]] for chat in prepared}
    tracker = _PartProgress(progress, "Chats", estimates_by_chat)
    rendered = 0
    for chat in prepared:
        messages = chat["messages"]
        estimates = estimates_by_chat[chat["safe_name"]]

        def render_part(chosen: list[int], number: int, total: int, pdf_path: Path,
                        chat=chat, messages=messages) -> bool:
            part = [messages[i] for i in chosen]
            cover, period = _chat_cover(chat, part, own_username, facts, number, total)
            page = generate_conversation_html(
                chat["contact"], part, own_username, chat["is_group"],
                chat["conversation_title"], media_map=media_map, pdf_mode=True, cover=cover,
            )
            done = _render_page(renderer, page, build_dir / f"{chat['safe_name']}.html", pdf_path,
                                f"{chat['title']} · Part {number}/{total}", period)
            tracker.part_done(chat["safe_name"], chosen, number, total, pdf_path)
            return done

        if render_group(target_dir / chat["safe_name"], chat["safe_name"], estimates, render_part):
            rendered += 1
            (target_dir / f"{chat['safe_name']}.pdf").unlink(missing_ok=True)
        tracker.group_done(chat["safe_name"])

    if rendered == len(prepared):
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
    with PdfRenderer() as renderer, Progress(console=console) as progress:
        if gallery and file_index:
            details = build_file_details(file_index, json_data)
            if _render_media(MEDIA_DETAILS, "Media gallery", "Every file with its details",
                             folder, out_dir, file_index, thumbs, DETAILS_TILE_BYTES,
                             lambda picked, cover: build_print_index(file_index, details, thumbs,
                                                                     cover, picked),
                             facts, renderer, progress):
                console.print(f"  Generated the media details PDFs in {out_dir / MEDIA_DETAILS}")
        if memories and file_index:
            previews = _print_previews(file_index, thumbs)
            if _render_media(MEDIA_PLAIN, "Memories", "The media on its own, nothing written over it",
                             folder, out_dir, file_index, previews, PLAIN_TILE_BYTES,
                             lambda picked, cover: build_plain_gallery(file_index, previews,
                                                                       cover, picked),
                             facts, renderer, progress):
                console.print(f"  Generated the media plain PDFs in {out_dir / MEDIA_PLAIN}")
        if stats and json_data and _render_stats(folder, out_dir, file_index, json_data,
                                                 facts, renderer, stats_only):
            console.print(f"  Generated stats.pdf in {out_dir}")
        if chats and json_data:
            count = _render_chats(folder, out_dir, json_data, build_media_id_map(file_index),
                                  facts, renderer, progress, chats_with, min_messages)
            if count:
                console.print(f"  Generated the PDFs of {count} chats in {out_dir / CHATS}")

    if not json_data:
        console.print(f"[yellow]{folder} has no _meta/json, so only the gallery could "
                      f"be rendered.[/yellow]")
    return True
