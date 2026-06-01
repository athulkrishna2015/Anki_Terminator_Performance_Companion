# addon/patch_1468920185_anki_terminator/__init__.py
import importlib

def apply_patches():
    # 1. Apply AdBlocker patches
    try:
        ad_blocker_mod = importlib.import_module("1468920185.ad_blocker")
        from . import ad_blocker_patch
        ad_blocker_patch.patch(ad_blocker_mod)
    except Exception as e:
        print(f"[Terminator Companion] AdBlocker patch failed: {e}")

    # 2. Apply WebEngine and Lifecycle patches
    try:
        dock_web_view_mod = importlib.import_module("1468920185.dock_web_view")
        from . import css_patch
        from . import lifecycle_patch
        css_patch.patch(dock_web_view_mod)
        lifecycle_patch.patch(dock_web_view_mod)
    except Exception as e:
        print(f"[Terminator Companion] Webview/Lifecycle patch failed: {e}")

# Apply immediately on module import
apply_patches()
