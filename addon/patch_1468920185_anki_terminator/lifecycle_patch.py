import importlib
from aqt import mw
from aqt.qt import *
from ..logger import companion_logger

def patch(dock_web_view_mod):
    # Check if lifecycle freezing is enabled
    config = mw.addonManager.getConfig("000_addon_fixes") or {}
    if not config.get("enable_lifecycle_freezing", True):
        companion_logger.log("Smart lifecycle freezing is disabled in settings, skipping.")
        return

    # Hook CustomWebEnginePage __init__ to handle initial load freeze
    original_init = dock_web_view_mod.CustomWebEnginePage.__init__
    
    def new_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        
        # When initial page finishes loading, let it settle, then freeze it
        def on_initial_load(success):
            if success:
                companion_logger.log("Initial load finished. Scheduling freeze in 5 seconds...")
                QTimer.singleShot(5000, lambda: freeze_page(self))
                
        self.loadFinished.connect(on_initial_load)

    dock_web_view_mod.CustomWebEnginePage.__init__ = new_init

    def freeze_page(page: QWebEnginePage):
        try:
            # Re-read config to check if still enabled
            cfg = mw.addonManager.getConfig("000_addon_fixes") or {}
            if not cfg.get("enable_lifecycle_freezing", True):
                return
            page.setLifecycleState(dock_web_view_mod.QWebEnginePage.LifecycleState.Frozen)
            companion_logger.log("WebEnginePage put to sleep -> state: Frozen (CPU reduced to 0%)")
        except Exception as e:
            companion_logger.log(f"Failed to freeze page: {e}")

    # Programmatic runJavaScript activation patch (wakes up on query, refreezes after thaw duration)
    original_runJavaScript = dock_web_view_mod.QWebEnginePage.runJavaScript

    def patched_runJavaScript(self, *args, **kwargs):
        try:
            cfg = mw.addonManager.getConfig("000_addon_fixes") or {}
            if cfg.get("enable_lifecycle_freezing", True):
                # Wake up the page to execute the query
                self.setLifecycleState(dock_web_view_mod.QWebEnginePage.LifecycleState.Active)
                companion_logger.log("WebEnginePage woke up -> state: Active (Processing prompt...)")
                
                # Re-freeze the page after thaw_duration_seconds
                thaw_duration = cfg.get("thaw_duration_seconds", 30) * 1000  # milliseconds
                
                def delayed_freeze():
                    freeze_page(self)
                        
                QTimer.singleShot(thaw_duration, delayed_freeze)
        except Exception as e:
            companion_logger.log(f"Error handling lifecycle on query: {e}")
            
        return original_runJavaScript(self, *args, **kwargs)

    dock_web_view_mod.QWebEnginePage.runJavaScript = patched_runJavaScript
    companion_logger.log("Successfully hooked QWebEnginePage for Smart CPU Freezing & Query Thawing.")
