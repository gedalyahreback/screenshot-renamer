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
# Dock click handler — injected into rumps' existing delegate at runtime
# ---------------------------------------------------------------------------

def _inject_dock_handler() -> None:
    """
    Add applicationShouldHandleReopen_hasVisibleWindows_ to rumps' internal
    NSApp delegate class so that clicking the Dock icon opens Settings.
    We inject rather than replace the delegate to avoid breaking rumps internals.
    """
    from rumps import rumps as _rumps_module

    def applicationShouldHandleReopen_hasVisibleWindows_(self, app, has_visible):  # noqa: N802
        _open_settings()
        return False

    # rumps' internal delegate class is named NSApp
    _rumps_module.NSApp.applicationShouldHandleReopen_hasVisibleWindows_ = (
        applicationShouldHandleReopen_hasVisibleWindows_
    )


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
        ns_app = AppKit.NSApplication.sharedApplication()

        if presence == "menubar":
            # Accessory: menu bar only, no Dock icon — current default behaviour
            ns_app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyAccessory)

        elif presence == "dock":
            # Regular: Dock icon only — hide the rumps menu bar icon
            ns_app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyRegular)
            self.icon = None
            self.title = None
            _inject_dock_handler()

        elif presence == "both":
            # Regular: Dock icon + keep the menu bar icon
            ns_app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyRegular)
            _inject_dock_handler()

    @rumps.clicked("Open Settings")
    def open_settings(self, _):
        _open_settings()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    presence = load_presence()
    ScreenshotRenamerApp(presence).run()
