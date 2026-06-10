# addon/patch_1468920185_anki_terminator/context_menu_patch.py
import importlib
from ..logger import companion_logger

# JavaScript snippet to extract the selected HTML content preserving styling/formatting
# and converting MathJax/LaTeX to Anki-style \(...\) and \[...\] delimiters.
JS_HTML_EXTRACTOR = r"""
(function() {
    var sel = window.getSelection();
    if (sel.rangeCount > 0) {
        var range = sel.getRangeAt(0).cloneRange();
        
        // Helper to extract LaTeX from various math elements
        function extractLatex(el) {
            if (el.tagName === 'ANKI-MATHJAX') {
                return el.getAttribute('data-formula') || el.innerText || '';
            }
            if (el.classList && (el.classList.contains('math-block') || el.classList.contains('math-inline'))) {
                return el.getAttribute('data-math') || '';
            }
            var ann = el.querySelector('annotation[encoding="application/x-tex"]');
            if (ann && ann.textContent) {
                return ann.textContent.trim();
            }
            var dataLatex = el.getAttribute('data-tex') || el.getAttribute('data-latex') || el.getAttribute('data-math') || el.getAttribute('data-formula') || el.getAttribute('data-copylatex-latex');
            if (dataLatex) {
                return dataLatex.trim();
            }
            if (el.tagName === 'MJX-CONTAINER') {
                var next = el.nextElementSibling;
                if (next && next.tagName === 'SCRIPT' && (next.type || '').includes('math/tex')) {
                    return next.textContent.trim();
                }
                var scr = el.querySelector('script');
                if (scr && (scr.type || '').includes('math/tex')) {
                    return scr.textContent.trim();
                }
            }
            if (el.classList && (el.classList.contains('MathJax') || el.classList.contains('MathJax_Display') || el.classList.contains('mjx-chtml'))) {
                var id = el.id;
                if (id) {
                    var baseId = id.replace(/-Frame|-Element-\d+-Frame/g, '');
                    var scriptEl = document.getElementById(baseId);
                    if (scriptEl && scriptEl.tagName === 'SCRIPT') {
                        return scriptEl.textContent.trim();
                    }
                }
                var sib = el.nextElementSibling;
                while (sib) {
                    if (sib.tagName === 'SCRIPT' && (sib.type || '').includes('math/tex')) {
                        return sib.textContent.trim();
                    }
                    sib = sib.nextElementSibling;
                }
            }
            if (el.tagName === 'IMG') {
                var alt = el.getAttribute('alt');
                if (alt) {
                    var match = alt.trim().match(/^\{\\displaystyle\s*([\s\S]*?)\}$/);
                    if (match) return match[1].trim();
                    return alt.trim();
                }
            }
            return null;
        }
        
        // Helper to determine display mode
        function isDisplayMode(el) {
            if (el.tagName === 'ANKI-MATHJAX') {
                return el.getAttribute('block') === 'true' || el.getAttribute('data-block') === 'true';
            }
            if (el.classList && el.classList.contains('math-block')) {
                return true;
            }
            if (el.tagName === 'MJX-CONTAINER') {
                return el.hasAttribute('display') || el.getAttribute('type') === 'display';
            }
            if (el.classList) {
                if (el.classList.contains('MathJax_Display') || el.classList.contains('mwe-math-fallback-image-display')) {
                    return true;
                }
                if (el.classList.contains('katex')) {
                    var parent = el.parentElement;
                    if (parent && (parent.classList.contains('katex-display') || parent.style.display === 'block')) {
                        return true;
                    }
                }
            }
            return el.getAttribute('display') === 'block';
        }

        var mathSelectors = "anki-mathjax, mjx-container, .katex, .MathJax, .MathJax_Display, .mjx-chtml, img, .math-block, .math-inline";
        var allMathElements = Array.from(document.querySelectorAll(mathSelectors));

        // 1. Expand the range to fully enclose any partially selected math elements
        allMathElements.forEach(function(el) {
            try {
                if (range.intersectsNode(el)) {
                    if (el.contains(range.startContainer)) {
                        range.setStartBefore(el);
                    }
                    if (el.contains(range.endContainer)) {
                        range.setEndAfter(el);
                    }
                }
            } catch (e) {}
        });

        // 2. Clone the expanded range contents
        var container = document.createElement("div");
        container.appendChild(range.cloneContents());

        // 3. Strip citation/source footnote/chip elements entirely
        var tagsToStrip = ["source-footnote", "sources-carousel-inline", "source-inline-chip", "button", "script", "style"];
        tagsToStrip.forEach(function(tag) {
            container.querySelectorAll(tag).forEach(function(n) { n.remove(); });
        });
        container.querySelectorAll(".source-inline-chip-container, .luminous-sources, .hide-from-message-actions").forEach(function(n) {
            n.remove();
        });

        // 4. Process math elements inside the cloned container
        var mathElements = Array.from(container.querySelectorAll(mathSelectors));
        mathElements.forEach(function(el) {
            if (container.contains(el)) {
                var latex = extractLatex(el);
                if (latex) {
                    var isBlock = isDisplayMode(el);
                    var replacement = isBlock ? ("\\[" + latex + "\\]") : ("\\(" + latex + "\\)");
                    el.replaceWith(document.createTextNode(replacement));
                }
            }
        });

        // 5. Strip remaining math rendering artifacts
        var artifacts = container.querySelectorAll("script, style, math, .katex-mathml, mjx-assistive-mml, annotation, semantics, .katex-html, .katex-fallback");
        artifacts.forEach(function(node) {
            node.remove();
        });

        // 6. Walk text nodes and replace $...$ and $$...$$
        var walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT, null);
        var textNodes = [];
        var node;
        while (node = walker.nextNode()) {
            textNodes.push(node);
        }
        textNodes.forEach(function(n) {
            var parent = n.parentElement;
            if (parent) {
                var tagName = parent.tagName.toUpperCase();
                if (tagName === "SCRIPT" || tagName === "STYLE") return;
            }
            var text = n.nodeValue || "";
            var updated = text.replace(/\$\$([\s\S]*?)\$\$/g, "\\[$1\\]");
            updated = updated.replace(/\$([\s\S]*?)\$/g, "\\($1\\)");
            if (updated !== text) {
                n.nodeValue = updated;
            }
        });

        // 7. Sanitize HTML tags and strip all non-whitelisted attributes
        var allowedTags = ["P", "SPAN", "BR", "B", "STRONG", "I", "EM", "U", "CODE", "PRE", "UL", "OL", "LI", "SUB", "SUP", "A", "DIV", "H1", "H2", "H3", "H4", "H5", "H6", "IMG"];
        
        function sanitizeNode(node) {
            if (node.nodeType === Node.ELEMENT_NODE) {
                var children = Array.from(node.childNodes);
                children.forEach(sanitizeNode);
                
                var tagName = node.tagName.toUpperCase();
                if (allowedTags.indexOf(tagName) === -1) {
                    // Unwrap disallowed tag: replace node with its children
                    var frag = document.createDocumentFragment();
                    while (node.firstChild) {
                        frag.appendChild(node.firstChild);
                    }
                    node.replaceWith(frag);
                } else {
                    // Allowed tag: strip all attributes except href on A, src on IMG
                    var attrs = Array.from(node.attributes);
                    attrs.forEach(function(attr) {
                        var attrName = attr.name.toLowerCase();
                        if (tagName === "A" && attrName === "href") {
                            // keep href
                        } else if (tagName === "IMG" && attrName === "src") {
                            // keep src
                        } else {
                            node.removeAttribute(attr.name);
                        }
                    });
                }
            }
        }
        
        Array.from(container.childNodes).forEach(sanitizeNode);
        
        return container.innerHTML;
    }
    return "";
})();
"""

