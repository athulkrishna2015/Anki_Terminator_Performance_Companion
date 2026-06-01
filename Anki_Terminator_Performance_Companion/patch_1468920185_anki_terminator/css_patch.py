import importlib
from aqt import mw
from aqt.qt import *
from ..logger import companion_logger

def inject_gemini_performance_css(page: QWebEnginePage):
    performance_js = """
(function() {
    const style = document.createElement('style');
    style.id = 'anki-performance-optimizer';
    style.textContent = `
        *, *::before, *::after {
            animation-delay: 0s !important;
            animation-duration: 0s !important;
            transition-delay: 0s !important;
            transition-duration: 0s !important;
            backdrop-filter: none !important;
        }
    `;
    document.head.appendChild(style);
})();
"""
    page.runJavaScript(performance_js)
    companion_logger.log("CSS patch injected successfully (Gemini animations/transitions disabled)")

def patch(dock_web_view_mod):
    # Check if CSS optimization is enabled
    config = mw.addonManager.getConfig("000_addon_fixes") or {}
    if not config.get("enable_css_optimization", True):
        companion_logger.log("CSS animation patch is disabled in settings, skipping.")
        return

    original_inject = dock_web_view_mod.ResizableWebView.inject_javascript

    def patched_inject(self):
        # Call original ChatGPT check
        original_inject(self)
        
        # Companion optimization for Gemini
        addon_config = mw.addonManager.getConfig("1468920185")
        if addon_config and addon_config.get("now_AI_type") == "Google_Bard":
            inject_gemini_performance_css(self.webpage)

    dock_web_view_mod.ResizableWebView.inject_javascript = patched_inject
    companion_logger.log("Successfully hooked ResizableWebView.inject_javascript for CSS injection.")
