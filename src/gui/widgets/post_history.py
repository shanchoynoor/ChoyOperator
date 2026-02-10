"""
Post History Widget - Shows list of posted content with timestamps.

Displays recent posts with platform icons and timestamps in a compact list.
"""

import json
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QListWidgetItem,
    QLabel, QHBoxLayout
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from src.config import PROJECT_ROOT
from src.utils.logger import get_logger


logger = get_logger(__name__)


@dataclass
class PostRecord:
    """Record of a posted content."""
    platform: str
    content: str
    posted_at: datetime
    status: str = "success"  # success, failed
    
    def to_dict(self) -> dict:
        return {
            "platform": self.platform,
            "content": self.content,
            "posted_at": self.posted_at.isoformat(),
            "status": self.status,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "PostRecord":
        return cls(
            platform=data["platform"],
            content=data["content"],
            posted_at=datetime.fromisoformat(data["posted_at"]),
            status=data.get("status", "success"),
        )


class PostHistoryManager:
    """Manages post history storage."""
    
    HISTORY_FILE = PROJECT_ROOT / "data" / "post_history.json"
    MAX_RECORDS = 100
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.records = []
            cls._instance._load()
        return cls._instance
    
    def _load(self):
        """Load history from file."""
        if not self.HISTORY_FILE.exists():
            return
        
        try:
            data = json.loads(self.HISTORY_FILE.read_text())
            self.records = [PostRecord.from_dict(r) for r in data]
            logger.info(f"Loaded {len(self.records)} post records")
        except Exception as e:
            logger.error(f"Failed to load post history: {e}")
    
    def _save(self):
        """Save history to file."""
        try:
            self.HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = [r.to_dict() for r in self.records]
            self.HISTORY_FILE.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Failed to save post history: {e}")
    
    def add_post(self, platform: str, content: str, status: str = "success") -> PostRecord:
        """Add a new post record."""
        record = PostRecord(
            platform=platform,
            content=content,
            posted_at=datetime.now(),
            status=status,
        )
        
        self.records.insert(0, record)
        
        # Keep only recent records
        if len(self.records) > self.MAX_RECORDS:
            self.records = self.records[:self.MAX_RECORDS]
        
        self._save()
        return record
    
    def get_recent(self, limit: int = 20) -> list[PostRecord]:
        """Get recent posts."""
        return self.records[:limit]
    
    def clear(self):
        """Clear all history."""
        self.records = []
        self._save()


def get_post_history() -> PostHistoryManager:
    """Get the post history manager."""
    return PostHistoryManager()


PLATFORM_ICONS = {
    "facebook": "📘",
    "twitter": "🐦",
    "linkedin": "💼",
    "youtube": "🎬",
}


class PostItemWidget(QWidget):
    """Custom widget for post history items - compact single-line design."""
    def __init__(self, record, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(4)
        
        # Platform icon
        icon = PLATFORM_ICONS.get(record.platform.lower(), "📱")
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 12px; background: transparent;")
        layout.addWidget(icon_label)
        
        # Content (truncated)
        content_preview = record.content[:20] + ("..." if len(record.content) > 20 else "")
        content_label = QLabel(content_preview)
        content_label.setStyleSheet("font-weight: bold; color: #f8fafc; font-size: 10px; background: transparent;")
        content_label.setWordWrap(False)
        layout.addWidget(content_label, stretch=1)
        
        # Time and date (12hr format with AM/PM and date)
        today = datetime.now().date()
        post_date = record.posted_at.date()
        
        if post_date == today:
            # Show only time for today's posts
            time_str = record.posted_at.strftime("%I:%M %p")
        else:
            # Show date and time for older posts
            time_str = record.posted_at.strftime("%b %d, %Y")
        
        time_label = QLabel(time_str)
        time_label.setStyleSheet("font-size: 9px; color: #64748b; background: transparent;")
        layout.addWidget(time_label)
        
        # Status icon
        status_icon = "✓" if record.status == "success" else "✗"
        status_color = "#22c55e" if record.status == "success" else "#ef4444"
        
        info_label = QLabel(f"<span style='color: {status_color};'>{status_icon}</span>")
        info_label.setStyleSheet("font-size: 10px; background: transparent;")
        layout.addWidget(info_label)
        
        self.setFixedHeight(26)
        self.setStyleSheet("background: transparent;")

class PostHistoryWidget(QWidget):
    """Widget showing recent post history."""
    
    post_clicked = pyqtSignal(object)  # Emits PostRecord
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.history = get_post_history()
        self._init_ui()
        self.refresh()
    
    def _init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        # Header
        header = QLabel("📋 Recent Posts")
        header.setStyleSheet("font-size: 14px; font-weight: bold; color: #f1f5f9;")
        layout.addWidget(header)
        
        # Post list
        self.post_list = QListWidget()
        self.post_list.setStyleSheet("""
            QListWidget {
                background: #0f172a;
                border: 1px solid #1e293b;
                border-radius: 8px;
                padding: 4px;
            }
            QListWidget::item {
                border-bottom: 1px solid #1e293b;
                min-height: 28px;
                padding: 1px 2px;
            }
            QListWidget::item:selected {
                background: #1e293b;
                border: 1px solid #3b82f6;
                border-radius: 4px;
            }
            QListWidget::item:hover {
                background: #1e293b;
            }
        """)
        self.post_list.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.post_list)
    
    def refresh(self):
        """Refresh the post list."""
        self.post_list.clear()
        
        records = self.history.get_recent(15)
        
        if not records:
            item = QListWidgetItem("No posts yet")
            item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
            item.setForeground(Qt.gray)
            self.post_list.addItem(item)
            return
        
        for record in records:
            item = QListWidgetItem(self.post_list)
            item.setData(Qt.UserRole, record)
            
            # Use custom widget - size calculated automatically
            widget = PostItemWidget(record)
            
            self.post_list.addItem(item)
            self.post_list.setItemWidget(item, widget)
            item.setSizeHint(widget.sizeHint())
    
    def _on_item_clicked(self, item: QListWidgetItem):
        """Handle item click."""
        record = item.data(Qt.UserRole)
        if record:
            self.post_clicked.emit(record)
    
    def add_post(self, platform: str, content: str, status: str = "success"):
        """Add a new post and refresh."""
        self.history.add_post(platform, content, status)
        self.refresh()
