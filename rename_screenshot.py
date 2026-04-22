#!/usr/bin/env python3
"""
screenshot-renamer: watches ~/Screenshots for new macOS screenshots,
prompts you to enter a name via a native dialog, and renames the file as:
  {your-name}-{YYYYMMDD}-{HHMMSS}.png
"""

import json
import logging
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from watchdog.events import FileSystemEventHandler
from watchdog.observers.fsevents import FSEventsObserver as Observer

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
LOG_FILE = Path(__file__).parent / "renamer.log"
SETTINGS_FILE = Path(__file__).parent / "settings.json"

# Matches macOS default screenshot and screen recording filenames
SCREENSHOT_PATTERN = re.compile(
    r"^(Screenshot|Screen Recording)\s+\d{4}-\d{2}-\d{2}.*\.(png|jpg|jpeg|mov|mp4)$",
    re.IGNORECASE,
)

# Characters that are safe in filenames
SAFE_CHAR = re.compile(r"[^a-z0-9]+")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
def load_settings() -> dict:
    """
    Read settings.json and return a dict with keys:
      dialog_mode (str), dialog_timeout (int), watch_dir (Path).
    Falls back to safe defaults if the file is missing or corrupt.
    """
    defaults = {
        "dialog_mode": "block",
        "dialog_timeout": 15,
        "watch_dir": Path.home() / "Screenshots",
        "convert_to_gif": False,
        "delete_original": True,
    }
    try:
        with open(SETTINGS_FILE, "r") as f:
            data = json.load(f)
        return {
            "dialog_mode": str(data.get("dialog_mode", defaults["dialog_mode"])),
            "dialog_timeout": int(data.get("dialog_timeout", defaults["dialog_timeout"])),
            "watch_dir": Path(data.get("watch_dir", str(defaults["watch_dir"]))).expanduser(),
            "convert_to_gif": bool(data.get("convert_to_gif", False)),
            "delete_original": bool(data.get("delete_original", True)),
        }
    except (FileNotFoundError, json.JSONDecodeError, ValueError):
        log.warning("Could not read %s — using defaults.", SETTINGS_FILE)
        return defaults


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def slugify(text: str) -> str:
    """Lowercase, replace runs of non-alphanumeric chars with a single hyphen."""
    return SAFE_CHAR.sub("-", text.lower()).strip("-")


def default_stem() -> str:
    """Timestamp-based pre-fill shown in the dialog (e.g. 'screenshot-20260414-120000')."""
    return datetime.now().strftime("screenshot-%Y%m%d-%H%M%S")


# ---------------------------------------------------------------------------
# Dialog
# ---------------------------------------------------------------------------
def prompt_for_name(
    prefill: str,
    mode: str = "block",
    timeout: int = 15,
) -> Optional[str]:
    """
    Show a native macOS dialog pre-filled with `prefill`.

    mode="block"  — waits indefinitely; Cancel leaves file as-is.
    mode="auto"   — auto-accepts the pre-filled name after `timeout` seconds.

    Returns the confirmed (possibly edited) stem, or None if cancelled.
    """
    safe_prefill = prefill.replace("\\", "\\\\").replace('"', '\\"')

    if mode == "auto":
        subtitle = f"Auto-accepting in {timeout}s if no response."
        lines = [
            'tell application "Finder"',
            '    activate',
            f'    set dlg to display dialog "Name this screenshot:\\n{subtitle}" '
            f'default answer "{safe_prefill}" '
            f'with title "Screenshot Renamer" '
            f'buttons {{"Cancel", "Save"}} default button "Save" '
            f'giving up after {timeout}',
            '    if gave up of dlg then',
            f'        return "{safe_prefill}"',
            '    else if button returned of dlg is "Cancel" then',
            '        return ""',
            '    else',
            '        return text returned of dlg',
            '    end if',
            'end tell',
        ]
    else:
        lines = [
            'tell application "Finder"',
            '    activate',
            f'    set dlg to display dialog "Name this screenshot:" '
            f'default answer "{safe_prefill}" '
            f'with title "Screenshot Renamer" '
            f'buttons {{"Cancel", "Save"}} default button "Save"',
            '    if button returned of dlg is "Cancel" then',
            '        return ""',
            '    else',
            '        return text returned of dlg',
            '    end if',
            'end tell',
        ]

    script = "\n".join(lines)

    proc = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
    )

    if proc.returncode != 0:
        return None

    result = proc.stdout.strip()
    if result == "":
        return None

    return slugify(result) or prefill


