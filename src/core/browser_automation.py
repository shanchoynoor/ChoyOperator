"""
Browser Automation - Selenium WebDriver Management.

Provides base browser session handling, cookie persistence,
and common utilities for DOM interaction.
"""

import os
import sys
import json
import pickle
from pathlib import Path
from typing import Literal

# Hide console windows on Windows for subprocesses
if sys.platform == "win32":
    import subprocess
    # Set global environment to hide console windows for child processes
    CREATE_NO_WINDOW = 0x08000000
    # Monkey-patch Popen to hide console windows by default
    _original_popen = subprocess.Popen
    
    class NoWindowPopen(_original_popen):
        def __init__(self, *args, **kwargs):
            if 'creationflags' not in kwargs:
                kwargs['creationflags'] = CREATE_NO_WINDOW
            super().__init__(*args, **kwargs)
    
    subprocess.Popen = NoWindowPopen
    os.environ['WDM_LOG'] = '0'  # Suppress webdriver-manager logs

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager

from src.config import config, PROJECT_ROOT


BrowserType = Literal["chrome", "firefox"]


class BrowserManager:
    """
    Manages Selenium WebDriver instances and browser sessions.
    
    Handles driver initialization, session persistence, and cleanup.
    """
    
    COOKIES_DIR = PROJECT_ROOT / "data" / "cookies"
    SCREENSHOTS_DIR = PROJECT_ROOT / "data" / "screenshots"
    
    def __init__(self):
        self.driver: webdriver.Chrome | webdriver.Firefox | None = None
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Create required directories."""
        self.COOKIES_DIR.mkdir(parents=True, exist_ok=True)
        self.SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    
    def get_driver(
        self, 
        browser_type: BrowserType | None = None,
        headless: bool | None = None
    ) -> webdriver.Chrome | webdriver.Firefox:
        """
        Get or create a WebDriver instance.
        
        Args:
            browser_type: Browser to use (chrome/firefox). Defaults to config.
            headless: Run in headless mode. Defaults to config.
            
        Returns:
            WebDriver instance
        """
        if self.driver:
            return self.driver
        
        browser = browser_type or config.browser.browser_type
        is_headless = headless if headless is not None else config.browser.headless
        
        if browser == "chrome":
            self.driver = self._create_chrome_driver(is_headless)
        else:
            self.driver = self._create_firefox_driver(is_headless)
        
        self.driver.implicitly_wait(config.browser.implicit_wait)
        self.driver.set_page_load_timeout(config.browser.page_load_timeout)
        
        return self.driver
    
    def _create_chrome_driver(self, headless: bool) -> webdriver.Chrome:
        """Create Chrome WebDriver with options."""
        options = ChromeOptions()
        
        if headless:
            options.add_argument("--headless=new")
        
        # Common options
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-infobars")
        options.add_argument("--start-maximized")
        options.add_argument("--disable-notifications")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        # Mask automation detection
        driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        
        return driver
    
    def _create_firefox_driver(self, headless: bool) -> webdriver.Firefox:
        """Create Firefox WebDriver with options."""
        options = FirefoxOptions()
        
        if headless:
            options.add_argument("--headless")
        
        options.set_preference("dom.webdriver.enabled", False)
        options.set_preference("useAutomationExtension", False)
        
        service = FirefoxService(GeckoDriverManager().install())
        return webdriver.Firefox(service=service, options=options)
    
    def save_cookies(self, platform: str):
        """
        Save browser cookies for a platform.
        
        Args:
            platform: Platform name (facebook/twitter/linkedin)
        """
        if not self.driver:
            return
        
        cookies = self.driver.get_cookies()
        cookie_file = self.COOKIES_DIR / f"{platform}_cookies.pkl"
        
        with open(cookie_file, "wb") as f:
            pickle.dump(cookies, f)
    
    def load_cookies(self, platform: str, base_url: str) -> bool:
        """
        Load saved cookies for a platform.
        
        Args:
            platform: Platform name
            base_url: Base URL to navigate to before loading cookies
            
        Returns:
            True if cookies were loaded successfully
        """
        if not self.driver:
            return False
        
        cookie_file = self.COOKIES_DIR / f"{platform}_cookies.pkl"
        
        if not cookie_file.exists():
            return False
        
        try:
            # Navigate to domain first (required for cookie loading)
            self.driver.get(base_url)
            
            with open(cookie_file, "rb") as f:
                cookies = pickle.load(f)
            
            for cookie in cookies:
                # Remove problematic fields
                cookie.pop("sameSite", None)
                cookie.pop("expiry", None)
                try:
                    self.driver.add_cookie(cookie)
                except Exception:
                    pass  # Skip invalid cookies
            
            return True
            
        except Exception:
            return False
    
    def clear_cookies(self, platform: str | None = None):
        """
        Clear saved cookies.
        
        Args:
            platform: Specific platform, or None for all
        """
        if platform:
            cookie_file = self.COOKIES_DIR / f"{platform}_cookies.pkl"
            if cookie_file.exists():
                cookie_file.unlink()
        else:
            for cookie_file in self.COOKIES_DIR.glob("*_cookies.pkl"):
                cookie_file.unlink()
    
    def take_screenshot(self, name: str) -> Path:
        """
        Take a screenshot for debugging.
        
        Args:
            name: Screenshot identifier
            
        Returns:
            Path to saved screenshot
        """
        if not self.driver:
            raise RuntimeError("No active browser session")
        
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{timestamp}.png"
        filepath = self.SCREENSHOTS_DIR / filename
        
        self.driver.save_screenshot(str(filepath))
        return filepath
    
    def wait_for_element(
        self, 
        by: By, 
        value: str, 
        timeout: int = 10,
        clickable: bool = False
    ):
        """
        Wait for an element to be present/clickable.
        
        Args:
            by: Locator strategy (By.ID, By.CSS_SELECTOR, etc.)
            value: Locator value
            timeout: Max wait time in seconds
            clickable: Wait for element to be clickable
            
        Returns:
            The found element
            
        Raises:
            TimeoutException: If element not found within timeout
        """
        if not self.driver:
            raise RuntimeError("No active browser session")
        
        wait = WebDriverWait(self.driver, timeout)
        
        if clickable:
            condition = EC.element_to_be_clickable((by, value))
        else:
            condition = EC.presence_of_element_located((by, value))
        
        return wait.until(condition)
    
    def safe_click(self, by: By, value: str, timeout: int = 10):
        """
        Safely click an element with wait.
        
        Args:
            by: Locator strategy
            value: Locator value
            timeout: Max wait time
        """
        element = self.wait_for_element(by, value, timeout, clickable=True)
        element.click()
    
    def safe_send_keys(self, by: By, value: str, text: str, timeout: int = 10):
        """
        Safely type into an element with wait.
        
        Args:
            by: Locator strategy
            value: Locator value
            text: Text to type
            timeout: Max wait time
        """
        element = self.wait_for_element(by, value, timeout)
        element.clear()
        element.send_keys(text)
    
    def close(self):
        """Close the browser and cleanup."""
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            finally:
                self.driver = None
    
    def __enter__(self):
        return self.get_driver()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Global browser manager
_browser_manager: BrowserManager | None = None


def get_browser_manager() -> BrowserManager:
    """Get or create the browser manager instance."""
    global _browser_manager
    if _browser_manager is None:
        _browser_manager = BrowserManager()
    return _browser_manager
