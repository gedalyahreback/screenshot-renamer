#!/usr/bin/env python3
"""
menubar.py — rumps menu bar app for screenshot-renamer.
Opens the settings window in-process on a background thread so Tkinter
has access to the window server (avoids the 'Python quit unexpectedly' crash).
"""

import json
import subprocess
from pathlib import Path

import rumps

# ---------------------------------------------------------------------------
# Menu bar app
# ---------------------------------------------------------------------------

class ScreenshotRenamerApp(rumps.App):
    def __init__(self):
        title_item = rumps.MenuItem("Screenshot Renamer")
        title_item.set_callback(None)

        super().__init__(
            "Screenshot Renamer",
            icon=str(Path(__file__).parent / "assets" / "logo.png"),
            template=False,
            menu=[
                title_item,
                None,
                "Open Settings",
            ],
            quit_button="Quit",
        )

    @rumps.clicked("Open Settings")
    def open_settings(self, _):
        venv_python = Path(__file__).parent / ".venv" / "bin" / "python3.12"
        script = Path(__file__).parent / "settings_app.py"
        subprocess.Popen(
            [str(venv_python), str(script)],
            stdout=open("/tmp/settings_app.log", "w"),
            stderr=subprocess.STDOUT,
        )


if __name__ == "__main__":
    ScreenshotRenamerApp().run()
