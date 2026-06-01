import importlib
from aqt import mw
from aqt.qt import *
from ..logger import companion_logger

def patch(dock_web_view_mod):
    companion_logger.log("[Lifecycle Patch] Initiating patches for CustomWebEnginePage...")

    # Hook CustomWebEnginePage __init__ to handle initial load freeze
    original_init = dock_web_view_mod.CustomWebEnginePage.__init__
    
    def new_init(self, *args, **kwargs):
        companion_logger.log(f"[Lifecycle Patch] CustomWebEnginePage instantiated (ID: {id(self)})")
        original_init(self, *args, **kwargs)
        
        # When initial page finishes loading, let it settle, then freeze it
        def on_initial_load(success):
            companion_logger.log(f"[Lifecycle Patch] CustomWebEnginePage.loadFinished triggered! Success state: {success}")
            if success:
                companion_logger.log("[Lifecycle Patch] Scheduling automatic page freeze in 5 seconds...")
                QTimer.singleShot(5000, lambda: freeze_page(self))
                
        self.loadFinished.connect(on_initial_load)
        companion_logger.log("[Lifecycle Patch] Successfully connected loadFinished signal for initial load freeze.")

    dock_web_view_mod.CustomWebEnginePage.__init__ = new_init

    def freeze_page(page: QWebEnginePage):
        try:
            # Re-read config to check if still enabled
            cfg = mw.addonManager.getConfig("000_addon_fixes") or {}
            if not cfg.get("enable_lifecycle_freezing", True):
                companion_logger.log("[Lifecycle Patch] Freeze aborted: smart freezing is disabled in settings.")
                return
            
            companion_logger.log(f"[Lifecycle Patch] Requesting page state change -> Frozen (Current state was: {page.lifecycleState()})")
            page.setLifecycleState(dock_web_view_mod.QWebEnginePage.LifecycleState.Frozen)
            companion_logger.log(f"[Lifecycle Patch] Successfully updated state! Current state is now: {page.lifecycleState()}")
        except Exception as e:
            companion_logger.log(f"[Lifecycle Patch] Failed to freeze page: {e}")

    # Programmatic runJavaScript activation patch (wakes up on query, refreezes after thaw duration)
    original_runJavaScript = dock_web_view_mod.QWebEnginePage.runJavaScript

    def patched_runJavaScript(self, *args, **kwargs):
        js_code = args[0] if args else "None"
        snippet = js_code[:100].replace('\n', ' ') + ('...' if len(js_code) > 100 else '')
        companion_logger.log(f"[Lifecycle Patch] Programmatic runJavaScript triggered! Code snippet: {snippet}")

        try:
            cfg = mw.addonManager.getConfig("000_addon_fixes") or {}
            if cfg.get("enable_lifecycle_freezing", True):
                # Wake up the page to execute the query
                companion_logger.log(f"[Lifecycle Patch] Requesting page state change -> Active (Current state: {self.lifecycleState()})")
                self.setLifecycleState(dock_web_view_mod.QWebEnginePage.LifecycleState.Active)
                companion_logger.log(f"[Lifecycle Patch] Successfully activated! Current state: {self.lifecycleState()}")
                
                # Re-freeze the page after thaw_duration_seconds
                thaw_duration_secs = cfg.get("thaw_duration_seconds", 30)
                thaw_duration = thaw_duration_secs * 1000  # milliseconds
                companion_logger.log(f"[Lifecycle Patch] Scheduling automatic refreeze in {thaw_duration_secs} seconds...")
                
                def delayed_freeze():
                    companion_logger.log(f"[Lifecycle Patch] Refreeze timer ({thaw_duration_secs}s) expired. Triggering refreeze...")
                    freeze_page(self)
                        
                QTimer.singleShot(thaw_duration, delayed_freeze)
        except Exception as e:
            companion_logger.log(f"[Lifecycle Patch] Error handling lifecycle on query: {e}")
            
        return original_runJavaScript(self, *args, **kwargs)

    dock_web_view_mod.QWebEnginePage.runJavaScript = patched_runJavaScript
    companion_logger.log("[Lifecycle Patch] Successfully hooked QWebEnginePage.runJavaScript with auto-thaw & refreeze.")
