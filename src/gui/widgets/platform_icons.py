"""
Platform Icons - Social media platform icons using SVG files.

Provides QIcon for social media platforms.
"""

import os
from PyQt5.QtGui import QIcon, QPixmap, QColor, QPainter, QFont
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtCore import Qt, QRect

# Get the project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
ICONS_DIR = os.path.join(PROJECT_ROOT, "icons")

def get_platform_icon(platform: str, size: int = 16) -> QIcon:
    """
    Get QIcon for a social media platform.
    
    Args:
        platform: Platform name (facebook, x, linkedin, youtube, instagram)
        size: Icon size in pixels
        
    Returns:
        QIcon with the platform's logo (SVG-based with emoji fallback)
    """
    platform_lower = platform.lower()
    
    # Map platform names to icon filenames
    platform_icons = {
        "facebook": "facebook.svg",
        "x": "twitter-154.svg",  # Using twitter icon for X
        "twitter": "twitter-154.svg",  # Keep twitter mapping for backwards compatibility
        "linkedin": "linkedin-161.svg",
        "youtube": "youtube-play.svg",
        "instagram": "📷",  # Instagram still uses emoji as no SVG provided
    }
    
    icon_path = platform_icons.get(platform_lower)
    
    if icon_path and icon_path.endswith('.svg'):
        # Try to load SVG
        full_path = os.path.join(ICONS_DIR, icon_path)
        if os.path.exists(full_path):
            try:
                renderer = QSvgRenderer(full_path)
                pixmap = QPixmap(size, size)
                pixmap.fill(Qt.transparent)
                painter = QPainter(pixmap)
                renderer.render(painter)
                painter.end()
                return QIcon(pixmap)
            except Exception as e:
                print(f"Failed to load SVG icon {full_path}: {e}")
    
    # Fallback to emoji if SVG fails or not available
    platform_emojis = {
        "facebook": "📘",
        "x": "🐦",
        "twitter": "🐦",
        "linkedin": "💼",
        "youtube": "🎬",
        "instagram": "📷",
    }
    
    emoji = platform_emojis.get(platform_lower, "📱")
    
    # Create pixmap with emoji
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    
    # Draw emoji
    font = QFont("Apple Color Emoji", size - 2)
    painter.setFont(font)
    painter.drawText(QRect(0, 0, size, size), Qt.AlignCenter, emoji)
    painter.end()
    
    return QIcon(pixmap)

def get_platform_pixmap(platform: str, size: int = 16) -> QPixmap:
    """Get QPixmap for a platform."""
    icon = get_platform_icon(platform, size)
    return icon.pixmap(size, size)
