# addon/patch_1468920185_anki_terminator/context_menu_patch.py
import importlib
from ..logger import companion_logger

def patch(add_fields_mod):
    companion_logger.log("[Context Menu Patch] Patching context_menu for rich/HTML paste support...")

    def patched_context_menu(note, webview, field, *args, **kwargs):
        companion_logger.log(f"[Context Menu] Action triggered: send selection to field '{field}'")
        # JavaScript snippet to extract the selected HTML content preserving styling/formatting
        # and converting MathJax/LaTeX to Anki-style \(...\) and \[...\] delimiters.
        js_code = r"""
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
                var allowedTags = ["P", "SPAN", "BR", "B", "STRONG", "I", "EM", "U", "CODE", "PRE", "UL", "OL", "LI", "SUB", "SUP", "A", "DIV", "H1", "H2", "H3", "H4", "H5", "H6"];
                
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
                            // Allowed tag: strip all attributes except href on A
                            var attrs = Array.from(node.attributes);
                            attrs.forEach(function(attr) {
                                if (tagName === "A" && attr.name.toLowerCase() === "href") {
                                    // keep href
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

        webview.page().runJavaScript(js_code, callback)

    def patched_add_text_to_card(note, field, selected, col):
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

    add_fields_mod.context_menu = patched_context_menu
    add_fields_mod._add_text_to_card = patched_add_text_to_card
    companion_logger.log("[Context Menu Patch] Successfully patched context_menu and _add_text_to_card!")

