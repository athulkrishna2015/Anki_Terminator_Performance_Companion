import importlib
from aqt import mw
from aqt.qt import *
from ..logger import companion_logger

def patch(dock_web_view_mod):
    companion_logger.log("[Lifecycle Patch] Initiating Flicker-Free QStackedWidget and Response Monitor hooks...")

    # Hook ResizableWebView __init__ to set up stacked widget layout
    original_init = dock_web_view_mod.ResizableWebView.__init__
    
    def new_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        
        # Track response state variables
        self.is_responding = False
        self.last_text_length = 0
        self.stable_checks = 0
        self.is_hovered = False
        
        # Create static screenshot label
        self.snapshot_label = QLabel(self)
        self.snapshot_label.setScaledContents(True)
        self.snapshot_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Create stacked widget for flicker-free transitions
        self.stacked_widget = QStackedWidget(self)
        self.stacked_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        if self.layout():
            # Reparent webview inside stacked widget
            self.layout().removeWidget(self.webview)
            self.stacked_widget.addWidget(self.webview)
            self.stacked_widget.addWidget(self.snapshot_label)
            
            # Add stacked widget back to layout
            self.layout().addWidget(self.stacked_widget)
            self.stacked_widget.setCurrentWidget(self.webview)
            
        # Hook the initial page load to freeze it after 5 seconds
        def on_initial_load(success):
            companion_logger.log(f"[Lifecycle Patch] CustomWebEnginePage.loadFinished triggered! Success state: {success}")
            if success:
                companion_logger.log("[Lifecycle Patch] Initial load finished. Scheduling freeze in 5 seconds...")
                QTimer.singleShot(5000, lambda: freeze_sidebar(self))
                
        if hasattr(self, "webpage") and self.webpage:
            self.webpage.loadFinished.connect(on_initial_load)
            companion_logger.log("[Lifecycle Patch] Connected loadFinished signal for initial load freeze.")

    dock_web_view_mod.ResizableWebView.__init__ = new_init

    # Helper functions to freeze and thaw using QStackedWidget
    def freeze_sidebar(sidebar):
        try:
            cfg = mw.addonManager.getConfig("000_addon_fixes") or {}
            if not cfg.get("enable_lifecycle_freezing", True):
                return
            
            # Do nothing if already frozen
            if sidebar.stacked_widget.currentWidget() == sidebar.snapshot_label:
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
                    if getattr(sidebar, "is_hovered", False) or sidebar.is_responding:
                        companion_logger.log("[Lifecycle Patch] Freeze cancelled: State changed during delay.")
                        return
                        
                    companion_logger.log("[Lifecycle Patch] Freezing sidebar -> Capturing static screenshot...")
                    
                    # 1. Grab snapshot of the active webview
                    pixmap = sidebar.webview.grab()
                    
                    if pixmap.isNull():
                        companion_logger.log("[Lifecycle Patch] Warning: Captured pixmap is null. Aborting freeze to prevent black screen.")
                        return
                        
                    sidebar.snapshot_label.setPixmap(pixmap)
                    
                    # 2. Swap pages in stacked widget (completely flicker-free!)
                    sidebar.stacked_widget.setCurrentWidget(sidebar.snapshot_label)
                    
                    # 3. Request background thread freeze
                    if hasattr(sidebar, "webpage") and sidebar.webpage:
                        try:
                            sidebar.webpage.setLifecycleState(dock_web_view_mod.QWebEnginePage.LifecycleState.Frozen)
                        except Exception:
                            pass
                    companion_logger.log("[Lifecycle Patch] WebEngine hidden in StackedWidget. Static screenshot active. CPU dropped to 0%!")
                except Exception as ex:
                    companion_logger.log(f"[Lifecycle Patch] Delayed capture freeze failed: {ex}")

            QTimer.singleShot(100, capture_and_freeze)
        except Exception as e:
            companion_logger.log(f"[Lifecycle Patch] Failed to schedule freeze: {e}")

    def thaw_sidebar(sidebar):
        try:
            # Do nothing if already active
            if sidebar.stacked_widget.currentWidget() == sidebar.webview:
                return
                
            companion_logger.log("[Lifecycle Patch] Thawing sidebar -> Warming up active WebEngine...")
            
            # 1. First, ensure WebEngine page is active and thawed
            if hasattr(sidebar, "webpage") and sidebar.webpage:
                try:
                    sidebar.webpage.setLifecycleState(dock_web_view_mod.QWebEnginePage.LifecycleState.Active)
                except Exception:
                    pass
            
            # 2. Wait 80ms for the WebEngine to render its frame before swapping, eliminating transition flicker!
            def complete_thaw():
                try:
                    # Cancel the swap if the user has already hovered out
                    if not getattr(sidebar, "is_hovered", False) and not sidebar.is_responding:
                        companion_logger.log("[Lifecycle Patch] Thaw swap cancelled: User already left.")
                        return
                    sidebar.stacked_widget.setCurrentWidget(sidebar.webview)
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
        js_code = args[0] if args else "None"
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
            else:
                companion_logger.log("[Lifecycle Patch] Warning: Could not resolve parent sidebar for runJavaScript.")
        except Exception as e:
            companion_logger.log(f"[Lifecycle Patch] Error handling UI freeze on query: {e}")
            
        return original_runJavaScript(self, *args, **kwargs)

    dock_web_view_mod.QWebEnginePage.runJavaScript = patched_runJavaScript

    # Hook ResizableWebView.auto_click_v2 to immediately thaw and start monitoring
    if hasattr(dock_web_view_mod.ResizableWebView, "auto_click_v2"):
        original_auto_click_v2 = dock_web_view_mod.ResizableWebView.auto_click_v2
        
        def new_auto_click_v2(self, *args, **kwargs):
            companion_logger.log("[Lifecycle Patch] auto_click_v2 triggered! Thawing sidebar and initiating response monitoring...")
            self.is_responding = True
            thaw_sidebar(self)
            start_response_monitoring(self)
            return original_auto_click_v2(self, *args, **kwargs)
            
        dock_web_view_mod.ResizableWebView.auto_click_v2 = new_auto_click_v2
        companion_logger.log("[Lifecycle Patch] Successfully hooked ResizableWebView.auto_click_v2")

    companion_logger.log("[Lifecycle Patch] Successfully hooked ResizableWebView and runJavaScript for Smart UI-Freezing.")

