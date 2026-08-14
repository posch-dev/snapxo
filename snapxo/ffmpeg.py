import shutil
import subprocess
from functools import lru_cache
from pathlib import Path

from rich.console import Console

console = Console()


def _run(cmd: list[str], **kwargs):
    # ffmpeg reads stdin when it is left attached and would swallow the answer to
    # the next prompt, so every call gets an empty one.
    return subprocess.run(cmd, stdin=subprocess.DEVNULL, **kwargs)


class FFmpeg:
    def __init__(self, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe",
                 no_hwaccel: bool = False, crf: int = 23):
        self.ffmpeg = self._resolve(ffmpeg_path, "ffmpeg")
        self.ffprobe = self._resolve(ffprobe_path, "ffprobe")
        self.crf = crf
        # Probing for hardware encoders is pointless without ffmpeg, and the
        # "falling back to libx265" note would be misleading when nothing is there
        self.qsv_available = False
        if not no_hwaccel and self.check():
            self.qsv_available = self._detect_qsv()

    def _resolve(self, path: str, name: str) -> str:
        if Path(path).is_file():
            return path
        resolved = shutil.which(path)
        if resolved:
            return resolved
        if path != name:
            # An explicitly given path that does not exist should be said out
            # loud rather than silently replaced by whatever is on PATH
            console.print(f"[yellow]{path} not found, looking for {name} on PATH instead[/yellow]")
        resolved = shutil.which(name)
        if resolved:
            return resolved
        bundled = self._static_binaries()
        if bundled and name in bundled:
            return bundled[name]
        return name

    @staticmethod
    @lru_cache(maxsize=1)
    def _static_binaries() -> dict[str, str] | None:
        # Binaries from the optional static-ffmpeg package, used only when nothing is
        # installed system wide. Those builds lack QSV, so a system ffmpeg stays better.
        # Cached because resolving may download them on first use.
        try:
            from static_ffmpeg import run
        except ImportError:
            return None
        try:
            ffmpeg, ffprobe = run.get_or_fetch_platform_executables_else_raise()
        except Exception:
            return None
        console.print("[dim]Using ffmpeg from the static-ffmpeg package[/dim]")
        return {"ffmpeg": ffmpeg, "ffprobe": ffprobe}

    def check(self) -> bool:
        try:
            _run([self.ffmpeg, "-version"], capture_output=True, timeout=5)
            _run([self.ffprobe, "-version"], capture_output=True, timeout=5)
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def _detect_qsv(self) -> bool:
        try:
            result = _run(
                [self.ffmpeg, "-hide_banner", "-encoders"],
                capture_output=True, text=True, timeout=10,
            )
            if "hevc_qsv" not in result.stdout:
                console.print("[yellow]QSV encoder not found, using software encoding (libx265)[/yellow]")
                return False
        except Exception:
            console.print("[yellow]QSV not available, using software encoding (libx265)[/yellow]")
            return False

        # Test actual QSV encoding with hw device init and realistic resolution
        try:
            result = _run(
                [self.ffmpeg, "-hide_banner",
                 "-init_hw_device", "qsv=hw",
                 "-f", "lavfi", "-i", "color=c=black:s=1920x1080:d=0.1:r=30",
                 "-c:v", "hevc_qsv", "-low_power", "0",
                 "-global_quality", str(self.crf),
                 "-frames:v", "1", "-f", "null", "-"],
                capture_output=True, text=True, timeout=15,
            )
            if result.returncode == 0:
                console.print("[green]QSV hardware encoding available (Intel Arc)[/green]")
                return True
        except Exception:
            pass

        console.print("[yellow]QSV test encode failed, using software encoding (libx265)[/yellow]")
        return False

    def get_video_codec(self, filepath: Path) -> str | None:
        try:
            result = _run(
                [self.ffprobe, "-v", "error", "-select_streams", "v:0",
                 "-show_entries", "stream=codec_name", "-of", "csv=p=0",
                 str(filepath)],
                capture_output=True, text=True, timeout=10,
            )
            return result.stdout.strip().rstrip(",") or None
        except Exception:
            return None

    def has_video_stream(self, filepath: Path) -> bool:
        try:
            result = _run(
                [self.ffprobe, "-v", "error", "-select_streams", "v",
                 "-show_entries", "stream=codec_type", "-of", "csv=p=0",
                 str(filepath)],
                capture_output=True, text=True, timeout=10,
            )
            return result.stdout.strip() != ""
        except Exception:
            return True

    def _h265_args(self, use_qsv: bool) -> list[str]:
        if use_qsv:
            return ["-c:v", "hevc_qsv", "-low_power", "0",
                    "-global_quality", str(self.crf), "-tag:v", "hvc1"]
        return ["-c:v", "libx265", "-crf", str(self.crf), "-tag:v", "hvc1"]

    def _hw_init_args(self, use_qsv: bool) -> list[str]:
        if use_qsv:
            return ["-init_hw_device", "qsv=hw"]
        return []

    def convert_to_h265(self, input_path: Path, output_path: Path) -> bool:
        for use_qsv in ([True, False] if self.qsv_available else [False]):
            try:
                cmd = [
                    self.ffmpeg, "-y",
                    *self._hw_init_args(use_qsv),
                    "-i", str(input_path),
                    *self._h265_args(use_qsv),
                    "-c:a", "aac", "-b:a", "128k",
                    str(output_path),
                ]
                result = _run(cmd, capture_output=True, text=True, timeout=600)
                if result.returncode == 0:
                    return True
                if use_qsv:
                    continue
            except Exception:
                if use_qsv:
                    continue
                return False
        return False

    def grab_frame(self, input_path: Path, output_path: Path, height: int = 320) -> bool:
        # Seeks a second in, the opening frame of a Snapchat video is often black.
        try:
            cmd = [
                self.ffmpeg, "-y", "-ss", "1",
                "-i", str(input_path),
                "-frames:v", "1",
                "-vf", f"scale=-2:{height}:force_original_aspect_ratio=decrease",
                str(output_path),
            ]
            result = _run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode == 0 and output_path.is_file() and output_path.stat().st_size > 0:
                return True
            # Video is shorter than the seek point.
            cmd[cmd.index("-ss") + 1] = "0"
            result = _run(cmd, capture_output=True, text=True, timeout=60)
            return result.returncode == 0 and output_path.is_file() and output_path.stat().st_size > 0
        except Exception:
            return False

    def burn_overlay_image(self, main_path: Path, overlay_path: Path, output_path: Path) -> bool:
        try:
            result = _run(
                [self.ffmpeg, "-y", "-i", str(main_path), "-i", str(overlay_path),
                 "-filter_complex", "[0][1]overlay=0:0",
                 "-q:v", "2", str(output_path)],
                capture_output=True, text=True, timeout=60,
            )
            return result.returncode == 0
        except Exception:
            return False

    def burn_overlay_video_h265(self, main_path: Path, overlay_path: Path, output_path: Path) -> bool:
        # Scale overlay to match video dimensions, then overlay
        filter_complex = "[1][0]scale2ref=w=iw:h=ih[ovr][base];[base][ovr]overlay=0:0"
        for use_qsv in ([True, False] if self.qsv_available else [False]):
            try:
                cmd = [
                    self.ffmpeg, "-y",
                    *self._hw_init_args(use_qsv),
                    "-i", str(main_path), "-i", str(overlay_path),
                    "-filter_complex", filter_complex,
                    *self._h265_args(use_qsv),
                    "-c:a", "aac", "-b:a", "128k",
                    str(output_path),
                ]
                result = _run(cmd, capture_output=True, text=True, timeout=600)
                if result.returncode == 0:
                    return True
                if use_qsv:
                    continue
            except Exception:
                if use_qsv:
                    continue
                return False
        return False

    def convert_voice_to_mp3(self, input_path: Path, output_path: Path) -> bool:
        try:
            result = _run(
                [self.ffmpeg, "-y", "-i", str(input_path),
                 "-vn", "-c:a", "libmp3lame", "-q:a", "2",
                 str(output_path)],
                capture_output=True, text=True, timeout=30,
            )
            return result.returncode == 0
        except Exception:
            return False
