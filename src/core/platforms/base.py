"""
Base Platform - Abstract interface for social media automation.

All platform-specific drivers must implement this interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path

from selenium.webdriver.remote.webdriver import WebDriver

from src.core.browser_automation import BrowserManager, get_browser_manager


class PostStatus(Enum):
    """Status of a post operation."""
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"
    CAPTCHA_REQUIRED = "captcha_required"
    AUTH_REQUIRED = "auth_required"


@dataclass
class Credentials:
    """Platform login credentials."""
    username: str
    password: str
    two_factor_secret: str | None = None


@dataclass
class PostResult:
    """Result of a post operation."""
    status: PostStatus
    message: str
    post_url: str | None = None
    screenshot_path: Path | None = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class BasePlatform(ABC):
    """
    Abstract base class for social media platform automation.
    
    All platform drivers (Facebook, Twitter, LinkedIn) must implement
    this interface for consistent automation behavior.
    """
    
    # Platform identification
    PLATFORM_NAME: str = "base"
    BASE_URL: str = ""
    LOGIN_URL: str = ""
    
    # Character limits
    MAX_POST_LENGTH: int = 500
    MAX_HASHTAGS: int = 10
    
    def __init__(self, browser_manager: BrowserManager | None = None):
        """
        Initialize platform driver.
        
        Args:
            browser_manager: Optional browser manager instance
        """
        self.browser = browser_manager or get_browser_manager()
        self._logged_in = False
    
    @property
    def driver(self) -> WebDriver:
        """Get the WebDriver instance."""
        return self.browser.get_driver()
    
    @property
    def is_logged_in(self) -> bool:
        """Check if currently logged in."""
        return self._logged_in
    
    @abstractmethod
    def login(self, credentials: Credentials) -> bool:
        """
        Log in to the platform.
        
        Args:
            credentials: Login credentials
            
        Returns:
            True if login successful
        """
        pass
    
    @abstractmethod
    def check_login_status(self) -> bool:
        """
        Check if currently logged in to the platform.
        
        Returns:
            True if logged in
        """
        pass
    
    @abstractmethod
    def create_post(
        self, 
        content: str, 
        media_paths: list[Path] | None = None
    ) -> PostResult:
        """
        Create a new post on the platform.
        
        Args:
            content: Post text content
            media_paths: Optional list of media files to attach
            
        Returns:
            PostResult with operation status
        """
        pass
    
    @abstractmethod
    def navigate_to_post_page(self):
        """Navigate to the page where posts are created."""
        pass
    
    def try_restore_session(self) -> bool:
        """
        Try to restore a previous session using saved cookies.
        
        Returns:
            True if session was restored successfully
        """
        loaded = self.browser.load_cookies(self.PLATFORM_NAME, self.BASE_URL)
        
        if loaded:
            # Refresh and check if actually logged in
            self.driver.get(self.BASE_URL)
            if self.check_login_status():
                self._logged_in = True
                return True
        
        return False
    
    def save_session(self):
        """Save current session cookies for later restoration."""
        if self._logged_in:
            self.browser.save_cookies(self.PLATFORM_NAME)
    
    def logout(self):
        """Clear session and logout state."""
        self._logged_in = False
        self.browser.clear_cookies(self.PLATFORM_NAME)
    
    def get_status(self) -> dict:
        """
        Get current platform status.
        
        Returns:
            Dict with platform status information
        """
        return {
            "platform": self.PLATFORM_NAME,
            "logged_in": self._logged_in,
            "base_url": self.BASE_URL,
        }
    
    def take_screenshot(self, name: str = "debug") -> Path:
        """Take a debug screenshot."""
        return self.browser.take_screenshot(f"{self.PLATFORM_NAME}_{name}")
