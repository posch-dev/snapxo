from pathlib import Path

from rich.console import Console

from .ffmpeg import FFmpeg
from .utils import copy_timestamps

console = Console()


def detect_voice_messages(files: list[Path], ff: FFmpeg) -> list[Path]:
    # Detect audio-only MP4 or MOV files, those are voice messages.
    voice = []
    for f in files:
        if f.suffix.lower() in (".mp4", ".mov"):
            if not ff.has_video_stream(f):
                voice.append(f)
    return voice


def convert_voice_messages(voice_files: list[Path], ff: FFmpeg, dry_run: bool = False, verbose: bool = False,
                           checkpoint=None) -> int:
    # Convert voice messages from MP4 to MP3. Returns the count.
    if checkpoint is not None:
        voice_files = [f for f in voice_files if not checkpoint.is_file_done("voice", f.name)]

    converted = 0
    for i, f in enumerate(voice_files, 1):
        mp3_path = f.with_suffix(".mp3")
        if verbose:
            console.print(f"  [cyan][{i}/{len(voice_files)}][/cyan] {f.parent.name}/{f.name}")
        if dry_run:
            converted += 1
            continue
        if ff.convert_voice_to_mp3(f, mp3_path):
            copy_timestamps(f, mp3_path)
            f.unlink()
            converted += 1
            if checkpoint is not None:
                checkpoint.mark_file_done("voice", f.name)
            if verbose:
                console.print(f"    [green]OK[/green] → {mp3_path.name}")
        else:
            console.print(f"  [red]FAILED[/red] {f.name}")
    return converted
