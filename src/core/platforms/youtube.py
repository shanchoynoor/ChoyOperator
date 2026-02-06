"""
YouTube Platform - Automation driver for YouTube.

Handles login, video upload, and community post creation on YouTube.
Note: Video uploads may require YouTube Data API for reliability.
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


class YouTubePlatform(BasePlatform):
    """YouTube automation driver."""
    
    PLATFORM_NAME = "youtube"
    BASE_URL = "https://www.youtube.com"
    LOGIN_URL = "https://accounts.google.com/signin"
    STUDIO_URL = "https://studio.youtube.com"
    
    MAX_POST_LENGTH = 5000  # Community post limit
    MAX_TITLE_LENGTH = 100
    MAX_DESCRIPTION_LENGTH = 5000
    MAX_HASHTAGS = 15
    
    # Selectors
    SELECTORS = {
        "email_input": 'input[type="email"]',
        "password_input": 'input[type="password"]',
        "next_button": "#identifierNext",
        "password_next": "#passwordNext",
        "avatar": "#avatar-btn",
        "create_button": "#create-icon",
        "upload_video_option": 'tp-yt-paper-item:has-text("Upload video")',
        "community_post_option": 'tp-yt-paper-item:has-text("Create post")',
        "file_input": 'input[type="file"]',
        "title_input": "#title-textarea",
        "description_input": "#description-textarea",
        "publish_button": "#done-button",
        "community_textarea": "#contenteditable-root",
        "post_button": "#submit-button",
    }
    
    def login(self, credentials: Credentials) -> bool:
        """
        Log in to YouTube via Google account.
        
        Args:
            credentials: Google account credentials
            
        Returns:
            True if login successful
        """
        try:
            # First try to restore existing session
            if self.try_restore_session():
                return True
            
            # Navigate to Google login
            self.driver.get(self.LOGIN_URL)
            time.sleep(2)
            
            # Enter email
            email_field = self.browser.wait_for_element(
                By.CSS_SELECTOR,
                self.SELECTORS["email_input"],
                timeout=10
            )
            email_field.send_keys(credentials.username)
            
            # Click Next
            next_button = self.browser.wait_for_element(
                By.CSS_SELECTOR,
                self.SELECTORS["next_button"],
                timeout=5,
                clickable=True
            )
            next_button.click()
            time.sleep(3)
            
            # Enter password
            password_field = self.browser.wait_for_element(
                By.CSS_SELECTOR,
                self.SELECTORS["password_input"],
                timeout=10
            )
            password_field.send_keys(credentials.password)
            
            # Click Next
            password_next = self.browser.wait_for_element(
                By.CSS_SELECTOR,
                self.SELECTORS["password_next"],
                timeout=5,
                clickable=True
            )
            password_next.click()
            time.sleep(5)
            
            # Navigate to YouTube to set cookies
            self.driver.get(self.BASE_URL)
            time.sleep(3)
            
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
        """Check if logged in to YouTube."""
        try:
            # Look for avatar button (indicates logged in)
            try:
                self.browser.wait_for_element(
                    By.CSS_SELECTOR,
                    self.SELECTORS["avatar"],
                    timeout=5
                )
                return True
            except TimeoutException:
                pass
            
            # Alternative: check for Sign In button absence
            try:
                self.driver.find_element(
                    By.XPATH,
                    "//ytd-button-renderer//a[contains(@href, 'accounts.google.com')]"
                )
                return False  # Sign in button exists = not logged in
            except NoSuchElementException:
                return True
            
        except Exception:
            return False
    
    def navigate_to_post_page(self):
        """Navigate to YouTube Studio for content creation."""
        self.driver.get(self.STUDIO_URL)
        time.sleep(3)
    
    def create_post(
        self, 
        content: str, 
        media_paths: list[Path] | None = None
    ) -> PostResult:
        """
        Create a community post on YouTube.
        
        For video uploads, use upload_video() instead.
        
        Args:
            content: Post text content
            media_paths: Optional images to attach
            
        Returns:
            PostResult with operation status
        """
        if not self._logged_in:
            return PostResult(
                status=PostStatus.AUTH_REQUIRED,
                message="Not logged in to YouTube"
            )
        
        if len(content) > self.MAX_POST_LENGTH:
            return PostResult(
                status=PostStatus.FAILED,
                message=f"Content exceeds {self.MAX_POST_LENGTH} character limit"
            )
        
        try:
            # Navigate to YouTube
            self.driver.get(self.BASE_URL)
            time.sleep(2)
            
            # Click Create button
            try:
                create_btn = self.browser.wait_for_element(
                    By.CSS_SELECTOR,
                    self.SELECTORS["create_button"],
                    timeout=10,
                    clickable=True
                )
                create_btn.click()
            except TimeoutException:
                # Try alternative selector
                create_btn = self.driver.find_element(
                    By.XPATH,
                    "//ytd-topbar-menu-button-renderer[@id='create-icon']"
                )
                create_btn.click()
            
            time.sleep(1)
            
            # Click "Create post" option
            try:
                post_option = self.browser.wait_for_element(
                    By.XPATH,
                    "//tp-yt-paper-item[contains(., 'Create post')]",
                    timeout=5,
                    clickable=True
                )
                post_option.click()
            except TimeoutException:
                return PostResult(
                    status=PostStatus.FAILED,
                    message="Community posts not available for this channel",
                    screenshot_path=self.take_screenshot("community_not_available")
                )
            
            time.sleep(2)
            
            # Find and fill the post textarea
            post_area = self.browser.wait_for_element(
                By.CSS_SELECTOR,
                self.SELECTORS["community_textarea"],
                timeout=10
            )
            post_area.click()
            post_area.send_keys(content)
            time.sleep(1)
            
            # Handle image uploads if provided
            if media_paths:
                for media_path in media_paths:
                    if media_path.exists() and media_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif']:
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
            post_button = self.browser.wait_for_element(
                By.CSS_SELECTOR,
                self.SELECTORS["post_button"],
                timeout=5,
                clickable=True
            )
            post_button.click()
            
            time.sleep(3)
            
            return PostResult(
                status=PostStatus.SUCCESS,
                message="Community post created successfully on YouTube"
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
    
    def upload_video(
        self,
        video_path: Path,
        title: str,
        description: str = "",
        visibility: str = "public"
    ) -> PostResult:
        """
        Upload a video to YouTube.
        
        Args:
            video_path: Path to video file
            title: Video title
            description: Video description
            visibility: public, unlisted, or private
            
        Returns:
            PostResult with operation status
        """
        if not self._logged_in:
            return PostResult(
                status=PostStatus.AUTH_REQUIRED,
                message="Not logged in to YouTube"
            )
        
        if not video_path.exists():
            return PostResult(
                status=PostStatus.FAILED,
                message=f"Video file not found: {video_path}"
            )
        
        try:
            # Navigate to YouTube Studio
            self.navigate_to_post_page()
            
            # Click Create/Upload button
            create_btn = self.browser.wait_for_element(
                By.CSS_SELECTOR,
                "#create-icon",
                timeout=10,
                clickable=True
            )
            create_btn.click()
            time.sleep(1)
            
            # Click Upload video
            upload_option = self.browser.wait_for_element(
                By.XPATH,
                "//tp-yt-paper-item[contains(., 'Upload video')]",
                timeout=5,
                clickable=True
            )
            upload_option.click()
            time.sleep(2)
            
            # Upload the video file
            file_input = self.browser.wait_for_element(
                By.CSS_SELECTOR,
                'input[type="file"]',
                timeout=10
            )
            file_input.send_keys(str(video_path.absolute()))
            
            # Wait for upload dialog
            time.sleep(5)
            
            # Set title
            title_field = self.browser.wait_for_element(
                By.CSS_SELECTOR,
                self.SELECTORS["title_input"],
                timeout=30
            )
            title_field.clear()
            title_field.send_keys(title[:self.MAX_TITLE_LENGTH])
            
            # Set description
            if description:
                desc_field = self.driver.find_element(
                    By.CSS_SELECTOR,
                    self.SELECTORS["description_input"]
                )
                desc_field.click()
                desc_field.send_keys(description[:self.MAX_DESCRIPTION_LENGTH])
            
            # Continue through the upload flow
            # This is simplified - actual flow has multiple steps
            for _ in range(3):
                try:
                    next_btn = self.driver.find_element(
                        By.CSS_SELECTOR, "#next-button"
                    )
                    next_btn.click()
                    time.sleep(2)
                except NoSuchElementException:
                    break
            
            # Set visibility and publish
            # Wait for upload to complete
            time.sleep(10)
            
            done_btn = self.browser.wait_for_element(
                By.CSS_SELECTOR,
                self.SELECTORS["publish_button"],
                timeout=60,
                clickable=True
            )
            done_btn.click()
            
            time.sleep(5)
            
            return PostResult(
                status=PostStatus.SUCCESS,
                message="Video uploaded successfully to YouTube"
            )
            
        except TimeoutException as e:
            return PostResult(
                status=PostStatus.FAILED,
                message=f"Timeout during video upload: {str(e)}",
                screenshot_path=self.take_screenshot("upload_timeout")
            )
        except Exception as e:
            return PostResult(
                status=PostStatus.FAILED,
                message=f"Error uploading video: {str(e)}",
                screenshot_path=self.take_screenshot("upload_error")
            )
