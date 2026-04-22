#!/usr/bin/env python3
"""
menubar.py — rumps menu bar / Dock app for screenshot-renamer.

Presence modes (controlled via settings.json):
  "menubar" — menu bar icon only, no Dock icon (LSUIElement behaviour)
  "dock"    — Dock icon only, no menu bar icon
  "both"    — Dock icon + menu bar icon
"""

import json
import subprocess
from pathlib import Path

import AppKit
import rumps

SETTINGS_FILE = Path(__file__).parent / "settings.json"
ASSETS_DIR = Path(__file__).parent / "assets"


def load_presence() -> str:
    """Read the 'presence' value from settings.json. Defaults to 'dock'."""
    try:
        with open(SETTINGS_FILE) as f:
            data = json.load(f)
        value = str(data.get("presence", "dock"))
        if value not in ("dock", "menubar", "both"):
            return "dock"
        return value
    except (FileNotFoundError, json.JSONDecodeError):
        return "dock"


def _open_settings() -> None:
    """Launch settings_app.py as a subprocess using the venv Python."""
    venv_python = Path(__file__).parent / ".venv" / "bin" / "python3.12"
    # Fall back to any python3 in the venv if the versioned binary is absent
    if not venv_python.exists():
        venv_python = Path(__file__).parent / ".venv" / "bin" / "python3"
    script = Path(__file__).parent / "settings_app.py"
    subprocess.Popen(
        [str(venv_python), str(script)],
        stdout=open("/tmp/settings_app.log", "w"),
        stderr=subprocess.STDOUT,
    )


# ---------------------------------------------------------------------------
# Dock delegate — handles Dock icon click when presence is "dock" or "both"
# ---------------------------------------------------------------------------

class _AppDelegate(AppKit.NSObject):
    """Minimal NSApplicationDelegate that opens Settings on Dock icon click."""

    def applicationShouldHandleReopen_hasVisibleWindows_(self, app, has_visible):  # noqa: N802
        _open_settings()
        return False


# ---------------------------------------------------------------------------
# Menu bar app
# ---------------------------------------------------------------------------

class ScreenshotRenamerApp(rumps.App):
    def __init__(self, presence: str) -> None:
        self._presence = presence

        title_item = rumps.MenuItem("Screenshot Renamer")
        title_item.set_callback(None)

        icon_path = str(ASSETS_DIR / "logo.png")

        super().__init__(
            "Screenshot Renamer",
            icon=icon_path,
            template=False,
            menu=[
                title_item,
                None,
                "Open Settings",
            ],
            quit_button="Quit",
        )

        # Apply activation policy and optionally hide the menu bar icon
        self._apply_presence(presence)

    def _apply_presence(self, presence: str) -> None:
        app = AppKit.NSApplication.sharedApplication()

        if presence == "menubar":
            # Accessory: menu bar only, no Dock icon — current default behaviour
            app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyAccessory)

        elif presence == "dock":
            # Regular: Dock icon only — hide the rumps menu bar icon
            app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyRegular)
            self.icon = None
            self.title = None
            # Install delegate so Dock-icon click opens Settings
            delegate = _AppDelegate.alloc().init()
            app.setDelegate_(delegate)
            # Keep a strong reference so it isn't garbage-collected
            self._delegate = delegate

        elif presence == "both":
            # Regular: Dock icon + keep the menu bar icon
            app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyRegular)
            delegate = _AppDelegate.alloc().init()
            app.setDelegate_(delegate)
            self._delegate = delegate

    @rumps.clicked("Open Settings")
    def open_settings(self, _):
        _open_settings()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    presence = load_presence()
    ScreenshotRenamerApp(presence).run()
