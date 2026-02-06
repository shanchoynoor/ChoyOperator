"""
Helpers - Utility functions for common operations.
"""

import re
import unicodedata
from datetime import datetime
from pathlib import Path

from src.core.llm_client import Platform


# Platform character limits
PLATFORM_LIMITS = {
    Platform.TWITTER: 280,
    Platform.FACEBOOK: 63206,
    Platform.LINKEDIN: 3000,
    Platform.YOUTUBE: 5000,
}


def validate_content_length(content: str, platform: Platform) -> tuple[bool, str]:
    """
    Validate content length for a platform.
    
    Args:
        content: Content to validate
        platform: Target platform
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    limit = PLATFORM_LIMITS.get(platform, 500)
    length = len(content)
    
    if length > limit:
        return False, f"Content exceeds {platform.value} limit ({length}/{limit} chars)"
    
    return True, ""


def extract_hashtags(content: str) -> list[str]:
    """
    Extract hashtags from content.
    
    Args:
        content: Text content
        
    Returns:
        List of hashtags (with # prefix)
    """
    pattern = r'#\w+'
    return re.findall(pattern, content)


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """
    Sanitize a string for use as a filename.
    
    Args:
        filename: Original filename
        max_length: Maximum length
        
    Returns:
        Sanitized filename
    """
    # Normalize unicode
    filename = unicodedata.normalize("NFKD", filename)
    
    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    
    # Replace spaces with underscores
    filename = filename.replace(' ', '_')
    
    # Truncate if too long
    if len(filename) > max_length:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        max_name = max_length - len(ext) - 1 if ext else max_length
        filename = f"{name[:max_name]}.{ext}" if ext else name[:max_length]
    
    return filename


def format_timestamp(dt: datetime | None = None, format_str: str = "%Y-%m-%d %H:%M") -> str:
    """
    Format a datetime for display.
    
    Args:
        dt: Datetime to format (defaults to now)
        format_str: Format string
        
    Returns:
        Formatted string
    """
    dt = dt or datetime.now()
    return dt.strftime(format_str)


def get_media_type(file_path: Path) -> str | None:
    """
    Determine media type from file extension.
    
    Args:
        file_path: Path to media file
        
    Returns:
        'image', 'video', or None
    """
    suffix = file_path.suffix.lower()
    
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
    video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}
    
    if suffix in image_extensions:
        return 'image'
    elif suffix in video_extensions:
        return 'video'
    
    return None


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate text to a maximum length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length including suffix
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def parse_schedule_time(time_str: str) -> datetime | None:
    """
    Parse various time string formats into datetime.
    
    Args:
        time_str: Time string (e.g., "2024-01-15 14:30", "tomorrow 9am")
        
    Returns:
        Parsed datetime or None
    """
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M",
        "%d/%m/%Y %H:%M",
        "%m/%d/%Y %H:%M",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(time_str, fmt)
        except ValueError:
            continue
    
    return None
