import shutil
from collections.abc import Callable
from pathlib import Path

from rich.console import Console

console = Console()

MB = 1024 * 1024
PART_LIMIT = 110 * MB
# Aimed below the limit, so a slightly low estimate still lands under it.
PART_TARGET = 95 * MB


def plan_parts(estimates: list[float], target: float = PART_TARGET) -> list[list[int]]:
    parts: list[list[int]] = []
    current: list[int] = []
    filled = 0.0
    for position, estimate in enumerate(estimates):
        if current and filled + estimate > target:
            parts.append(current)
            current, filled = [], 0.0
        current.append(position)
        filled += estimate
    if current:
        parts.append(current)
    return parts


def part_name(stem: str, number: int, total: int) -> str:
    width = len(str(total))
    return f"{stem}-part-{number:0{width}d}-of-{total}.pdf"


def _restore_interrupted_swap(final_dir: Path, old_dir: Path) -> None:
    if old_dir.is_dir() and not final_dir.exists():
        old_dir.rename(final_dir)
    shutil.rmtree(old_dir, ignore_errors=True)


def _swap_in(built_dir: Path, final_dir: Path, old_dir: Path) -> bool:
    try:
        if final_dir.exists():
            final_dir.rename(old_dir)
        built_dir.rename(final_dir)
    except OSError as error:
        _restore_interrupted_swap(final_dir, old_dir)
        console.print(f"    [red]Could not replace {final_dir} ({error}). Is one of its PDFs "
                      f"still open? The new version waits in {built_dir}.[/red]")
        return False
    shutil.rmtree(old_dir, ignore_errors=True)
    return True


def render_group(
    final_dir: Path,
    stem: str,
    estimates: list[int],
    render_part: Callable[[list[int], int, int, Path], bool],
    limit: int = PART_LIMIT,
    target: int = PART_TARGET,
) -> bool:
    # Renders every part next to final_dir first; the old PDFs go only once all
    # new ones exist and fit under the limit.
    built_dir = final_dir.with_name(f".{final_dir.name}.tmp")
    old_dir = final_dir.with_name(f".{final_dir.name}.old")
    _restore_interrupted_swap(final_dir, old_dir)

    scale = 1.0
    while True:
        parts = plan_parts([estimate * scale for estimate in estimates], target)
        shutil.rmtree(built_dir, ignore_errors=True)
        built_dir.mkdir(parents=True)

        oversized = None
        for number, positions in enumerate(parts, 1):
            pdf_path = built_dir / part_name(stem, number, len(parts))
            if not render_part(positions, number, len(parts), pdf_path):
                return False
            size = pdf_path.stat().st_size
            if size > limit and len(positions) > 1:
                oversized = size / max(1, sum(estimates[p] for p in positions))
                break

        if oversized is None:
            return _swap_in(built_dir, final_dir, old_dir)
        # Always above the old scale, so every round plans smaller parts.
        scale = max(scale * limit / target, oversized)
        console.print(f"    [yellow]{stem}: a part came out above {limit // MB} MB, "
                      f"splitting finer[/yellow]")
