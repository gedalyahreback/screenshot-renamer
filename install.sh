#!/usr/bin/env bash
set -euo pipefail

echo "==============================="
echo " screenshot-renamer installer"
echo "==============================="

# Check for python3
if ! command -v python3 &>/dev/null; then
    echo "Error: python3 is not available. Install Python 3 and try again." >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$HOME/.screenshot-renamer"

echo "Installing to $INSTALL_DIR ..."
mkdir -p "$INSTALL_DIR"

# Copy project files
cp "$SCRIPT_DIR/rename_screenshot.py"  "$INSTALL_DIR/rename_screenshot.py"
cp "$SCRIPT_DIR/menubar.py"            "$INSTALL_DIR/menubar.py"
cp "$SCRIPT_DIR/settings_app.py"      "$INSTALL_DIR/settings_app.py"
cp "$SCRIPT_DIR/requirements.txt"     "$INSTALL_DIR/requirements.txt"
cp -r "$SCRIPT_DIR/assets"            "$INSTALL_DIR/assets"

# Create virtualenv
echo "Creating virtualenv ..."
python3 -m venv "$INSTALL_DIR/.venv"

# Install dependencies
echo "Installing Python dependencies ..."
"$INSTALL_DIR/.venv/bin/pip" install -q -r "$INSTALL_DIR/requirements.txt"

# Copy default settings only if not already present
if [ ! -f "$INSTALL_DIR/settings.json" ]; then
    cp "$SCRIPT_DIR/settings.json.example" "$INSTALL_DIR/settings.json"
    echo "Created default settings.json"
fi

# Install LaunchAgent plist
PLIST_DIR="$HOME/Library/LaunchAgents"
PLIST_DEST="$PLIST_DIR/com.user.screenshot-renamer.plist"
mkdir -p "$PLIST_DIR"
cp "$SCRIPT_DIR/com.user.screenshot-renamer.plist" "$PLIST_DEST"

# Load the LaunchAgent
launchctl unload "$PLIST_DEST" 2>/dev/null || true
launchctl load "$PLIST_DEST"

echo ""
echo "==============================="
echo " Installation complete!"
echo "==============================="
echo ""
echo "Next step — store your OpenAI API key:"
echo ""
echo "  echo 'OPENAI_API_KEY=sk-...' > ~/.screenshot-renamer-env"
echo "  chmod 600 ~/.screenshot-renamer-env"
echo ""
echo "The watcher will start automatically at login."
echo "Logs: /tmp/screenshot-renamer.log"
