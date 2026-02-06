"""
AI-Powered Social Media Poster - Intelligent DOM manipulation for Facebook posting.
Uses multiple detection strategies and AI-like fallback logic to find and interact
with elements reliably, even when Facebook changes their DOM structure.
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional
from playwright.async_api import async_playwright, Page, Locator

from src.config import config
from src.data.database import get_database
from src.utils.logger import get_logger

from src.core.browser_session_manager import get_session_manager, BrowserSessionManager

logger = get_logger(__name__)


class IntelligentElementFinder:
    """Intelligent element finder with multiple detection strategies."""
    
    @staticmethod
    async def find_text_input_intelligent(page: Page) -> Optional[Locator]:
        """Intelligently find Facebook's text input/composer with extensive fallbacks."""
        logger.info("🔍 Searching for text input...")
        
        # Wait a moment for any animations/dialogs to settle
        await page.wait_for_timeout(1500)
        
        # Comprehensive selector list - ordered by specificity
        selectors = [
            # Most specific - modern Facebook composer
            "div[contenteditable='true'][data-lexical-editor='true']",
            "div[data-lexical-editor='true'][contenteditable='true']",
            "div[data-contents='true'][contenteditable='true']",
            # Standard patterns
            "div[contenteditable='true'][role='textbox']",
            "div[role='textbox'][contenteditable='true']",
            "div[contenteditable='true'][spellcheck='false']",
            # Placeholder based
            "div[aria-placeholder*='mind']",
            "div[aria-placeholder*='your']",
            "div[aria-placeholder*='post']",
            "div[aria-placeholder*='text']",
            # Data attributes
            "[data-lexical-editor='true']",
            "[data-contents='true']",
            "[data-testid*='composer']",
            "[data-testid*='textbox']",
            # Class patterns (Facebook uses hashed classes but some patterns persist)
            "div[class*='notranslate']",
            "div[class*='editor']",
            "div[class*='composer']",
            # Generic fallbacks
            "div[contenteditable='true']",
            "div[role='textbox']",
            "[contenteditable='true']",
        ]
        
        logger.info(f"Trying {len(selectors)} selectors...")
        
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                count = await locator.count()
                if count > 0:
                    is_visible = await locator.is_visible()
                    if is_visible:
                        # Try to verify it's actually a text input
                        try:
                            contenteditable = await locator.get_attribute("contenteditable")
                            role = await locator.get_attribute("role")
                            placeholder = await locator.get_attribute("aria-placeholder")
                            logger.info(f"✓ Found element: {selector} (contenteditable={contenteditable}, role={role}, placeholder={placeholder})")
                            if contenteditable == "true" or role == "textbox":
                                logger.info(f"✓ Confirmed text input: {selector}")
                                return locator
                        except Exception:
                            # If we can't check attributes but it's visible and contenteditable, use it
                            if "contenteditable" in selector:
                                logger.info(f"✓ Using visible contenteditable: {selector}")
                                return locator
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
                continue
        
        # Deep fallback: scan all page elements for contenteditable
        logger.info("🔍 Deep scan: looking for any contenteditable element...")
        try:
            # Get all contenteditable elements
            all_editables = page.locator("[contenteditable='true']")
            count = await all_editables.count()
            logger.info(f"Found {count} contenteditable elements total")
            
            # Check each one
            for i in range(min(count, 10)):
                try:
                    locator = all_editables.nth(i)
                    if await locator.is_visible():
                        # Get some info about it
                        text = await locator.inner_text()
                        logger.info(f"  Element {i}: visible, text='{text[:50]}...'")
                        # Return the first visible one that's likely a composer
                        if i == 0 or len(text) < 500:  # First one or not too much text
                            logger.info(f"✓ Using contenteditable element {i}")
                            return locator
                except Exception as e:
                    logger.debug(f"Element {i} check failed: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Deep scan failed: {e}")
        
        logger.error("❌ Could not find any text input element")
        return None
    
    @staticmethod
    async def find_button_by_text(page: Page, text: str) -> Optional[Locator]:
        """Find button by text content."""
        logger.info(f"Searching for button: '{text}'")
        
        selectors = [
            f"div[aria-label='{text}'][role='button']",
            f"button:has-text('{text}')",
            f"div[role='button']:has-text('{text}')",
            f"span:has-text('{text}')",
        ]
        
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                if await locator.count() > 0 and await locator.is_visible():
                    return locator
            except Exception:
                continue
        
        return None


