# Anki Terminator Companion

An elegant, dynamic performance-optimization add-on for Anki. 

This companion addon is designed to run seamlessly alongside the original **Anki Terminator V2 - ChatGPT DeepSeek Sidebar for Reviewer** (`1468920185`). By dynamically patching memory during Anki startup, it eliminates high-CPU bottlenecks completely **without modifying a single line of code in the original addon's directory**.

---

## Key Features & Optimization Highlights

### ⚡ 1. Smart UI-Freezing with Active Hover Tracking (0% Idle CPU)
* **The Problem**: Chromium (`QtWebEngineProcess`) refuses to freeze a webpage if it's visible on the viewport, meaning Gemini/ChatGPT continue to consume high CPU even when you aren't looking at them.
* **The Solution**: 
  - When the sidebar loses focus or you are studying cards, the companion captures a pixel-perfect static screenshot of the webview (`webview.grab()`) and displays it instantly in a `QLabel` via a `QStackedWidget` layout swap.
  - While hidden behind the static view, Chromium completely suspends all paints and JavaScript loops, instantly dropping CPU usage to **0%**.
  - **Flicker-Free Transitions**: By utilizing a `QStackedWidget`, page swaps are completely imperceptible and flicker-free.
  - **Active Hover & Stream Protection**: The sidebar stays 100% active and responsive under your cursor. In addition, when Gemini is actively generating a response, freezing is automatically deferred until the response finishes streaming, allowing you to watch the answer populate in real-time.

### 🚫 2. Optimized O(1) Suffix Ad-Blocker Lookup
* **The Problem**: If the C-based Rust ad-blocker engine is unavailable, the original addon falls back to scanning a list of **~46,000 domains** using slow, linear substring matching (`domain in url`) for *every single network request*. This blocks the main Qt UI thread.
* **The Solution**: The companion parses and splits those rules into pure domain lookups, executing a set-based suffix-matching algorithm in `O(1)` time. This eliminates frame drops during page loads.

### 🎨 3. CSS Animation & Transitions Disabler
* **The Problem**: High-CPU draw on Gemini's website due to continuous background shimmer animations, blur filters, and glow gradients.
* **The Solution**: Dynamically injects highly optimized CSS when the page loads to disable background animations, transition effects, and intensive CSS blur/backdrop-filters globally.

### 📝 4. Rich HTML Context Menu Paste Support (Preserves Formatting)
* **The Problem**: Right-clicking in the sidebar to "Add selection to field" originally uses plain-text copy-pasting, stripping out all markdown, links, lists, bold text, italics, and image elements.
* **The Solution**: Dynamically intercepts the context menu triggers to extract selection text as raw HTML using a specialized JavaScript range cloner. This allows you to append formatted answers directly into your Anki fields with all formatting and styling intact.

### 📋 5. Clipboard-Free Text Injection (No Clipboard Pollution)
* **The Problem**: Original prompt inputs relied on system clipboard copy-paste actions with timers. Lag spikes often caused the webview to paste the user's restored original clipboard data instead of the prompt text, polluting their clipboard history.
* **The Solution**: Patches the input insertion mechanism to inject queries directly via Chromium's native `document.execCommand('insertText')` API. It leaves your system clipboard completely untouched and guarantees instant, race-condition-free pasting across all AI platforms.

---

## Project Directory Structure

```
Anki_Terminator_Companion/ (Repo Root)
├── README.md                 # Main overview and optimization documentation (This file)
├── DEVELOPMENT.md            # Advanced developer guide (versioning, packaging, local setups)
├── bump.py                   # SemVer version bump utility
├── make_ankiaddon.py         # Packages the directory into a production .ankiaddon release
└── addon/ (Addon Source)
    ├── __init__.py           # Pre-load orchestrator; dynamically applies memory patches
    ├── manifest.json         # Addon declaration
    ├── config.json           # Optimization features configuration
    ├── config_ui.py          # Modern settings GUI dialog inside Anki
    ├── logger.py             # Thread-safe asynchronous logging worker
    ├── companion.log         # Real-time event log
    └── patch_1468920185_anki_terminator/
        ├── __init__.py       # Target patch orchestrator
        ├── ad_blocker_patch.py # O(1) Suffix set lookup patches
        ├── css_patch.py      # CSS optimization injection patch
        └── lifecycle_patch.py # Smart UI-freezing, hover-state, & stream monitoring
```

---

## How to Install and Test

1. Ensure the original addon (`1468920185`) is installed.
2. Link or place the `Anki_Terminator_Companion` source folder inside your Anki profile directory's `addons21` folder.
3. Start Anki. Open the addon settings panel to access the custom Configuration UI, enabling you to toggle features, adjust freeze-thaw sensitivity, and inspect logs in real time.
