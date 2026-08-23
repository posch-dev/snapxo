# PDF rendering through Playwright's headless Chromium, one browser for all pages.

import os
import sys
from html import escape
from pathlib import Path

from rich.console import Console

console = Console()

LAUNCH_ARGS = [
    "--disable-background-networking",
    "--disable-component-update",
    "--disable-sync",
    "--disable-default-apps",
    "--no-first-run",
    "--no-default-browser-check",
]

PDF_OPTIONS = {
    "format": "A4",
    "print_background": True,
    "margin": {"top": "16mm", "bottom": "15mm", "left": "10mm", "right": "10mm"},
}

# Chromium fills pageNumber and totalPages itself. Styles must be inline, the
# page stylesheet does not reach these.
_BAR = ('<div style="font-size:8px;width:100%;padding:0 10mm;color:#999;'
        'display:flex;justify-content:space-between;font-family:sans-serif">'
        '<span>{left}</span><span>{right}</span></div>')
EMPTY_BAR = '<div></div>'


def _browser_cache_dir() -> Path:
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
    # Looks for the browser directory instead of starting the driver, which costs a
    # second and leaves noisy async teardown behind. Reason is "package" or "browser".
    try:
        import playwright  # noqa: F401
    except ImportError:
        return False, "package"

    cache = _browser_cache_dir()
    if cache.is_dir() and any(cache.glob("chromium*")):
        return True, ""
    return False, "browser"


class PdfRenderer:
    # A context manager. Without a usable browser `available` stays False and
    # render() reports once and does nothing, rather than aborting a long run.

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
            # Makes "everything stays local" enforced rather than promised.
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

    def render(self, html_path: Path, pdf_path: Path, header_left: str = "",
               header_right: str = "", footer_left: str = "") -> bool:
        if not self.available:
            if not self._warned:
                console.print("[yellow]Skipping PDFs - no browser available[/yellow]")
                self._warned = True
            return False

        page = None
        try:
            page = self._context.new_page()
            # Chromium resolves relative links against the file URL, so the images
            # beside the HTML load without extra permissions.
            page.goto(html_path.resolve().as_uri(), wait_until="load", timeout=60_000)
            options = dict(PDF_OPTIONS)
            options["display_header_footer"] = True
            options["header_template"] = (
                _BAR.format(left=escape(header_left), right=escape(header_right))
                if header_left or header_right else EMPTY_BAR
            )
            options["footer_template"] = _BAR.format(
                left=escape(footer_left),
                right='Page <span class="pageNumber"></span> of <span class="totalPages"></span>',
            )
            page.pdf(path=str(pdf_path), **options)
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
    target = pdf_path or html_path.with_suffix(".pdf")
    with PdfRenderer() as renderer:
        if renderer.render(html_path, target):
            console.print(f"  Generated {target.name}")
            return True
    return False
