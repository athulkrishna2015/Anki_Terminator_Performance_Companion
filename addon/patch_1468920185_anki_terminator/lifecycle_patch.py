import importlib
from aqt import mw
from aqt.qt import *
from ..logger import companion_logger

def patch(dock_web_view_mod):
    companion_logger.log("[Lifecycle Patch] Initiating Flicker-Free QStackedWidget and Response Monitor hooks...")

    from html.parser import HTMLParser
    import html

    class HTMLToCleanTextParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.result = []
            self.ignore_tags = {"style", "script"}
            self.current_ignore = False
            self.ignore_stack = []

        def handle_starttag(self, tag, attrs):
            if tag in self.ignore_tags:
                self.ignore_stack.append(tag)
                self.current_ignore = True
                return
            if tag in {"br", "hr"}:
                self.result.append("\n")
            elif tag in {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr"}:
                if self.result and self.result[-1] != "\n":
                    self.result.append("\n")

        def handle_endtag(self, tag):
            if self.ignore_stack and tag == self.ignore_stack[-1]:
                self.ignore_stack.pop()
                self.current_ignore = bool(self.ignore_stack)
                return
            if tag in {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr"}:
                if self.result and self.result[-1] != "\n":
                    self.result.append("\n")

        def handle_data(self, data):
            if not self.current_ignore:
                self.result.append(data)

    def clean_html_for_ai(html_text: str) -> str:
        if not html_text:
            return ""
        parser = HTMLToCleanTextParser()
        try:
            parser.feed(html_text)
            txt = "".join(parser.result)
        except Exception:
            import re
            txt = re.sub(r'<[^>]+>', ' ', html_text)
        
        txt = html.unescape(txt)
        lines = []
        for line in txt.splitlines():
            cleaned_line = " ".join(line.split())
            if cleaned_line:
                lines.append(cleaned_line)
        return "\n".join(lines)

    # Hook ResizableWebView __init__ to set up stacked widget layout
    original_init = dock_web_view_mod.ResizableWebView.__init__
    
    def new_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        
        # Track response state variables
        self.is_responding = False
        self.last_text_length = 0
        self.stable_checks = 0
        self.is_hovered = False
        # Create static screenshot label overlaying the webview
        self.snapshot_label = QLabel(self.webview)
        self.snapshot_label.setScaledContents(True)
        self.snapshot_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.snapshot_label.hide()
        
        # Sync snapshot label geometry on resize
        original_webview_resize = self.webview.resizeEvent
        def new_webview_resize(event):
            if hasattr(self, "snapshot_label") and self.snapshot_label:
                self.snapshot_label.setGeometry(self.webview.rect())
            if original_webview_resize:
                original_webview_resize(event)
            else:
                super(self.webview.__class__, self.webview).resizeEvent(event)
        self.webview.resizeEvent = new_webview_resize
            
        # Hook the initial page load to freeze it after 5 seconds
        def on_initial_load(success):
            companion_logger.log(f"[Lifecycle Patch] CustomWebEnginePage.loadFinished triggered! Success state: {success}")
            if success:
                companion_logger.log("[Lifecycle Patch] Initial load finished. Scheduling freeze in 5 seconds...")
                QTimer.singleShot(5000, lambda: freeze_sidebar(self))
                
        if hasattr(self, "webpage") and self.webpage:
            self.webpage.loadFinished.connect(on_initial_load)
            self.webpage._is_terminator_sidebar = True
            companion_logger.log("[Lifecycle Patch] Connected loadFinished signal for initial load freeze.")

    dock_web_view_mod.ResizableWebView.__init__ = new_init

    # Helper functions to freeze and thaw using QStackedWidget
    def freeze_sidebar(sidebar):
        try:
            cfg = mw.addonManager.getConfig("Anki_Terminator_Companion") or {}
            if not cfg.get("enable_lifecycle_freezing", True):
                return
            
            # Do nothing if already frozen
            if sidebar.snapshot_label.isVisible():
                return
                
            # REFUSE TO FREEZE if sidebar is still loading
            if getattr(sidebar, "loading", False) or not sidebar.webview.isVisible():
                companion_logger.log("[Lifecycle Patch] Freeze deferred: Sidebar is still loading...")
                return

            # REFUSE TO FREEZE if Gemini is actively generating a response!
            if sidebar.is_responding:
                companion_logger.log("[Lifecycle Patch] Freeze deferred: Gemini is currently generating a response...")
                return
                
            # REFUSE TO FREEZE if user is hovering over the sidebar
            if getattr(sidebar, "is_hovered", False):
                companion_logger.log("[Lifecycle Patch] Freeze deferred: User is actively hovering over the sidebar...")
                return
                
            # Capture snapshot and freeze after a tiny delay (100ms) to allow GPU/paints to complete
            def capture_and_freeze():
                try:
                    # Double-check states after the delay
                    if getattr(sidebar, "is_hovered", False) or sidebar.is_responding or not sidebar.webview.isVisible():
                        companion_logger.log("[Lifecycle Patch] Freeze cancelled: State changed during delay.")
                        return
                        
                    companion_logger.log("[Lifecycle Patch] Freezing sidebar -> Capturing static screenshot...")
                    
                    # 1. Grab snapshot of the active webview
                    pixmap = sidebar.webview.grab()
                    
                    if pixmap.isNull():
                        companion_logger.log("[Lifecycle Patch] Warning: Captured pixmap is null. Aborting freeze to prevent black screen.")
                        return
                        
                    sidebar.snapshot_label.setPixmap(pixmap)
                    sidebar.snapshot_label.setGeometry(sidebar.webview.rect())
                    
                    # 2. Show overlay
                    sidebar.snapshot_label.show()
                    sidebar.snapshot_label.raise_()
                    
                    # 3. Request background thread freeze
                    if hasattr(sidebar, "webpage") and sidebar.webpage:
                        try:
                            sidebar.webpage.setLifecycleState(dock_web_view_mod.QWebEnginePage.LifecycleState.Frozen)
                        except Exception:
                            pass
                    if hasattr(sidebar, "stop_timer") and sidebar.stop_timer:
                        try:
                            sidebar.stop_timer.stop()
                        except Exception:
                            pass
                    companion_logger.log("[Lifecycle Patch] Overlay visible. WebEngine frozen. CPU dropped to 0%!")
                except Exception as ex:
                    companion_logger.log(f"[Lifecycle Patch] Delayed capture freeze failed: {ex}")

            QTimer.singleShot(100, capture_and_freeze)
        except Exception as e:
            companion_logger.log(f"[Lifecycle Patch] Failed to schedule freeze: {e}")

    def thaw_sidebar(sidebar):
        try:
            # Do nothing if already active
            if not sidebar.snapshot_label.isVisible():
                return
                
            companion_logger.log("[Lifecycle Patch] Thawing sidebar -> Warming up active WebEngine...")
            
            # 1. First, ensure WebEngine page is active and thawed
            if hasattr(sidebar, "webpage") and sidebar.webpage:
                try:
                    sidebar.webpage.setLifecycleState(dock_web_view_mod.QWebEnginePage.LifecycleState.Active)
                except Exception:
                    pass
            
            # 2. Wait 80ms for the WebEngine to render its frame before hiding the overlay, eliminating transition flicker!
            def complete_thaw():
                try:
                    # Cancel the swap if the user has already hovered out
                    if not getattr(sidebar, "is_hovered", False) and not sidebar.is_responding:
                        companion_logger.log("[Lifecycle Patch] Thaw swap cancelled: User already left.")
                        return
                    sidebar.snapshot_label.hide()
                    companion_logger.log("[Lifecycle Patch] WebEngine visible and fully active!")
                except Exception as ex:
                    companion_logger.log(f"[Lifecycle Patch] Complete thaw failed: {ex}")

            QTimer.singleShot(80, complete_thaw)
        except Exception as e:
            companion_logger.log(f"[Lifecycle Patch] Failed to thaw sidebar: {e}")

    # Hook ResizableWebView hover events
    original_enterEvent = dock_web_view_mod.ResizableWebView.enterEvent
    original_leaveEvent = dock_web_view_mod.ResizableWebView.leaveEvent

    def new_enterEvent(self, event):
        self.is_hovered = True
        thaw_sidebar(self)
        if original_enterEvent:
            original_enterEvent(self, event)
        else:
            super(dock_web_view_mod.ResizableWebView, self).enterEvent(event)

    def new_leaveEvent(self, event):
        self.is_hovered = False
        freeze_sidebar(self)
        if original_leaveEvent:
            original_leaveEvent(self, event)
        else:
            super(dock_web_view_mod.ResizableWebView, self).leaveEvent(event)

    dock_web_view_mod.ResizableWebView.enterEvent = new_enterEvent
    dock_web_view_mod.ResizableWebView.leaveEvent = new_leaveEvent

    # Response progress monitor to auto-detect when Gemini finishes responding
    def start_response_monitoring(sidebar):
        sidebar.is_responding = True
        sidebar.last_text_length = 0
        sidebar.stable_checks = 0
        companion_logger.log("[Lifecycle Patch] Gemini query detected. Initiating response monitoring loop...")
        
        # Periodic checker
        def check_response_progress():
            if not sidebar.is_responding:
                return
                
            # JavaScript callback to inspect inner text length
            def on_length_retrieved(length):
                try:
                    if not sidebar.is_responding:
                        return
                    
                    val = int(length) if length is not None else 0
                    companion_logger.log(f"[Lifecycle Patch] Checking response progress -> text length: {val} (previous: {sidebar.last_text_length})")
                    
                    if val > 0 and val == sidebar.last_text_length:
                        sidebar.stable_checks += 1
                    else:
                        sidebar.stable_checks = 0
                        sidebar.last_text_length = val
                        
                    # If text length stays stable for 3 consecutive checks (6 seconds), response is complete!
                    if sidebar.stable_checks >= 3:
                        companion_logger.log("[Lifecycle Patch] Gemini has finished responding! De-activating and freezing...")
                        sidebar.is_responding = False
                        freeze_sidebar(sidebar)
                    else:
                        # Schedule next check in 2 seconds
                        QTimer.singleShot(2000, check_response_progress)
                except Exception as ex:
                    companion_logger.log(f"[Lifecycle Patch] Progress check error: {ex}")
                    sidebar.is_responding = False
                    freeze_sidebar(sidebar)

            try:
                sidebar.webview.page().runJavaScript("document.body ? document.body.innerText.length : 0;", on_length_retrieved)
            except Exception as ex:
                companion_logger.log(f"[Lifecycle Patch] Failed to run progress script: {ex}")
                sidebar.is_responding = False
                freeze_sidebar(sidebar)
                
        # Start checking 4 seconds in (allowing Gemini to receive and start typing)
        QTimer.singleShot(4000, check_response_progress)

    # Helper to find sidebar robustly from QWebEnginePage
    def find_sidebar_from_page(page):
        try:
            # 1. Try view()
            if hasattr(page, "view") and callable(page.view):
                v = page.view()
                if v and hasattr(v, "parent_window") and v.parent_window:
                    return v.parent_window
            # 2. Try parent()
            if hasattr(page, "parent") and callable(page.parent):
                p = page.parent()
                if p:
                    if hasattr(p, "parent_window") and p.parent_window:
                        return p.parent_window
                    elif hasattr(p, "page") and p.page() == page:
                        if hasattr(p, "parent_window") and p.parent_window:
                            return p.parent_window
            # 3. Fallback: Search mw children
            for widget in mw.findChildren(dock_web_view_mod.ResizableWebView):
                if hasattr(widget, "webview") and widget.webview and widget.webview.page() == page:
                    return widget
        except Exception as e:
            companion_logger.log(f"[Lifecycle Patch] Error in find_sidebar_from_page: {e}")
        return None

    # Hook QWebEnginePage.runJavaScript to thaw page and start monitoring on queries
    original_runJavaScript = dock_web_view_mod.QWebEnginePage.runJavaScript

    def patched_runJavaScript(self, *args, **kwargs):
        if not getattr(self, "_is_terminator_sidebar", False):
            return original_runJavaScript(self, *args, **kwargs)

        js_code = args[0] if args else "None"
        cfg = mw.addonManager.getConfig("Anki_Terminator_Companion") or {}
        image_pasting_enabled = cfg.get("enable_image_pasting", True)

        is_prompt_execution = False
        if isinstance(js_code, str):
            if "replaceValue" in js_code or "execCommand('insertText'" in js_code:
                is_prompt_execution = True

        if isinstance(js_code, str) and "setInterval(findAndClickButton, 2000);" in js_code:
            js_code = js_code.replace(
                "setInterval(findAndClickButton, 2000);",
                "setInterval(function() { if (!document.hidden) { findAndClickButton(); } }, 2000);"
            )
            args = list(args)
            args[0] = js_code
        snippet = js_code[:100].replace('\n', ' ') + ('...' if len(js_code) > 100 else '')
        
        # Quietly skip logger progress JS check statements to avoid loop spamming
        if "document.body.innerText.length" in js_code or "document.body ?" in js_code:
            return original_runJavaScript(self, *args, **kwargs)
            
        companion_logger.log(f"[Lifecycle Patch] Programmatic runJavaScript triggered! Snippet: {snippet}")

        try:
            sidebar = find_sidebar_from_page(self)
            if sidebar:
                # Make sure the sidebar is thawed to render the response
                thaw_sidebar(sidebar)
                
                # Start monitoring text length progress
                start_response_monitoring(sidebar)

                # Check if there is an image to paste into the AI text input area
                if is_prompt_execution and image_pasting_enabled and getattr(sidebar, "_pending_image_to_paste", False):
                    sidebar._pending_image_to_paste = False
                    
                    # Intercept click delay and increase it to 1200ms to allow image upload to finish first
                    import re
                    js_code = re.sub(r'\}\s*,\s*(?:100|200)\s*\)\s*;', '}, 1200);', js_code)
                    args = list(args)
                    args[0] = js_code
                    
                    def trigger_paste():
                        try:
                            sidebar.webview.triggerPageAction(dock_web_view_mod.QWebEnginePage.WebAction.Paste)
                            companion_logger.log("[Lifecycle Patch] Triggered clipboard paste of image to AI.")
                            
                            # Restore user's original clipboard
                            if hasattr(sidebar, "_companion_backup_clipboard") and sidebar._companion_backup_clipboard:
                                from PyQt6.QtWidgets import QApplication
                                from PyQt6.QtGui import QClipboard
                                QApplication.clipboard().setMimeData(sidebar._companion_backup_clipboard, QClipboard.Mode.Clipboard)
                                sidebar._companion_backup_clipboard = None
                                companion_logger.log("[Lifecycle Patch] User clipboard restored successfully.")
                        except Exception as ex:
                            companion_logger.log(f"[Lifecycle Patch] Image paste trigger or clipboard restore failed: {ex}")
                    
                    # Delay by 200ms to allow textarea focusing to finish first
                    QTimer.singleShot(200, trigger_paste)
            else:
                companion_logger.log("[Lifecycle Patch] Warning: Could not resolve parent sidebar for runJavaScript.")
        except Exception as e:
            companion_logger.log(f"[Lifecycle Patch] Error handling UI freeze on query: {e}")
            
        return original_runJavaScript(self, *args, **kwargs)

    dock_web_view_mod.QWebEnginePage.runJavaScript = patched_runJavaScript

    # Hook ResizableWebView.auto_click_v2 to immediately thaw, start monitoring, and paste clipboard-free
    if hasattr(dock_web_view_mod.ResizableWebView, "auto_click_v2"):
        def new_auto_click_v2(self, stop_button_class, class_name, prompt_text, button_class):
            companion_logger.log("[Lifecycle Patch] auto_click_v2 triggered! Thawing sidebar and initiating response monitoring (Clipboard-Free)...")
            self.is_responding = True
            thaw_sidebar(self)
            start_response_monitoring(self)

            import json
            js_prompt = json.dumps(prompt_text)
            
            js_code = f"""
            (function() {{
                // 1. Click stop button if exists
                var stop_button_class = {json.dumps(stop_button_class)};
                if (stop_button_class && stop_button_class !== 'None') {{
                    var stop_button = document.querySelector(stop_button_class);
                    if (stop_button && !stop_button.disabled && stop_button.getAttribute('aria-disabled') !== 'true') {{
                        stop_button.click();
                    }}
                }}

                // 2. Focus and select input element
                var selector = {json.dumps(class_name)};
                const nodeList = document.querySelectorAll(selector);
                const allElements = Array.from(nodeList);
                let element = null;
                let maxArea = -1;

                allElements.forEach(eachElement => {{
                    const width = eachElement.offsetWidth || 0;
                    const height = eachElement.offsetHeight || 0;
                    const area = width * height;
                    if (area > maxArea) {{
                        maxArea = area;
                        element = eachElement;
                    }}
                }});

                if (element) {{
                    const eventOptions = {{ bubbles: true, cancelable: true, view: window }};
                    element.dispatchEvent(new MouseEvent('mousedown', eventOptions));
                    element.focus();
                    element.dispatchEvent(new MouseEvent('mouseup', eventOptions));
                    element.click();

                    // 3. Write text using execCommand (safe & clipboard-free)
                    try {{
                        document.execCommand('selectAll', false, null);
                        document.execCommand('insertText', false, {js_prompt});
                    }} catch(e) {{
                        // Fallback for elements that don't support execCommand
                        element.value = {js_prompt};
                        element.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    }}

                    // 4. Click submit button after a tiny delay to allow React state to sync
                    var button_class = {json.dumps(button_class)};
                    if (button_class && button_class !== 'None') {{
                        setTimeout(function() {{
                            var buttons = document.querySelectorAll(button_class);
                            var targetButton = null;
                            for (var i = 0; i < buttons.length; i++) {{
                                var button = buttons[i];
                                var style = window.getComputedStyle(button);
                                var isVisible = style.display !== 'none' && button.offsetParent !== null && style.pointerEvents !== 'none';
                                if (isVisible) {{
                                    targetButton = button;
                                    break;
                                }}
                            }}
                            if (targetButton && !targetButton.disabled && targetButton.getAttribute('aria-disabled') !== 'true') {{
                                targetButton.click();
                            }}
                        }}, 100);
                    }}
                }}
            }})();
            """
            self.webview.page().runJavaScript(js_code, self.js_callback_v2_click)

        dock_web_view_mod.ResizableWebView.auto_click_v2 = new_auto_click_v2
        companion_logger.log("[Lifecycle Patch] Successfully hooked ResizableWebView.auto_click_v2 with clipboard-free injection.")

    # Hook ResizableWebView handle_audio_state to suppress active timers when hidden or frozen
    if hasattr(dock_web_view_mod.ResizableWebView, "handle_audio_state"):
        original_handle_audio_state = dock_web_view_mod.ResizableWebView.handle_audio_state

        def patched_handle_audio_state(self, audible):
            # If the webview itself is not visible, do not start audio timers or execute recorders
            if not self.webview.isVisible():
                if self.stop_timer and self.stop_timer.isActive():
                    try:
                        self.stop_timer.stop()
                    except Exception:
                        pass
                return

            # If the sidebar is currently frozen (snapshot overlay is visible), also suppress
            if hasattr(self, "snapshot_label") and self.snapshot_label and self.snapshot_label.isVisible():
                if self.stop_timer and self.stop_timer.isActive():
                    try:
                        self.stop_timer.stop()
                    except Exception:
                        pass
                return

            return original_handle_audio_state(self, audible)

        dock_web_view_mod.ResizableWebView.handle_audio_state = patched_handle_audio_state
        companion_logger.log("[Lifecycle Patch] Successfully patched ResizableWebView.handle_audio_state!")

    # Hook ResizableWebView.set_last_text to clean HTML tags from card fields before sending to AI
    if hasattr(dock_web_view_mod.ResizableWebView, "set_last_text"):
        original_set_last_text = dock_web_view_mod.ResizableWebView.set_last_text

        def patched_set_last_text(self, text):
            self._pending_image_to_paste = False
            
            if not isinstance(text, str):
                return original_set_last_text(self, text)

            cfg = mw.addonManager.getConfig("Anki_Terminator_Companion") or {}
            image_pasting_enabled = cfg.get("enable_image_pasting", True)
            html_cleanup_enabled = cfg.get("enable_html_cleanup", True)

            # Extract image source if present in the original HTML text and enabled
            if image_pasting_enabled:
                import re
                img_match = re.search(r'<img\b[^>]*\bsrc=["\']?([^"\'>\s]+)["\']?', text, re.IGNORECASE)
                if img_match:
                    img_src = img_match.group(1)
                    try:
                        from aqt import mw
                        from PyQt6.QtGui import QImage, QClipboard
                        from PyQt6.QtCore import QMimeData
                        from PyQt6.QtWidgets import QApplication
                        import os

                        media_dir = mw.col.media.dir()
                        image_path = os.path.join(media_dir, img_src)
                        if os.path.exists(image_path):
                            image = QImage(image_path)
                            if not image.isNull():
                                # Backup current clipboard
                                cb = QApplication.clipboard()
                                orig_data = cb.mimeData()
                                self._companion_backup_clipboard = QMimeData()
                                for fmt in orig_data.formats():
                                    self._companion_backup_clipboard.setData(fmt, orig_data.data(fmt))

                                # Set image on clipboard
                                cb.setImage(image)
                                self._pending_image_to_paste = True
                                companion_logger.log(f"[Lifecycle Patch] Image '{img_src}' copied to clipboard for AI input.")
                    except Exception as e:
                        companion_logger.log(f"[Lifecycle Patch] Failed to handle image for clipboard: {e}")

            if html_cleanup_enabled:
                cleaned_text = clean_html_for_ai(text)
            else:
                cleaned_text = text
            return original_set_last_text(self, cleaned_text)

        dock_web_view_mod.ResizableWebView.set_last_text = patched_set_last_text
        companion_logger.log("[Lifecycle Patch] Successfully patched ResizableWebView.set_last_text to clean HTML!")

    # Hook ResizableWebView.get_field_text to support sending multiple fields if configured
    if hasattr(dock_web_view_mod.ResizableWebView, "get_field_text"):
        original_get_field_text = dock_web_view_mod.ResizableWebView.get_field_text

        def patched_get_field_text(self, card=None):
            config = mw.addonManager.getConfig(__name__) or {}
            
            if card is None and mw.state == "review":
                card = mw.reviewer.card
            else:
                return

            self.last_card = card
            note = card.note()
            self.last_card_note = note
            note_type = note.note_type()

            if self.is_excluded_note_type(config, note_type):
                return

            if config.get("send_multiple_fields", False):
                parts = []
                for field_name, field_value in note.items():
                    if clean_html_for_ai(field_value).strip():
                        parts.append(f"<b>{field_name}</b>:<br>{field_value}")
                if parts:
                    text = "<br><br>".join(parts)
                else:
                    text = ""
                self.set_last_text(text)
            else:
                original_get_field_text(self, card)

        dock_web_view_mod.ResizableWebView.get_field_text = patched_get_field_text
        companion_logger.log("[Lifecycle Patch] Successfully patched ResizableWebView.get_field_text for multiple fields support!")

    # Hook the configuration UI SetPopupConfig
    try:
        config_mod = importlib.import_module("1468920185.config.PopUpAnkiConfig")
        
        original_config_init = config_mod.SetPopupConfig.__init__
        def new_config_init(self, *args, **kwargs):
            original_config_init(self, *args, **kwargs)
            try:
                # Find QTabWidget child
                tab_widget = self.findChild(QTabWidget)
                if tab_widget:
                    for i in range(tab_widget.count()):
                        if tab_widget.tabText(i) == self.TAB_SEVEN:
                            fields_tab_widget = tab_widget.widget(i)
                            layout = fields_tab_widget.layout()
                            if layout:
                                cfg = mw.addonManager.getConfig("1468920185") or {}
                                self.send_multiple_fields_checkbox = QCheckBox("Send Multiple Fields")
                                self.send_multiple_fields_checkbox.setChecked(cfg.get("send_multiple_fields", False))
                                # Insert before the last stretch spacing
                                layout.insertWidget(layout.count() - 1, self.send_multiple_fields_checkbox)
                                companion_logger.log("[Config Patch] Injected 'Send Multiple Fields' checkbox into Fields tab.")
                                break
            except Exception as ex:
                companion_logger.log(f"[Config Patch] Failed to inject checkbox: {ex}")

        config_mod.SetPopupConfig.__init__ = new_config_init

        original_save_config = config_mod.SetPopupConfig.save_config_fontfamiles
        def new_save_config(self):
            original_save_config(self)
            try:
                if hasattr(self, "send_multiple_fields_checkbox"):
                    val = self.send_multiple_fields_checkbox.isChecked()
                    cfg = mw.addonManager.getConfig("1468920185") or {}
                    cfg["send_multiple_fields"] = val
                    mw.addonManager.writeConfig("1468920185", cfg)
                    companion_logger.log(f"[Config Patch] Saved send_multiple_fields = {val} to 1468920185 config.")
            except Exception as ex:
                companion_logger.log(f"[Config Patch] Failed to save send_multiple_fields: {ex}")

        config_mod.SetPopupConfig.save_config_fontfamiles = new_save_config
        companion_logger.log("[Config Patch] Successfully patched SetPopupConfig class!")
    except Exception as e:
        companion_logger.log(f"[Config Patch] Failed to patch SetPopupConfig: {e}")

    companion_logger.log("[Lifecycle Patch] Successfully hooked ResizableWebView and runJavaScript for Smart UI-Freezing.")

