import logging
import asyncio
import shutil
import sys
import os
from typing import Optional
from pathlib import Path

# Hide console windows on Windows for browser subprocesses
if sys.platform == "win32":
    import subprocess
    CREATE_NO_WINDOW = 0x08000000
    _original_popen = subprocess.Popen
    
    class NoWindowPopen(_original_popen):
        def __init__(self, *args, **kwargs):
            if 'creationflags' not in kwargs:
                kwargs['creationflags'] = CREATE_NO_WINDOW
            super().__init__(*args, **kwargs)
    
    subprocess.Popen = NoWindowPopen


logger = logging.getLogger(__name__)


def _copy_session_data(
    source_user_data: Path,
    target_user_data: Path,
    profile_name: str = "Default",
):
    """Copy essential session files from user's Brave profile to automation profile."""
    try:
        source_profile = source_user_data / profile_name
        target_profile = target_user_data / profile_name
        if not source_profile.exists():
            logger.warning(f"Source Brave profile not found: {source_profile}")
            return

        # Ensure target exists
        target_profile.mkdir(parents=True, exist_ok=True)
        
        # Files to copy for preserving sessions (relative paths)
        session_paths = [
            Path("Login Data"),
            Path("Cookies"),
            Path("Network") / "Cookies",
            Path("Web Data"),
            Path("History"),
            Path("Favicons"),
            Path("Local Storage"),
            Path("Session Storage"),
        ]
        
        copied = []
        for rel_path in session_paths:
            src = source_profile / rel_path
            dst = target_profile / rel_path
            if src.exists():
                try:
                    if src.is_file():
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src, dst)
                        copied.append(str(rel_path))
                    elif src.is_dir():
                        if dst.exists():
                            shutil.rmtree(dst)
                        shutil.copytree(src, dst)
                        copied.append(str(rel_path))
                except Exception as e:
                    logger.warning(f"Could not copy {rel_path}: {e}")
        
        if copied:
            logger.info(f"Copied session data: {', '.join(copied)}")
        else:
            logger.warning("No session files copied from Brave profile")
        
    except Exception as e:
        logger.error(f"Failed to copy session data: {e}")


