"""
Facebook Platform - Automation driver for Facebook.

Handles login, post creation, and navigation on Facebook.
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


class FacebookPlatform(BasePlatform):
    """Facebook automation driver."""
    
    PLATFORM_NAME = "facebook"
    BASE_URL = "https://www.facebook.com"
    LOGIN_URL = "https://www.facebook.com/login"
    
    MAX_POST_LENGTH = 63206
    MAX_HASHTAGS = 30
    
    # Selectors
    SELECTORS = {
        "email_input": "email",
        "password_input": "pass",
        "login_button": "login",
        "post_box": '[aria-label="What\'s on your mind"]',
        "post_box_alt": '[data-testid="post_message"]',
        "post_button": '[aria-label="Post"]',
        "post_button_alt": 'form[method="POST"] button[type="submit"]',
        "profile_menu": '[aria-label="Your profile"]',
        "create_post_button": '[aria-label="Create post"]',
    }
    
    def login(self, credentials: Credentials) -> bool:
        """
        Log in to Facebook.
        
        Args:
            credentials: Facebook login credentials
            
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
                By.ID, self.SELECTORS["email_input"], timeout=10
            )
            email_field.clear()
            email_field.send_keys(credentials.username)
            
            # Enter password
            password_field = self.driver.find_element(
                By.ID, self.SELECTORS["password_input"]
            )
            password_field.clear()
            password_field.send_keys(credentials.password)
            
            # Click login button
            login_button = self.driver.find_element(
                By.NAME, self.SELECTORS["login_button"]
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
        """Check if logged in to Facebook."""
        try:
            current_url = self.driver.current_url
            
            # Check if we're on a logged-in page
            if "login" in current_url.lower():
                return False
            
            # Try to find profile menu or other logged-in indicators
            try:
                self.browser.wait_for_element(
                    By.CSS_SELECTOR, 
                    self.SELECTORS["profile_menu"],
                    timeout=5
                )
                return True
            except TimeoutException:
                pass
            
            # Alternative: check for news feed
            try:
                self.driver.find_element(By.CSS_SELECTOR, '[role="feed"]')
                return True
            except NoSuchElementException:
                pass
            
            return False
            
        except Exception:
            return False
    
    def navigate_to_post_page(self):
        """Navigate to Facebook home/news feed for posting."""
        self.driver.get(self.BASE_URL)
        time.sleep(2)
    
    def create_post(
        self, 
        content: str, 
        media_paths: list[Path] | None = None
    ) -> PostResult:
        """
        Create a post on Facebook.
        
        Args:
            content: Post text content
            media_paths: Optional list of image/video paths
            
        Returns:
            PostResult with operation status
        """
        if not self._logged_in:
            return PostResult(
                status=PostStatus.AUTH_REQUIRED,
                message="Not logged in to Facebook"
            )
        
        try:
            self.navigate_to_post_page()
            
            # Click on "What's on your mind" to open post dialog
            try:
                post_trigger = self.browser.wait_for_element(
                    By.CSS_SELECTOR,
                    self.SELECTORS["post_box"],
                    timeout=10
                )
                post_trigger.click()
            except TimeoutException:
                # Try clicking create post button instead
                try:
                    create_btn = self.browser.wait_for_element(
                        By.CSS_SELECTOR,
                        self.SELECTORS["create_post_button"],
                        timeout=5
                    )
                    create_btn.click()
                except TimeoutException:
                    return PostResult(
                        status=PostStatus.FAILED,
                        message="Could not find post creation area",
                        screenshot_path=self.take_screenshot("post_area_not_found")
                    )
            
            time.sleep(2)
            
            # Find the text input in the dialog
            # Facebook's post dialog uses contenteditable divs
            post_input = self.browser.wait_for_element(
                By.CSS_SELECTOR,
                '[contenteditable="true"][role="textbox"]',
                timeout=10
            )
            post_input.click()
            
            # Type the content
            post_input.send_keys(content)
            time.sleep(1)
            
            # Handle media uploads if provided
            if media_paths:
                for media_path in media_paths:
                    if media_path.exists():
                        try:
                            # Find file input for media
                            file_input = self.driver.find_element(
                                By.CSS_SELECTOR, 'input[type="file"]'
                            )
                            file_input.send_keys(str(media_path.absolute()))
                            time.sleep(2)
                        except NoSuchElementException:
                            pass  # Media input not found
            
            # Click the Post button
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
                # Try alternative post button
                post_buttons = self.driver.find_elements(
                    By.XPATH, 
                    "//span[contains(text(), 'Post')]//ancestor::div[@role='button']"
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
                message="Post created successfully on Facebook"
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
