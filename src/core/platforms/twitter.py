"""
Twitter/X Platform - Automation driver for Twitter.

Handles login, tweet creation, and navigation on Twitter/X.
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


class TwitterPlatform(BasePlatform):
    """Twitter/X automation driver."""
    
    PLATFORM_NAME = "twitter"
    BASE_URL = "https://x.com"
    LOGIN_URL = "https://x.com/i/flow/login"
    
    MAX_POST_LENGTH = 280
    MAX_HASHTAGS = 10
    
    # Selectors
    SELECTORS = {
        "username_input": 'input[autocomplete="username"]',
        "password_input": 'input[name="password"]',
        "next_button": '[role="button"]:has-text("Next")',
        "login_button": '[data-testid="LoginForm_Login_Button"]',
        "tweet_box": '[data-testid="tweetTextarea_0"]',
        "tweet_button": '[data-testid="tweetButtonInline"]',
        "compose_button": '[data-testid="SideNav_NewTweet_Button"]',
        "home_timeline": '[data-testid="primaryColumn"]',
        "profile_link": '[data-testid="AppTabBar_Profile_Link"]',
    }
    
    def login(self, credentials: Credentials) -> bool:
        """
        Log in to Twitter/X.
        
        Args:
            credentials: Twitter login credentials
            
        Returns:
            True if login successful
        """
        try:
            # First try to restore existing session
            if self.try_restore_session():
                return True
            
            # Navigate to login page
            self.driver.get(self.LOGIN_URL)
            time.sleep(3)
            
            # Enter username/email
            username_field = self.browser.wait_for_element(
                By.CSS_SELECTOR, 
                self.SELECTORS["username_input"],
                timeout=15
            )
            username_field.send_keys(credentials.username)
            
            # Click Next
            time.sleep(1)
            next_buttons = self.driver.find_elements(
                By.XPATH, "//span[contains(text(), 'Next')]//ancestor::button"
            )
            if next_buttons:
                next_buttons[0].click()
            else:
                # Try pressing Enter
                username_field.send_keys(Keys.ENTER)
            
            time.sleep(2)
            
            # Enter password
            password_field = self.browser.wait_for_element(
                By.CSS_SELECTOR,
                self.SELECTORS["password_input"],
                timeout=10
            )
            password_field.send_keys(credentials.password)
            
            # Click Log in
            time.sleep(1)
            try:
                login_button = self.browser.wait_for_element(
                    By.CSS_SELECTOR,
                    self.SELECTORS["login_button"],
                    timeout=5,
                    clickable=True
                )
                login_button.click()
            except TimeoutException:
                # Try pressing Enter
                password_field.send_keys(Keys.ENTER)
            
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
        """Check if logged in to Twitter."""
        try:
            current_url = self.driver.current_url
            
            # Check if we're on login flow
            if "login" in current_url.lower() or "flow" in current_url.lower():
                return False
            
            # Try to find home timeline or profile link
            try:
                self.browser.wait_for_element(
                    By.CSS_SELECTOR,
                    self.SELECTORS["home_timeline"],
                    timeout=5
                )
                return True
            except TimeoutException:
                pass
            
            try:
                self.driver.find_element(
                    By.CSS_SELECTOR,
                    self.SELECTORS["profile_link"]
                )
                return True
            except NoSuchElementException:
                pass
            
            return False
            
        except Exception:
            return False
    
    def navigate_to_post_page(self):
        """Navigate to Twitter home for posting."""
        self.driver.get(f"{self.BASE_URL}/home")
        time.sleep(2)
    
    def create_post(
        self, 
        content: str, 
        media_paths: list[Path] | None = None
    ) -> PostResult:
        """
        Create a tweet on Twitter/X.
        
        Args:
            content: Tweet text content
            media_paths: Optional list of image/video paths
            
        Returns:
            PostResult with operation status
        """
        if not self._logged_in:
            return PostResult(
                status=PostStatus.AUTH_REQUIRED,
                message="Not logged in to Twitter"
            )
        
        # Enforce character limit
        if len(content) > self.MAX_POST_LENGTH:
            return PostResult(
                status=PostStatus.FAILED,
                message=f"Content exceeds {self.MAX_POST_LENGTH} character limit"
            )
        
        try:
            self.navigate_to_post_page()
            
            # Find tweet compose box
            try:
                tweet_box = self.browser.wait_for_element(
                    By.CSS_SELECTOR,
                    self.SELECTORS["tweet_box"],
                    timeout=10
                )
            except TimeoutException:
                # Try clicking compose button first
                try:
                    compose_btn = self.browser.wait_for_element(
                        By.CSS_SELECTOR,
                        self.SELECTORS["compose_button"],
                        timeout=5,
                        clickable=True
                    )
                    compose_btn.click()
                    time.sleep(2)
                    tweet_box = self.browser.wait_for_element(
                        By.CSS_SELECTOR,
                        self.SELECTORS["tweet_box"],
                        timeout=5
                    )
                except TimeoutException:
                    return PostResult(
                        status=PostStatus.FAILED,
                        message="Could not find tweet compose area",
                        screenshot_path=self.take_screenshot("tweet_area_not_found")
                    )
            
            # Click and type content
            tweet_box.click()
            time.sleep(0.5)
            tweet_box.send_keys(content)
            time.sleep(1)
            
            # Handle media uploads if provided
            if media_paths:
                for media_path in media_paths:
                    if media_path.exists():
                        try:
                            file_input = self.driver.find_element(
                                By.CSS_SELECTOR, 'input[data-testid="fileInput"]'
                            )
                            file_input.send_keys(str(media_path.absolute()))
                            time.sleep(3)
                        except NoSuchElementException:
                            pass
            
            # Click Tweet button
            time.sleep(1)
            tweet_button = self.browser.wait_for_element(
                By.CSS_SELECTOR,
                self.SELECTORS["tweet_button"],
                timeout=5,
                clickable=True
            )
            tweet_button.click()
            
            # Wait for tweet to post
            time.sleep(3)
            
            return PostResult(
                status=PostStatus.SUCCESS,
                message="Tweet posted successfully"
            )
            
        except TimeoutException as e:
            return PostResult(
                status=PostStatus.FAILED,
                message=f"Timeout during tweet creation: {str(e)}",
                screenshot_path=self.take_screenshot("tweet_timeout")
            )
        except Exception as e:
            return PostResult(
                status=PostStatus.FAILED,
                message=f"Error creating tweet: {str(e)}",
                screenshot_path=self.take_screenshot("tweet_error")
            )
