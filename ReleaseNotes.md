# Release Notes

## v0.1.1 — 2026-04-28

Added an **Append timestamp to filename** toggle in the Settings window. When disabled, the `-YYYYMMDD-HHMMSS` suffix is omitted and the file is saved using only the chosen name. The setting is stored as `append_timestamp` in `settings.json` and defaults to `true`, preserving existing behavior.

## v0.1.0 — Initial Release

First public release of Screenshot Renamer.

- Watches a configurable directory (default `~/Screenshots`) for new macOS screenshots and screen recordings.
- Prompts for a custom filename via a native macOS dialog.
- Supports `block` mode (waits indefinitely) and `auto` mode (accepts the pre-filled name after a configurable timeout).
- Optionally converts screen recordings to GIF using ffmpeg's two-pass palette method.
- Optionally deletes the original video after GIF conversion.
- App presence is configurable: Dock, Menu Bar, or both.
- Automated GitHub Release workflow triggers on version tags and dispatches a Homebrew formula update.
- Installed via `brew install <your-username>/tools/screenshot-renamer` or manually via `install.sh`.
