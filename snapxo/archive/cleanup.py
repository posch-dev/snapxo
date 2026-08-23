from pathlib import Path

from rich.console import Console

console = Console()


def cleanup_tmp_files(output_dir: Path, verbose: bool = False) -> int:
    removed = 0
    for f in output_dir.rglob("*.tmp*"):
        if f.is_file():
            removed += 1
            if verbose:
                console.print(f"  [cyan][{removed}][/cyan] {f.relative_to(output_dir)}")
            f.unlink()
    return removed
