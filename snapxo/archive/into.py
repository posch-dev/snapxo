# organize --into: a new export is organized beside the archive, merged with it into
# a third folder, verified, and only then swapped in under the archive's name.

import glob
import os
import re
import shutil
from datetime import date
from pathlib import Path
from typing import NoReturn

from rich.console import Console

from ..config import Config
from ..files import file_hash
from ..pipeline import run_pipeline
from .checkpoint import CHECKPOINT_FILE
from .manifest import archive_zone, load_manifest
from .merge import _file_type, _is_media_dir, _transfer, merge_outputs
from .refresh import check_tools, found_outputs, refresh_outputs
from .verify import print_report, verify_folder

console = Console()


def organized_path(archive: Path) -> Path:
    return archive.with_name(f"{archive.name}.into-new")


def merged_path(archive: Path) -> Path:
    return archive.with_name(f"{archive.name}.into-tmp")


def before_path(archive: Path, today: date | None = None) -> Path:
    base = f"{archive.name}.before-{(today or date.today()).isoformat()}"
    candidate = archive.with_name(base)
    number = 2
    while candidate.exists():
        candidate = archive.with_name(f"{base}-{number}")
        number += 1
    return candidate


def _stop(*lines: str) -> NoReturn:
    for line in lines:
        console.print(line)
    raise SystemExit(1)


def check_leftovers(archive: Path) -> None:
    # A run that died halfway is explained, never guessed at.
    merged = merged_path(archive)
    befores = sorted(archive.parent.glob(f"{glob.escape(archive.name)}.before-*"))
    if archive.is_dir() and merged.exists():
        _stop(f"[red]A previous --into run stopped before swapping. {archive} is untouched.[/red]",
              f"  {merged} holds its unfinished merge. Delete it, then run the command again.")
    if archive.is_dir():
        return
    if merged.is_dir() and befores:
        _stop(f"[red]A previous --into run stopped in the middle of the swap, {archive} is missing.[/red]",
              f"  The previous archive is {befores[-1]}",
              f"  The new, verified one is {merged}",
              f"  To finish: rename {merged.name} to {archive.name}",
              f"  To go back: rename {befores[-1].name} to {archive.name} and delete {merged.name}")
    if befores:
        _stop(f"[red]{archive} does not exist, but {befores[-1]} does.[/red]",
              f"  Nothing was changed. To bring the previous archive back, rename "
              f"{befores[-1].name} to {archive.name}.")
    _stop(f"[red]{archive} is not a folder.[/red]")


def folder_structure_of(manifest: dict) -> str:
    subfolders = {entry.get("subfolder", "") for entry in manifest.get("files", [])}
    return "year-month" if any(re.fullmatch(r"\d{4}-\d{2}", name) for name in subfolders) else "year"


