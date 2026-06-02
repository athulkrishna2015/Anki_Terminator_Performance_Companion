# addon/config_ui_general_tab.py
from aqt.qt import *

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
        
        group_layout.addWidget(self.lifecycle_chk)
        group_layout.addWidget(self.adblocker_chk)
        group_layout.addWidget(self.css_chk)
        
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
            "thaw_duration_seconds": self.thaw_sb.value()
        }
