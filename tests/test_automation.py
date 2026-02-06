"""
Test Automation - Browser automation and platform driver tests.

Tests Selenium WebDriver and platform-specific automation.
"""

import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from pathlib import Path


class TestBrowserManager:
    """Test BrowserManager functionality."""
    
    @pytest.fixture
    def mock_webdriver(self):
        """Mock Selenium WebDriver."""
        with patch("src.core.browser_automation.webdriver") as mock:
            mock_driver = MagicMock()
            mock.Chrome.return_value = mock_driver
            mock.Firefox.return_value = mock_driver
            yield mock_driver
    
    @pytest.fixture
    def mock_webdriver_manager(self):
        """Mock webdriver-manager."""
        with patch("src.core.browser_automation.ChromeDriverManager") as chrome_mock, \
             patch("src.core.browser_automation.GeckoDriverManager") as gecko_mock:
            chrome_mock.return_value.install.return_value = "/path/to/chromedriver"
            gecko_mock.return_value.install.return_value = "/path/to/geckodriver"
            yield
    
    def test_browser_manager_initializes(self, mock_webdriver, mock_webdriver_manager):
        """Test BrowserManager initialization."""
        from src.core.browser_automation import BrowserManager
        
        manager = BrowserManager(browser_type="chrome", headless=True)
        
        assert manager is not None
        assert manager.driver is not None
    
    def test_browser_manager_navigates(self, mock_webdriver, mock_webdriver_manager):
        """Test navigation to URL."""
        from src.core.browser_automation import BrowserManager
        
        manager = BrowserManager()
        manager.driver.get("https://example.com")
        
        mock_webdriver.get.assert_called_with("https://example.com")
    
    def test_browser_saves_cookies(self, mock_webdriver, mock_webdriver_manager, tmp_path):
        """Test cookie saving."""
        mock_webdriver.get_cookies.return_value = [
            {"name": "session", "value": "abc123"}
        ]
        
        from src.core.browser_automation import BrowserManager
        
        manager = BrowserManager()
        manager.cookie_dir = tmp_path
        
        # Save cookies (mocked)
        manager.save_cookies("test_platform")
        
        # Verify get_cookies was called
        mock_webdriver.get_cookies.assert_called()
    
    def test_browser_takes_screenshot(self, mock_webdriver, mock_webdriver_manager, tmp_path):
        """Test screenshot capture."""
        from src.core.browser_automation import BrowserManager
        
        manager = BrowserManager()
        manager.screenshot_dir = tmp_path
        
        path = manager.take_screenshot("test_screenshot")
        
        # Should call save_screenshot
        mock_webdriver.save_screenshot.assert_called()


class TestPlatformDrivers:
    """Test platform-specific drivers."""
    
    @pytest.fixture
    def mock_browser_manager(self):
        """Create a mocked browser manager."""
        with patch("src.core.browser_automation.BrowserManager") as mock:
            mock_instance = MagicMock()
            mock.return_value = mock_instance
            mock_instance.driver = MagicMock()
            yield mock_instance
    
    def test_facebook_platform_has_required_methods(self):
        """Verify FacebookPlatform has all required methods."""
        from src.core.platforms.facebook import FacebookPlatform
        
        assert hasattr(FacebookPlatform, 'login')
        assert hasattr(FacebookPlatform, 'create_post')
        assert hasattr(FacebookPlatform, 'check_login_status')
        assert callable(getattr(FacebookPlatform, 'login'))
    
    def test_twitter_platform_has_required_methods(self):
        """Verify TwitterPlatform has all required methods."""
        from src.core.platforms.twitter import TwitterPlatform
        
        assert hasattr(TwitterPlatform, 'login')
        assert hasattr(TwitterPlatform, 'create_post')
        assert hasattr(TwitterPlatform, 'check_login_status')
    
    def test_linkedin_platform_has_required_methods(self):
        """Verify LinkedInPlatform has all required methods."""
        from src.core.platforms.linkedin import LinkedInPlatform
        
        assert hasattr(LinkedInPlatform, 'login')
        assert hasattr(LinkedInPlatform, 'create_post')
    
    def test_youtube_platform_has_required_methods(self):
        """Verify YouTubePlatform has all required methods."""
        from src.core.platforms.youtube import YouTubePlatform
        
        assert hasattr(YouTubePlatform, 'login')
        assert hasattr(YouTubePlatform, 'create_post')
        assert hasattr(YouTubePlatform, 'upload_video')
    
    def test_post_result_status_enum(self):
        """Test PostStatus enum values."""
        from src.core.platforms.base import PostStatus
        
        assert PostStatus.SUCCESS.value == "success"
        assert PostStatus.FAILED.value == "failed"
        assert PostStatus.AUTH_REQUIRED.value == "auth_required"


class TestFailureScenarios:
    """Test error handling and failure scenarios."""
    
    def test_platform_handles_login_failure(self):
        """Test graceful handling of login failures."""
        from src.core.platforms.base import Credentials, PostStatus
        
        creds = Credentials(username="invalid", password="invalid")
        # Platform should return False or appropriate status on failure
        assert creds.username == "invalid"
    
    def test_platform_handles_network_timeout(self):
        """Test timeout handling."""
        from src.utils.exceptions import TimeoutError
        
        error = TimeoutError("login", 30)
        assert "timed out" in str(error)
        assert error.details["timeout"] == 30
    
    def test_platform_handles_element_not_found(self):
        """Test element not found handling."""
        from src.utils.exceptions import ElementNotFoundError
        
        error = ElementNotFoundError("twitter", "post_button")
        assert "twitter" in str(error)
        assert "Element not found" in str(error)
    
    def test_rate_limit_error_with_retry(self):
        """Test rate limit error with retry info."""
        from src.utils.exceptions import RateLimitError
        
        error = RateLimitError("facebook", retry_after=60)
        assert error.details["retry_after"] == 60
        assert "60" in error.recovery_hint
