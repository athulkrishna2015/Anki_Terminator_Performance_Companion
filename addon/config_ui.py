# addon/config_ui.py
from aqt import mw
from aqt.qt import *
from .logger import companion_logger

class CompanionConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(mw)
        self.setWindowTitle("Terminator Companion Config")
        self.resize(550, 400)
        self.config = mw.addonManager.getConfig(__name__.split(".")[0]) or {}
        
        # Main Layout
        self.main_layout = QVBoxLayout(self)
        
        # Tab Widget
        self.tabs = QTabWidget(self)
        
        # 1. General Tab
        self.general_tab = QWidget()
        self.setup_general_tab()
        self.tabs.addTab(self.general_tab, "General Settings")
        
        # 2. Logs Tab
        self.logs_tab = QWidget()
        self.setup_logs_tab()
        self.tabs.addTab(self.logs_tab, "Performance Logs")
        
        self.main_layout.addWidget(self.tabs)
        
        # Bottom Buttons
        self.bottom_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save Settings", self)
        self.save_btn.clicked.connect(self.save_config)
        self.close_btn = QPushButton("Close", self)
        self.close_btn.clicked.connect(self.reject)
        
        self.bottom_layout.addStretch()
        self.bottom_layout.addWidget(self.save_btn)
        self.bottom_layout.addWidget(self.close_btn)
        self.main_layout.addLayout(self.bottom_layout)
        
        # Register Callback for live log updates
        companion_logger.register_callback(self.on_log_added)
        
    def setup_general_tab(self):
        layout = QVBoxLayout(self.general_tab)
        
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
        
    def setup_logs_tab(self):
        layout = QVBoxLayout(self.logs_tab)
        
        self.log_text = QPlainTextEdit(self)
        self.log_text.setReadOnly(True)
        self.log_text.setPlainText(companion_logger.get_logs())
        
        # Scroll to bottom
        self.log_text.moveCursor(QTextCursor.MoveOperation.End)
        
        btn_layout = QHBoxLayout()
        self.copy_btn = QPushButton("Copy Logs", self)
        self.copy_btn.clicked.connect(self.copy_logs)
        
        self.clear_btn = QPushButton("Clear Logs", self)
        self.clear_btn.clicked.connect(self.clear_logs)
        
        btn_layout.addWidget(self.copy_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.clear_btn)
        
        layout.addWidget(self.log_text)
        layout.addLayout(btn_layout)
        
    def on_log_added(self, line):
        if not line:
            self.log_text.setPlainText("")
        else:
            self.log_text.appendPlainText(line)
            self.log_text.moveCursor(QTextCursor.MoveOperation.End)
            
    def copy_logs(self):
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(self.log_text.toPlainText())
        QToolTip.showText(self.copy_btn.mapToGlobal(QPoint(0, 0)), "Logs copied to clipboard!")
            
    def clear_logs(self):
        companion_logger.clear()
        
    def save_config(self):
        self.config["enable_lifecycle_freezing"] = self.lifecycle_chk.isChecked()
        self.config["enable_adblocker_optimization"] = self.adblocker_chk.isChecked()
        self.config["enable_css_optimization"] = self.css_chk.isChecked()
        self.config["thaw_duration_seconds"] = self.thaw_sb.value()
        
        mw.addonManager.writeConfig(__name__.split(".")[0], self.config)
        QMessageBox.information(self, "Success", "Settings saved successfully!\nPlease restart Anki for changes to take effect.")
        self.accept()
        
    def closeEvent(self, event):
        companion_logger.unregister_callback(self.on_log_added)
        event.accept()

def show_config_dialog(parent=None):
    dialog = CompanionConfigDialog(parent)
    dialog.exec()
