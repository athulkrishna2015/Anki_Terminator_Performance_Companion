# addon/__init__.py
import os
import importlib
from aqt import mw
from aqt import gui_hooks
from aqt.qt import QTimer
from .logger import companion_logger

ADDON_PACKAGE = __name__.split(".")[0]

# Register of target addon folders to patch
PATCH_TARGETS = [
    "patch_1468920185_anki_terminator"  # Anki Terminator V2
]

def load_companion_patches():
    companion_logger.log("Initializing Anki Terminator Companion...")
    for target in PATCH_TARGETS:
        try:
            importlib.import_module(f".{target}", __name__)
            companion_logger.log(f"Successfully loaded and applied patches from target folder: {target}")
        except Exception as e:
            companion_logger.log(f"Failed to load patches from {target}: {e}")

# Register custom configuration dialog GUI in Anki
def init_config():
    try:
        from .config_ui import show_config_dialog
        mw.addonManager.setConfigAction(__name__, show_config_dialog)
        companion_logger.log("Successfully registered configuration GUI Action.")
    except Exception as e:
        companion_logger.log(f"Failed to register configuration GUI Action: {e}")

def check_support_on_update():
    """Automatically opens the Support tab once after an update, unless opted out."""
    try:
        # 1. Get current version from VERSION file
        addon_dir = os.path.dirname(os.path.abspath(__file__))
        version_path = os.path.join(addon_dir, "VERSION")
        if not os.path.exists(version_path):
            return
        with open(version_path, "r", encoding="utf-8") as f:
            current_version = f.read().strip()

        # 2. Get meta state
        meta = mw.addonManager.addonMeta(ADDON_PACKAGE)
        last_version = meta.get("last_seen_version", "")
        opt_out = meta.get("supporter_opt_out", False)

        # 3. Trigger if version changed
        if current_version != last_version:
            meta["last_seen_version"] = current_version
            mw.addonManager.writeAddonMeta(ADDON_PACKAGE, meta)
            
            if not opt_out:
                # Delay the automatic window opening to ensure Anki is stable
                def _open_support():
                    if not mw or not mw.col:
                        return
                    from .config_ui import CompanionConfigDialog
                    # Open dialog and switch to Support tab (Index 2)
                    dialog = CompanionConfigDialog(mw)
                    dialog.tabs.setCurrentIndex(2)
                    dialog.show()
                    # Store reference to prevent GC garbage collection if non-modal
                    mw._companion_support_dialog = dialog
                
                QTimer.singleShot(5000, _open_support)
    except Exception as e:
        companion_logger.log(f"Support update check failed: {e}")

# Load patches and register config GUI on startup
load_companion_patches()
init_config()

# Register the supporter welcome screen update check hook
gui_hooks.profile_did_open.append(check_support_on_update)
