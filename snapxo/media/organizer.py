import shutil
from collections import defaultdict
from pathlib import Path

from rich.console import Console

from ..filenames import extract_media_id
from ..read.scanner import MediaFile

console = Console()



def organize_into_folders(
    files: list[MediaFile],
    output_dir: Path,
    folder_structure: str = "year",
    dry_run: bool = False,
    checkpoint=None,
    step: str = "organize",
) -> list[dict]:
    # On resume only the copying is skipped, the index is always built in full.
    year_counters: dict[str, int] = defaultdict(int)
    file_index = []

    sorted_files = sorted(files, key=lambda f: (f.date, f.original_name))

    for mf in sorted_files:
        year = mf.date[:4] if mf.date != "unknown" else "unknown"

        if folder_structure == "year-month":
            subfolder = mf.date[:7] if mf.date != "unknown" else "unknown"
        else:
            subfolder = year

        counter_key = subfolder
        year_counters[counter_key] += 1
        counter = year_counters[counter_key]

        new_ext = ".mp4" if mf.is_video else mf.ext
        new_name = f"{mf.date}_{counter:04d}{new_ext}"

        dest_dir = output_dir / subfolder
        dest = dest_dir / new_name
        key = f"{subfolder}/{new_name}"

        # Copying again would undo an encode or overlay burn already applied here.
        already_done = checkpoint is not None and checkpoint.is_file_done(step, key)

        if not dry_run and not already_done:
            dest_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(mf.path), str(dest))
            if checkpoint is not None:
                checkpoint.mark_file_done(step, key)

        file_index.append({
            "date": mf.date,
            "year": year,
            "subfolder": subfolder,
            "new_name": new_name,
            "original_name": mf.original_name,
            "source": mf.source,
            "type": "video" if mf.is_video else ("image" if mf.is_image else "other"),
            "ext": new_ext,
            "uuid": mf.uuid,
            # Only chat media carries a Media ID chat_history.json refers to.
            "media_id": extract_media_id(mf.original_name) if mf.source == "chat" else None,
            "dest": str(dest),
        })

    return file_index
