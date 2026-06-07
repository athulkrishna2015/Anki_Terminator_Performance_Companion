# addon/patch_1468920185_anki_terminator/__init__.py
import importlib
from ..logger import companion_logger

def apply_ai_hints_patch():
    try:
        import sys
        import re
        patched_ai_hints = False
        for name, module in list(sys.modules.items()):
            if name.endswith("anki_terminator_patch"):
                if hasattr(module, "clean_ai_hints_from_text") and not hasattr(module, "_companion_optimized"):
                    original_clean = module.clean_ai_hints_from_text
                    
                    CLEAN_PAT = re.compile(
                        r'(?:[\s\n\r]|<br\s*/?>|&nbsp;|<div>\s*</div>)*<div\b[^>]*class=["\'][^"\']*(?:ai-hints-json|ai-hints-container)[^"\']*["\'][^>]*>.*?</div>(?:[\s\n\r]|<br\s*/?>|&nbsp;|<div>\s*</div>)*',
                        flags=re.DOTALL | re.IGNORECASE,
                    )
                    
                    def optimized_clean_ai_hints_from_text(text: str) -> str:
                        from aqt import mw
                        cfg = mw.addonManager.getConfig("Anki_Terminator_Companion") or {}
                        if not cfg.get("enable_ai_hints_optimization", True):
                            return original_clean(text)

                        if not isinstance(text, str):
                            return text
                        if "hints" not in text and "options" not in text:
                            return text
                        
                        cleaned = CLEAN_PAT.sub("", text)
                        
                        # Strip plain/tag-stripped JSON payloads that get saved in sfld (Sort Field)
                        idx = 0
                        while True:
                            start_idx = cleaned.find("{", idx)
                            if start_idx == -1:
                                break
                            chunk = cleaned[start_idx:start_idx+150]
                            if any(f'"c{i}"' in chunk for i in range(1, 10)) and ('"hints"' in chunk or '"options"' in chunk):
                                brace_count = 0
                                end_idx = -1
                                for i in range(start_idx, len(cleaned)):
                                    if cleaned[i] == '{':
                                        brace_count += 1
                                    elif cleaned[i] == '}':
                                        brace_count -= 1
                                        if brace_count == 0:
                                            end_idx = i
                                            break
                                if end_idx != -1:
                                    cleaned = cleaned[:start_idx] + cleaned[end_idx+1:]
                                    idx = start_idx
                                    continue
                            idx = start_idx + 1
                        return cleaned.strip()

                    module.clean_ai_hints_from_text = optimized_clean_ai_hints_from_text
                    module._companion_optimized = True
                    companion_logger.log("[AI-Hints Patch] Successfully patched clean_ai_hints_from_text with O(n) fast path!")
                    patched_ai_hints = True
                    break
        if not patched_ai_hints:
            companion_logger.log("[AI-Hints Patch] Module 'anki_terminator_patch' not found in sys.modules yet.")
    except Exception as e:
        companion_logger.log(f"[AI-Hints Patch] Patch failed: {e}")

def apply_patches():
    # 1. Apply AdBlocker patches
    try:
        ad_blocker_mod = importlib.import_module("1468920185.ad_blocker")
        from . import ad_blocker_patch
        ad_blocker_patch.patch(ad_blocker_mod)
    except Exception as e:
        companion_logger.log(f"[Terminator Companion] AdBlocker patch failed: {e}")

    # 2. Apply WebEngine, Lifecycle, and Context Menu patches
    try:
        dock_web_view_mod = importlib.import_module("1468920185.dock_web_view")
        add_fields_mod = importlib.import_module("1468920185.context_menu.add_fields")
        from . import css_patch
        from . import lifecycle_patch
        from . import context_menu_patch
        css_patch.patch(dock_web_view_mod)
        lifecycle_patch.patch(dock_web_view_mod)
        context_menu_patch.patch(add_fields_mod)
    except Exception as e:
        companion_logger.log(f"[Terminator Companion] Webview/Lifecycle/Context Menu patch failed: {e}")

    # 3. Apply AI-Hints optimization patch
    apply_ai_hints_patch()
    try:
        from aqt.qt import QTimer
        QTimer.singleShot(2000, apply_ai_hints_patch)
    except Exception:
        pass

# Apply immediately on module import
apply_patches()

