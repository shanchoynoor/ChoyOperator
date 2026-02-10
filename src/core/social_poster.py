"""
AI-Powered Social Media Poster - Intelligent DOM manipulation for Facebook posting.
Uses multiple detection strategies and AI-like fallback logic to find and interact
with elements reliably, even when Facebook changes their DOM structure.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
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
        
        # Check for iframes first - Facebook sometimes puts composer in iframe
        logger.info("Checking for iframes...")
        frames = page.frames
        logger.info(f"Found {len(frames)} frame(s)")
        
        for i, frame in enumerate(frames):
            if frame != page.main_frame:
                try:
                    # Try to find text input in iframe
                    iframe_input = frame.locator("[contenteditable='true'], [role='textbox']").first
                    count = await iframe_input.count()
                    if count > 0:
                        is_visible = await iframe_input.is_visible()
                        is_editable = await iframe_input.is_editable()
                        logger.info(f"✓ Found text input in iframe {i}: visible={is_visible}, editable={is_editable}")
                        if is_visible and is_editable:
                            return iframe_input
                except Exception as e:
                    logger.debug(f"Frame {i} check failed: {e}")
        
        # Comprehensive selector list - ordered by specificity (using role/aria, not classes)
        selectors = [
            # Most specific - role-based selectors (most reliable)
            "div[role='textbox'][contenteditable='true']",
            "div[contenteditable='true'][role='textbox']",
            "[role='textbox']",
            # Contenteditable with data attributes
            "div[contenteditable='true'][data-lexical-editor='true']",
            "div[data-lexical-editor='true'][contenteditable='true']",
            "div[data-contents='true'][contenteditable='true']",
            # Standard contenteditable patterns
            "div[contenteditable='true'][spellcheck='false']",
            # Placeholder based (aria)
            "div[aria-placeholder*='mind']",
            "div[aria-placeholder*='your']",
            "div[aria-placeholder*='post']",
            "div[aria-placeholder*='text']",
            # Data attributes
            "[data-lexical-editor='true']",
            "[data-contents='true']",
            "[data-testid*='composer']",
            "[data-testid*='textbox']",
            # Generic fallbacks
            "div[contenteditable='true']",
            "[contenteditable='true']",
        ]
        
        logger.info(f"Trying {len(selectors)} selectors...")
        
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                count = await locator.count()
                if count > 0:
                    # Log detailed state for debugging
                    is_visible = await locator.is_visible()
                    is_editable = await locator.is_editable()
                    is_enabled = await locator.is_enabled()
                    
                    logger.info(f"  Selector {selector}: count={count}, visible={is_visible}, editable={is_editable}, enabled={is_enabled}")
                    
                    if is_visible and is_editable:
                        # Try to verify it's actually a text input
                        try:
                            contenteditable = await locator.get_attribute("contenteditable")
                            role = await locator.get_attribute("role")
                            placeholder = await locator.get_attribute("aria-placeholder")
                            
                            if contenteditable == "true" or role == "textbox":
                                logger.info(f"✓ Confirmed text input: {selector} (contenteditable={contenteditable}, role={role}, placeholder={placeholder})")
                                return locator
                        except Exception:
                            # If we can't check attributes but it's visible and editable, use it
                            logger.info(f"✓ Using visible editable element: {selector}")
                            return locator
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
                continue
        
        # Deep fallback: scan all page elements for contenteditable that's visible and editable
        logger.info("🔍 Deep scan: looking for any interactable contenteditable element...")
        try:
            # Get all contenteditable elements
            all_editables = page.locator("[contenteditable='true']")
            count = await all_editables.count()
            logger.info(f"Found {count} contenteditable elements total")
            
            # Check each one for visibility and editability
            for i in range(min(count, 10)):
                try:
                    locator = all_editables.nth(i)
                    is_visible = await locator.is_visible()
                    is_editable = await locator.is_editable()
                    
                    if is_visible and is_editable:
                        # Get some info about it
                        text = await locator.inner_text()
                        role = await locator.get_attribute("role")
                        logger.info(f"  Element {i}: visible={is_visible}, editable={is_editable}, role={role}, text='{text[:50]}...'")
                        # Return the first visible, editable one that's likely a composer
                        if i == 0 or len(text) < 500:  # First one or not too much text
                            logger.info(f"✓ Using contenteditable element {i}")
                            return locator
                except Exception as e:
                    logger.debug(f"Element {i} check failed: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Deep scan failed: {e}")
        
        logger.error("❌ Could not find any interactable text input element")
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
    
    @asynccontextmanager
    async def _facebook_session(self, headless: bool = True):
        """Provide an authenticated Facebook page inside a managed browser."""
        platform = "facebook"
        if not self.session_manager.has_session(platform):
            success, message = await self.session_manager.authenticate(platform, headless=False)
            if not success:
                raise RuntimeError(f"Authentication required: {message}")
            logger.info(f"Authentication successful: {message}")
        playwright = await async_playwright().start()
        browser = None
        try:
            browser_config = self.session_manager.browser_configs.get(platform)
            if not browser_config:
                raise RuntimeError("No browser configured")
            session = self.session_manager.get_session(platform)
            browser = await playwright.chromium.launch(
                headless=headless,
                executable_path=browser_config.executable_path,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-first-run",
                    "--start-maximized",
                    "--window-size=1920,1080",
                    "--force-device-scale-factor=1",
                ]
            )
            context = await browser.new_context(
                viewport=None,
                user_agent=session.user_agent if session else None,
            )
            if session and session.cookies:
                await context.add_cookies(session.cookies)
            page = await context.new_page()
            page.set_default_timeout(30000)
            await page.goto("https://www.facebook.com/", wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)
            cookies = await context.cookies()
            if not any(c.get("name") == "c_user" for c in cookies):
                logger.warning("Session expired, retrying authentication")
                await browser.close()
                await playwright.stop()
                success, message = await self.session_manager.authenticate(platform, headless=False)
                if not success:
                    raise RuntimeError(f"Session expired and re-authentication failed: {message}")
                async with self._facebook_session(headless=headless) as retry_page:
                    yield retry_page
                return
            logger.info("✓ Logged in with saved session")
            try:
                yield page
            finally:
                await browser.close()
        finally:
            await playwright.stop()
    
    def post_to_facebook(self, content: str, media_paths: list[str] = None, headless: bool = True) -> tuple[bool, str]:
        """Public method to post to Facebook (called by worker thread)."""
        return asyncio.run(self._async_post_to_facebook(content, media_paths or [], headless))
    
    def post_to_facebook_reel(self, content: str, media_paths: list[str], headless: bool = True) -> tuple[bool, str]:
        """Post a Facebook Reel (videos only)."""
        return asyncio.run(self._async_post_to_facebook_reel(content, media_paths or [], headless))
    
    def post(self, platform: str, content: str, media_paths: list[str]) -> tuple[bool, str]:
        """Post content to social media platform."""
        if platform.lower() == "facebook":
            return self.post_to_facebook(content, media_paths)
        return False, f"{platform} posting not implemented"
    
    async def _async_post_to_facebook(
        self, content: str, media_paths: list[str], headless: bool = True
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
                
                # Launch browser with maximized window
                browser = await p.chromium.launch(
                    headless=headless,
                    executable_path=browser_config.executable_path,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-first-run",
                        "--start-maximized",
                        "--window-size=1920,1080",
                        "--force-device-scale-factor=1",
                    ]
                )
                
                # Create context with no viewport constraint (full window)
                context = await browser.new_context(
                    viewport=None,  # Use full window size
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
                    media_success = await self._upload_media(page, media_paths)
                    
                    if not media_success:
                        logger.error("Media upload failed - cannot proceed with post")
                        await browser.close()
                        return False, "Media upload failed - please check your media files and try again"
                    
                    logger.info("✓ Media upload completed")
                    # Extra wait for Facebook to process
                    await page.wait_for_timeout(3000)

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
    
    async def _async_post_to_facebook_reel(
        self, content: str, media_paths: list[str], headless: bool = True
    ) -> tuple[bool, str]:
        """Post videos as a Facebook Reel following the dedicated workflow."""
        logger.info("Starting Facebook Reel workflow...")
        if not media_paths:
            return False, "Reels require at least one video file"
        try:
            async with self._facebook_session(headless=headless) as page:
                composer_ready = await self._open_reel_composer(page)
                if not composer_ready:
                    return False, "Could not open Facebook Reel composer"
                upload_success = await self._upload_reel_media(page, media_paths)
                if not upload_success:
                    return False, "Failed to upload Reel video"
                caption_success = await self._enter_reel_caption(page, content)
                if not caption_success:
                    return False, "Failed to enter Reel caption"
                publish_success = await self._publish_reel(page)
                if not publish_success:
                    return False, "Could not find Share button for Reels"
                verification_success = await self._verify_reel_post(page, content)
                if not verification_success:
                    return False, "Reel may not have been published (verification failed)"
                return True, "Reel posted successfully!"
        except Exception as exc:
            logger.exception("Facebook Reel posting error: %s", exc)
            return False, f"Error posting Reel: {exc}"
    
    async def _open_reel_composer(self, page: Page) -> bool:
        """Navigate to the Reel composer and ensure the upload surface is ready."""
        logger.info("Opening Reel composer...")
        target_urls = [
            "https://www.facebook.com/reels/create/",
            "https://www.facebook.com/creatorstudio/?tab=reels",
        ]
        for url in target_urls:
            try:
                await page.goto(url, wait_until="domcontentloaded")
                await page.wait_for_timeout(3000)
                file_input = page.locator("input[type='file'][accept*='video']").first
                if await file_input.count() > 0:
                    logger.info("✓ Reel composer ready via direct URL")
                    return True
            except Exception as exc:
                logger.debug("Composer URL %s failed: %s", url, exc)
        logger.info("Direct navigation failed, trying UI navigation")
        create_selectors = [
            "div[role='button']:has-text('Create')",
            "div[aria-label='Create'][role='button']",
            "div[role='button']:has-text('Reel')",
            "[aria-label*='Reel'][role='button']",
        ]
        for selector in create_selectors:
            try:
                trigger = page.locator(selector).first
                if await trigger.count() == 0 or not await trigger.is_visible():
                    continue
                logger.info("Clicking %s to open Reel options", selector)
                await trigger.click()
                await page.wait_for_timeout(2000)
                reel_option_selectors = [
                    "div[role='menuitem']:has-text('Reel')",
                    "div[role='button']:has-text('Reel')",
                    "div[role='menuitem']:has-text('Create reel')",
                ]
                for option_selector in reel_option_selectors:
                    option = page.locator(option_selector).first
                    if await option.count() > 0 and await option.is_visible():
                        await option.click()
                        await page.wait_for_timeout(4000)
                        file_input = page.locator("input[type='file'][accept*='video']").first
                        if await file_input.count() > 0:
                            logger.info("✓ Reel composer opened via UI navigation")
                            return True
            except Exception as exc:
                logger.debug("Create selector %s failed: %s", selector, exc)
        logger.error("Failed to open Reel composer")
        return False
    
    async def _upload_reel_media(self, page: Page, media_paths: list[str]) -> bool:
        """Upload Reel video files using the dedicated composer."""
        valid_paths = [str(Path(p)) for p in media_paths if Path(p).exists()]
        if not valid_paths:
            logger.error("No valid video files found for Reel")
            return False
        logger.info("Uploading %d video file(s) for Reel", len(valid_paths))
        uploader_selectors = [
            "input[type='file'][accept*='video']",
            "input[type='file'][accept*='mp4']",
            "input[type='file'][aria-label*='video']",
            "input[type='file']",
        ]
        file_input = None
        for selector in uploader_selectors:
            candidate = page.locator(selector).first
            try:
                if await candidate.count() > 0:
                    file_input = candidate
                    break
            except Exception:
                continue
        if not file_input:
            logger.error("Could not locate Reel video file input")
            return False
        try:
            await file_input.set_input_files(valid_paths)
            logger.info("✓ Videos queued, waiting for processing...")
            return await self._wait_for_reel_media_ready(page)
        except Exception as exc:
            logger.exception("Failed to set Reel files: %s", exc)
            return False
    
    async def _wait_for_reel_media_ready(self, page: Page) -> bool:
        """Wait for Facebook to process Reel media uploads."""
        preview_selectors = [
            "video",
            "[data-testid*='reel']",
            "[data-testid*='preview']",
            "div[role='img']",
            "img[src*='fbcdn']",
        ]
        for attempt in range(60):
            for selector in preview_selectors:
                locator = page.locator(selector).first
                try:
                    if await locator.count() > 0 and await locator.is_visible():
                        logger.info("✓ Reel media preview detected (%s)", selector)
                        return True
                except Exception:
                    continue
            status_texts = ["Uploading", "Processing", "Finishing up"]
            for text in status_texts:
                try:
                    if await page.locator(f"text={text}").count() > 0:
                        logger.info("Reel media %s... (%d/60)", text.lower(), attempt + 1)
                        break
                except Exception:
                    continue
            await page.wait_for_timeout(1000)
        logger.error("Reel media never indicated as ready")
        return False
    
    async def _enter_reel_caption(self, page: Page, content: str) -> bool:
        """Enter caption text inside the Reel composer."""
        if not content or not content.strip():
            logger.info("No caption provided for Reel")
            return True
        caption_selectors = [
            "div[role='textbox'][aria-label*='caption']",
            "div[role='textbox'][aria-label*='Caption']",
            "textarea[aria-label*='caption']",
            "div[contenteditable='true'][data-lexical-editor='true']",
            "div[contenteditable='true'][aria-placeholder*='caption']",
        ]
        for selector in caption_selectors:
            try:
                locator = page.locator(selector).first
                if await locator.count() > 0 and await locator.is_visible():
                    logger.info("Entering Reel caption using %s", selector)
                    return await self._enter_text(page, locator, content)
            except Exception as exc:
                logger.debug("Caption selector %s failed: %s", selector, exc)
                continue
        logger.info("Falling back to intelligent text input finder for caption")
        text_input = await self.element_finder.find_text_input_intelligent(page)
        if text_input:
            return await self._enter_text(page, text_input, content)
        logger.error("Could not locate caption input")
        return False
    
    async def _publish_reel(self, page: Page) -> bool:
        """Click the Share button to publish the Reel."""
        logger.info("Looking for Reel Share button...")
        share_selectors = [
            "div[role='button']:has-text('Share reel')",
            "div[role='button']:has-text('Share now')",
            "button:has-text('Share reel')",
            "button:has-text('Share now')",
            "div[aria-label='Share'][role='button']",
        ]
        for attempt in range(40):
            for selector in share_selectors:
                try:
                    locator = page.locator(selector).first
                    if await locator.count() == 0 or not await locator.is_visible():
                        continue
                    aria_disabled = await locator.get_attribute("aria-disabled")
                    if aria_disabled and aria_disabled.lower() == "true":
                        logger.debug("Share button disabled, waiting...")
                        continue
                    logger.info("Clicking Reel share button: %s", selector)
                    await locator.click()
                    await page.wait_for_timeout(4000)
                    return True
                except Exception as exc:
                    logger.debug("Share selector %s failed: %s", selector, exc)
            if attempt % 5 == 0:
                logger.info("Waiting for Share button... (%d/40)", attempt + 1)
            await page.wait_for_timeout(1000)
        logger.error("Failed to locate enabled Share button")
        return False
    
    async def _verify_reel_post(self, page: Page, expected_content: str = "") -> bool:
        """Verify Reel publication via success indicators."""
        success_indicators = [
            "text=Your reel is now live",
            "text=Reel posted",
            "text=Your reel has been shared",
            "text=Check it out in your profile",
        ]
        for indicator in success_indicators:
            try:
                if await page.locator(indicator).count() > 0:
                    logger.info("✓ Reel success indicator found: %s", indicator)
                    return True
            except Exception:
                continue
        logger.info("Reel success indicators not found, falling back to generic verification")
        return await self._verify_post(page, expected_content)
    
    async def _enter_text(self, page: Page, text_input: Locator, content: str) -> bool:
        """Enter text using robust strategies for Facebook contenteditable editor."""
        logger.info(f"Attempting to enter text (length: {len(content)} chars)...")
        
        # Log element state for debugging
        try:
            count = await text_input.count()
            visible = await text_input.is_visible() if count > 0 else False
            editable = await text_input.is_editable() if count > 0 else False
            logger.info(f"Text input state: count={count}, visible={visible}, editable={editable}")
            
            if count > 1:
                logger.warning(f"Found {count} matching elements - may be typing into wrong one!")
        except Exception as e:
            logger.warning(f"Could not check element state: {e}")
        
        # Strategy 1: Proper focus + pressSequentially (best for contenteditable)
        try:
            logger.info("Strategy 1: Focus + pressSequentially...")
            await text_input.click()
            await page.wait_for_timeout(500)  # Stabilization wait
            await text_input.press_sequentially(content, delay=10)
            await page.wait_for_timeout(500)
            
            # Verify text was entered
            entered_text = await text_input.inner_text()
            if content[:20] in entered_text or len(entered_text) >= len(content) * 0.8:
                logger.info("✓ Text entered successfully with pressSequentially")
                return True
            else:
                logger.warning(f"Text verification failed: expected '{content[:30]}...', got '{entered_text[:30]}...'")
        except Exception as e:
            logger.warning(f"Strategy 1 failed: {e}")
        
        # Strategy 2: Clear first then type
        try:
            logger.info("Strategy 2: Clear and re-type...")
            await text_input.click()
            await page.wait_for_timeout(300)
            await text_input.press("Control+a")
            await text_input.press("Delete")
            await page.wait_for_timeout(200)
            await text_input.press_sequentially(content, delay=10)
            await page.wait_for_timeout(500)
            
            entered_text = await text_input.inner_text()
            if content[:20] in entered_text:
                logger.info("✓ Text entered successfully with clear+type")
                return True
        except Exception as e:
            logger.warning(f"Strategy 2 failed: {e}")
        
        # Strategy 3: Keyboard typing after explicit focus
        try:
            logger.info("Strategy 3: Explicit focus + keyboard.type...")
            await text_input.focus()
            await page.wait_for_timeout(300)
            await page.keyboard.type(content, delay=20)
            await page.wait_for_timeout(500)
            
            entered_text = await text_input.inner_text()
            if content[:20] in entered_text:
                logger.info("✓ Text entered successfully with keyboard.type")
                return True
        except Exception as e:
            logger.warning(f"Strategy 3 failed: {e}")
        
        # Strategy 4: JavaScript injection (last resort)
        try:
            logger.info("Strategy 4: JavaScript injection...")
            await self._javascript_type(page, text_input, content)
            await page.wait_for_timeout(500)
            
            entered_text = await text_input.inner_text()
            if content[:20] in entered_text or len(entered_text) > 0:
                logger.info("✓ Text entered successfully with JavaScript")
                return True
        except Exception as e:
            logger.warning(f"Strategy 4 failed: {e}")
        
        logger.error("All text entry strategies failed")
        return False
    
    async def _force_type(self, page: Page, text_input: Locator, content: str):
        """Force click and type with explicit focus."""
        await text_input.click(force=True)
        await page.wait_for_timeout(500)
        await text_input.press_sequentially(content, delay=15)
        await page.wait_for_timeout(300)
    
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
    
    async def _upload_media(self, page: Page, media_paths: list[str]) -> bool:
        """Upload media files directly without opening OS file picker."""
        try:
            # Debug screenshot before upload
            try:
                await page.screenshot(path="fb_before_upload.png")
                logger.info("Debug screenshot: fb_before_upload.png")
            except:
                pass
            
            # Verify files exist first
            valid_paths = []
            for path in media_paths:
                if Path(path).exists():
                    valid_paths.append(path)
                    logger.info(f"Found media file: {path}")
                else:
                    logger.warning(f"Media file not found: {path}")
            
            if not valid_paths:
                logger.error("No valid media files found")
                return False
            
            # Get the dialog context
            logger.info("Getting dialog context...")
            dialog = page.locator("div[role='dialog']").first
            dialog_count = await dialog.count()
            
            if dialog_count == 0:
                logger.error("No dialog found - cannot upload media")
                return False
            
            logger.info(f"✓ Found dialog, ready for direct file upload")
            
            # CRITICAL: Do NOT click any buttons - that opens the OS file picker
            # Instead, directly find or create a file input and set files on it
            
            file_input = None
            
            # Strategy 1: Look for existing hidden file input in dialog
            logger.info("Looking for hidden file input in dialog...")
            dialog_file = dialog.locator("input[type='file']").first
            if await dialog_file.count() > 0:
                logger.info("✓ Found existing file input in dialog")
                file_input = dialog_file
            
            # Strategy 2: Look for file input anywhere on page (might be in body)
            if not file_input:
                logger.info("Looking for file input on page...")
                page_file = page.locator("input[type='file']").first
                if await page_file.count() > 0:
                    logger.info("✓ Found file input on page")
                    file_input = page_file
            
            # Strategy 3: Inject a file input into the dialog (without clicking anything)
            if not file_input:
                logger.info("Creating hidden file input in dialog...")
                try:
                    await dialog.evaluate("""
                        (dialog) => {
                            // Remove any existing synthetic input
                            const existing = document.getElementById('__playwright_file_input');
                            if (existing) existing.remove();
                            
                            // Create new hidden file input
                            const input = document.createElement('input');
                            input.type = 'file';
                            input.id = '__playwright_file_input';
                            input.style.display = 'none';
                            input.style.visibility = 'hidden';
                            input.multiple = true;
                            
                            // Append to dialog
                            dialog.appendChild(input);
                            
                            // Also trigger any existing Facebook handlers
                            return true;
                        }
                    """)
                    await page.wait_for_timeout(500)
                    file_input = dialog.locator("#__playwright_file_input").first
                    if await file_input.count() > 0:
                        logger.info("✓ Created synthetic file input in dialog")
                except Exception as e:
                    logger.error(f"Could not create synthetic input: {e}")
            
            if not file_input:
                logger.error("Failed to find or create file input")
                return False
            
            # Upload files directly - this bypasses OS file picker
            logger.info(f"Uploading {len(valid_paths)} files directly...")
            uploaded_count = 0
            for path in valid_paths:
                try:
                    # Use set_input_files which directly sets the FileList without opening OS dialog
                    await file_input.set_input_files(path)
                    uploaded_count += 1
                    logger.info(f"✓ Set file: {Path(path).name}")
                    
                    # Trigger change event to notify Facebook
                    await file_input.evaluate("""
                        (el) => {
                            // Create a proper FileList with the files
                            const dt = new DataTransfer();
                            const files = el.files;
                            if (files && files.length > 0) {
                                for (let i = 0; i < files.length; i++) {
                                    dt.items.add(files[i]);
                                }
                            }
                            el.files = dt.files;
                            
                            // Dispatch events that Facebook listens for
                            el.dispatchEvent(new Event('change', { bubbles: true }));
                            el.dispatchEvent(new Event('input', { bubbles: true }));
                            
                            // Also try to find and trigger React handlers
                            const reactKey = Object.keys(el).find(k => k.startsWith('__react'));
                            if (reactKey && el[reactKey]) {
                                const props = el[reactKey];
                                if (props && props.onChange) {
                                    props.onChange({ target: el, currentTarget: el });
                                }
                            }
                            
                            // Look for parent form and submit
                            const form = el.closest('form');
                            if (form) {
                                form.dispatchEvent(new Event('change', { bubbles: true }));
                            }
                        }
                    """)
                    
                    await page.wait_for_timeout(3000)  # Give Facebook time to process
                except Exception as e:
                    logger.error(f"Failed to set file {path}: {e}")
            
            if uploaded_count == 0:
                logger.error("No media files were set successfully")
                return False
            
            logger.info(f"✓ Set {uploaded_count} files, waiting for them to appear...")
            
            # Debug screenshot after upload
            try:
                await page.screenshot(path="fb_after_upload.png")
                logger.info("Debug screenshot: fb_after_upload.png")
            except:
                pass
            
            # Verify media appears in composer - LENIENT MODE
            # If we successfully set files, give Facebook time to process even if detection fails
            logger.info("Waiting for media to appear in composer...")
            media_found = False
            
            for attempt in range(30):  # Wait up to 30 seconds
                # Check for media thumbnails/preview within dialog - EXPANDED selectors
                media_indicators = [
                    "img[src*='scontent']",  # Facebook CDN images
                    "img[src*='fbcdn']",
                    "img[src*='facebook']",
                    "video",
                    "[data-testid*='media']",
                    "[data-testid*='photo']",
                    "[data-testid*='video']",
                    "[data-testid*='attachment']",
                    "img[alt*='photo']",
                    "div[role='img']",
                    ".x1ll5l",  # Facebook image container class pattern
                    "[class*='attachment']",
                ]
                
                found = False
                for indicator in media_indicators:
                    try:
                        locator = dialog.locator(indicator).first
                        count = await locator.count()
                        if count > 0:
                            visible = await locator.is_visible()
                            if visible:
                                logger.info(f"✓ Media detected: {indicator}")
                                found = True
                                media_found = True
                                break
                    except:
                        continue
                
                # Check for processing indicators
                try:
                    processing = await dialog.locator("text=Processing").count()
                    uploading = await dialog.locator("text=Uploading").count()
                    loading = await dialog.locator("text=Loading").count()
                except:
                    processing = 0
                    uploading = 0
                    loading = 0
                
                if found and processing == 0 and uploading == 0 and loading == 0:
                    logger.info(f"✓ Media successfully attached after {attempt + 1} seconds")
                    return True
                
                # Early success: if processing/uploading text appears, media is being handled
                if uploading > 0 or processing > 0:
                    logger.info(f"Media is being processed (uploading/processing detected)")
                    media_found = True
                
                if attempt % 5 == 0:
                    logger.info(f"Waiting for media... {attempt + 1}/30 (processing: {processing}, uploading: {uploading})")
                
                await page.wait_for_timeout(1000)
            
            # LENIENT MODE: If we successfully set files but detection took too long, 
            # still consider it a success if files were uploaded
            if uploaded_count > 0 and media_found:
                logger.info("✓ Media files were set and processing was detected - considering upload successful")
                return True
            
            # Even more lenient: if files were set, assume success and let Post button handle it
            if uploaded_count > 0:
                logger.warning("✓ Media files were set but visual detection failed - proceeding anyway (lenient mode)")
                return True
            
            # Debug screenshot at failure
            try:
                await page.screenshot(path="fb_upload_failed.png")
                logger.info("Debug screenshot: fb_upload_failed.png")
            except:
                pass
                
            logger.error("Media upload failed - no files were set")
            return False
            
        except Exception as e:
            logger.exception(f"Media upload error: {e}")
            return False
    
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
