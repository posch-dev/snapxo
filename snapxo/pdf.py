# PDF rendering through Playwright's headless Chromium. One browser is started for
# all pages: wkhtmltopdf spawned a process per file, which dominated the runtime
# on exports with many chats.

import os
import sys
from pathlib import Path

from rich.console import Console

console = Console()

# Keep Chromium from doing anything but rendering the local file
LAUNCH_ARGS = [
    "--disable-background-networking",
    "--disable-component-update",
    "--disable-sync",
    "--disable-default-apps",
    "--no-first-run",
    "--no-default-browser-check",
]

# Chromium uses print CSS for PDFs by default, which is what the pages expect
PDF_OPTIONS = {
    "format": "A4",
    "print_background": True,
    "margin": {"top": "12mm", "bottom": "12mm", "left": "10mm", "right": "10mm"},
}


def _browser_cache_dir() -> Path:
    # Where Playwright keeps downloaded browsers on this platform.
    override = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if override:
        return Path(override)
    if sys.platform.startswith("win"):
        base = os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local")
        return Path(base) / "ms-playwright"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / "ms-playwright"
    return Path.home() / ".cache" / "ms-playwright"


def playwright_status() -> tuple[bool, str]:
    # Returns (usable, reason), reason is "package" or "browser". Looks for the browser
    # directory instead of starting the driver, which costs a second and leaves noisy
    # async teardown behind.
    try:
        import playwright  # noqa: F401
    except ImportError:
        return False, "package"

    cache = _browser_cache_dir()
    if cache.is_dir() and any(cache.glob("chromium*")):
        return True, ""
    return False, "browser"


class PdfRenderer:
    # Renders local HTML to PDF, reusing one browser. Use as a context manager. If the
    # browser cannot start, `available` is False and render() reports once and does
    # nothing, so a long run is never aborted halfway just because of PDFs.

    def __init__(self):
        self._playwright = None
        self._browser = None
        self._context = None
        self.available = False
        self._warned = False

    def __enter__(self):
        try:
            from playwright.sync_api import sync_playwright

            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(args=LAUNCH_ARGS)
            # offline=True makes "everything stays local" an enforced property
            # rather than a promise: the pages are file:// and need nothing else
            self._context = self._browser.new_context(offline=True)
            self.available = True
        except Exception as e:
            console.print(f"[red]Could not start the PDF browser: {e}[/red]")
            self.available = False
        return self

    def __exit__(self, *exc):
        try:
            if self._context:
                self._context.close()
            if self._browser:
                self._browser.close()
        finally:
            if self._playwright:
                self._playwright.stop()
        return False

    def render(self, html_path: Path, pdf_path: Path) -> bool:
        if not self.available:
            if not self._warned:
                console.print("[yellow]Skipping PDFs - no browser available[/yellow]")
                self._warned = True
            return False

        page = None
        try:
            page = self._context.new_page()
            # Chromium resolves relative links against the file URL, so images
            # stored next to the HTML load without extra permissions
            page.goto(html_path.resolve().as_uri(), wait_until="load", timeout=60_000)
            page.pdf(path=str(pdf_path), **PDF_OPTIONS)
            return True
        except Exception as e:
            console.print(f"    [red]PDF failed ({html_path.name}): {e}[/red]")
            return False
        finally:
            if page:
                try:
                    page.close()
                except Exception:
                    pass


def render_single(html_path: Path, pdf_path: Path | None = None) -> bool:
    # For one-off conversions such as stats.html.
    target = pdf_path or html_path.with_suffix(".pdf")
    with PdfRenderer() as renderer:
        if renderer.render(html_path, target):
            console.print(f"  Generated {target.name}")
            return True
    return False
