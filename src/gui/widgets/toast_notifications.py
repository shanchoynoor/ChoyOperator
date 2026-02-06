"""
Toast Notifications - Bottom-right popup notifications.

Provides non-intrusive notifications for success, error, and info messages.
"""

from PyQt5.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, 
    QPushButton, QGraphicsOpacityEffect, QApplication
)
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, pyqtSignal
from PyQt5.QtGui import QFont
from enum import Enum


class ToastType(Enum):
    """Toast notification types."""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class Toast(QWidget):
    """Single toast notification widget."""
    
    closed = pyqtSignal()
    
    COLORS = {
        ToastType.SUCCESS: ("#059669", "#d1fae5"),
        ToastType.ERROR: ("#dc2626", "#fee2e2"),
        ToastType.WARNING: ("#d97706", "#fef3c7"),
        ToastType.INFO: ("#2563eb", "#dbeafe"),
    }
    
    ICONS = {
        ToastType.SUCCESS: "✓",
        ToastType.ERROR: "✗",
        ToastType.WARNING: "⚠",
        ToastType.INFO: "ℹ",
    }
    
    def __init__(
        self, 
        title: str, 
        message: str, 
        toast_type: ToastType = ToastType.INFO,
        duration: int = 5000,
        parent=None
    ):
        super().__init__(parent)
        
        self.duration = duration
        self.toast_type = toast_type
        
        self.setWindowFlags(
            Qt.FramelessWindowHint | 
            Qt.WindowStaysOnTopHint | 
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        
        self._setup_ui(title, message)
        self._setup_animation()
    
    def _setup_ui(self, title: str, message: str):
        """Set up the toast UI."""
        bg_color, _ = self.COLORS[self.toast_type]
        icon = self.ICONS[self.toast_type]
        
        container = QWidget()
        container.setStyleSheet(f"""
            QWidget {{
                background: #1e293b;
                border-radius: 8px;
                border-left: 4px solid {bg_color};
            }}
        """)
        
        layout = QHBoxLayout(container)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        
        icon_label = QLabel(icon)
        icon_label.setFont(QFont("", 18))
        icon_label.setStyleSheet(f"color: {bg_color};")
        layout.addWidget(icon_label)
        
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)
        
        title_label = QLabel(title)
        title_label.setFont(QFont("", 11, QFont.Bold))
        title_label.setStyleSheet("color: #f1f5f9;")
        text_layout.addWidget(title_label)
        
        if message:
            msg_label = QLabel(message)
            msg_label.setFont(QFont("", 10))
            msg_label.setStyleSheet("color: #94a3b8;")
            msg_label.setWordWrap(True)
            msg_label.setMaximumWidth(250)
            text_layout.addWidget(msg_label)
        
        layout.addLayout(text_layout)
        layout.addStretch()
        
        close_btn = QPushButton("×")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet("""
            QPushButton { background: transparent; color: #64748b; font-size: 16px; border: none; }
            QPushButton:hover { color: #f1f5f9; }
        """)
        close_btn.clicked.connect(self.close_toast)
        layout.addWidget(close_btn, alignment=Qt.AlignTop)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(container)
        
        self.setFixedWidth(320)
    
    def _setup_animation(self):
        """Set up fade animation."""
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        
        self.fade_in = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_in.setDuration(200)
        self.fade_in.setStartValue(0)
        self.fade_in.setEndValue(1)
        
        self.fade_out = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_out.setDuration(300)
        self.fade_out.setStartValue(1)
        self.fade_out.setEndValue(0)
        self.fade_out.finished.connect(self._on_fade_out_finished)
    
    def show_toast(self):
        """Show the toast with animation."""
        self.show()
        self.fade_in.start()
        
        if self.duration > 0:
            QTimer.singleShot(self.duration, self.close_toast)
    
    def close_toast(self):
        """Close the toast with animation."""
        self.fade_out.start()
    
    def _on_fade_out_finished(self):
        """Handle fade out completion."""
        self.closed.emit()
        self.close()
        self.deleteLater()


class ToastManager:
    """
    Manages toast notifications in bottom-right corner.
    Simple class (not QWidget) to avoid singleton issues.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.toasts = []
            cls._instance.margin = 20
            cls._instance.spacing = 10
        return cls._instance
    
    def show_toast(
        self,
        title: str,
        message: str = "",
        toast_type: ToastType = ToastType.INFO,
        duration: int = 5000,
    ):
        """Show a toast notification."""
        try:
            toast = Toast(title, message, toast_type, duration)
            toast.closed.connect(lambda: self._remove_toast(toast))
            
            self.toasts.append(toast)
            self._position_toasts()
            toast.show_toast()
        except Exception as e:
            print(f"Toast error: {e}")
    
    def success(self, title: str, message: str = ""):
        """Show success toast."""
        self.show_toast(title, message, ToastType.SUCCESS)
    
    def error(self, title: str, message: str = ""):
        """Show error toast."""
        self.show_toast(title, message, ToastType.ERROR, duration=8000)
    
    def warning(self, title: str, message: str = ""):
        """Show warning toast."""
        self.show_toast(title, message, ToastType.WARNING)
    
    def info(self, title: str, message: str = ""):
        """Show info toast."""
        self.show_toast(title, message, ToastType.INFO)
    
    def _remove_toast(self, toast: Toast):
        """Remove toast and reposition remaining."""
        if toast in self.toasts:
            self.toasts.remove(toast)
            self._position_toasts()
    
    def _position_toasts(self):
        """Position all toasts in bottom-right corner."""
        try:
            screen = QApplication.primaryScreen()
            if not screen:
                return
            
            geom = screen.availableGeometry()
            y_offset = self.margin
            
            for toast in reversed(self.toasts):
                toast.adjustSize()
                
                x = geom.right() - toast.width() - self.margin
                y = geom.bottom() - toast.height() - y_offset
                
                toast.move(x, y)
                y_offset += toast.height() + self.spacing
        except Exception:
            pass


# Global toast manager
_toast_manager: ToastManager | None = None


def get_toast_manager() -> ToastManager:
    """Get or create the global toast manager."""
    global _toast_manager
    if _toast_manager is None:
        _toast_manager = ToastManager()
    return _toast_manager


def toast_success(title: str, message: str = ""):
    """Show success toast notification."""
    try:
        get_toast_manager().success(title, message)
    except Exception:
        pass


def toast_error(title: str, message: str = ""):
    """Show error toast notification."""
    try:
        get_toast_manager().error(title, message)
    except Exception:
        pass


def toast_warning(title: str, message: str = ""):
    """Show warning toast notification."""
    try:
        get_toast_manager().warning(title, message)
    except Exception:
        pass


def toast_info(title: str, message: str = ""):
    """Show info toast notification."""
    try:
        get_toast_manager().info(title, message)
    except Exception:
        pass
