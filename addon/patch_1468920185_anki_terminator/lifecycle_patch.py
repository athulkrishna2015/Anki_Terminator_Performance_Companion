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
        self.snapshot_label = QLabel(self)
        self.snapshot_label.setScaledContents(True)
        self.snapshot_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.snapshot_label.setStyleSheet("background-color: #1a1a1a;") # Match Anki dark theme
        self.snapshot_label.hide()
        
        # Sync snapshot label geometry on resize
        original_webview_resize = self.webview.resizeEvent
        def new_webview_resize(event):
            if hasattr(self, "snapshot_label") and self.snapshot_label:
                self.snapshot_label.setGeometry(self.webview.geometry())
            if hasattr(self, "progress_bar") and self.progress_bar:
                # Progress bar always at absolute top, full width
                self.progress_bar.setGeometry(0, 0, self.width(), 2)
            if original_webview_resize:
                original_webview_resize(event)
            else:
                super(self.webview.__class__, self.webview).resizeEvent(event)
        self.webview.resizeEvent = new_webview_resize

        # Navigation UI Components (Created directly without container)
        self.btn_back = QPushButton(" < ")
        self.btn_forward = QPushButton(" > ")
        self.btn_reload = QPushButton(" R ")
        self.btn_home = QPushButton(" H ")
        
        # Search UI Component container
        self.search_control = QWidget()
        self.search_control.setMaximumHeight(26)
        search_layout = QHBoxLayout(self.search_control)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(2)

        self.address_bar = QLineEdit()
        self.address_bar.setPlaceholderText("URL or Search...")
        self.address_bar.setMinimumWidth(100)
        self.address_bar.setMaximumWidth(250)
        self.address_bar.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.address_bar.setAttribute(Qt.WidgetAttribute.WA_MacShowFocusRect, False)
        # Style to match Anki's dark theme text boxes
        self.address_bar.setStyleSheet("QLineEdit { border: 1px solid #555; border-radius: 4px; padding: 2px 6px; background: #2a2a2a; color: #eee; height: 20px; font-size: 13px; }")

        search_layout.addWidget(self.address_bar)
        
        # Anki's custom layouts often swallow clicks. Force focus on click.
        class FocusFilter(QObject):
            def eventFilter(self, obj, event):
                if event.type() == QEvent.Type.MouseButtonPress:
                    obj.setFocus()
                return super().eventFilter(obj, event)
                
        self._focus_filter = FocusFilter(self.address_bar)
        self.address_bar.installEventFilter(self._focus_filter)
        
        # Helper to capture snapshot for persistent view
        def capture_persistent_snapshot():
            cfg = mw.addonManager.getConfig(__name__.split(".")[0]) or {}
            if not cfg.get("enable_persistent_view", True):
                return
            if hasattr(self, "snapshot_label") and self.snapshot_label:
                try:
                    pixmap = self.webview.grab()
                    if not pixmap.isNull() and pixmap.height() > 10:
                        self.snapshot_label.setPixmap(pixmap)
                        self.snapshot_label.setGeometry(self.webview.geometry())
                        companion_logger.log("[Lifecycle Patch] Pre-captured snapshot for persistent view.")
                except: pass

        def handle_reload():
            capture_persistent_snapshot()
            # Reload page and clear history to prevent back/forward navigation
            self.webview.reload()
            if self.webview.history():
                self.webview.history().clear()
                
        def handle_home():
            capture_persistent_snapshot()
            if hasattr(self, "home_url") and self.home_url:
                self.webview.load(QUrl(self.home_url))
                if self.webview.history():
                    self.webview.history().clear()
                
        self.btn_back.clicked.connect(lambda: (capture_persistent_snapshot(), self.webview.back()))
        self.btn_forward.clicked.connect(lambda: (capture_persistent_snapshot(), self.webview.forward()))
        self.btn_reload.clicked.connect(handle_reload)
        self.btn_home.clicked.connect(handle_home)
        
        def handle_return_pressed():
            if self.address_bar.hasFocus():
                capture_persistent_snapshot()
                # Clear history when a new URL or search is entered manually
                if self.webview.history():
                    self.webview.history().clear()
                navigate_address(self, self.address_bar.text())
                
        self.address_bar.returnPressed.connect(handle_return_pressed)
        
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setFixedHeight(2)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("QProgressBar { border: none; background: transparent !important; } QProgressBar::chunk { background-color: #2196F3; }")
        self.progress_bar.hide()
        
        # Hook loading signals
        self.webview.loadProgress.connect(lambda p: update_loading_progress(self, p))
        self.webview.urlChanged.connect(lambda u: self.address_bar.setText(u.toString()))
        
        def on_load_started():
            companion_logger.log("[Lifecycle Patch] webview.loadStarted triggered.")
            cfg = mw.addonManager.getConfig(__name__.split(".")[0]) or {}
            
            # Immediately try to kill original loading screen before it draws
            hide_original_loading(self)
            
            # Persistent View: If link click (not button), grab now if possible
            if cfg.get("enable_persistent_view", True) and hasattr(self, "snapshot_label"):
                if not self.snapshot_label.isVisible():
                    capture_persistent_snapshot()
                
                if self.snapshot_label.pixmap() and not self.snapshot_label.pixmap().isNull():
                    self.snapshot_label.show()
                    self.snapshot_label.raise_()
                    companion_logger.log("[Lifecycle Patch] Persistent view snapshot shown.")
                else:
                    # If no snapshot, show black screen to prevent white flash
                    self.snapshot_label.show()
                    self.snapshot_label.raise_()
                    companion_logger.log("[Lifecycle Patch] No snapshot available; showing black screen.")

            if cfg.get("enable_progress_bar", True) and hasattr(self, "progress_bar"):
                self.progress_bar.setValue(0)
                self.progress_bar.show()
                self.progress_bar.raise_()
            
            # Keep killing original loading screen periodically during load
            QTimer.singleShot(100, lambda: hide_original_loading(self))
            QTimer.singleShot(500, lambda: hide_original_loading(self))
            
        self.webview.loadStarted.connect(on_load_started)

        # Try to suppress original loading overlay immediately and periodically
        def hide_original_loading(sidebar):
            try:
                # Find ALL widgets that are children of the sidebar
                for child in sidebar.findChildren(QWidget):
                    # NEVER hide our own components or critical UI parts
                    if child in [getattr(sidebar, "progress_bar", None), getattr(sidebar, "snapshot_label", None)]:
                        continue
                    if child in [sidebar.btn_back, sidebar.btn_forward, sidebar.btn_reload, sidebar.btn_home, sidebar.address_bar, sidebar.search_control]:
                        continue
                    if child == sidebar.webview:
                        continue
                    
                    classname = child.metaObject().className().lower()
                    # Protect main UI types unless they are explicitly named 'loading'
                    if any(c in classname for c in ["qtoolbar", "qmenubar", "qlineedit", "qpushbutton", "qscrollbar"]):
                        # Only hide if the name EXPLICITLY contains loading (not just 'bar' or 'wait')
                        oname = child.objectName().lower()
                        if "loading" not in oname:
                            continue
                    
                    oname = child.objectName().lower()
                    text = ""
                    if hasattr(child, "text") and callable(child.text):
                        try: text = child.text().lower()
                        except: pass
                    
                    # Keywords from the screenshot and common loading patterns
                    keywords = ["loading", "spinner", "overlay", "wait", "mask", "shigeyuki", "patron", "created by", "become a"]
                    is_loading = any(k in oname or k in text or k in classname for k in keywords)
                    
                    # Specifically target any other progress bars or large labels with images in webview area
                    if not is_loading:
                        if classname == "qprogressbar":
                            is_loading = True
                        elif isinstance(child, QLabel):
                            if (child.pixmap() and not child.pixmap().isNull()) or child.movie():
                                if child.width() > 50 and child.height() > 50:
                                    if sidebar.webview.geometry().intersects(child.geometry()):
                                        is_loading = True
                    
                    if is_loading:
                        if not hasattr(sidebar, "_logged_loading_hide"):
                            companion_logger.log(f"[Lifecycle Patch] Killing original loading widget: {classname} | {oname} (text: {text})")
                        child.hide()
                        child.setMaximumSize(0, 0)
                        # Patch show() to prevent it coming back
                        if not hasattr(child, "_companion_hidden"):
                            child.show = lambda: None
                            child._companion_hidden = True
                sidebar._logged_loading_hide = True
            except: pass
            
        hide_original_loading(self)
        QTimer.singleShot(2000, lambda: hide_original_loading(self))
            
        # Hook the initial page load to freeze it after 5 seconds
        def on_initial_load(success):
            companion_logger.log(f"[Lifecycle Patch] CustomWebEnginePage.loadFinished triggered! Success state: {success}")
            if hasattr(self, "snapshot_label"):
                # Delay hiding to ensure page is actually painted
                QTimer.singleShot(150, self.snapshot_label.hide)
            if success:
                if not hasattr(self, "home_url") or not self.home_url:
                    self.home_url = self.webview.url().toString()
                    companion_logger.log(f"[Lifecycle Patch] Captured Home URL: {self.home_url}")
                companion_logger.log("[Lifecycle Patch] Initial load finished. Scheduling freeze in 5 seconds...")
                QTimer.singleShot(5000, lambda: freeze_sidebar(self))
                
        if hasattr(self, "webpage") and self.webpage:
            self.webpage.loadFinished.connect(on_initial_load)
            self.webpage._is_terminator_sidebar = True
            companion_logger.log("[Lifecycle Patch] Connected loadFinished signal for initial load freeze.")

        # Inject Browser Controls and Companion Config button
        def inject_companion_button():
            try:
                # Find all buttons to locate settings and mnemonic buttons
                buttons = self.findChildren(QPushButton)
                settings_btn = None
                mnemonic_btn = None
                cfg = mw.addonManager.getConfig(__name__.split(".")[0]) or {}
                
                for btn in buttons:
                    txt = btn.text().lower()
                    tooltip = btn.toolTip().lower()
                    
                    if "⚙" in btn.text() or "settings" in tooltip:
                        settings_btn = btn
                    elif "mnemonic" in txt or "mnemonic" in tooltip:
                        mnemonic_btn = btn
                    
                    # Handle configurable button visibility
                    if "add text to card" in tooltip or "wiki" in tooltip:
                        if not cfg.get("show_wiki_button", True):
                            btn.hide()
                            btn.setEnabled(False)
                            if btn.parentWidget() and btn.parentWidget().layout():
                                btn.parentWidget().layout().removeWidget(btn)
                    
                    if "💖" in txt or "donate" in tooltip or "support" in tooltip:
                        if not cfg.get("show_donate_button", True):
                            btn.hide()
                            btn.setEnabled(False)
                            if btn.parentWidget() and btn.parentWidget().layout():
                                btn.parentWidget().layout().removeWidget(btn)

                # 1. Inject Search Control next to Mnemonic button
                if mnemonic_btn:
                    prompt_toolbar = mnemonic_btn.parentWidget()
                    if isinstance(prompt_toolbar, QToolBar):
                        prompt_toolbar.addWidget(self.search_control)
                        self.search_control.show()
                        companion_logger.log("[Lifecycle Patch] Injected Search control into prompt QToolBar.")
                    else:
                        layout = prompt_toolbar.layout() if prompt_toolbar else None
                        if layout:
                            if hasattr(layout, 'addWidget'):
                                layout.addWidget(self.search_control)
                                self.search_control.show()
                                companion_logger.log("[Lifecycle Patch] Injected Search control into prompt layout.")

                # 2. Inject Nav Controls and Companion Config button next to Settings cogwheel
                if settings_btn:
                    parent_toolbar = settings_btn.parentWidget()
                    if isinstance(parent_toolbar, QToolBar):
                        from ..config_ui import show_config_dialog
                        
                        # Style nav buttons exactly like config button
                        for btn in [self.btn_back, self.btn_forward, self.btn_reload, self.btn_home]:
                            btn.setFixedSize(settings_btn.size())
                            btn.setCursor(Qt.CursorShape.PointingHandCursor)
                            btn.setStyleSheet("QPushButton { margin: 1px; padding: 1px; font-weight: bold; color: #2196F3; }")
                            btn.setToolTip("Browser Navigation")
                        
                        self.companion_config_btn = QPushButton(" C ")
                        self.companion_config_btn.setToolTip("Terminator Companion Config")
                        self.companion_config_btn.setFixedSize(settings_btn.size())
                        self.companion_config_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                        self.companion_config_btn.setStyleSheet("QPushButton { margin: 1px; padding: 1px; font-weight: bold; color: #2196F3; }")
                        
                        # Find action for settings button to insert before it
                        settings_action = None
                        for action in parent_toolbar.actions():
                            if parent_toolbar.widgetForAction(action) == settings_btn:
                                settings_action = action
                                break
                        
                        if settings_action:
                            parent_toolbar.insertWidget(settings_action, self.btn_back)
                            parent_toolbar.insertWidget(settings_action, self.btn_forward)
                            parent_toolbar.insertWidget(settings_action, self.btn_reload)
                            parent_toolbar.insertWidget(settings_action, self.btn_home)
                            parent_toolbar.insertWidget(settings_action, self.companion_config_btn)
                        else:
                            parent_toolbar.addWidget(self.btn_back)
                            parent_toolbar.addWidget(self.btn_forward)
                            parent_toolbar.addWidget(self.btn_reload)
                            parent_toolbar.addWidget(self.btn_home)
                            parent_toolbar.addWidget(self.companion_config_btn)
                            
                        self.companion_config_btn.clicked.connect(lambda: show_config_dialog(mw))
                        companion_logger.log("[Lifecycle Patch] Injected Nav buttons and Config button into QToolBar header.")
                    else:
                        # Fallback simple injection if layout structure is different
                        layout = parent_toolbar.layout() if parent_toolbar else None
                        if layout:
                            from ..config_ui import show_config_dialog
                            
                            for btn in [self.btn_back, self.btn_forward, self.btn_reload, self.btn_home]:
                                btn.setFixedSize(settings_btn.size())
                                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                                btn.setStyleSheet("QPushButton { margin: 1px; padding: 1px; font-weight: bold; color: #2196F3; }")
                                btn.setToolTip("Browser Navigation")
                                
                            self.companion_config_btn = QPushButton(" C ")
                            self.companion_config_btn.setToolTip("Terminator Companion Config")
                            self.companion_config_btn.setFixedSize(settings_btn.size())
                            self.companion_config_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                            self.companion_config_btn.setStyleSheet("QPushButton { margin: 1px; padding: 1px; font-weight: bold; color: #2196F3; }")
                            
                            if hasattr(layout, 'insertWidget'):
                                idx = layout.indexOf(settings_btn)
                                layout.insertWidget(idx, self.btn_back)
                                layout.insertWidget(idx + 1, self.btn_forward)
                                layout.insertWidget(idx + 2, self.btn_reload)
                                layout.insertWidget(idx + 3, self.btn_home)
                                layout.insertWidget(idx + 4, self.companion_config_btn)
                            elif hasattr(layout, 'addWidget'):
                                layout.addWidget(self.btn_back)
                                layout.addWidget(self.btn_forward)
                                layout.addWidget(self.btn_reload)
                                layout.addWidget(self.btn_home)
                                layout.addWidget(self.companion_config_btn)
                                
                            self.companion_config_btn.clicked.connect(lambda: show_config_dialog(mw))
                            companion_logger.log("[Lifecycle Patch] Injected Nav buttons and Config button via layout fallback.")
            except Exception as ex:                companion_logger.log(f"[Lifecycle Patch] Failed to inject header/browser controls: {ex}")

        # Delay injection slightly to ensure original UI is constructed
        QTimer.singleShot(1000, inject_companion_button)

    dock_web_view_mod.ResizableWebView.__init__ = new_init

    # Hook last_text_toolbar to replace "AI" button with QComboBox dropdown
    original_last_text_toolbar = dock_web_view_mod.ResizableWebView.last_text_toolbar
    
    def new_last_text_toolbar(self, layout):
        original_make_button = self.make_button
        
        def custom_make_button(button_name, action_function, toolbar, sound=False, tooltip_text=None):
            if button_name == "AI":
                from aqt.qt import QComboBox
                
                combo = QComboBox()
                combo.setToolTip("Quick Change AI")
                
                try:
                    path_manager = importlib.import_module("1468920185.path_manager")
                    themes = [t for t in path_manager.THEMES if t not in path_manager.WITHOUT_THEMES]
                except Exception:
                    themes = ["Chat_GPT", "Google_Bard", "Google_AI_mode", "Bing_Chat", "Claude", "perplexity", "DeepSeek", "Grok_AI", "Duck_AI"]
                
                combo.addItems(themes)
                
                config = mw.addonManager.getConfig("1468920185") or {}
                now_ai = config.get("now_AI_type", "Chat_GPT")
                if now_ai in themes:
                    combo.setCurrentText(now_ai)
                
                combo.setStyleSheet(
                    "QComboBox { border: 1px solid #555; border-radius: 4px; padding: 1px 4px; background: #2a2a2a; color: #eee; font-weight: bold; }"
                )
                combo.setFixedHeight(25)
                combo.setCursor(Qt.CursorShape.PointingHandCursor)
                
                def on_ai_activated(index):
                    selected_ai = combo.itemText(index)
                    current_config = mw.addonManager.getConfig("1468920185") or {}
                    active_ai = current_config.get("now_AI_type", "Chat_GPT")
                    
                    if selected_ai == active_ai:
                        companion_logger.log(f"[AI Dropdown] Same AI '{selected_ai}' selected. Performing hard refresh...")
                        if hasattr(self, "webview") and self.webview:
                            try:
                                from aqt.qt import QWebEnginePage
                                self.webview.triggerPageAction(QWebEnginePage.WebAction.ReloadAndBypassCache)
                            except Exception:
                                self.webview.reload()
                            if self.webview.history():
                                self.webview.history().clear()
                    else:
                        companion_logger.log(f"[AI Dropdown] Changing AI to '{selected_ai}'...")
                        current_config["now_AI_type"] = selected_ai
                        mw.addonManager.writeConfig("1468920185", current_config)
                        
                        try:
                            path_manager = importlib.import_module("1468920185.path_manager")
                            THEME_CHANGE = path_manager.THEME_CHANGE
                            PYGsound = dock_web_view_mod.PYGsound
                            PYGsound(THEME_CHANGE)
                        except Exception as e:
                            companion_logger.log(f"[AI Dropdown] Failed to play sound: {e}")
                            
                        self.change_AI_type(update=False)
                
                combo.activated.connect(on_ai_activated)
                self.ai_dropdown = combo
                toolbar.addWidget(combo)
                companion_logger.log("[AI Dropdown] Successfully replaced 'AI' button with QComboBox dropdown.")
            else:
                original_make_button(button_name, action_function, toolbar, sound, tooltip_text)
                
        self.make_button = custom_make_button
        try:
            original_last_text_toolbar(self, layout)
        finally:
            if hasattr(self, "__dict__") and "make_button" in self.__dict__:
                del self.make_button

    dock_web_view_mod.ResizableWebView.last_text_toolbar = new_last_text_toolbar

    # Sync dropdown selection with actual active AI type
    original_change_AI_type = dock_web_view_mod.ResizableWebView.change_AI_type
    
    def new_change_AI_type(self, update=True):
        original_change_AI_type(self, update=update)
        if hasattr(self, "ai_dropdown") and self.ai_dropdown:
            config = mw.addonManager.getConfig("1468920185") or {}
            now_ai = config.get("now_AI_type", "Chat_GPT")
            self.ai_dropdown.blockSignals(True)
            self.ai_dropdown.setCurrentText(now_ai)
            self.ai_dropdown.blockSignals(False)
            
    dock_web_view_mod.ResizableWebView.change_AI_type = new_change_AI_type

    def navigate_address(sidebar, text):
        if not text.strip(): return
        if "." in text and " " not in text:
            url_str = text if text.startswith(("http://", "https://")) else "https://" + text
        else:
            cfg = mw.addonManager.getConfig(__name__.split(".")[0]) or {}
            custom_url = cfg.get("custom_search_url", "https://www.google.com/search?q=")
            import urllib.parse
            url_str = custom_url + urllib.parse.quote(text)
        sidebar.webview.load(QUrl(url_str))

    def update_loading_progress(sidebar, progress):
        if not hasattr(sidebar, "progress_bar"): return
        if progress < 100:
            if sidebar.progress_bar.isHidden():
                companion_logger.log(f"[Lifecycle Patch] Progress bar shown at {progress}%")
            sidebar.progress_bar.setValue(progress)
            sidebar.progress_bar.show()
            
            # Layering: Webview < Snapshot < Progress Bar
            if hasattr(sidebar, "snapshot_label") and sidebar.snapshot_label.isVisible():
                sidebar.snapshot_label.raise_()
            sidebar.progress_bar.raise_()
        else:
            companion_logger.log("[Lifecycle Patch] Progress finished (100%). Hiding progress bar.")
            sidebar.progress_bar.hide()

    # Helper functions to freeze and thaw using QStackedWidget
    def freeze_sidebar(sidebar):
        try:
            cfg = mw.addonManager.getConfig(__name__.split(".")[0]) or {}
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
                    sidebar.snapshot_label.setGeometry(sidebar.webview.geometry())
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
            cfg = mw.addonManager.getConfig(__name__.split(".")[0]) or {}
            if cfg.get("enable_html_cleanup", True) and isinstance(text, str):
                text = clean_html_for_ai(text)
            return original_set_last_text(self, text)
        dock_web_view_mod.ResizableWebView.set_last_text = patched_set_last_text

    # Hook ResizableWebView.get_field_text
    if hasattr(dock_web_view_mod.ResizableWebView, "get_field_text"):
        original_get_field_text = dock_web_view_mod.ResizableWebView.get_field_text

        def patched_get_field_text(self, card=None):
            config = mw.addonManager.getConfig(__name__.split(".")[0]) or {}
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
                                comp_cfg = mw.addonManager.getConfig(__name__.split(".")[0]) or {}
                                
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
                    comp_cfg = mw.addonManager.getConfig(__name__.split(".")[0]) or {}
                    comp_cfg["enable_add_to_new_card"] = val
                    mw.addonManager.writeConfig(__name__.split(".")[0], comp_cfg)
            except: pass
        config_mod.SetPopupConfig.save_config_fontfamiles = new_save_config
    except: pass
