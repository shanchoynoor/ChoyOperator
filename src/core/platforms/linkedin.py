"""
LinkedIn Platform - Automation driver for LinkedIn.

Handles login, post creation, and navigation on LinkedIn.
"""

import time
from pathlib import Path

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from src.core.platforms.base import (
    BasePlatform, 
    Credentials, 
    PostResult, 
    PostStatus
)


class LinkedInPlatform(BasePlatform):
    """LinkedIn automation driver."""
    
    PLATFORM_NAME = "linkedin"
    BASE_URL = "https://www.linkedin.com"
    LOGIN_URL = "https://www.linkedin.com/login"
    
    MAX_POST_LENGTH = 3000
    MAX_HASHTAGS = 30
    
    # Selectors
    SELECTORS = {
        "username_input": "#username",
        "password_input": "#password",
        "login_button": 'button[type="submit"]',
        "start_post_button": ".share-box-feed-entry__trigger",
        "start_post_alt": '[data-test-app-aware-link="Start a post"]',
        "post_editor": ".ql-editor",
        "post_button": ".share-actions__primary-action",
        "feed_container": ".scaffold-layout__main",
        "profile_icon": ".feed-identity-module",
    }
    
    def login(self, credentials: Credentials) -> bool:
        """
        Log in to LinkedIn.
        
        Args:
            credentials: LinkedIn login credentials
            
        Returns:
            True if login successful
        """
        try:
            # First try to restore existing session
            if self.try_restore_session():
                return True
            
            # Navigate to login page
            self.driver.get(self.LOGIN_URL)
            time.sleep(2)
            
            # Enter email
            email_field = self.browser.wait_for_element(
                By.CSS_SELECTOR,
                self.SELECTORS["username_input"],
                timeout=10
            )
            email_field.clear()
            email_field.send_keys(credentials.username)
            
            # Enter password
            password_field = self.driver.find_element(
                By.CSS_SELECTOR,
                self.SELECTORS["password_input"]
            )
            password_field.clear()
            password_field.send_keys(credentials.password)
            
            # Click Sign in button
            login_button = self.driver.find_element(
                By.CSS_SELECTOR,
                self.SELECTORS["login_button"]
            )
            login_button.click()
            
            # Wait for redirect
            time.sleep(5)
            
            # Check login success
            if self.check_login_status():
                self._logged_in = True
                self.save_session()
                return True
            
            return False
            
        except TimeoutException:
            self.take_screenshot("login_timeout")
            return False
        except Exception as e:
            self.take_screenshot("login_error")
            return False
    
    def check_login_status(self) -> bool:
        """Check if logged in to LinkedIn."""
        try:
            current_url = self.driver.current_url
            
            # Check if we're still on login page
            if "login" in current_url.lower() or "checkpoint" in current_url.lower():
                return False
            
            # Check for feed or profile elements
            try:
                self.browser.wait_for_element(
                    By.CSS_SELECTOR,
                    self.SELECTORS["feed_container"],
                    timeout=5
                )
                return True
            except TimeoutException:
                pass
            
            try:
                self.driver.find_element(
                    By.CSS_SELECTOR,
                    self.SELECTORS["profile_icon"]
                )
                return True
            except NoSuchElementException:
                pass
            
            return False
            
        except Exception:
            return False
    
    def navigate_to_post_page(self):
        """Navigate to LinkedIn feed for posting."""
        self.driver.get(f"{self.BASE_URL}/feed/")
        time.sleep(2)
    
    def create_post(
        self, 
        content: str, 
        media_paths: list[Path] | None = None
    ) -> PostResult:
        """
        Create a post on LinkedIn.
        
        Args:
            content: Post text content
            media_paths: Optional list of image/video paths
            
        Returns:
            PostResult with operation status
        """
        if not self._logged_in:
            return PostResult(
                status=PostStatus.AUTH_REQUIRED,
                message="Not logged in to LinkedIn"
            )
        
        # Enforce character limit
        if len(content) > self.MAX_POST_LENGTH:
            return PostResult(
                status=PostStatus.FAILED,
                message=f"Content exceeds {self.MAX_POST_LENGTH} character limit"
            )
        
        try:
            self.navigate_to_post_page()
            
            # Click "Start a post" button
            try:
                start_post_btn = self.browser.wait_for_element(
                    By.CSS_SELECTOR,
                    self.SELECTORS["start_post_button"],
                    timeout=10,
                    clickable=True
                )
                start_post_btn.click()
            except TimeoutException:
                # Try alternative selector
                try:
                    start_post_btn = self.driver.find_element(
                        By.XPATH,
                        "//span[contains(text(), 'Start a post')]//ancestor::button"
                    )
                    start_post_btn.click()
                except NoSuchElementException:
                    return PostResult(
                        status=PostStatus.FAILED,
                        message="Could not find 'Start a post' button",
                        screenshot_path=self.take_screenshot("start_post_not_found")
                    )
            
            time.sleep(2)
            
            # Find and fill the post editor
            try:
                post_editor = self.browser.wait_for_element(
                    By.CSS_SELECTOR,
                    self.SELECTORS["post_editor"],
                    timeout=10
                )
            except TimeoutException:
                # Try contenteditable div
                post_editor = self.browser.wait_for_element(
                    By.CSS_SELECTOR,
                    '[contenteditable="true"]',
                    timeout=5
                )
            
            post_editor.click()
            post_editor.send_keys(content)
            time.sleep(1)
            
            # Handle media uploads if provided
            if media_paths:
                for media_path in media_paths:
                    if media_path.exists():
                        try:
                            file_input = self.driver.find_element(
                                By.CSS_SELECTOR, 'input[type="file"]'
                            )
                            file_input.send_keys(str(media_path.absolute()))
                            time.sleep(3)
                        except NoSuchElementException:
                            pass
            
            # Click Post button
            time.sleep(1)
            try:
                post_button = self.browser.wait_for_element(
                    By.CSS_SELECTOR,
                    self.SELECTORS["post_button"],
                    timeout=5,
                    clickable=True
                )
                post_button.click()
            except TimeoutException:
                # Try finding by text
                post_buttons = self.driver.find_elements(
                    By.XPATH,
                    "//span[text()='Post']//ancestor::button"
                )
                if post_buttons:
                    post_buttons[0].click()
                else:
                    return PostResult(
                        status=PostStatus.FAILED,
                        message="Could not find Post button",
                        screenshot_path=self.take_screenshot("post_button_not_found")
                    )
            
            # Wait for post to complete
            time.sleep(5)
            
            return PostResult(
                status=PostStatus.SUCCESS,
                message="Post created successfully on LinkedIn"
            )
            
        except TimeoutException as e:
            return PostResult(
                status=PostStatus.FAILED,
                message=f"Timeout during post creation: {str(e)}",
                screenshot_path=self.take_screenshot("post_timeout")
            )
        except Exception as e:
            return PostResult(
                status=PostStatus.FAILED,
                message=f"Error creating post: {str(e)}",
                screenshot_path=self.take_screenshot("post_error")
            )
