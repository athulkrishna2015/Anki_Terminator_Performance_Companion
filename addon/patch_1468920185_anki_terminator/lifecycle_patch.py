import importlib
from aqt.qt import *

def patch(dock_web_view_mod):
    # Hook CustomWebEnginePage __init__ to handle initial load freeze
    original_init = dock_web_view_mod.CustomWebEnginePage.__init__
    
    def new_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        
        # When initial page finishes loading, let it settle, then freeze it
        def on_initial_load(success):
            if success:
                print("[Terminator Companion] Initial load finished. Freezing page in 5 seconds...")
                QTimer.singleShot(5000, lambda: self.setLifecycleState(dock_web_view_mod.QWebEnginePage.LifecycleState.Frozen))
                
        self.loadFinished.connect(on_initial_load)

    dock_web_view_mod.CustomWebEnginePage.__init__ = new_init

    # Programmatic runJavaScript activation patch (wakes up on query, refreezes after 30s)
    original_runJavaScript = dock_web_view_mod.QWebEnginePage.runJavaScript

    def patched_runJavaScript(self, *args, **kwargs):
        try:
            # Wake up the page to execute the query
            self.setLifecycleState(dock_web_view_mod.QWebEnginePage.LifecycleState.Active)
            print("[Terminator Companion] WebEnginePage state -> Active (Query Started)")
            
            # Re-freeze the page after 30 seconds
            def delayed_freeze():
                try:
                    self.setLifecycleState(dock_web_view_mod.QWebEnginePage.LifecycleState.Frozen)
                    print("[Terminator Companion] WebEnginePage state -> Frozen (Query Finished)")
                except Exception as e:
                    print(f"[Terminator Companion] Delayed freeze failed: {e}")
                    
            QTimer.singleShot(30000, delayed_freeze)
        except Exception as e:
            print(f"[Terminator Companion] Error handling lifecycle on query: {e}")
            
        return original_runJavaScript(self, *args, **kwargs)

    dock_web_view_mod.QWebEnginePage.runJavaScript = patched_runJavaScript
    print("[Terminator Companion] Successfully patched QWebEnginePage for Default-Freeze & Query-Thaw lifecycle!")
