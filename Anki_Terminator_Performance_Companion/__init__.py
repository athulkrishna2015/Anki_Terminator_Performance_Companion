# addon/__init__.py
import importlib
from aqt import mw
from .logger import companion_logger

# Register of target addon folders to patch
PATCH_TARGETS = [
    "patch_1468920185_anki_terminator"  # Anki Terminator V2
]

def load_companion_patches():
    companion_logger.log("Initializing Anki Terminator Performance Companion...")
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

# Load patches and register config GUI on startup
load_companion_patches()
init_config()
