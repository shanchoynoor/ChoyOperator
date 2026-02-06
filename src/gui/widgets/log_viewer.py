"""
Log Viewer Widget - Display application logs in real-time.
"""

from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QComboBox, QCheckBox
)
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtGui import QColor


class LogViewerWidget(QWidget):
    """Widget for displaying application logs."""
    
    LEVEL_COLORS = {
        "DEBUG": "#B0BEC5",
        "INFO": "#7CFFCB",
        "WARNING": "#FFE57F",
        "ERROR": "#FF8A65",
        "CRITICAL": "#E573FF",
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Header
        header_layout = QHBoxLayout()
        header = QLabel("📋 Logs")
        header.setStyleSheet("font-size: 16px; font-weight: bold;")
        header_layout.addWidget(header)
        
        header_layout.addStretch()
        
        # Filter
        self.level_filter = QComboBox()
        self.level_filter.addItems(["All", "INFO+", "WARNING+", "ERROR+"])
        self.level_filter.setCurrentIndex(1)  # INFO+ by default
        header_layout.addWidget(self.level_filter)
        
        layout.addLayout(header_layout)
        
        # Log display using QListWidget
        self.log_display = QListWidget()
        self.log_display.setStyleSheet("""
            QListWidget {
                background-color: #0d111a;
                color: #f5f5f5;
                font-family: 'SFMono-Regular', 'Consolas', 'Courier New', monospace;
                font-size: 11px;
                border: 1px solid #2a2f3a;
                border-radius: 6px;
                outline: none;
            }
            QListWidget::item {
                padding: 3px 6px;
                border-bottom: 1px solid #1e1e1e;
            }
        """)
        self.log_display.setWordWrap(True)
        layout.addWidget(self.log_display)
        
        # Bottom controls
        bottom_layout = QHBoxLayout()
        
        self.auto_scroll = QCheckBox("Auto-scroll")
        self.auto_scroll.setChecked(True)
        bottom_layout.addWidget(self.auto_scroll)
        
        bottom_layout.addStretch()
        
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.log_display.clear)
        bottom_layout.addWidget(clear_btn)
        
        layout.addLayout(bottom_layout)
    
    @pyqtSlot(str, str)
    def add_log(self, level: str, message: str):
        """
        Add a log entry to the display.
        
        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            message: Log message
        """
        # Check filter
        filter_idx = self.level_filter.currentIndex()
        levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        
        if filter_idx > 0:
            min_level = ["DEBUG", "INFO", "WARNING", "ERROR"][filter_idx]
            if levels.index(level) < levels.index(min_level):
                return
        
        # Format and add
        color = self.LEVEL_COLORS.get(level, "#ddd")
        
        # Get level icon
        icons = {
            "DEBUG": "🔍",
            "INFO": "ℹ️",
            "WARNING": "⚠️",
            "ERROR": "❌",
            "CRITICAL": "🔥",
        }
        icon = icons.get(level, "📝")
        
        # Create list item with HTML for proper color
        item_text = f"<span style='color: {color};'>{icon} {message}</span>"
        item = QListWidgetItem()
        item.setText(message)
        item.setData(Qt.UserRole, item_text)  # Store HTML
        
        # Set foreground color explicitly
        item.setForeground(QColor(color))
        
        # Ensure text is visible
        item.setFlags(item.flags() | Qt.ItemIsEnabled)
        
        self.log_display.addItem(item)
        
        # Set item text color via stylesheet on the item
        item.setData(Qt.ForegroundRole, QColor(color))
        
        # Auto-scroll
        if self.auto_scroll.isChecked():
            self.log_display.scrollToBottom()