def on_add_to_new_card(webview):
    def callback(selected_html):
        if not selected_html:
            selected_html = webview.page().selectedText()
        
        if not selected_html or selected_html.strip() == "":
            return

        from aqt import mw, dialogs
        add_cards = dialogs.open("AddCards", mw)
        note = add_cards.editor.note
        if note and note.keys():
            first_field = note.keys()[0]
            current_content = note[first_field]
            if current_content and current_content.strip():
                note[first_field] = current_content + "<br><br>" + selected_html
            else:
                note[first_field] = selected_html
            add_cards.editor.loadNoteKeepingFocus()
            companion_logger.log(f"[Context Menu] Added/Appended selection to new card window (field: {first_field})")

    webview.page().runJavaScript(JS_HTML_EXTRACTOR, callback)

def patch(add_fields_mod, dock_web_view_mod=None):
    companion_logger.log("[Context Menu Patch] Patching context_menu for rich/HTML paste support...")

    original_context_menu = add_fields_mod.context_menu
    original_add_text_to_card = add_fields_mod._add_text_to_card
    original_add_context_menu = getattr(add_fields_mod, "add_context_menu", None)

    def patched_add_context_menu(webview, menu, *args, **kwargs):
        # Call original first to add field actions
        if original_add_context_menu:
            original_add_context_menu(webview, menu, *args, **kwargs)
        
        from aqt import mw, QAction
        from aqt.qt import QWebEnginePage

        cfg = mw.addonManager.getConfig(__name__.split(".")[0]) or {}
        if not cfg.get("enable_add_to_new_card", True):
            return

        # Try to find and replace the existing "Add text to card" (wiki) action
        replaced = False
        for action in menu.actions():
            text = action.text().lower()
            if "add text to card" in text or "wiki" in text:
                action.setText("Add to new card")
                try:
                    action.triggered.disconnect()
                except:
                    pass
                action.triggered.connect(lambda: on_add_to_new_card(webview))
                replaced = True
                companion_logger.log(f"[Context Menu] Replaced original wiki action '{text}' with Add to New Card")
                break
        
        # Fallback: if not found but selection exists, add it as a new item
        if not replaced and webview.pageAction(QWebEnginePage.WebAction.Copy).isEnabled():
            menu.addSeparator()
            new_card_action = QAction("Add to new card", webview)
            new_card_action.triggered.connect(lambda: on_add_to_new_card(webview))
            menu.addAction(new_card_action)

    def patched_context_menu(note, webview, field, *args, **kwargs):
        from aqt import mw
        cfg = mw.addonManager.getConfig(__name__.split(".")[0]) or {}
        if not cfg.get("enable_right_click_hints_preservation", True):
            return original_context_menu(note, webview, field, *args, **kwargs)

        companion_logger.log(f"[Context Menu] Action triggered: send selection to field '{field}'")
        
        def callback(selected_html):
            # Fallback to plain selectedText if JS returned nothing
            if not selected_html:
                companion_logger.log("[Context Menu] JS returned empty selection; falling back to selectedText()")
                selected_html = webview.page().selectedText()
                
            if not selected_html or selected_html.strip() == "":
                companion_logger.log(f"[Context Menu] Selection is empty. No text sent to field '{field}'.")
                return
                
            companion_logger.log(f"[Context Menu] Sending processed text to field '{field}': {repr(selected_html)}")
            # Call original note processing helper
            add_fields_mod.launch_bg_note_processing(note, field, selected_html)

        webview.page().runJavaScript(JS_HTML_EXTRACTOR, callback)

    def patched_add_text_to_card(note, field, selected, col):
        from aqt import mw
        cfg = mw.addonManager.getConfig(__name__.split(".")[0]) or {}
        if not cfg.get("enable_right_click_hints_preservation", True):
            return original_add_text_to_card(note, field, selected, col)

        import re
        pattern = re.compile(
            r'(?:[\s\n\r]|<br\s*/?>|&nbsp;|<div>\s*</div>)*<div\b[^>]*class=["\'][^"\']*(?:ai-hints-json|ai-hints-container)[^"\']*["\'][^>]*>.*?</div>(?:[\s\n\r]|<br\s*/?>|&nbsp;|<div>\s*</div>)*',
            flags=re.DOTALL | re.IGNORECASE,
        )
        original_field_val = note[field]
        
        # Extract all AI hints blocks
        hints_blocks = [m.group(0) for m in re.finditer(pattern, original_field_val)]
        hints_block = "".join(hints_blocks)
        
        # Remove the blocks to get the base text
        base_text = re.sub(pattern, "", original_field_val)
        
        add_br = ""
        if base_text.strip() != "":
            add_br = "<br>"
            
        selected_formatted = selected.replace("\n", "<br>")
        new_base_text = base_text + add_br + selected_formatted
        
        if hints_block:
            note[field] = new_base_text + hints_block
        else:
            note[field] = new_base_text
            
        return col.update_note(note)

    add_fields_mod.add_context_menu = patched_add_context_menu
    if dock_web_view_mod:
        dock_web_view_mod.add_context_menu = patched_add_context_menu
        
        original_dock_context_menu = dock_web_view_mod.ResizableWebView.contextMenu
        
        def new_dock_context_menu(self, webview, menu, *args, **kwargs):
            original_dock_context_menu(self, webview, menu, *args, **kwargs)
            selected = webview.page().selectedText()
            if selected:
                from aqt import mw, QAction
                
                cloze_action = QAction("🤖Explain cloze with AnkiTerminator", mw)
                
                def explain_cloze(selected_text):
                    import re
                    processed_text = selected_text
                    
                    # 1. Direct raw braces replacement (if selection contains raw braces)
                    def raw_cloze_replacer(match):
                        hint = match.group(2)
                        return f"[{hint.strip()}]" if hint and hint.strip() else "[...]"
                    processed_text = re.sub(r'\{\{c\d+::(.*?)(?:::(.*?))?\}\}', raw_cloze_replacer, processed_text)
                    
                    # 2. Dynamic active cloze answer replacement based on current card
                    if hasattr(mw, 'reviewer') and mw.reviewer.card:
                        try:
                            card = mw.reviewer.card
                            note = card.note()
                            cloze_num = card.ord + 1
                            
                            cloze_pattern = re.compile(r'\{\{c' + str(cloze_num) + r'::(.*?)(?:::(.*?))?\}\}', re.IGNORECASE)
                            
                            replacements = []
                            for field_name, field_value in note.items():
                                for match in cloze_pattern.finditer(field_value):
                                    ans = match.group(1).strip()
                                    hint = match.group(2)
                                    if hint:
                                        hint = hint.strip()
                                    
                                    # Strip HTML tags from the answer in case it has tags in the note field
                                    ans_clean = re.sub(r'<[^>]+>', '', ans).strip()
                                    
                                    replacement_text = f"[{hint}]" if hint else "[...]"
                                    
                                    if ans_clean:
                                        replacements.append((ans_clean, replacement_text))
                                    if ans:
                                        replacements.append((ans, replacement_text))
                                        
                            # Sort by length descending to replace longer phrases first
                            replacements.sort(key=lambda x: len(x[0]), reverse=True)
                            
                            for ans, replacement_text in replacements:
                                escaped_ans = re.escape(ans)
                                processed_text = re.sub(escaped_ans, replacement_text, processed_text, flags=re.IGNORECASE)
                        except Exception as e:
                            companion_logger.log(f"[Explain Cloze] Error processing active cloze: {e}")
                            
                    self.explain_with_ankiteminator(processed_text)
                    
                cloze_action.triggered.connect(
                    lambda _, selected_text=selected: explain_cloze(selected_text)
                )
                menu.addAction(cloze_action)
                
        dock_web_view_mod.ResizableWebView.contextMenu = new_dock_context_menu

    add_fields_mod.context_menu = patched_context_menu
    add_fields_mod._add_text_to_card = patched_add_text_to_card
    companion_logger.log("[Context Menu Patch] Successfully patched context_menu, _add_text_to_card, and ResizableWebView contextMenu!")

