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

        self.add_to_new_card_chk = QCheckBox("Enable 'Add to New Card' (Context Menu & Toolbar)")
        self.add_to_new_card_chk.setChecked(self.config.get("enable_add_to_new_card", True))
        self.add_to_new_card_chk.setToolTip("Adds a shortcut to create a new Anki card from the sidebar selection via right-click.")

        self.progress_bar_chk = QCheckBox("Enable Sleek Progress Bar")
        self.progress_bar_chk.setChecked(self.config.get("enable_progress_bar", True))
        self.progress_bar_chk.setToolTip("Shows a thin blue progress bar at the top of the sidebar while pages are loading.")

        self.persistent_view_chk = QCheckBox("Enable Persistent View (Flicker-Free Transitions)")
        self.persistent_view_chk.setChecked(self.config.get("enable_persistent_view", True))
        self.persistent_view_chk.setToolTip("Keeps the current page visible until the new one is fully loaded, preventing white/blank screens during navigation.")

        # Toolbar Settings
        self.toolbar_group = QGroupBox("Toolbar Settings")
        toolbar_layout = QVBoxLayout(self.toolbar_group)

        self.show_wiki_chk = QCheckBox("Show 'Wiki' (?) Button")
        self.show_wiki_chk.setChecked(self.config.get("show_wiki_button", True))
        
        self.show_donate_chk = QCheckBox("Show 'Donate' (💖) Button")
        self.show_donate_chk.setChecked(self.config.get("show_donate_button", True))

        toolbar_layout.addWidget(self.show_wiki_chk)
        toolbar_layout.addWidget(self.show_donate_chk)

        # Search Engine Configuration
        self.search_group = QGroupBox("Search & Address Bar Settings")
        search_layout = QFormLayout(self.search_group)

        self.search_engine_combo = QComboBox()
        self.search_engine_combo.addItems(["Google", "DuckDuckGo", "Bing", "Custom"])
        self.search_engine_combo.setCurrentText(self.config.get("search_engine", "Google"))
        
        self.custom_search_edit = QLineEdit()
        self.custom_search_edit.setText(self.config.get("custom_search_url", "https://www.google.com/search?q="))
        self.custom_search_edit.setPlaceholderText("e.g., https://example.com/search?q=")
        self.custom_search_edit.setEnabled(self.search_engine_combo.currentText() == "Custom")
        
        self.search_engine_combo.currentTextChanged.connect(self._on_search_engine_changed)

        search_layout.addRow("Search Engine:", self.search_engine_combo)
        search_layout.addRow("Search URL / Template:", self.custom_search_edit)

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
        group_layout.addWidget(self.add_to_new_card_chk)
        group_layout.addWidget(self.progress_bar_chk)
        group_layout.addWidget(self.persistent_view_chk)
        group_layout.addWidget(self.send_multiple_chk)
        
        layout.addWidget(self.group)
        layout.addWidget(self.toolbar_group)
        layout.addWidget(self.search_group)
        
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

    def _on_search_engine_changed(self, text):
        self.custom_search_edit.setEnabled(text == "Custom")
        if text == "Google":
            self.custom_search_edit.setText("https://www.google.com/search?q=")
        elif text == "DuckDuckGo":
            self.custom_search_edit.setText("https://duckduckgo.com/?q=")
        elif text == "Bing":
            self.custom_search_edit.setText("https://www.bing.com/search?q=")

    def get_settings(self):
        return {
            "enable_lifecycle_freezing": self.lifecycle_chk.isChecked(),
            "enable_adblocker_optimization": self.adblocker_chk.isChecked(),
            "enable_css_optimization": self.css_chk.isChecked(),
            "enable_html_cleanup": self.html_cleanup_chk.isChecked(),
            "enable_ai_hints_optimization": self.ai_hints_opt_chk.isChecked(),
            "enable_right_click_hints_preservation": self.right_click_hints_chk.isChecked(),
            "enable_add_to_new_card": self.add_to_new_card_chk.isChecked(),
            "enable_progress_bar": self.progress_bar_chk.isChecked(),
            "enable_persistent_view": self.persistent_view_chk.isChecked(),
            "show_wiki_button": self.show_wiki_chk.isChecked(),
            "show_donate_button": self.show_donate_chk.isChecked(),
            "search_engine": self.search_engine_combo.currentText(),
            "custom_search_url": self.custom_search_edit.text(),
            "thaw_duration_seconds": self.thaw_sb.value(),
            "send_multiple_fields": self.send_multiple_chk.isChecked()
        }
