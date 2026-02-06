"""
Settings Dialog - Configure application settings.
"""

from pathlib import Path

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QTabWidget,
    QWidget, QLineEdit, QPushButton, QLabel, QCheckBox,
    QFileDialog, QMessageBox, QComboBox, QGroupBox, QSpinBox
)
from PyQt5.QtCore import Qt

from src.config import config, PROJECT_ROOT
from src.utils.logger import get_logger


logger = get_logger(__name__)


class SettingsDialog(QDialog):
    """Application settings dialog."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(500)
        self._init_ui()
        self._load_settings()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # Tab widget
        tabs = QTabWidget()
        
        # API Settings tab
        api_tab = QWidget()
        api_layout = QFormLayout(api_tab)
        
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setPlaceholderText("sk-or-v1-...")
        api_layout.addRow("OpenRouter API Key:", self.api_key_input)
        
        self.show_key = QCheckBox("Show key")
        self.show_key.toggled.connect(self._toggle_key_visibility)
        api_layout.addRow("", self.show_key)
        
        self.model_input = QComboBox()
        self.model_input.addItems([
            "anthropic/claude-3.5-sonnet",
            "anthropic/claude-3-opus",
            "anthropic/claude-3-haiku",
            "openai/gpt-4-turbo",
            "openai/gpt-3.5-turbo",
        ])
        self.model_input.setEditable(True)
        api_layout.addRow("LLM Model:", self.model_input)
        
        tabs.addTab(api_tab, "API")
        
        # Browser Settings tab
        browser_tab = QWidget()
        browser_layout = QFormLayout(browser_tab)
        
        self.browser_type = QComboBox()
        self.browser_type.addItems(["brave", "chrome", "edge", "firefox"])
        browser_layout.addRow("Browser:", self.browser_type)
        
        self.headless = QCheckBox("Run in background (headless)")
        browser_layout.addRow("", self.headless)
        
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(10, 120)
        self.timeout_spin.setValue(30)
        self.timeout_spin.setSuffix(" seconds")
        browser_layout.addRow("Page Timeout:", self.timeout_spin)
        
        tabs.addTab(browser_tab, "Browser")
        
        # Folder Watch tab
        folder_tab = QWidget()
        folder_layout = QVBoxLayout(folder_tab)
        
        watch_group = QGroupBox("Auto-Schedule Folder")
        watch_layout = QFormLayout(watch_group)
        
        folder_row = QHBoxLayout()
        self.watch_folder_input = QLineEdit()
        self.watch_folder_input.setPlaceholderText("Select folder to watch...")
        folder_row.addWidget(self.watch_folder_input)
        
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self._browse_folder)
        folder_row.addWidget(browse_btn)
        
        watch_layout.addRow("Folder:", folder_row)
        
        self.auto_generate = QCheckBox("Auto-generate content for new files")
        watch_layout.addRow("", self.auto_generate)
        
        self.default_delay = QSpinBox()
        self.default_delay.setRange(1, 168)  # 1 hour to 1 week
        self.default_delay.setValue(1)
        self.default_delay.setSuffix(" hour(s)")
        watch_layout.addRow("Default schedule delay:", self.default_delay)
        
        folder_layout.addWidget(watch_group)
        folder_layout.addStretch()
        
        tabs.addTab(folder_tab, "Folder Watch")
        
        # General tab
        general_tab = QWidget()
        general_layout = QFormLayout(general_tab)
        
        self.log_level = QComboBox()
        self.log_level.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        self.log_level.setCurrentIndex(1)
        general_layout.addRow("Log Level:", self.log_level)
        
        self.start_minimized = QCheckBox("Start minimized to tray")
        general_layout.addRow("", self.start_minimized)
        
        tabs.addTab(general_tab, "General")
        
        layout.addWidget(tabs)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save_settings)
        save_btn.setDefault(True)
        btn_layout.addWidget(save_btn)
        
        layout.addLayout(btn_layout)
    
    def _toggle_key_visibility(self, checked: bool):
        mode = QLineEdit.Normal if checked else QLineEdit.Password
        self.api_key_input.setEchoMode(mode)
    
    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Watch Folder")
        if folder:
            self.watch_folder_input.setText(folder)
    
    def _load_settings(self):
        """Load current settings into the UI."""
        # API
        if config.llm.api_key:
            self.api_key_input.setText(config.llm.api_key)
        self.model_input.setCurrentText(config.llm.model)
        
        # Browser
        browser_map = {"brave": 0, "chrome": 1, "edge": 2, "firefox": 3}
        browser = getattr(config.browser, 'browser_type', 'brave').lower()
        idx = browser_map.get(browser, 0)
        self.browser_type.setCurrentIndex(idx)
        self.headless.setChecked(config.browser.headless)
        self.timeout_spin.setValue(config.browser.page_load_timeout)
        
        # Logging
        levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
        if config.logging.level in levels:
            self.log_level.setCurrentIndex(levels.index(config.logging.level))
    
    def _save_settings(self):
        """Save settings to .env file."""
        env_path = PROJECT_ROOT / ".env"
        
        # Read existing .env or create new
        env_content = {}
        if env_path.exists():
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_content[key.strip()] = value.strip()
        
        # Update values
        api_key = self.api_key_input.text().strip()
        if api_key:
            env_content["OPENROUTER_API_KEY"] = api_key
        
        env_content["LLM_MODEL"] = self.model_input.currentText()
        env_content["BROWSER_TYPE"] = self.browser_type.currentText()
        env_content["BROWSER_HEADLESS"] = "true" if self.headless.isChecked() else "false"
        env_content["LOG_LEVEL"] = self.log_level.currentText()
        
        watch_folder = self.watch_folder_input.text().strip()
        if watch_folder:
            env_content["WATCH_FOLDER"] = watch_folder
        
        # Write back
        with open(env_path, 'w') as f:
            for key, value in env_content.items():
                f.write(f"{key}={value}\n")
        
        logger.info("Settings saved")
        QMessageBox.information(
            self, 
            "Settings Saved", 
            "Settings saved. Some changes may require restarting the application."
        )
        self.accept()
