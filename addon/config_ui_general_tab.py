# addon/config_ui_general_tab.py
from aqt.qt import *
from aqt import mw

class GeneralTab(QWidget):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Optimization Toggles
        self.group = QGroupBox("Active Optimizations")
        group_layout = QVBoxLayout(self.group)
        
        self.lifecycle_chk = QCheckBox("Enable Smart CPU Freezing (Lifecycle State)")
        self.lifecycle_chk.setChecked(self.config.get("enable_lifecycle_freezing", True))
        self.lifecycle_chk.setToolTip("Puts Gemini to sleep (Frozen state) 5 seconds after loading, and wakes it temporarily during prompts.")
        
        self.adblocker_chk = QCheckBox("Enable Ad-Blocker O(1) Suffix Match Optimization")
        self.adblocker_chk.setChecked(self.config.get("enable_adblocker_optimization", True))
        self.adblocker_chk.setToolTip("Optimizes adblock rule parsing using O(1) set-lookup domain suffixes instead of O(N) linear loops.")
        
        self.css_chk = QCheckBox("Inject CSS Gemini Animation Disabler")
        self.css_chk.setChecked(self.config.get("enable_css_optimization", True))
        self.css_chk.setToolTip("Injects custom styles into Gemini to completely disable background animations and glowing gradients.")
        
        self.html_cleanup_chk = QCheckBox("Enable HTML Stripping for AI Prompts")
        self.html_cleanup_chk.setChecked(self.config.get("enable_html_cleanup", True))
        self.html_cleanup_chk.setToolTip("Automatically strips HTML formatting from card fields before sending prompts to the AI (preserves LaTeX).")

        self.ai_hints_opt_chk = QCheckBox("Enable AI-Hints O(n) Regex Bypass Optimization")
        self.ai_hints_opt_chk.setChecked(self.config.get("enable_ai_hints_optimization", True))
        self.ai_hints_opt_chk.setToolTip("Speeds up card rendering by short-circuiting expensive AI-Hints clean regex scans when no hints are present.")

        self.right_click_hints_chk = QCheckBox("Enable AI-Hints Context Menu Preservation")
        self.right_click_hints_chk.setChecked(self.config.get("enable_right_click_hints_preservation", True))
        self.right_click_hints_chk.setToolTip("Ensures AI-Hints JSON data block at the end of card fields is not overwritten during right-click context menu inserts.")

        # Multiple Fields Toggle
        self.send_multiple_chk = QCheckBox("Send Multiple Fields to AI")
        anki_terminator_config = mw.addonManager.getConfig("1468920185") or {}
        self.send_multiple_chk.setChecked(anki_terminator_config.get("send_multiple_fields", False))
        self.send_multiple_chk.setToolTip("Concatenates all non-empty fields of the current card and sends them to the AI instead of just the priority field.")

        group_layout.addWidget(self.lifecycle_chk)
        group_layout.addWidget(self.adblocker_chk)
        group_layout.addWidget(self.css_chk)
        group_layout.addWidget(self.html_cleanup_chk)
        group_layout.addWidget(self.ai_hints_opt_chk)
        group_layout.addWidget(self.right_click_hints_chk)
        group_layout.addWidget(self.send_multiple_chk)
        
        layout.addWidget(self.group)
        
        # Thaw Duration Form Layout
        form_layout = QFormLayout()
        self.thaw_sb = QSpinBox(self)
        self.thaw_sb.setRange(5, 300)
        self.thaw_sb.setSuffix(" seconds")
        self.thaw_sb.setValue(self.config.get("thaw_duration_seconds", 30))
        self.thaw_sb.setToolTip("The duration Gemini stays Active before freezing back after you press any AI button.")
        
        form_layout.addRow("Thaw Duration after Query:", self.thaw_sb)
        layout.addLayout(form_layout)
        layout.addStretch()

    def get_settings(self):
        return {
            "enable_lifecycle_freezing": self.lifecycle_chk.isChecked(),
            "enable_adblocker_optimization": self.adblocker_chk.isChecked(),
            "enable_css_optimization": self.css_chk.isChecked(),
            "enable_html_cleanup": self.html_cleanup_chk.isChecked(),
            "enable_ai_hints_optimization": self.ai_hints_opt_chk.isChecked(),
            "enable_right_click_hints_preservation": self.right_click_hints_chk.isChecked(),
            "thaw_duration_seconds": self.thaw_sb.value(),
            "send_multiple_fields": self.send_multiple_chk.isChecked()
        }
