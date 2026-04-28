![Screenshot Renamer](assets/logo.png)

Watches `~/Screenshots` for new screenshots and renames them automatically using GPT-4o vision.

## How it works

When a new PNG appears in the configured watch directory, the watcher sends the image to GPT-4o and receives a concise, descriptive filename in the format `{main-idea}-{descriptor}-{YYYYMMDD}-{HHMMSS}.png`. The original file is replaced with the renamed version. A native macOS dialog optionally prompts for confirmation or allows a custom name before renaming.

## Installation

### Via Homebrew

This is the recommended installation method.

```bash
brew tap <your-username>/tools
brew install screenshot-renamer
```

Follow the post-install caveats printed by Homebrew to store your API key and load the background agent.

### Manual

Clone or download this repository, then run the installer script.

```bash
bash install.sh
```

The installer copies all project files to `~/.screenshot-renamer`, creates a Python virtualenv, installs dependencies, and registers the LaunchAgent so the watcher starts at login.

## Configuration

Configuration lives in `~/.screenshot-renamer/settings.json`. See `settings.json.example` for the full template. The `dialog_mode` field controls how the rename prompt behaves: `\"block\"` waits for user input, while `\"timeout\"` accepts the GPT suggestion automatically after `dialog_timeout` seconds. The `watch_dir` field sets the directory to monitor (default `~/Screenshots`). Setting `convert_to_gif` to `true` converts the screenshot to an animated GIF before renaming. Setting `delete_original` to `false` keeps the original file alongside the renamed copy. Setting `append_timestamp` to `false` omits the `-YYYYMMDD-HHMMSS` suffix so the file is saved using only the chosen name.

## API Key

The watcher reads your OpenAI API key from `~/.screenshot-renamer-env` at startup. Create this file with the following commands.

```bash
echo 'OPENAI_API_KEY=sk-...' > ~/.screenshot-renamer-env
chmod 600 ~/.screenshot-renamer-env
```

Never commit or share this file. It is excluded from version control by `.gitignore`.

## Uninstall

```bash
launchctl unload ~/Library/LaunchAgents/com.user.screenshot-renamer.plist
rm ~/Library/LaunchAgents/com.user.screenshot-renamer.plist
rm -rf ~/.screenshot-renamer
rm ~/.screenshot-renamer-env
```
