"""
Log Viewer Widget - Display application logs in real-time.
"""

from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QLabel, QComboBox, QCheckBox
)
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtGui import QTextCursor, QColor


class LogViewerWidget(QWidget):
    """Widget for displaying application logs."""
    
    LEVEL_COLORS = {
        "DEBUG": "#888888",
        "INFO": "#4CAF50",
        "WARNING": "#FF9800",
        "ERROR": "#F44336",
        "CRITICAL": "#9C27B0",
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
    
    def _init_ui(self):
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
        
        # Log display
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setFont(self.font())
        self.log_display.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a1a;
                color: #ddd;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
                border: 1px solid #333;
                border-radius: 5px;
            }
        """)
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
        
        html = f'<span style="color: {color}">{icon} {message}</span><br>'
        
        cursor = self.log_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.log_display.setTextCursor(cursor)
        self.log_display.insertHtml(html)
        
        # Auto-scroll
        if self.auto_scroll.isChecked():
            scrollbar = self.log_display.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
