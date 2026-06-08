# Anki Terminator Companion

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/D1D01W6NQT)

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

### 🧹 6. HTML Stripping for AI Prompts (LaTeX Clean)
* **The Problem**: Card fields sent to the AI often contain extensive HTML layout tag boilerplate (`<br>`, `<div>`, `<span style="...">`), which wastes token limits and confuses LLMs.
* **The Solution**: Automatically parses and strips all raw HTML tags from prompts, preserving clean text and raw LaTeX/MathJax expressions (`\(...\)` and `\[...\]`) for optimal AI processing.

### ⚡ 7. Instant Config Access (Header Button)
* **The Problem**: To change companion settings, users had to navigate through the Add-on Manager, which is slow during active study sessions.
* **The Solution**: Injects a custom **"C" button** directly into the sidebar header toolbar (next to the settings cogwheel). Clicking it instantly opens the Terminator Companion settings dialog.

### 🗃️ 8. Multiple Fields Support
* **The Problem**: Original sidebar only reads the single designated priority field.
* **The Solution**: Allows concatenating and sending all non-empty card fields to the AI, formatted clearly as `FieldName: FieldValue`. It automatically filters out empty fields and fields containing only boilerplate spaces or tags.

---

## Configuration & Settings

The companion add-on introduces a dedicated settings dialog inside Anki's Add-on Manager (accessible via **Tools > Add-ons > Select Anki Terminator Companion > Config**).

### Tabs Overview:
1. **General Settings**:
   * **Enable Smart CPU Freezing (Lifecycle State)**: Toggles the dynamic freezing/thawing system for Gemini/ChatGPT.
   * **Enable Ad-Blocker O(1) Suffix Match Optimization**: Toggles the fast suffix domain set lookup algorithm.
   * **Inject CSS Gemini Animation Disabler**: Toggles the custom animation disabler styles.
   * **Enable HTML Stripping for AI Prompts**: Toggles stripping of HTML tags from prompts (preserves math).
   * **Enable AI-Hints O(n) Regex Bypass Optimization**: Toggles fast-path rendering when no AI hints are present.
   * **Enable AI-Hints Context Menu Preservation**: Toggles safety check when appending right-click selections.
   * **Send Multiple Fields to AI**: Toggles sending all non-empty fields instead of just the priority field (configurable in both companion config and original Terminator "Fields" tab).
   * **Thaw Duration after Query**: Configures the duration in seconds that Gemini stays Active before freezing back after clicking any prompt buttons.
2. **Performance Logs**:
   * Displays thread-safe, real-time diagnostic and performance events from the companion.
   * Includes handy buttons to **Copy Logs** to clipboard and **Clear Logs**.
3. **Support**:
   * Offers direct links and QR codes to support the creator (UPI, BTC, ETH, and Ko-fi links).
   * Includes a checkbox option: `"I have supported this addon (Hide automatic update welcome)"` to disable the welcome screen popping up after future updates.

---

## Development & Local Installation

Please refer to [DEVELOPMENT.md](DEVELOPMENT.md) for details on project directory structure, local setup, manual testing, versioning, and building release packages.

---

## Changelog

### June 7, 2026 (v1.4.1)
- **Fixed Button Race Condition**:
  - Added a 200ms lifecycle-aware delay when clicking AI prompt buttons while the sidebar is frozen.
  - This ensures Chromium has transitioned from `Frozen` to `Active` state before executing the prompt injection, resolving the issue where buttons occasionally had to be pressed twice.

### June 7, 2026 (v1.4.0)
- **Instant Config Access (Header Button)**:
  - Injected a new **"C" button** in the sidebar header next to the existing settings cogwheel.
  - Provides immediate access to the companion settings dialog during study sessions.
- **Improved Text Detection & Stability**:
  - Refactored `patched_get_field_text` to correctly fall back to the original add-on logic, resolving "empty text window" issues.
  - Refined `is_responding` state management to only trigger on explicit prompt submissions, preventing interference with background JS calls.
- **HTML Cleanup Fallback**:
  - Enhanced the HTML stripper with a robust regex-based fallback to ensure text is always captured even if the primary parser encounters edge cases.
