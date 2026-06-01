# addon/__init__.py
import importlib

# Register of target addon folders to patch
PATCH_TARGETS = [
    "patch_1468920185_anki_terminator"  # Anki Terminator V2
]

def load_companion_patches():
    for target in PATCH_TARGETS:
        try:
            importlib.import_module(f".{target}", __name__)
            print(f"[Companion] Fully loaded patches from subfolder: {target}")
        except Exception as e:
            print(f"[Companion] Failed to load patches from {target}: {e}")

# Load all companion patches on startup
load_companion_patches()