# ---------------------------------------------------------------------------
# Rename logic
# ---------------------------------------------------------------------------
def rename_screenshot(
    src: Path,
    dialog_mode: str = "block",
    dialog_timeout: int = 15,
    do_gif_convert: bool = False,
    delete_original: bool = True,
) -> None:
    """Full pipeline: validate -> wait -> prompt -> rename -> (optional GIF conversion)."""
    if not SCREENSHOT_PATTERN.match(src.name):
        return

    log.info("New screenshot detected: %s", src.name)

    # Brief pause to let macOS finish any final file operations
    time.sleep(0.3)

    if not src.exists():
        log.warning("File disappeared before we could rename it: %s", src)
        return

    prefill = default_stem()
    chosen_stem = prompt_for_name(prefill, mode=dialog_mode, timeout=dialog_timeout)

    if chosen_stem is None:
        log.info("User cancelled rename for %s -- leaving as-is", src.name)
        return

    now = datetime.now()
    stem = f"{chosen_stem}-{now.strftime('%Y%m%d')}-{now.strftime('%H%M%S')}"
    ext = src.suffix.lower()
    target = src.parent / f"{stem}{ext}"
    counter = 2
    while target.exists():
        target = src.parent / f"{stem}_{counter}{ext}"
        counter += 1

    src.rename(target)
    log.info("Renamed  %s  ->  %s", src.name, target.name)

    if do_gif_convert and ext in (".mov", ".mp4"):
        convert_to_gif(target, delete_original)


# ---------------------------------------------------------------------------
# GIF conversion
# ---------------------------------------------------------------------------
FFMPEG = "/opt/homebrew/bin/ffmpeg"


def convert_to_gif(src: Path, delete_original: bool) -> None:
    """Convert a video file to a high-quality GIF using ffmpeg palette trick."""
    import subprocess as sp

    gif_path = src.with_suffix(".gif")
    palette = src.with_suffix(".png")  # temp palette file

    try:
        # Pass 1: generate palette
        r1 = sp.run(
            [
                FFMPEG, "-y", "-i", str(src),
                "-vf", "fps=15,scale=800:-1:flags=lanczos,palettegen",
                str(palette),
            ],
            capture_output=True,
        )
        if r1.returncode != 0:
            log.error(
                "ffmpeg palette generation failed for %s: %s",
                src.name,
                r1.stderr.decode(),
            )
            return

        # Pass 2: generate GIF using palette
        r2 = sp.run(
            [
                FFMPEG, "-y", "-i", str(src), "-i", str(palette),
                "-filter_complex", "fps=15,scale=800:-1:flags=lanczos[x];[x][1:v]paletteuse",
                str(gif_path),
            ],
            capture_output=True,
        )
        if r2.returncode != 0:
            log.error(
                "ffmpeg GIF conversion failed for %s: %s",
                src.name,
                r2.stderr.decode(),
            )
            return

        log.info("Converted  %s  ->  %s", src.name, gif_path.name)

        if delete_original:
            src.unlink()
            log.info("Deleted original: %s", src.name)

    finally:
        # Clean up temp palette file
        if palette.exists():
            palette.unlink()


# ---------------------------------------------------------------------------
# Watchdog handler
# ---------------------------------------------------------------------------
class ScreenshotHandler(FileSystemEventHandler):
    def __init__(
        self,
        dialog_mode: str,
        dialog_timeout: int,
        convert_to_gif: bool = False,
        delete_original: bool = True,
    ) -> None:
        super().__init__()
        self.dialog_mode = dialog_mode
        self.dialog_timeout = dialog_timeout
        self.convert_to_gif = convert_to_gif
        self.delete_original = delete_original

    def on_created(self, event):
        if not event.is_directory:
            rename_screenshot(
                Path(event.src_path),
                dialog_mode=self.dialog_mode,
                dialog_timeout=self.dialog_timeout,
                do_gif_convert=self.convert_to_gif,
                delete_original=self.delete_original,
            )

    def on_moved(self, event):
        # macOS writes screenshots via the markup editor using a move/rename,
        # so we must also handle on_moved and treat the destination as the new file.
        if not event.is_directory:
            rename_screenshot(
                Path(event.dest_path),
                dialog_mode=self.dialog_mode,
                dialog_timeout=self.dialog_timeout,
                do_gif_convert=self.convert_to_gif,
                delete_original=self.delete_original,
            )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    settings = load_settings()
    watch_dir: Path = settings["watch_dir"]
    dialog_mode: str = settings["dialog_mode"]
    dialog_timeout: int = settings["dialog_timeout"]
    do_convert_to_gif: bool = settings["convert_to_gif"]
    do_delete_original: bool = settings["delete_original"]

    if not watch_dir.exists():
        log.error("Watch directory does not exist: %s", watch_dir)
        sys.exit(1)

    log.info("screenshot-renamer starting -- watching %s", watch_dir)

    observer = Observer()
    observer.schedule(
        ScreenshotHandler(
            dialog_mode,
            dialog_timeout,
            convert_to_gif=do_convert_to_gif,
            delete_original=do_delete_original,
        ),
        str(watch_dir),
        recursive=False,
    )
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        observer.stop()
        observer.join()
        log.info("screenshot-renamer stopped.")


if __name__ == "__main__":
    main()
