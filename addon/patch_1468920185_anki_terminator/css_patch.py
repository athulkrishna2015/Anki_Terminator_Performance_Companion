import importlib
from aqt import mw
from aqt.qt import *

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

def patch(dock_web_view_mod):
    original_inject = dock_web_view_mod.CustomWebEnginePage.inject_javascript

    def patched_inject(self):
        # Call original ChatGPT check
        original_inject(self)
        
        # Companion optimization for Gemini
        config = mw.addonManager.getConfig("1468920185")
        if config and config.get("now_AI_type") == "Google_Bard":
            inject_gemini_performance_css(self)

    dock_web_view_mod.CustomWebEnginePage.inject_javascript = patched_inject
    print("[Terminator Companion] Successfully patched CustomWebEnginePage.inject_javascript for Gemini CSS optimization!")
