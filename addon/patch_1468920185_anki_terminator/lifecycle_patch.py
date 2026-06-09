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
        
        # If it doesn't look like HTML, just return it sanitized of extra whitespace
        if "<" not in html_text or ">" not in html_text:
            return " ".join(html_text.split())

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
        
        result = "\n".join(lines)
        if not result.strip() and html_text.strip():
            import re
            result = re.sub(r'<[^>]+>', ' ', html_text)
            result = " ".join(result.split())
            
        return result

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

        # Inject Companion Config button next to settings cogwheel
        def inject_companion_button():
            try:
                # Find the settings button (cogwheel) which is a QPushButton in a QToolBar
                buttons = self.findChildren(QPushButton)
                settings_btn = None
                cfg = mw.addonManager.getConfig("Anki_Terminator_Companion") or {}
                for btn in buttons:
                    if "⚙" in btn.text():
                        settings_btn = btn
                    
                    # Also look for the "add text to card" / wiki button to replace it
                    tooltip = btn.toolTip().lower()
                    if cfg.get("enable_add_to_new_card", True) and ("add text to card" in tooltip or "wiki" in tooltip):
                        btn.setToolTip("Add selection to new card")
                        btn.setText(" ➕ ")
                        btn.setCursor(Qt.CursorShape.PointingHandCursor)
                        # Disconnect original signals (opens wiki) and connect to our new logic
                        try:
                            btn.clicked.disconnect()
                        except:
                            pass
                        from .context_menu_patch import on_add_to_new_card
                        btn.clicked.connect(lambda _, b=btn: on_add_to_new_card(self.webview))
                        companion_logger.log(f"[Lifecycle Patch] Replaced original button '{tooltip}' with Add to New Card action.")
                
                if settings_btn:
                    parent_toolbar = settings_btn.parentWidget()
                    if isinstance(parent_toolbar, QToolBar):
                        from ..config_ui import show_config_dialog
                        
                        self.companion_config_btn = QPushButton(" C ")
                        self.companion_config_btn.setToolTip("Terminator Companion Config")
                        self.companion_config_btn.setFixedSize(settings_btn.size())
                        self.companion_config_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                        # Styling to match the original buttons but with a blue tint
                        self.companion_config_btn.setStyleSheet("QPushButton { margin: 1px; padding: 1px; font-weight: bold; color: #2196F3; }")
                        
                        # Add to toolbar
                        parent_toolbar.insertWidget(parent_toolbar.actions()[parent_toolbar.actions().index(settings_btn.graphicsProxyWidget().action() if settings_btn.graphicsProxyWidget() else next(a for a in parent_toolbar.actions() if parent_toolbar.widgetForAction(a) == settings_btn))], self.companion_config_btn)
                        self.companion_config_btn.clicked.connect(lambda: show_config_dialog(self))
                        companion_logger.log("[Lifecycle Patch] Injected Companion Config button into header.")
                    else:
                        # Fallback simple injection if layout structure is different
                        layout = parent_toolbar.layout() if parent_toolbar else None
                        if layout:
                            from ..config_ui import show_config_dialog
                            self.companion_config_btn = QPushButton(" C ")
                            self.companion_config_btn.setToolTip("Terminator Companion Config")
                            self.companion_config_btn.setFixedSize(settings_btn.size())
                            self.companion_config_btn.setStyleSheet("QPushButton { margin: 1px; padding: 1px; font-weight: bold; color: #2196F3; }")
                            idx = layout.indexOf(settings_btn)
                            layout.insertWidget(idx, self.companion_config_btn)
                            self.companion_config_btn.clicked.connect(lambda: show_config_dialog(self))
                            companion_logger.log("[Lifecycle Patch] Injected Companion Config button via layout fallback.")
            except Exception as ex:
                companion_logger.log(f"[Lifecycle Patch] Failed to inject header button: {ex}")

        # Delay injection slightly to ensure original UI is constructed
        QTimer.singleShot(1000, inject_companion_button)

    dock_web_view_mod.ResizableWebView.__init__ = new_init

    # Helper functions to freeze and thaw using QStackedWidget
    def freeze_sidebar(sidebar):
        try:
            cfg = mw.addonManager.getConfig("Anki_Terminator_Companion") or {}
            if not cfg.get("enable_lifecycle_freezing", True):
                return
            
            if sidebar.snapshot_label.isVisible():
                return
                
            if getattr(sidebar, "loading", False) or not sidebar.webview.isVisible():
                return

            if sidebar.is_responding:
                return
                
            if getattr(sidebar, "is_hovered", False):
                return
                
            def capture_and_freeze():
                try:
                    if getattr(sidebar, "is_hovered", False) or sidebar.is_responding or not sidebar.webview.isVisible():
                        return
                        
                    pixmap = sidebar.webview.grab()
                    if pixmap.isNull():
                        return
                        
                    sidebar.snapshot_label.setPixmap(pixmap)
                    sidebar.snapshot_label.setGeometry(sidebar.webview.rect())
                    sidebar.snapshot_label.show()
                    sidebar.snapshot_label.raise_()
                    
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
                except Exception:
                    pass

            QTimer.singleShot(100, capture_and_freeze)
        except Exception:
            pass

    def thaw_sidebar(sidebar):
        try:
            if not sidebar.snapshot_label.isVisible():
                return
                
            if hasattr(sidebar, "webpage") and sidebar.webpage:
                try:
                    sidebar.webpage.setLifecycleState(dock_web_view_mod.QWebEnginePage.LifecycleState.Active)
                except Exception:
                    pass
            
            def complete_thaw():
                try:
                    if not getattr(sidebar, "is_hovered", False) and not sidebar.is_responding:
                        return
                    sidebar.snapshot_label.hide()
                except Exception:
                    pass

            QTimer.singleShot(80, complete_thaw)
        except Exception:
            pass

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
        
        def check_response_progress():
            if not sidebar.is_responding:
                return
                
            def on_length_retrieved(length):
                try:
                    if not sidebar.is_responding:
                        return
                    val = int(length) if length is not None else 0
                    if val > 0 and val == sidebar.last_text_length:
                        sidebar.stable_checks += 1
                    else:
                        sidebar.stable_checks = 0
                        sidebar.last_text_length = val
                    if sidebar.stable_checks >= 3:
                        sidebar.is_responding = False
                        freeze_sidebar(sidebar)
                    else:
                        QTimer.singleShot(2000, check_response_progress)
                except Exception:
                    sidebar.is_responding = False
                    freeze_sidebar(sidebar)

            try:
                sidebar.webview.page().runJavaScript("document.body ? document.body.innerText.length : 0;", on_length_retrieved)
            except Exception:
                sidebar.is_responding = False
                freeze_sidebar(sidebar)
                
        QTimer.singleShot(4000, check_response_progress)

    def find_sidebar_from_page(page):
        try:
            if hasattr(page, "view") and callable(page.view):
                v = page.view()
                if v and hasattr(v, "parent_window") and v.parent_window:
                    return v.parent_window
            if hasattr(page, "parent") and callable(page.parent):
                p = page.parent()
                if p:
                    if hasattr(p, "parent_window") and p.parent_window:
                        return p.parent_window
                    elif hasattr(p, "page") and p.page() == page:
                        if hasattr(p, "parent_window") and p.parent_window:
                            return p.parent_window
            for widget in mw.findChildren(dock_web_view_mod.ResizableWebView):
                if hasattr(widget, "webview") and widget.webview and widget.webview.page() == page:
                    return widget
        except Exception:
            pass
        return None

    # Hook QWebEnginePage.runJavaScript
    original_runJavaScript = dock_web_view_mod.QWebEnginePage.runJavaScript

    def patched_runJavaScript(self, *args, **kwargs):
        if not getattr(self, "_is_terminator_sidebar", False):
            return original_runJavaScript(self, *args, **kwargs)

        js_code = args[0] if args else ""
        if "document.body.innerText.length" in js_code:
            return original_runJavaScript(self, *args, **kwargs)

        try:
            sidebar = find_sidebar_from_page(self)
            if sidebar:
                thaw_sidebar(sidebar)
                # Only monitor if it looks like a submit action
                if isinstance(js_code, str) and ("replaceValue" in js_code or "execCommand" in js_code):
                    start_response_monitoring(sidebar)
        except Exception:
            pass
            
        return original_runJavaScript(self, *args, **kwargs)

    dock_web_view_mod.QWebEnginePage.runJavaScript = patched_runJavaScript

    # Hook ResizableWebView.auto_click_v2
    if hasattr(dock_web_view_mod.ResizableWebView, "auto_click_v2"):
        original_auto_click_v2 = dock_web_view_mod.ResizableWebView.auto_click_v2
        
        def new_auto_click_v2(self, *args, **kwargs):
            self.is_responding = True
            # Check if frozen BEFORE thawing
            was_frozen = hasattr(self, "snapshot_label") and self.snapshot_label.isVisible()
            
            thaw_sidebar(self)
            start_response_monitoring(self)
            
            if was_frozen:
                # If we were frozen, we must delay the JS execution to give Chromium
                # enough time to fully resume the lifecycle state from 'Frozen' to 'Active'.
                # Otherwise, the runJavaScript call might be silently ignored.
                QTimer.singleShot(200, lambda: original_auto_click_v2(self, *args, **kwargs))
            else:
                return original_auto_click_v2(self, *args, **kwargs)
            
        dock_web_view_mod.ResizableWebView.auto_click_v2 = new_auto_click_v2

    # Hook ResizableWebView handle_audio_state
    if hasattr(dock_web_view_mod.ResizableWebView, "handle_audio_state"):
        original_handle_audio_state = dock_web_view_mod.ResizableWebView.handle_audio_state
        def patched_handle_audio_state(self, audible):
            if not self.webview.isVisible() or (hasattr(self, "snapshot_label") and self.snapshot_label.isVisible()):
                if self.stop_timer and self.stop_timer.isActive():
                    try: self.stop_timer.stop()
                    except: pass
                return
            return original_handle_audio_state(self, audible)
        dock_web_view_mod.ResizableWebView.handle_audio_state = patched_handle_audio_state

    # Hook ResizableWebView.set_last_text
    if hasattr(dock_web_view_mod.ResizableWebView, "set_last_text"):
        original_set_last_text = dock_web_view_mod.ResizableWebView.set_last_text
        def patched_set_last_text(self, text):
            cfg = mw.addonManager.getConfig("Anki_Terminator_Companion") or {}
            if cfg.get("enable_html_cleanup", True) and isinstance(text, str):
                text = clean_html_for_ai(text)
            return original_set_last_text(self, text)
        dock_web_view_mod.ResizableWebView.set_last_text = patched_set_last_text

    # Hook ResizableWebView.get_field_text
    if hasattr(dock_web_view_mod.ResizableWebView, "get_field_text"):
        original_get_field_text = dock_web_view_mod.ResizableWebView.get_field_text

        def patched_get_field_text(self, card=None):
            config = mw.addonManager.getConfig("Anki_Terminator_Companion") or {}
            original_config = mw.addonManager.getConfig("1468920185") or {}

            if card is None and mw.state == "review":
                card = mw.reviewer.card

            if card and config.get("send_multiple_fields", False):
                self.last_card = card
                note = card.note()
                self.last_card_note = note
                note_type = note.note_type()

                if hasattr(self, "is_excluded_note_type") and self.is_excluded_note_type(original_config, note_type):
                    return

                parts = []
                for field_name, field_value in note.items():
                    if clean_html_for_ai(field_value).strip():
                        parts.append(f"<b>{field_name}</b>:<br>{field_value}")
                text = "<br><br>".join(parts) if parts else ""
                self.set_last_text(text)
                return

            return original_get_field_text(self, card)

        dock_web_view_mod.ResizableWebView.get_field_text = patched_get_field_text

    # Hook the configuration UI SetPopupConfig
    try:
        config_mod = importlib.import_module("1468920185.config.PopUpAnkiConfig")
        original_config_init = config_mod.SetPopupConfig.__init__
        def new_config_init(self, *args, **kwargs):
            original_config_init(self, *args, **kwargs)
            try:
                tab_widget = self.findChild(QTabWidget)
                if tab_widget:
                    for i in range(tab_widget.count()):
                        if tab_widget.tabText(i) == self.TAB_SEVEN:
                            fields_tab_widget = tab_widget.widget(i)
                            layout = fields_tab_widget.layout()
                            if layout:
                                cfg = mw.addonManager.getConfig("1468920185") or {}
                                comp_cfg = mw.addonManager.getConfig("Anki_Terminator_Companion") or {}
                                
                                self.send_multiple_fields_checkbox = QCheckBox("Send Multiple Fields")
                                self.send_multiple_fields_checkbox.setChecked(cfg.get("send_multiple_fields", False))
                                layout.insertWidget(layout.count() - 1, self.send_multiple_fields_checkbox)

                                self.add_to_new_card_checkbox = QCheckBox("Enable 'Add to New Card'")
                                self.add_to_new_card_checkbox.setChecked(comp_cfg.get("enable_add_to_new_card", True))
                                layout.insertWidget(layout.count() - 1, self.add_to_new_card_checkbox)
                                break
            except: pass
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
                
                if hasattr(self, "add_to_new_card_checkbox"):
                    val = self.add_to_new_card_checkbox.isChecked()
                    comp_cfg = mw.addonManager.getConfig("Anki_Terminator_Companion") or {}
                    comp_cfg["enable_add_to_new_card"] = val
                    mw.addonManager.writeConfig("Anki_Terminator_Companion", comp_cfg)
            except: pass
        config_mod.SetPopupConfig.save_config_fontfamiles = new_save_config
    except: pass
