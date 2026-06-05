# Anki Terminator Companion - Developer Documentation

This repository contains the source code for the **Anki Terminator Companion** add-on.

This addon is designed to be installed alongside the original **Anki Terminator V2 - ChatGPT DeepSeek Sidebar for Reviewer** (`1468920185`). At startup, it dynamically patches the original addon in memory to eliminate high-CPU hotspots without modifying a single file in the original addon's directory.

---

## Project Structure

```
Anki_Terminator_Companion/ (Repo Root)
├── addon/ (Addon Source)
│   ├── __init__.py           # Entry point: performs in-memory monkey patching of 1468920185
│   ├── manifest.json         # Core add-on metadata and configuration requirements
│   └── VERSION               # Tracking file for the current SemVer version
├── DEVELOPMENT.md            # This documentation file
├── bump.py                   # Version auto-increment script
└── make_ankiaddon.py         # Packaging script → produces the .ankiaddon release file
```

---

## Optimization Architecture

The companion addon works by implementing runtime dynamic overrides (monkey patches) on the imported classes of addon `1468920185`:

### 1. Ad-Blocker O(1) Suffix Lookup Patch
* **The Problem**: If the C-based Rust ad-blocker engine is not loaded, the original addon falls back to scanning a list of **~46,000 domains** via linear substring matching (`domain in url`) for every network request made in the sidebar. This blocks the Qt/UI thread and causes high CPU usage.
* **The Solution**: The companion patches the matching mechanism to separate pure domains (96% of rules) from path-specific rules. Pure domains are matched in `O(1)` time using a set lookup on the target URL's domain suffixes.

### 2. Gemini CSS Animation Disabler Patch
* **The Problem**: When the sidebar is visible and Gemini (`Google_Bard`) is selected, the renderer process (`QtWebEngineProcess`) consumes high CPU due to continuous painting of background shimmer animations, glow gradients, and backdrop filters.
* **The Solution**: The companion hooks into the webview's `inject_javascript` routine to inject a tiny CSS style block when Gemini loads, which disables all transitions, animations, and backdrop filters globally on the page, keeping the renderer idle and quiet.

---

## Development Workflow

### 1. Local Testing
To test this addon, ensure that the original addon (`1468920185`) is installed in your Anki profile, and that the `addon` source folder is symlinked or placed inside your Anki addons directory.

**Linux:**
```shell
ln -s "$(pwd)/addon" ~/.local/share/Anki2/addons21/Anki_Terminator_Companion
```

Restart Anki to automatically apply the optimizations. You will see confirmation logs in the terminal/stdout:
```
[Terminator Companion] Successfully patched AdBlocker interceptRequest for O(1) domain lookups!
[Terminator Companion] Successfully patched CustomWebEnginePage.inject_javascript for Gemini optimization!
```

---

## Building and Versioning

### 1. Auto-increment Version (SemVer)
```shell
# Increments the patch version (e.g. 1.0.0 -> 1.0.1) and updates manifest.json and VERSION
python bump.py

# Explicitly bump minor or major:
python bump.py minor
python bump.py major
```

### 2. Package the `.ankiaddon`
To package the addon for distribution on AnkiWeb:
```shell
python make_ankiaddon.py
```
This automatically bumps the patch version, ignores the build scripts (`bump.py`, `make_ankiaddon.py`, `DEVELOPMENT.md`), and outputs a timestamped `.ankiaddon` file in the root folder (e.g. `Anki_Terminator_Companion_v1.0.1_202606011830.ankiaddon`).
