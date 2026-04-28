#!/usr/bin/env python3
"""
settings_app.py — Tkinter settings window for screenshot-renamer.
"""

import json
import subprocess
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SETTINGS_FILE = Path(__file__).parent / "settings.json"
PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / "com.user.screenshot-renamer.plist"
MENUBAR_PLIST_PATH = (
    Path.home() / "Library" / "LaunchAgents" / "com.user.screenshot-renamer-menubar.plist"
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_settings() -> dict:
    defaults = {
        "dialog_mode": "block",
        "dialog_timeout": 15,
        "watch_dir": str(Path.home() / "Screenshots"),
        "convert_to_gif": False,
        "delete_original": True,
        "presence": "dock",
        "append_timestamp": True,
    }
    try:
        with open(SETTINGS_FILE, "r") as f:
            data = json.load(f)
        presence = str(data.get("presence", defaults["presence"]))
        if presence not in ("dock", "menubar", "both"):
            presence = "dock"
        return {
            "dialog_mode": str(data.get("dialog_mode", defaults["dialog_mode"])),
            "dialog_timeout": int(data.get("dialog_timeout", defaults["dialog_timeout"])),
            "watch_dir": str(Path(data.get("watch_dir", defaults["watch_dir"])).expanduser()),
            "convert_to_gif": bool(data.get("convert_to_gif", False)),
            "delete_original": bool(data.get("delete_original", True)),
            "presence": presence,
            "append_timestamp": bool(data.get("append_timestamp", True)),
        }
    except (FileNotFoundError, json.JSONDecodeError, ValueError):
        return defaults


def save_settings(
    dialog_mode: str,
    dialog_timeout: int,
    watch_dir: str,
    convert_to_gif: bool = False,
    delete_original: bool = True,
    presence: str = "dock",
    append_timestamp: bool = True,
) -> None:
    data = {
        "dialog_mode": dialog_mode,
        "dialog_timeout": dialog_timeout,
        "watch_dir": watch_dir,
        "convert_to_gif": convert_to_gif,
        "delete_original": delete_original,
        "presence": presence,
        "append_timestamp": append_timestamp,
    }
    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def check_login_item() -> bool:
    """Return True if the watcher LaunchAgent is currently loaded."""
    try:
        result = subprocess.run(
            ["launchctl", "list"],
            capture_output=True,
            text=True,
        )
        for line in result.stdout.splitlines():
            if "com.user.screenshot-renamer" in line and "menubar" not in line:
                return True
        return False
    except Exception:
        return False


def reload_watcher() -> None:
    """Unload then load the watcher LaunchAgent to pick up new settings."""
    plist = str(PLIST_PATH)
    subprocess.run(["launchctl", "unload", plist], capture_output=True)
    subprocess.run(["launchctl", "load", plist], capture_output=True)


def _restart_menubar() -> None:
    """Kill the running menubar.py process and relaunch it so presence changes take effect."""
    import signal
    import os

    # Find and kill any running menubar.py process
    try:
        result = subprocess.run(
            ["pgrep", "-f", "menubar.py"],
            capture_output=True,
            text=True,
        )
        for pid_str in result.stdout.strip().splitlines():
            try:
                os.kill(int(pid_str), signal.SIGTERM)
            except (ProcessLookupError, ValueError):
                pass
    except Exception:
        pass

    # Relaunch menubar.py using the venv Python
    venv_python = Path(__file__).parent / ".venv" / "bin" / "python3.12"
    if not venv_python.exists():
        venv_python = Path(__file__).parent / ".venv" / "bin" / "python3"
    script = Path(__file__).parent / "menubar.py"
    subprocess.Popen(
        [str(venv_python), str(script)],
        stdout=open("/tmp/menubar.log", "w"),
        stderr=subprocess.STDOUT,
    )


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

class SettingsApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title("Screenshot Renamer Settings")
        root.resizable(False, False)

        settings = load_settings()

        # ------------------------------------------------------------------ #
        # Variables
        # ------------------------------------------------------------------ #
        self.dialog_mode_var = tk.StringVar(value=settings["dialog_mode"])
        self.timeout_var = tk.IntVar(value=settings["dialog_timeout"])
        self.watch_dir_var = tk.StringVar(value=settings["watch_dir"])
        self.login_item_var = tk.BooleanVar(value=check_login_item())
        self.convert_gif_var = tk.BooleanVar(value=settings["convert_to_gif"])
        self.delete_original_var = tk.BooleanVar(value=settings["delete_original"])
        self.append_timestamp_var = tk.BooleanVar(value=settings["append_timestamp"])
        self.presence_var = tk.StringVar(value=settings["presence"])

        pad = {"padx": 12, "pady": 6}

        # ------------------------------------------------------------------ #
        # Dialog Mode row
        # ------------------------------------------------------------------ #
        mode_frame = tk.Frame(root)
        mode_frame.pack(fill="x", **pad)

        tk.Label(mode_frame, text="Dialog Mode:", width=18, anchor="w").pack(side="left")
        mode_menu = tk.OptionMenu(
            mode_frame,
            self.dialog_mode_var,
            "block",
            "auto",
            command=self._on_mode_change,
        )
        mode_menu.pack(side="left")

        # ------------------------------------------------------------------ #
        # Auto-accept Timeout row
        # ------------------------------------------------------------------ #
        timeout_frame = tk.Frame(root)
        timeout_frame.pack(fill="x", **pad)

        tk.Label(timeout_frame, text="Auto-accept Timeout:", width=18, anchor="w").pack(side="left")
        self.timeout_spinbox = tk.Spinbox(
            timeout_frame,
            from_=1,
            to=120,
            width=5,
            textvariable=self.timeout_var,
        )
        self.timeout_spinbox.pack(side="left")
        self.timeout_label = tk.Label(timeout_frame, text=" seconds")
        self.timeout_label.pack(side="left")

        # Set initial enabled/disabled state
        self._set_timeout_state(settings["dialog_mode"])

        # ------------------------------------------------------------------ #
        # Watch Folder row
        # ------------------------------------------------------------------ #
        folder_frame = tk.Frame(root)
        folder_frame.pack(fill="x", **pad)

        tk.Label(folder_frame, text="Watch Folder:", width=18, anchor="w").pack(side="left")
        self.folder_entry = tk.Entry(
            folder_frame,
            textvariable=self.watch_dir_var,
            state="readonly",
            width=32,
        )
        self.folder_entry.pack(side="left", padx=(0, 6))
        tk.Button(folder_frame, text="Change\u2026", command=self._choose_folder).pack(side="left")

        # ------------------------------------------------------------------ #
        # Start at Login row
        # ------------------------------------------------------------------ #
        login_frame = tk.Frame(root)
        login_frame.pack(fill="x", **pad)

        self.login_cb = tk.Checkbutton(
            login_frame,
            text="Start at Login",
            variable=self.login_item_var,
            command=self._toggle_login_item,
        )
        self.login_cb.pack(side="left")

        # ------------------------------------------------------------------ #
        # Convert to GIF row
        # ------------------------------------------------------------------ #
        gif_frame = tk.Frame(root)
        gif_frame.pack(fill="x", **pad)

        self.convert_gif_cb = tk.Checkbutton(
            gif_frame,
            text="Convert recordings to GIF",
            variable=self.convert_gif_var,
            command=self._on_convert_gif_toggle,
        )
        self.convert_gif_cb.pack(side="left")

        # Sub-row: Delete original
        delete_frame = tk.Frame(root)
        delete_frame.pack(fill="x", padx=(36, 12), pady=(0, 6))

        self.delete_original_cb = tk.Checkbutton(
            delete_frame,
            text="Delete original after conversion",
            variable=self.delete_original_var,
        )
        self.delete_original_cb.pack(side="left")

        # Set initial state of delete_original_cb based on convert_gif_var
        self._on_convert_gif_toggle()

        # ------------------------------------------------------------------ #
        # Append Timestamp row
        # ------------------------------------------------------------------ #
        timestamp_frame = tk.Frame(root)
        timestamp_frame.pack(fill="x", **pad)

        self.append_timestamp_cb = tk.Checkbutton(
            timestamp_frame,
            text="Append timestamp to filename",
            variable=self.append_timestamp_var,
        )
        self.append_timestamp_cb.pack(side="left")

        # ------------------------------------------------------------------ #
        # App Presence row
        # ------------------------------------------------------------------ #
        presence_frame = tk.Frame(root)
        presence_frame.pack(fill="x", **pad)

        tk.Label(presence_frame, text="Show App In:", width=18, anchor="w").pack(side="left")
        for value, label in [("dock", "Dock"), ("menubar", "Menu Bar"), ("both", "Both")]:
            tk.Radiobutton(
                presence_frame,
                text=label,
                variable=self.presence_var,
                value=value,
            ).pack(side="left", padx=(0, 8))

        # ------------------------------------------------------------------ #
        # Separator
        # ------------------------------------------------------------------ #
        tk.Frame(root, height=1, bg="#cccccc").pack(fill="x", padx=12, pady=4)

        # ------------------------------------------------------------------ #
        # Bottom buttons
        # ------------------------------------------------------------------ #
        btn_frame = tk.Frame(root)
        btn_frame.pack(fill="x", padx=12, pady=(4, 12))

        tk.Button(btn_frame, text="Cancel", width=10, command=self._cancel).pack(
            side="right", padx=(6, 0)
        )
        tk.Button(btn_frame, text="Save", width=10, command=self._save, default="active").pack(
            side="right"
        )

        # ------------------------------------------------------------------ #
        # Center window on screen
        # ------------------------------------------------------------------ #
        root.update_idletasks()
        w = root.winfo_width()
        h = root.winfo_height()
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        root.geometry(f"+{x}+{y}")

    # ---------------------------------------------------------------------- #
    # Callbacks
    # ---------------------------------------------------------------------- #

    def _on_mode_change(self, value: str) -> None:
        self._set_timeout_state(value)

    def _set_timeout_state(self, mode: str) -> None:
        state = "normal" if mode == "auto" else "disabled"
        self.timeout_spinbox.config(state=state)
        self.timeout_label.config(state=state)

    def _on_convert_gif_toggle(self) -> None:
        state = "normal" if self.convert_gif_var.get() else "disabled"
        self.delete_original_cb.config(state=state)

    def _choose_folder(self) -> None:
        current = self.watch_dir_var.get()
        chosen = filedialog.askdirectory(
            title="Choose Watch Folder",
            initialdir=current if Path(current).exists() else str(Path.home()),
        )
        if chosen:
            self.watch_dir_var.set(chosen)

    def _toggle_login_item(self) -> None:
        plist = str(PLIST_PATH)
        if self.login_item_var.get():
            subprocess.run(["launchctl", "load", plist], capture_output=True)
        else:
            subprocess.run(["launchctl", "unload", plist], capture_output=True)

    def _save(self) -> None:
        try:
            timeout_val = int(self.timeout_spinbox.get())
        except ValueError:
            messagebox.showerror(
                "Invalid Input",
                "Timeout must be a whole number between 1 and 120.",
            )
            return

        save_settings(
            dialog_mode=self.dialog_mode_var.get(),
            dialog_timeout=timeout_val,
            watch_dir=self.watch_dir_var.get(),
            convert_to_gif=self.convert_gif_var.get(),
            delete_original=self.delete_original_var.get(),
            presence=self.presence_var.get(),
            append_timestamp=self.append_timestamp_var.get(),
        )
        reload_watcher()
        _restart_menubar()
        self.root.destroy()

    def _cancel(self) -> None:
        self.root.destroy()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = SettingsApp(root)
    root.mainloop()