def files_to_carry(archive: Path) -> list[str]:
    # Everything merge neither transfers nor writes itself: pdf/, spreadsheet/, docker files, notes.
    carried = []
    for path in sorted(archive.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(archive)
        if rel.parts[0] in ("_meta", "_overlays"):
            continue
        if len(rel.parts) == 2 and _is_media_dir(path.parent) and _file_type(path.suffix.lower()):
            continue
        carried.append(rel.as_posix())
    return carried


def carry_over(archive: Path, merged: Path) -> list[str]:
    carried = []
    for rel in files_to_carry(archive):
        if (merged / rel).exists():
            continue
        # PDFs and spreadsheets are only ever replaced by rename, HTML and docker files are rewritten in place.
        _transfer(archive / rel, merged / rel, hardlink=rel.startswith(("pdf/", "spreadsheet/")))
        carried.append(rel)
    return carried


def _same_content(first: Path, second: Path) -> bool:
    try:
        if os.path.samefile(first, second):
            return True
    except OSError:
        return False
    return file_hash(first) == file_hash(second)


def find_losses(archive: Path, merged: Path, seen_hashes: dict[Path, str], carried: list[str]) -> list[str]:
    report, computed = verify_folder(merged, hashes=True)
    print_report(report)
    problems = [f"{label}: {rel}" for label, items in (("missing", report.missing),
                                                        ("wrong size", report.wrong_size),
                                                        ("changed content", report.wrong_hash))
                for rel in items]
    if not report.has_manifest:
        problems.append("the merged archive has no manifest")

    present = set(computed.values())
    problems += [f"not in the new archive: {src}" for src, digest in seen_hashes.items() if digest not in present]
    problems += [f"not carried over intact: {rel}" for rel in carried
                 if not _same_content(archive / rel, merged / rel)]
    return problems


def _swap(archive: Path, merged: Path) -> Path:
    before = before_path(archive)
    try:
        archive.rename(before)
    except OSError as error:
        _stop(f"[red]Could not rename {archive} ({error}), so it is untouched. Is a file in it still open?[/red]",
              f"  The verified merge waits in {merged}.")
    try:
        merged.rename(archive)
    except OSError as error:
        before.rename(archive)
        _stop(f"[red]Could not move {merged.name} into place ({error}). {archive} is back as it was, "
              f"the verified merge is still in {merged}.[/red]")
    return before


def organize_into(config: Config, archive: Path, delete_old: bool = False, verify: bool = True,
                  refresh: bool = False) -> bool:
    check_leftovers(archive)
    manifest = load_manifest(archive)
    if not manifest:
        _stop(f"[red]{archive} has no _meta/manifest.json, so it is not an archive SnapXO produced.[/red]")

    zone = archive_zone(manifest)
    if config.timezone and config.timezone != zone:
        _stop(f"[red]{archive} is kept in {zone}, not {config.timezone}. Media names come from local "
              f"dates, so the export is organized in the archive's zone.[/red]",
              f"  Leave out --timezone, or switch the archive first: "
              f"[cyan]snapxo rebuild {archive} --timezone {config.timezone}[/cyan]")
    structure = folder_structure_of(manifest)
    if config.folder_structure and config.folder_structure != structure:
        _stop(f"[red]{archive} is sorted by {structure}, not {config.folder_structure}.[/red]",
              "  Leave out --folder-structure, the new export follows the archive.")

    outputs = found_outputs(archive)
    if refresh and not check_tools(outputs):
        raise SystemExit(1)

    organized, merged = organized_path(archive), merged_path(archive)
    config.timezone, config.folder_structure, config.output = zone, structure, organized

    console.rule(f"[bold yellow]Organize into {organized.name}[/bold yellow]")
    run_pipeline(config)
    if config.dry_run:
        console.print(f"Would merge {archive.name} and {organized.name} into {merged.name}, verify it, "
                      f"rename {archive.name} to {before_path(archive).name} and the merge to {archive.name}")
        if delete_old:
            console.print(f"Would delete {before_path(archive).name} afterwards")
        for command in outputs.commands(archive) if refresh else []:
            console.print(f"Would refresh with: {command}")
        return True
    if not load_manifest(organized) or (organized / CHECKPOINT_FILE).exists():
        _stop(f"[red]Organizing did not finish, {archive} is untouched. Run the same command again "
              f"to pick up in {organized}.[/red]")

    seen_hashes: dict[Path, str] = {}
    merge_outputs([archive, organized], merged, hardlink=True, yes=True, folder_structure=structure,
                  verify=verify, timezone_name=zone, seen_hashes=seen_hashes, pdf_hint=False)
    if not load_manifest(merged):
        _stop(f"[red]The merge did not finish, {archive} is untouched.[/red]",
              f"  Delete {merged} before running the command again.")

    console.rule("[bold yellow]Carry over[/bold yellow]")
    carried = carry_over(archive, merged)
    console.print(f"Carried over {len(carried)} files the merge does not write itself")

    console.rule("[bold yellow]Verify before swapping[/bold yellow]")
    problems = find_losses(archive, merged, seen_hashes, carried)
    if problems:
        for problem in problems[:10]:
            console.print(f"  [red]{problem}[/red]")
        if len(problems) > 10:
            console.print(f"  [red]... and {len(problems) - 10} more[/red]")
        _stop(f"[red]{len(problems)} problems, so {archive} is untouched.[/red]",
              f"  The merge stays in {merged} and the organized export in {organized} for a look.")
    console.print(f"[green]Every file of {archive.name} and of the new export is in the new archive.[/green]")

    console.rule("[bold yellow]Swap[/bold yellow]")
    before = _swap(archive, merged)
    shutil.rmtree(organized, ignore_errors=True)
    console.print(f"{archive} is the new archive, the previous one is {before}")

    if refresh and outputs:
        console.rule("[bold yellow]Refresh[/bold yellow]")
        refresh_outputs(archive, outputs)
    elif outputs:
        console.print("[yellow]The PDFs, spreadsheets and pages from before do not have the new export "
                      "yet. --refresh does this next time, or run:[/yellow]")
        for command in outputs.commands(archive):
            console.print(f"  [cyan]{command}[/cyan]")

    if delete_old:
        _delete_before(before, config.yes)
    return True


def _delete_before(before: Path, yes: bool) -> None:
    console.print("[dim]With hardlinks the previous archive shares its media with the new one, "
                  "it guards against a bad merge, not against a failing disk.[/dim]")
    if not yes:
        answer = console.input(f"\n[bold red]Delete {before}? [y/N] [/bold red]")
        if answer.strip().lower() != "y":
            console.print(f"Keeping {before}.")
            return
    shutil.rmtree(before)
    console.print(f"Deleted {before}")
