# addon/patch_1468920185_anki_terminator/context_menu_patch.py
import importlib
from ..logger import companion_logger

def patch(add_fields_mod):
    companion_logger.log("[Context Menu Patch] Patching context_menu for rich/HTML paste support...")

    def patched_context_menu(note, webview, field, *args, **kwargs):
        # JavaScript snippet to extract the selected HTML content preserving styling/formatting
        js_code = """
        (function() {
            var sel = window.getSelection();
            if (sel.rangeCount > 0) {
                var container = document.createElement("div");
                for (var i = 0; i < sel.rangeCount; ++i) {
                    container.appendChild(sel.getRangeAt(i).cloneContents());
                }
                return container.innerHTML;
            }
            return "";
        })();
        """
        
        def callback(selected_html):
            # Fallback to plain selectedText if JS returned nothing
            if not selected_html:
                selected_html = webview.page().selectedText()
                
            if not selected_html or selected_html.strip() == "":
                return
                
            # Call original note processing helper
            add_fields_mod.launch_bg_note_processing(note, field, selected_html)

        webview.page().runJavaScript(js_code, callback)

    add_fields_mod.context_menu = patched_context_menu
    companion_logger.log("[Context Menu Patch] Successfully patched context_menu to retrieve selected HTML!")
