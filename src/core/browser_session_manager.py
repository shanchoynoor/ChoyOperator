"""
Browser Session Manager - Simple cookie-based session persistence.

Captures browser cookies after manual login and reuses them for posting.
Works with any browser (Brave, Chrome, etc.) without needing API keys.
"""

import json
import logging
import asyncio
import os
import sys
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List

from playwright.async_api import async_playwright

from src.config import PROJECT_ROOT
from src.data.encryption import get_encryption

logger = logging.getLogger(__name__)


@dataclass
class BrowserSession:
    """Stored browser session with cookies."""
    platform: str
    cookies: List[dict]
    user_agent: str
    user_name: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    last_used: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        return {
            "platform": self.platform,
            "cookies": self.cookies,
            "user_agent": self.user_agent,
            "user_name": self.user_name,
            "created_at": self.created_at.isoformat(),
            "last_used": self.last_used.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "BrowserSession":
        return cls(
            platform=data["platform"],
            cookies=data.get("cookies", []),
            user_agent=data.get("user_agent", ""),
            user_name=data.get("user_name"),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
            last_used=datetime.fromisoformat(data.get("last_used", datetime.now().isoformat())),
        )


@dataclass
class BrowserConfig:
    """Browser configuration for a platform."""
    platform: str
    browser_type: str  # "brave", "chrome", "firefox", etc.
    executable_path: str
    is_default: bool = False
    
    def to_dict(self) -> dict:
        return {
            "platform": self.platform,
            "browser_type": self.browser_type,
            "executable_path": self.executable_path,
            "is_default": self.is_default,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "BrowserConfig":
        return cls(
            platform=data["platform"],
            browser_type=data.get("browser_type", "brave"),
            executable_path=data["executable_path"],
            is_default=data.get("is_default", False),
        )


class BrowserSessionManager:
    """
    Manages browser sessions and cookie-based authentication.
    
    Simple workflow:
    1. User logs in via browser (manual)
    2. App captures cookies automatically
    3. Cookies saved encrypted
    4. Future posts reuse cookies (no re-login needed)
    """
    
    SESSIONS_FILE = PROJECT_ROOT / "data" / "browser_sessions.enc"
    BROWSER_CONFIG_FILE = PROJECT_ROOT / "data" / "browser_config.json"
    
    PLATFORM_URLS = {
        "facebook": {
            "login_url": "https://www.facebook.com/login",
            "home_url": "https://www.facebook.com/",
            "session_cookie": "c_user",  # Facebook user ID cookie
        },
        "twitter": {
            "login_url": "https://twitter.com/login",
            "home_url": "https://twitter.com/home",
            "session_cookie": "auth_token",
        },
        "linkedin": {
            "login_url": "https://www.linkedin.com/login",
            "home_url": "https://www.linkedin.com/feed",
            "session_cookie": "li_at",
        },
    }
    
    def __init__(self):
        self.encryption = get_encryption()
        self.sessions: Dict[str, BrowserSession] = {}
        self.browser_configs: Dict[str, BrowserConfig] = {}
        self._load_sessions()
        self._load_browser_configs()
    
    def _load_sessions(self):
        """Load saved sessions from encrypted file."""
        if not self.SESSIONS_FILE.exists():
            return
        
        try:
            encrypted = self.SESSIONS_FILE.read_bytes()
            decrypted = self.encryption.decrypt(encrypted)
            data = json.loads(decrypted)
            
            for platform, session_data in data.items():
                self.sessions[platform] = BrowserSession.from_dict(session_data)
            
            logger.info(f"Loaded {len(self.sessions)} browser sessions")
        except Exception as e:
            logger.error(f"Failed to load sessions: {e}")
    
    def _save_sessions(self):
        """Save sessions to encrypted file."""
        try:
            self.SESSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {platform: session.to_dict() for platform, session in self.sessions.items()}
            encrypted = self.encryption.encrypt(json.dumps(data))
            self.SESSIONS_FILE.write_bytes(encrypted)
            logger.info("Browser sessions saved")
        except Exception as e:
            logger.error(f"Failed to save sessions: {e}")
    
    def _load_browser_configs(self):
        """Load browser configurations."""
        if not self.BROWSER_CONFIG_FILE.exists():
            # Auto-detect browsers
            self._auto_detect_browsers()
            return
        
        try:
            data = json.loads(self.BROWSER_CONFIG_FILE.read_text())
            for platform, config_data in data.items():
                self.browser_configs[platform] = BrowserConfig.from_dict(config_data)
            logger.info(f"Loaded browser configs for {len(self.browser_configs)} platforms")
        except Exception as e:
            logger.error(f"Failed to load browser configs: {e}")
            self._auto_detect_browsers()
    
    def _save_browser_configs(self):
        """Save browser configurations."""
        try:
            self.BROWSER_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {platform: config.to_dict() for platform, config in self.browser_configs.items()}
            self.BROWSER_CONFIG_FILE.write_text(json.dumps(data, indent=2))
            logger.info("Browser configs saved")
        except Exception as e:
            logger.error(f"Failed to save browser configs: {e}")
    
    def _auto_detect_browsers(self):
        """Auto-detect available browsers on the system."""
        detected = []
        browser_paths = self._get_default_browser_paths()
        
        for browser_type, paths in browser_paths.items():
            for raw_path in paths:
                path = Path(raw_path).expanduser()
                if path.exists():
                    detected.append({
                        "type": browser_type,
                        "path": str(path),
                    })
                    break
        
        if detected:
            logger.info(f"Auto-detected browsers: {[b['type'] for b in detected]}")
            for platform in self.PLATFORM_URLS.keys():
                self.browser_configs[platform] = BrowserConfig(
                    platform=platform,
                    browser_type=detected[0]["type"],
                    executable_path=detected[0]["path"],
                    is_default=True,
                )
            self._save_browser_configs()
        else:
            logger.warning("No browsers auto-detected. Please set a browser path in settings.")

    def _get_default_browser_paths(self) -> dict[str, list[str]]:
        """Return common browser install paths for the current OS."""
        if sys.platform.startswith("darwin"):
            return {
                "brave": [
                    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
                    "/Applications/Brave Browser.app/Contents/MacOS/Brave",
                ],
                "chrome": [
                    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                    "/Applications/Chromium.app/Contents/MacOS/Chromium",
                ],
                "firefox": [
                    "/Applications/Firefox.app/Contents/MacOS/firefox",
                ],
                "edge": [
                    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
                ],
            }
        if os.name == "nt":
            program_files = os.environ.get("PROGRAMFILES", r"C:\\Program Files")
            program_files_x86 = os.environ.get("PROGRAMFILES(X86)", r"C:\\Program Files (x86)")
            return {
                "brave": [
                    fr"{program_files}\\BraveSoftware\\Brave-Browser\\Application\\brave.exe",
                    fr"{program_files_x86}\\BraveSoftware\\Brave-Browser\\Application\\brave.exe",
                ],
                "chrome": [
                    fr"{program_files}\\Google\\Chrome\\Application\\chrome.exe",
                    fr"{program_files_x86}\\Google\\Chrome\\Application\\chrome.exe",
                ],
                "edge": [
                    fr"{program_files}\\Microsoft\\Edge\\Application\\msedge.exe",
                    fr"{program_files_x86}\\Microsoft\\Edge\\Application\\msedge.exe",
                ],
                "firefox": [
                    fr"{program_files}\\Mozilla Firefox\\firefox.exe",
                    fr"{program_files_x86}\\Mozilla Firefox\\firefox.exe",
                ],
            }
        # Linux / other unix
        return {
            "brave": [
                "/usr/bin/brave-browser",
                "/snap/bin/brave",
            ],
            "chrome": [
                "/usr/bin/google-chrome",
                "/usr/bin/chromium-browser",
            ],
            "edge": [
                "/usr/bin/microsoft-edge",
            ],
            "firefox": [
                "/usr/bin/firefox",
            ],
        }
    
    def get_available_browsers(self) -> List[dict]:
        """Get list of available browsers."""
        browsers = []
        browser_paths = {
            "brave": [
                "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
                "/Applications/Brave Browser.app/Contents/MacOS/Brave",
            ],
            "chrome": [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            ],
            "firefox": [
                "/Applications/Firefox.app/Contents/MacOS/firefox",
            ],
            "edge": [
                "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            ],
        }
        
        for browser_type, paths in browser_paths.items():
            for path in paths:
                if Path(path).exists():
                    browsers.append({
                        "type": browser_type,
                        "name": browser_type.title(),
                        "path": path,
                    })
                    break
        
        return browsers
    
    def set_browser_for_platform(self, platform: str, browser_type: str, executable_path: str):
        """Set preferred browser for a platform."""
        self.browser_configs[platform] = BrowserConfig(
            platform=platform,
            browser_type=browser_type,
            executable_path=executable_path,
            is_default=True,
        )
        self._save_browser_configs()
        logger.info(f"Set {browser_type} as browser for {platform}")
    
    def has_session(self, platform: str) -> bool:
        """Check if we have a saved session for platform."""
        return platform in self.sessions and len(self.sessions[platform].cookies) > 0
    
    def get_session(self, platform: str) -> Optional[BrowserSession]:
        """Get saved session for platform."""
        return self.sessions.get(platform)
    
    async def authenticate(self, platform: str, headless: bool = False) -> tuple[bool, str]:
        """
        Authenticate with a platform by capturing browser session.
        
        Opens browser, user logs in manually, app captures cookies.
        
        Args:
            platform: Platform to authenticate (facebook, twitter, linkedin)
            headless: Whether to run browser headless
            
        Returns:
            (success: bool, message: str)
        """
        if platform not in self.PLATFORM_URLS:
            return False, f"Unsupported platform: {platform}"
        
        platform_config = self.PLATFORM_URLS[platform]
        browser_config = self.browser_configs.get(platform)
        
        if not browser_config:
            return False, "No browser configured. Please set a browser first."
        
        logger.info(f"Starting authentication for {platform} using {browser_config.browser_type}")
        browser = None
        
        async with async_playwright() as p:
            try:
                # Launch browser
                browser = await p.chromium.launch(
                    headless=headless,
                    executable_path=browser_config.executable_path,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-first-run",
                    ]
                )
                
                context = await browser.new_context(viewport={"width": 1280, "height": 800})
                page = await context.new_page()
                page.set_default_timeout(60000)
                
                # Navigate to login page
                logger.info(f"Opening {platform} login page...")
                await page.goto(platform_config["login_url"], wait_until="domcontentloaded")
                
                # Wait for user to complete login
                logger.info("Waiting for login... (max 3 minutes)")
                max_wait = 180  # seconds
                check_interval = 3
                
                for i in range(max_wait // check_interval):
                    await page.wait_for_timeout(check_interval * 1000)
                    
                    # Check if logged in by looking for session cookie
                    cookies = await context.cookies()
                    session_cookie = None
                    
                    for cookie in cookies:
                        if cookie.get("name") == platform_config["session_cookie"]:
                            session_cookie = cookie
                            break
                    
                    if session_cookie:
                        logger.info(f"✓ Login detected for {platform}!")
                        
                        # Try to get user name
                        user_name = None
                        try:
                            if platform == "facebook":
                                # Navigate to profile to get name
                                await page.goto("https://www.facebook.com/me")
                                await page.wait_for_timeout(2000)
                                # Look for profile name in various places
                                selectors = ["h1", "[role='main'] h2", "[data-testid='profile_name']"]
                                for selector in selectors:
                                    try:
                                        elem = page.locator(selector).first
                                        if await elem.count() > 0:
                                            text = await elem.inner_text()
                                            if text and len(text) < 100:
                                                user_name = text.strip()
                                                break
                                    except:
                                        continue
                        except Exception as e:
                            logger.debug(f"Could not get user name: {e}")
                        
                        # Save session
                        all_cookies = [{k: v for k, v in c.items()} for c in cookies]
                        
                        session = BrowserSession(
                            platform=platform,
                            cookies=all_cookies,
                            user_agent=await page.evaluate("() => navigator.userAgent"),
                            user_name=user_name,
                        )
                        
                        self.sessions[platform] = session
                        self._save_sessions()
                        
                        await browser.close()
                        
                        msg = f"Successfully authenticated with {platform.title()}"
                        if user_name:
                            msg += f" as {user_name}"
                        return True, msg
                
                await browser.close()
                return False, "Login timeout - please complete login within 3 minutes"
                
            except Exception as e:
                logger.error(f"Authentication error: {e}")
                if browser:
                    try:
                        await browser.close()
                    except:
                        pass
                return False, f"Authentication failed: {str(e)}"
    
    async def create_context_with_session(self, platform: str, p) -> tuple[Optional[any], Optional[str]]:
        """
        Create browser context with saved session cookies.
        
        Args:
            platform: Platform to create context for
            p: Playwright instance
            
        Returns:
            (context, error_message)
        """
        if not self.has_session(platform):
            return None, f"No saved session for {platform}. Please authenticate first."
        
        session = self.sessions[platform]
        browser_config = self.browser_configs.get(platform)
        
        if not browser_config:
            return None, "No browser configured"
        
        try:
            # Launch browser
            browser = await p.chromium.launch(
                headless=False,
                executable_path=browser_config.executable_path,
                args=["--disable-blink-features=AutomationControlled"],
            )
            
            # Create context with saved cookies
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent=session.user_agent,
            )
            
            # Add cookies
            await context.add_cookies(session.cookies)
            
            # Update last used
            session.last_used = datetime.now()
            self._save_sessions()
            
            return context, None
            
        except Exception as e:
            logger.error(f"Failed to create context: {e}")
            return None, f"Failed to restore session: {str(e)}"
    
    def get_stored_accounts(self) -> List[dict]:
        """Get list of stored authenticated accounts."""
        accounts = []
        for platform, session in self.sessions.items():
            accounts.append({
                "platform": platform,
                "user": session.user_name or "Unknown",
                "browser": self.browser_configs.get(platform, {}).browser_type or "Unknown",
                "created": session.created_at.strftime("%Y-%m-%d %H:%M"),
                "last_used": session.last_used.strftime("%Y-%m-%d %H:%M"),
            })
        return accounts
    
    def logout(self, platform: str) -> bool:
        """Logout from platform and clear session."""
        if platform in self.sessions:
            del self.sessions[platform]
            self._save_sessions()
            logger.info(f"Logged out from {platform}")
            return True
        return False
    
    def clear_all_sessions(self):
        """Clear all saved sessions."""
        self.sessions.clear()
        self._save_sessions()
        logger.info("All sessions cleared")


# Singleton instance
_session_manager: Optional[BrowserSessionManager] = None


def get_session_manager() -> BrowserSessionManager:
    """Get or create the session manager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = BrowserSessionManager()
    return _session_manager
