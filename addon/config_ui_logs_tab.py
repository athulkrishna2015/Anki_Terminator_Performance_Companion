# addon/config_ui_logs_tab.py
from aqt.qt import *
from .logger import companion_logger

class LogsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        companion_logger.register_callback(self.on_log_added)
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
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

    def disconnect_logger(self):
        companion_logger.unregister_callback(self.on_log_added)