- **Removed Experimental Features**:
  - Reverted experimental image pasting and regex-based `runJavaScript` optimizations to prioritize core stability and text detection accuracy.

### June 7, 2026 (v1.3.3)
- **Idle CPU Optimization & Busy Loop Mitigation**:
  - Implemented visibility-aware checks for the background `findAndClickButton` interval (`setInterval`), suspending it when the sidebar is hidden/inactive.
  - Patched `ResizableWebView.handle_audio_state` and the sidebar freeze routine to stop active audio recording timers (`stop_timer`) when the sidebar is not visible or currently frozen.
  - Optimized the AI-Hints `clean_ai_hints_from_text` routine with a fast `O(n)` substring pre-check, preventing expensive regular expression scans on every field lookup when no hints are present.
- **HTML Stripping for AI Prompts**:
  - Automatically strips raw HTML tags (such as `<br>`, `<hr>`, `<div>`, `<span>`) from card field texts before sending them to the AI, ensuring only clean text and LaTeX/MathJax expressions are transmitted.
- **Automatic Image Clipboard Pasting**:
  - Automatically detects and extracts any referenced card images (`<img>` tags) in the field. Loads and places the image on the system clipboard, focuses the AI input area, and triggers a native WebEngine paste event to upload the image to the chatbot.
  - Automatically backs up and restores the user's original system clipboard immediately after pasting, preserving the clipboard state.
- **Multiple Fields Support**:
  - Added support for concatenating and sending all non-empty card fields to the AI, rather than only the priority field.
  - Fully configurable via the "Fields" tab in both the main Anki Terminator settings dialog and the Terminator Companion config UI (disabled by default).
  - Automatically filters out fields that contain only HTML boilerplate or whitespace to ensure clean transmission.

### June 6, 2026 (v1.3.2)
- **AI-Hints Preservation**:
  - Patched note saving to detect and keep AI-Hints JSON blocks at the absolute end of the field when appending selection text via the right-click menu.

### June 6, 2026 (v1.3.1)
- **AI Chatbot MathJax & HTML Sanitization**:
  - Added support for extracting and reconstructing LaTeX formulas from chatbot-rendered containers (supporting MathJax v2, MathJax v3, KaTeX, and Wikipedia formats) to standard Anki delimiters (`\( ... \)` and `\[ ... \]`).
  - Resolved partial selection bugs by implementing a range-expansion logic that automatically captures the complete formula.
  - Implemented strict HTML tag whitelist and attribute sanitization to strip all Angular scoping attributes, tracking data, and citation/footnote chips, ensuring only clean formatting is sent to Anki.
  - Added context-menu action logs to the performance log viewer.

### June 5, 2026 (v1.3.0)
- **Clipboard-Free Text Injection**: Patched the input insertion mechanism to inject queries directly via Chromium's native `document.execCommand('insertText')` API, completely avoiding system clipboard pollution and resolving clipboard paste race conditions.
- **Support & Customization Settings**: Added Ko-fi support badges and detailed configuration settings descriptions.

### June 5, 2026 (v1.2.0)
- **Rename & Branding**: Renamed add-on from "Anki Terminator Performance Companion" to "Anki Terminator Companion".
- **Rich HTML Context Menu Paste**: Intercepted context menu triggers to extract selection text as raw HTML using a specialized JavaScript range cloner, allowing formatted text insertion into Anki fields.

### June 2, 2026 (v1.1.0)
- **Config UI Improvements**: Refactored settings dialog into a modular tabbed layout and added a new QR Support tab.
- **Supporter Welcome Hook**: Implemented a supporter status check hook on startup.

### June 2, 2026 (v1.0.2)
- **WebView Performance**: Optimized `runJavaScript` targeting, fixed loading layout screen representation, and resolved mouse hover transition flickers.

### June 1, 2026 (v1.0.0)
- **Initial Release**: Released version 1.0.0 featuring core optimizations: smart CPU freezing (0% idle CPU), O(1) suffix ad-blocker lookup, and CSS animation/transition disabler.

