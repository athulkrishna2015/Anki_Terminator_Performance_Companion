# addon/config_ui.py
from aqt import mw
from aqt.qt import *
from .config_ui_general_tab import GeneralTab
from .config_ui_logs_tab import LogsTab
from .tab_support import SupportTabMixin

class CompanionConfigDialog(QDialog, SupportTabMixin):
    def __init__(self, parent=None):
        super().__init__(mw)
        self.setWindowTitle("Terminator Companion Config")
        self.resize(550, 480)  # Make it slightly taller for Support tab content
        self.config = mw.addonManager.getConfig(__name__.split(".")[0]) or {}
        
        # Main Layout
        self.main_layout = QVBoxLayout(self)
        
        # Tab Widget
        self.tabs = QTabWidget(self)
        
        # 1. General Tab
        self.general_tab = GeneralTab(self.config, self)
        self.tabs.addTab(self.general_tab, "General Settings")
        
        # 2. Logs Tab
        self.logs_tab = LogsTab(self)
        self.tabs.addTab(self.logs_tab, "Performance Logs")
        
        # 3. Support Tab
        self.support_tab = self._create_support_tab()
        self.tabs.addTab(self.support_tab, "Support")
        
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
        
    def save_config(self):
        settings = self.general_tab.get_settings()
        self.config.update(settings)
        
        mw.addonManager.writeConfig(__name__.split(".")[0], self.config)
        
        # Sync to Anki Terminator (1468920185) config
        send_multiple = settings.get("send_multiple_fields", False)
        anki_terminator_config = mw.addonManager.getConfig("1468920185") or {}
        anki_terminator_config["send_multiple_fields"] = send_multiple
        mw.addonManager.writeConfig("1468920185", anki_terminator_config)
        
        QMessageBox.information(self, "Success", "Settings saved successfully!\nPlease restart Anki for changes to take effect.")
        self.accept()
        
    def closeEvent(self, event):
        self.logs_tab.disconnect_logger()
        event.accept()

def show_config_dialog(parent=None):
    dialog = CompanionConfigDialog(parent)
    dialog.exec()