class BrowserDOMPoster:
    """AI-powered social media poster using intelligent DOM manipulation."""
    
    def __init__(self):
        self.element_finder = IntelligentElementFinder()
        self.session_manager = get_session_manager()
    
    def post_to_facebook(self, content: str, media_paths: list[str] = None, headless: bool = False) -> tuple[bool, str]:
        """Public method to post to Facebook (called by worker thread)."""
        return asyncio.run(self._async_post_to_facebook(content, media_paths or [], headless))
    
    def post(self, platform: str, content: str, media_paths: list[str]) -> tuple[bool, str]:
        """Post content to social media platform."""
        if platform.lower() == "facebook":
            return self.post_to_facebook(content, media_paths)
        return False, f"{platform} posting not implemented"
    
    async def _async_post_to_facebook(
        self, content: str, media_paths: list[str], headless: bool = False
    ) -> tuple[bool, str]:
        """Post to Facebook using saved browser session."""
        logger.info("Starting Facebook post...")
        platform = "facebook"
        
        # Check if we have a saved session
        if not self.session_manager.has_session(platform):
            logger.info("No saved session found. Need to authenticate first.")
            success, message = await self.session_manager.authenticate(platform, headless=False)
            if not success:
                return False, f"Authentication required: {message}"
            logger.info(f"Authentication successful: {message}")
        
        # Now post using the saved session
        browser = None
        
        async with async_playwright() as p:
            try:
                # Get browser config
                browser_config = self.session_manager.browser_configs.get(platform)
                if not browser_config:
                    return False, "No browser configured"
                
                session = self.session_manager.get_session(platform)
                
                # Launch browser
                browser = await p.chromium.launch(
                    headless=headless,
                    executable_path=browser_config.executable_path,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-first-run",
                        "--start-maximized",
                    ]
                )
                
                # Create context with session cookies
                context = await browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    user_agent=session.user_agent if session else None,
                )
                
                # Add saved cookies
                if session and session.cookies:
                    await context.add_cookies(session.cookies)
                    logger.info(f"Loaded {len(session.cookies)} cookies from saved session")
                
                page = await context.new_page()
                page.set_default_timeout(30000)
                
                # Navigate to Facebook
                logger.info("Navigating to Facebook...")
                await page.goto("https://www.facebook.com/", wait_until="domcontentloaded")
                await page.wait_for_timeout(3000)
                
                # Check if still logged in
                cookies = await context.cookies()
                has_session = any(
                    c.get("name") == "c_user" for c in cookies
                )
                
                if not has_session:
                    logger.warning("Session expired, need to re-authenticate")
                    await browser.close()
                    
                    # Try to re-authenticate
                    success, message = await self.session_manager.authenticate(platform, headless=False)
                    if not success:
                        return False, f"Session expired and re-authentication failed: {message}"
                    
                    # Retry posting
                    return await self._async_post_to_facebook(content, media_paths, headless)
                
                logger.info("✓ Logged in with saved session")
                
                # Take screenshot of feed
                try:
                    await page.screenshot(path="fb_feed.png")
                    logger.info("Screenshot saved: fb_feed.png")
                except Exception as e:
                    logger.warning(f"Screenshot failed: {e}")

                # Open composer - try multiple approaches
                logger.info("Looking for composer trigger...")
                composer_clicked = False
                
                # Try "What's on your mind" button
                composer_selectors = [
                    "div[role='button']:has-text('mind')",
                    "div[role='button']:has-text('post')",
                    "[aria-label*='Create a post']",
                    "[aria-label*='composer']",
                    "div[role='button'][class*='composer']",
                    "div[role='button'][class*='create']",
                ]
                
                for selector in composer_selectors:
                    try:
                        locator = page.locator(selector).first
                        if await locator.count() > 0 and await locator.is_visible():
                            logger.info(f"Found composer trigger: {selector}")
                            await locator.click()
                            await page.wait_for_timeout(3000)
                            composer_clicked = True
                            break
                    except Exception as e:
                        logger.debug(f"Selector {selector} failed: {e}")
                        continue
                
                if not composer_clicked:
                    logger.warning("Could not find composer trigger, looking for text input directly...")

                # Take screenshot after attempting to open composer
                try:
                    await page.screenshot(path="fb_composer.png")
                    logger.info("Screenshot saved: fb_composer.png")
                except Exception as e:
                    logger.warning(f"Screenshot failed: {e}")

                # Find text input
                text_input = await self.element_finder.find_text_input_intelligent(page)
                if not text_input:
                    await browser.close()
                    return False, "Could not find text input"

                # Enter text
                logger.info("Entering text...")
                text_entered = await self._enter_text(page, text_input, content)
                if not text_entered:
                    await browser.close()
                    return False, "Failed to enter text"

                # Upload media
                if media_paths:
                    logger.info(f"Uploading {len(media_paths)} media files...")
                    await self._upload_media(page, media_paths)
                    
                    # Wait for media processing - check multiple indicators
                    logger.info("Waiting for media processing...")
                    for attempt in range(60):  # Wait up to 60 seconds
                        # Check various processing states
                        processing = await page.locator("text=Processing").count()
                        uploading = await page.locator("text=Uploading").count()
                        loading = await page.locator("text=Loading").count()
                        
                        if processing == 0 and uploading == 0 and loading == 0:
                            # Extra wait to ensure button is ready
                            await page.wait_for_timeout(2000)
                            logger.info("Media processing complete")
                            break
                        
                        if attempt % 5 == 0:  # Log every 5 seconds
                            logger.info(f"Media still processing... {attempt + 1}/60")
                        await page.wait_for_timeout(1000)
                    else:
                        logger.warning("Media processing timeout - continuing anyway")

                # DEBUG: Screenshot before looking for buttons
                try:
                    await page.screenshot(path="fb_before_buttons.png")
                    logger.info("Screenshot saved: fb_before_buttons.png")
                except:
                    pass

                # Find and click Post - with smart waiting
                logger.info("Looking for Post/Next button...")
                post_btn = None
                
                # Wait up to 30 seconds for buttons to appear and be enabled
                for attempt in range(30):
                    # Try Post button - must be visible AND not disabled
                    post_locator = page.locator("div[aria-label='Post'][role='button']").first
                    if await post_locator.count() > 0:
                        is_visible = await post_locator.is_visible()
                        if is_visible:
                            # Check if disabled
                            try:
                                aria_disabled = await post_locator.get_attribute("aria-disabled")
                                if aria_disabled and aria_disabled.lower() == "true":
                                    logger.debug(f"Post button disabled, waiting... ({attempt + 1}/30)")
                                else:
                                    post_btn = post_locator
                                    logger.info("✓ Found enabled Post button")
                                    break
                            except:
                                post_btn = post_locator
                                logger.info("✓ Found Post button")
                                break
                    
                    # Try Next button - must be visible AND not disabled
                    next_locator = page.locator("div[aria-label='Next'][role='button']").first
                    if await next_locator.count() > 0:
                        is_visible = await next_locator.is_visible()
                        if is_visible:
                            try:
                                aria_disabled = await next_locator.get_attribute("aria-disabled")
                                if aria_disabled and aria_disabled.lower() == "true":
                                    logger.debug(f"Next button disabled, waiting... ({attempt + 1}/30)")
                                else:
                                    logger.info("Found Next button, clicking...")
                                    await next_locator.click()
                                    await page.wait_for_timeout(3000)
                                    # Now look for Post button again
                                    continue  # Go to next iteration to find Post
                            except:
                                logger.info("Found Next button, clicking...")
                                await next_locator.click()
                                await page.wait_for_timeout(3000)
                                continue
                    
                    if attempt % 5 == 0:
                        logger.info(f"Waiting for buttons to appear... {attempt + 1}/30")
                    await page.wait_for_timeout(1000)
                
                if not post_btn:
                    logger.error("Could not find Post button after extended wait")
                    try:
                        await page.screenshot(path="fb_no_post_button.png")
                        logger.info("Debug screenshot: fb_no_post_button.png")
                    except:
                        pass
                    await browser.close()
                    return False, "Could not find Post button - media may still be processing"

                logger.info("Clicking Post...")
                await post_btn.click()
                
                # Wait longer for post to actually publish
                logger.info("Waiting for post to publish...")
                await page.wait_for_timeout(5000)
                
                # Verify with screenshot
                try:
                    await page.screenshot(path="fb_after_post.png")
                    logger.info("Screenshot saved: fb_after_post.png")
                except Exception as e:
                    logger.warning(f"Screenshot failed: {e}")

                # Verify
                success = await self._verify_post(page, content)
                
                # Close browser
                logger.info("Closing browser...")
                await browser.close()
                
                if success:
                    return True, "Posted successfully!"
                return False, "Post verification failed - post may not have been published"
                
            except Exception as e:
                logger.error(f"Error: {e}")
                try:
                    if 'browser' in locals() and browser:
                        await browser.close()
                except:
                    pass
                return False, f"Error: {e}"
    
    async def _enter_text(self, page: Page, text_input: Locator, content: str) -> bool:
        """Enter text using multiple strategies."""
        strategies = [
            lambda: text_input.fill(content),
            lambda: self._force_type(page, text_input, content),
            lambda: self._javascript_type(page, text_input, content),
        ]
        
        for strategy in strategies:
            try:
                await strategy()
                await page.wait_for_timeout(500)
                text = await text_input.inner_text()
                if text.strip():
                    return True
            except Exception:
                continue
        
        return False
    
    async def _force_type(self, page: Page, text_input: Locator, content: str):
        """Force click and type."""
        await text_input.click(force=True)
        await page.wait_for_timeout(300)
        await page.keyboard.type(content, delay=20)
    
    async def _javascript_type(self, page: Page, text_input: Locator, content: str):
        """Use JavaScript to set text."""
        handle = await text_input.element_handle()
        if handle:
            await handle.evaluate("""
                (el, text) => {
                    el.focus();
                    el.textContent = text;
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                }
            """, content)
    
    async def _upload_media(self, page: Page, media_paths: list[str]):
        """Upload media files."""
        try:
            # Find photo/video button
            photo_btn = await self.element_finder.find_button_by_text(page, "Photo/video")
            if photo_btn:
                await photo_btn.click()
                await page.wait_for_timeout(1500)
            
            # Find file input
            file_input = page.locator("input[type='file']").first
            if await file_input.count() > 0:
                for path in media_paths:
                    if Path(path).exists():
                        await file_input.set_input_files(path)
                        await page.wait_for_timeout(1000)
        except Exception as e:
            logger.error(f"Media upload error: {e}")
    
    async def _verify_post(self, page: Page, expected_content: str = "") -> bool:
        """Verify post was actually published successfully."""
        try:
            # Wait a moment for any navigation/state changes
            await page.wait_for_timeout(2000)
            
            # Check 1: Look for success toast/notification
            success_indicators = [
                "text=Posted",
                "text=Your post has been shared",
                "text=Posting",
                "[role='alert']:has-text('Posted')",
            ]
            
            for indicator in success_indicators:
                try:
                    if await page.locator(indicator).count() > 0:
                        logger.info(f"✓ Found success indicator: {indicator}")
                        return True
                except:
                    continue
            
            # Check 2: Check if we're back on feed (but dialog is closed)
            current_url = page.url
            dialogs = await page.locator("div[role='dialog']").count()
            
            logger.info(f"URL after post: {current_url}, Dialogs: {dialogs}")
            
            # Must have no dialog AND be on feed
            if dialogs == 0 and ("feed" in current_url or current_url.rstrip('/').endswith("facebook.com")):
                # Additional check: look for the post content on the page
                if expected_content:
                    # Try to find the posted content
                    short_content = expected_content[:30]
                    try:
                        # Look for post content in feed
                        post_locator = page.locator(f"text={short_content}").first
                        if await post_locator.count() > 0 and await post_locator.is_visible():
                            logger.info("✓ Found posted content in feed")
                            return True
                    except:
                        pass
                
                # If we can't verify content, at least verify dialog is closed and URL changed
                logger.info("⚠ Dialog closed and on feed, but couldn't verify content")
                return True  # Partial success
            
            # Check 3: If dialog still open, post likely failed
            if dialogs > 0:
                logger.warning("⚠ Post dialog still open - post may have failed")
                return False
                
        except Exception as e:
            logger.error(f"Verification error: {e}")
        
        return False


_poster: Optional[BrowserDOMPoster] = None


def get_poster() -> BrowserDOMPoster:
    """Get or create the social media poster."""
    global _poster
    if _poster is None:
        _poster = BrowserDOMPoster()
    return _poster
