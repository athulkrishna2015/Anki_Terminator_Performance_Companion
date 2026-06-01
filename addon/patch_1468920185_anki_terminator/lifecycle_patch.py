import importlib
from aqt.qt import *

def patch(dock_web_view_mod):
    # Mouse-hover active / freeze lifecycle patch
    original_enterEvent = dock_web_view_mod.ResizableWebView.enterEvent
    original_leaveEvent = dock_web_view_mod.ResizableWebView.leaveEvent

    def new_enterEvent(self, event):
        try:
            if hasattr(self, "webpage") and self.webpage:
                self.webpage.setLifecycleState(dock_web_view_mod.QWebEnginePage.LifecycleState.Active)
                print("[Terminator Companion] WebEnginePage state -> Active (Mouse Entered)")
        except Exception as e:
            print(f"[Terminator Companion] Error activating page on hover: {e}")
        
        if original_enterEvent:
            original_enterEvent(self, event)
        else:
            super(dock_web_view_mod.ResizableWebView, self).enterEvent(event)

    def new_leaveEvent(self, event):
        try:
            if hasattr(self, "webpage") and self.webpage:
                self.webpage.setLifecycleState(dock_web_view_mod.QWebEnginePage.LifecycleState.Frozen)
                print("[Terminator Companion] WebEnginePage state -> Frozen (Mouse Left)")
        except Exception as e:
            print(f"[Terminator Companion] Error freezing page on leave: {e}")
        
        if original_leaveEvent:
            original_leaveEvent(self, event)
        else:
            super(dock_web_view_mod.ResizableWebView, self).leaveEvent(event)

    dock_web_view_mod.ResizableWebView.enterEvent = new_enterEvent
    dock_web_view_mod.ResizableWebView.leaveEvent = new_leaveEvent

    # Programmatic runJavaScript activation patch
    original_runJavaScript = dock_web_view_mod.QWebEnginePage.runJavaScript

    def patched_runJavaScript(self, *args, **kwargs):
        try:
            self.setLifecycleState(dock_web_view_mod.QWebEnginePage.LifecycleState.Active)
            print("[Terminator Companion] WebEnginePage state -> Active (Query Started)")
            
            def delayed_freeze():
                try:
                    if hasattr(self, "view") and self.view() and hasattr(self.view(), "parent_window") and self.view().parent_window:
                        sidebar = self.view().parent_window
                        if not sidebar.underMouse():
                            self.setLifecycleState(dock_web_view_mod.QWebEnginePage.LifecycleState.Frozen)
                            print("[Terminator Companion] WebEnginePage state -> Frozen (Delayed)")
                except Exception as e:
                    print(f"[Terminator Companion] Delayed freeze failed: {e}")
                    
            QTimer.singleShot(15000, delayed_freeze)
        except Exception as e:
            print(f"[Terminator Companion] Error handling lifecycle on query: {e}")
            
        return original_runJavaScript(self, *args, **kwargs)

    dock_web_view_mod.QWebEnginePage.runJavaScript = patched_runJavaScript
    print("[Terminator Companion] Successfully patched ResizableWebView and QWebEnginePage for Smart CPU freezing!")
