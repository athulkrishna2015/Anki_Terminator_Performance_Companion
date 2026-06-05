# Anki Terminator Companion - Developer Documentation

This repository contains the source code for the **Anki Terminator Companion** add-on.

This addon is designed to be installed alongside the original **Anki Terminator V2 - ChatGPT DeepSeek Sidebar for Reviewer** (`1468920185`). At startup, it dynamically patches the original addon in memory to eliminate high-CPU hotspots without modifying a single file in the original addon's directory.

---

## Project Structure

```
Anki_Terminator_Companion/ (Repo Root)
├── DEVELOPMENT.md            # Advanced developer guide (This file)
├── README.md                 # Main overview and user documentation
├── bump.py                   # SemVer version bump utility
├── make_ankiaddon.py         # Packaging script → produces the .ankiaddon release file
└── addon/ (Addon Source)
    ├── __init__.py           # Entry point: performs in-memory monkey patching of 1468920185
    ├── manifest.json         # Core add-on metadata and configuration requirements
    ├── config.json           # Default configuration settings
    ├── config_ui.py          # Configuration UI orchestrator
    ├── config_ui_general_tab.py # General settings UI tab
    ├── config_ui_logs_tab.py # Live performance logs UI tab
    ├── tab_support.py        # Supporter QR and links UI tab
    ├── logger.py             # Thread-safe asynchronous logging worker
    ├── VERSION               # Tracking file for the current SemVer version
    ├── companion.log         # Real-time event log
    └── patch_1468920185_anki_terminator/
        ├── __init__.py       # Target patch orchestrator
        ├── ad_blocker_patch.py # O(1) Suffix set lookup patches
        ├── css_patch.py      # CSS optimization injection patch
        └── lifecycle_patch.py # Smart UI-freezing, hover-state, & stream monitoring
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

### 1. Local Setup & Testing

To test this add-on locally:
1. Ensure the original add-on (**Anki Terminator V2 - ChatGPT DeepSeek Sidebar for Reviewer**, ID `1468920185`) is installed in your Anki profile.
2. Link or copy the `addon` directory into your Anki profile directory's `addons21` folder under the name `Anki_Terminator_Companion`.

**Symlink Command (Linux):**
```shell
ln -s "$(pwd)/addon" ~/.local/share/Anki2/addons21/Anki_Terminator_Companion
```

3. Restart Anki to automatically apply the memory patches. You will see confirmation logs in the terminal/stdout or in the companion log file:
```
[Terminator Companion] Successfully patched AdBlocker interceptRequest for O(1) domain lookups!
[Terminator Companion] Successfully patched CustomWebEnginePage.inject_javascript for Gemini optimization!
```
4. Open the configuration dialog under **Tools > Add-ons > Anki Terminator Companion > Config** to verify tab controls, settings, and logs.

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