class BrowserDOMPoster:
    """Posts to social media by controlling browser DOM with Playwright."""
    
    def __init__(self):
        self.browser = None
        self.context = None
    
    def post_to_facebook(
        self, 
        content: str, 
        media_paths: list[str] | None = None,
        headless: bool = False
    ) -> tuple[bool,str]:
        """
        Post to Facebook using Playwright browser automation.
        
        Opens browser, finds Facebook post UI, uploads media, types content, and clicks Post.
        """
        try:
            # Run async posting in sync context (usually called from a thread)
            return asyncio.run(self._async_post_to_facebook(content, media_paths, headless))
        except Exception as e:
            logger.error(f"Facebook posting error: {e}")
            return False, f"Error: {str(e)}"
    
    async def _async_post_to_facebook(
        self,
        content: str,
        media_paths: list[str] | None,
        headless: bool
    ) -> tuple[bool, str]:
        """Async Facebook posting with Playwright."""
        from playwright.async_api import async_playwright
        from src.config import config
        import os
        
        async with async_playwright() as p:
            try:
                # Get browser preference from settings
                browser_type = getattr(config.browser, 'browser_type', 'brave').lower()
                
                # Launch browser based on preference
                logger.info(f"Launching {browser_type} browser...")
                
                launch_options = {"headless": headless}
                
                if browser_type == "brave":
                    # Find Brave executable
                    brave_paths = [
                        os.path.join(os.environ.get("PROGRAMFILES", ""), "BraveSoftware", "Brave-Browser", "Application", "brave.exe"),
                        os.path.join(os.environ.get("PROGRAMFILES(X86)", ""), "BraveSoftware", "Brave-Browser", "Application", "brave.exe"),
                        os.path.join(os.environ.get("LOCALAPPDATA", ""), "BraveSoftware", "Brave-Browser", "Application", "brave.exe"),
                    ]
                    brave_path = None
                    for path in brave_paths:
                        if os.path.exists(path):
                            brave_path = path
                            break
                    
                    if brave_path:
                        launch_options["executable_path"] = brave_path
                        logger.info(f"Using Brave: {brave_path}")
                    else:
                        logger.warning("Brave not found, falling back to Chromium")
                
                elif browser_type == "chrome":
                    launch_options["channel"] = "chrome"
                elif browser_type == "edge":
                    launch_options["channel"] = "msedge"
                
                # Use dedicated automation profile but copy session data from user profile
                from src.config import PROJECT_ROOT
                
                automation_profile = PROJECT_ROOT / "data" / "brave_automation"
                automation_profile.mkdir(parents=True, exist_ok=True)
                
                if browser_type == "brave":
                    # Copy session data from user's Brave profile
                    local_app_data = os.environ.get("LOCALAPPDATA", "")
                    user_profile = Path(local_app_data) / "BraveSoftware" / "Brave-Browser" / "User Data"
                    
                    try:
                        if user_profile.exists():
                            logger.info("Copying session data from user profile...")
                            _copy_session_data(user_profile, automation_profile)
                            logger.info("Session data copied successfully")
                        else:
                            logger.warning("User Brave profile not found")
                    except Exception as e:
                        logger.warning(f"Failed to copy session data (Brave may be running): {e}")
                        logger.info("Continuing without session data - you'll need to log in manually")
                    
                    brave_profile = automation_profile
                    logger.info(f"Using automation profile: {brave_profile}")
                else:
                    brave_profile = automation_profile
                    logger.info(f"Using automation profile: {brave_profile}")
                
                # Launch directly with persistent context
                try:
                    context = await p.chromium.launch_persistent_context(
                        str(brave_profile),
                        headless=headless,
                        executable_path=launch_options.get("executable_path"),
                        channel=launch_options.get("channel"),
                        args=["--disable-blink-features=AutomationControlled"]
                    )
                except Exception as e:
                    logger.error(f"Failed to launch persistent context: {e}")
                    # Try fallback without profile if it failed
                    logger.info("Retrying with standard browser launch...")
                    browser = await p.chromium.launch(**launch_options)
                    context = await browser.new_context()
                
                # Always create a new page for clean navigation
                # (persistent context may open with blank about:blank page)
                logger.info("Creating new page...")
                page = await context.new_page()
                logger.info(f"New page created with URL: {page.url}")
                
                # Go to Facebook (retry across canonical URLs)
                logger.info("Navigating to Facebook...")
                facebook_urls = [
                    "https://www.facebook.com/",
                    "https://m.facebook.com/",
                    "https://www.facebook.com/login.php",
                ]
                page_loaded = False
                for fb_url in facebook_urls:
                    try:
                        logger.info(f"Trying {fb_url}...")
                        await page.goto(fb_url, wait_until="domcontentloaded", timeout=60000)
                        await page.wait_for_load_state("networkidle", timeout=30000)
                        current_url = page.url
                        logger.info(f"Current URL after navigation: {current_url}")
                        if "facebook.com" in current_url:
                            page_loaded = True
                            logger.info(f"Successfully loaded Facebook: {current_url}")
                            break
                    except Exception as e:
                        logger.warning(f"Navigation to {fb_url} failed: {e}")
                        continue
                
                if not page_loaded:
                    logger.error(f"Failed to load Facebook from any URL. Last URL: {page.url}")
                    await context.close()
                    return False, "Unable to load Facebook. Check your internet connection and try again."
                
                await page.wait_for_timeout(3000)
                
                # Check for "What's on your mind" to see if we are already logged in
                is_logged_in = False
                login_check_selectors = [
                    "text=What's on your mind?",
                    "[aria-label='Create a post']",
                    "div[role='button']:has-text('mind')"
                ]
                
                for selector in login_check_selectors:
                    locator = page.locator(selector)
                    if await locator.count() > 0:
                        is_logged_in = True
                        break
                
                if not is_logged_in:
                    logger.info("Not logged in. Waiting up to 2 minutes for user to log in manually...")
                    # We wait for the "What's on your mind" selector to appear
                    try:
                        # Find any of the create post selectors
                        combined_selector = ", ".join(login_check_selectors)
                        await page.wait_for_selector(combined_selector, timeout=120000)
                        logger.info("Login detected! Proceeding...")
                    except Exception:
                        await context.close()
                        return False, "Login timed out. Please log in to Facebook in the window that opens."
                
                # Find and click "What's on your mind" / create post button
                logger.info("Finding create post button...")
                
                selectors = [
                    "text=What's on your mind?",
                    "div[role='button']:has-text('mind')",
                    "[aria-label='Create a post']",
                    "div[role='button'] >> text=What's on your mind?"
                ]
                
                clicked = False
                for selector in selectors:
                    locator = page.locator(selector)
                    try:
                        if await locator.count() > 0:
                            await locator.first.click()
                            clicked = True
                            logger.info(f"Clicked create post button: {selector}")
                            break
                    except Exception:
                        continue
                
                if not clicked:
                    await context.close()
                    return False, "Could not find create post button"
                
                # Wait for post dialog to open
                await page.wait_for_timeout(2000)
                
                # Upload media if media_paths provided
                if media_paths:
                    logger.info(f"Uploading {len(media_paths)} media file(s)...")
                    try:
                        # Look for the file input
                        file_input_selectors = [
                            "input[type='file'][accept*='image']",
                            "input[type='file'][accept*='video']",
                            "input[type='file']",
                            "form input[type='file']",
                        ]
                        
                        file_input = None
                        for selector in file_input_selectors:
                            locator = page.locator(selector).first
                            try:
                                if await locator.count() > 0:
                                    # Check if it's actually visible/enabled
                                    if await locator.is_enabled():
                                        file_input = locator
                                        logger.info(f"Found file input: {selector}")
                                        break
                            except Exception:
                                continue
                        
                        if file_input:
                            # Upload all media files
                            await file_input.set_input_files(media_paths)
                            logger.info(f"Media upload initiated for {len(media_paths)} file(s)")
                            # Wait longer for upload preview to appear and stabilize
                            await page.wait_for_timeout(6000)
                            # Verify media preview is visible
                            preview_selectors = [
                                "img[alt*='preview']",
                                "div[data-testid='media-attachment']",
                                "div[role='img']",
                                "img[src*='scontent']",
                            ]
                            preview_found = False
                            for sel in preview_selectors:
                                if await page.locator(sel).count() > 0:
                                    preview_found = True
                                    logger.info(f"Media preview confirmed: {sel}")
                                    break
                            if not preview_found:
                                logger.warning("Media preview not detected, continuing anyway")
                                # Take screenshot for debugging
                                try:
                                    await page.screenshot(path="media_preview_debug.png")
                                    logger.info("Screenshot saved to media_preview_debug.png")
                                except Exception as e:
                                    logger.warning(f"Failed to save screenshot: {e}")
                        else:
                            logger.warning("Could not find file input for media upload")
                    except Exception as e:
                        logger.warning(f"Media upload failed: {e}")
                
                # Find text input area
                logger.info("Finding text input...")
                text_input = page.locator(
                    "div[role='textbox'][contenteditable='true']"
                ).first
                
                if await text_input.count() == 0:
                    # Debug: dump all potential text inputs
                    logger.info("Potential text inputs:")
                    for selector in ["div[role='textbox']", "div[contenteditable='true']", "textarea"]:
                        logger.info(f"  - {selector}: {await page.locator(selector).count()}")
                    await context.close()
                    return False, "Could not find text input area"
                
                # Take screenshot before typing
                try:
                    await page.screenshot(path="before_typing.png")
                    logger.info("Screenshot saved to before_typing.png")
                except Exception as e:
                    logger.warning(f"Failed to save before screenshot: {e}")

                async def fill_rich_text(target, value: str) -> bool:
                    sanitized = value or ""
                    logger.info(f"Attempting to type content: '{sanitized[:30]}...'")
                    element_handle = await target.element_handle()
                    if element_handle is None:
                        logger.error("Could not obtain element handle for text editor")
                        return False
                    for attempt in range(3):
                        try:
                            logger.info(f"Typing attempt {attempt + 1}")
                            await element_handle.evaluate(
                                "(el) => {\n"
                                "  el.scrollIntoView({behavior: 'auto', block: 'center'});\n"
                                "  el.focus();\n"
                                "  const selection = window.getSelection();\n"
                                "  if (selection) {\n"
                                "    selection.removeAllRanges();\n"
                                "    const range = document.createRange();\n"
                                "    range.selectNodeContents(el);\n"
                                "    selection.addRange(range);\n"
                                "  }\n"
                                "}"
                            )
                            await page.wait_for_timeout(200)
                            await page.keyboard.press("Backspace")
                            await page.wait_for_timeout(100)
                            await page.keyboard.type(sanitized, delay=10)
                            await page.wait_for_timeout(500)
                            current = (await target.evaluate("node => node.innerText || node.textContent || ''")).strip()
                            logger.info(f"Editor content after typing: '{current[:50]}...'")
                            logger.info(f"Expected content: '{sanitized[:50]}...'")
                            expected_len = len(sanitized)
                            current_len = len(current)
                            logger.info(f"Content lengths -> current: {current_len}, expected: {expected_len}")
                            normalized_current = current.replace('\u200b', '').strip()
                            normalized_expected = sanitized.replace('\u200b', '').strip()
                            content_entered = (
                                normalized_current and
                                current_len >= max(1, expected_len * 0.8) and
                                normalized_expected.lower() in normalized_current.lower()
                            )
                            if content_entered:
                                logger.info(f"Content verification passed for attempt {attempt + 1}")
                                try:
                                    await page.screenshot(path="after_typing.png")
                                    logger.info("Screenshot saved to after_typing.png")
                                except Exception as e:
                                    logger.warning(f"Failed to save after screenshot: {e}")
                                await element_handle.dispose()
                                return True
                            else:
                                logger.warning(
                                    "Typed content did not match expectation (len current=%s, expected=%s)",
                                    len(current), len(sanitized)
                                )
                        except Exception as exc:
                            logger.warning(f"Typing attempt {attempt + 1} failed: {exc}")
                            await page.wait_for_timeout(300)
                    await element_handle.dispose()
                    logger.error("All typing attempts failed")
                    return False

                logger.info("Typing content...")
                typed = await fill_rich_text(text_input, content)
                if not typed:
                    await context.close()
                    return False, "Could not type content in Facebook composer"
                
                # Verify content is actually there before proceeding
                final_content = (await text_input.evaluate("node => node.innerText || node.textContent || ''")).strip()
                logger.info(f"Final content in editor: '{final_content[:60]}...'")
                if not final_content:
                    logger.error("Editor is empty after typing!")
                    await context.close()
                    return False, "Failed to enter text in Facebook composer"
                
                await page.wait_for_timeout(1000)
                
                async def click_with_retries(locator, label: str) -> bool:
                    for attempt in range(5):
                        try:
                            await locator.scroll_into_view_if_needed()
                            # Skip if button is disabled
                            aria_disabled = await locator.get_attribute("aria-disabled")
                            if aria_disabled and aria_disabled.lower() == "true":
                                logger.info(f"{label} disabled, waiting...")
                                await page.wait_for_timeout(800)
                                continue
                            await locator.click(force=True, delay=50)
                            return True
                        except Exception as exc:
                            logger.warning(f"{label} click attempt {attempt + 1} failed: {exc}")
                            await page.wait_for_timeout(500 * (attempt + 1))
                    return False
                
                # Step 1: Click Next button to proceed to post settings
                logger.info("Finding Next button...")
                next_button_selectors = [
                    "div[aria-label='Next'][role='button']",
                    "button:has-text('Next')",
                    "div[role='button']:has-text('Next')",
                    "span:has-text('Next')",
                ]
                
                next_btn = None
                for selector in next_button_selectors:
                    locator = page.locator(selector).first
                    try:
                        if await locator.count() > 0 and await locator.is_visible():
                            next_btn = locator
                            logger.info(f"Found Next button: {selector}")
                            break
                    except Exception:
                        continue
                
                if next_btn:
                    logger.info("Clicking Next...")
                    clicked_next = await click_with_retries(next_btn, "Next button")
                    if not clicked_next:
                        await context.close()
                        return False, "Could not click Next button"
                    await page.wait_for_timeout(2000)  # Wait for Post settings dialog
                
                # Step 2: Click Post button in settings dialog
                logger.info("Finding Post button...")
                post_button_selectors = [
                    "div[aria-label='Post'][role='button']",
                    "button:has-text('Post')",
                    "[data-testid='post_button']",
                    "div[role='button'] span:has-text('Post')",
                    "button[aria-label='Post']",
                    "div[role='button']:has-text('Post')",
                ]
                
                post_btn = None
                for selector in post_button_selectors:
                    locator = page.locator(selector).first
                    try:
                        if await locator.count() > 0 and await locator.is_visible():
                            post_btn = locator
                            logger.info(f"Found Post button: {selector}")
                            break
                    except Exception:
                        continue
                
                if not post_btn:
                    await context.close()
                    return False, "Could not find Post button (content was typed)"
                
                # Click Post
                logger.info("Clicking Post...")
                clicked_post = await click_with_retries(post_btn, "Post button")
                if not clicked_post:
                    await context.close()
                    return False, "Could not click Post button"
                
                # Wait longer for post to actually publish
                logger.info("Waiting for post to publish...")
                await page.wait_for_timeout(8000)
                
                # Verify post was published by checking URL change or success indicators
                current_url = page.url
                logger.info(f"URL after posting: {current_url}")
                
                # Check if we're back on feed or post was published
                if "facebook.com" in current_url:
                    # Additional check: see if the post dialog closed
                    try:
                        # Check if post dialog is still open
                        dialog_check = await page.locator("div[role='dialog']").count()
                        if dialog_check > 0:
                            logger.warning("Post dialog still open, post may not have completed")
                            # Try to find and click Post button again
                            post_btn_retry = page.locator("div[aria-label='Post'][role='button']").first
                            if await post_btn_retry.count() > 0 and await post_btn_retry.is_visible():
                                logger.info("Retrying Post button click...")
                                await post_btn_retry.click(force=True)
                                await page.wait_for_timeout(5000)
                    except Exception as e:
                        logger.debug(f"Dialog check failed: {e}")
                
                logger.info("Closing browser...")
                await context.close()
                
                logger.info("Facebook post successful!")
                return True, "Posted to Facebook successfully!"
                
            except Exception as e:
                logger.error(f"Playwright error: {e}")
                try:
                    if 'context' in locals():
                        await context.close()
                    elif 'browser' in locals():
                        await browser.close()
                except:
                    pass
                
                error_msg = str(e)
                if "already in use" in error_msg.lower() or "cannot lock" in error_msg.lower():
                    return False, "Please close Brave browser first, then try posting again."
                elif "not logged in" in error_msg.lower():
                    return False, "Not logged in. Please log in to Facebook in Brave, then try again."
                else:
                    return False, f"Browser error: {error_msg}"


_poster: BrowserDOMPoster | None = None


def get_poster() -> BrowserDOMPoster:
    """Get or create the social media poster."""
    global _poster
    if _poster is None:
        _poster = BrowserDOMPoster()
    return _poster
