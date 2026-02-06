"""
Browser Connect - Simple browser-based session capture.

Opens user's default browser for login, captures session via manual confirmation.
"""

import webbrowser
import json
import logging
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Callable

from src.config import PROJECT_ROOT
from src.data.encryption import get_encryption

logger = logging.getLogger(__name__)


class SocialPlatform(Enum):
    """Supported social media platforms."""
    FACEBOOK = "facebook"
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    YOUTUBE = "youtube"


@dataclass
class ConnectedAccount:
    """Represents a connected social media account."""
    platform: SocialPlatform
    display_name: str
    connected_at: datetime
    
    def to_dict(self) -> dict:
        return {
            "platform": self.platform.value,
            "display_name": self.display_name,
            "connected_at": self.connected_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ConnectedAccount":
        return cls(
            platform=SocialPlatform(data["platform"]),
            display_name=data["display_name"],
            connected_at=datetime.fromisoformat(data["connected_at"]),
        )


PLATFORM_CONFIG = {
    SocialPlatform.FACEBOOK: {
        "name": "Facebook",
        "login_url": "https://www.facebook.com/",
        "color": "#1877f2",
    },
    SocialPlatform.TWITTER: {
        "name": "Twitter / X",
        "login_url": "https://twitter.com/login",
        "color": "#1da1f2",
    },
    SocialPlatform.LINKEDIN: {
        "name": "LinkedIn",
        "login_url": "https://www.linkedin.com/login",
        "color": "#0077b5",
    },
    SocialPlatform.YOUTUBE: {
        "name": "YouTube",
        "login_url": "https://www.youtube.com/",
        "color": "#ff0000",
    },
}


class BrowserConnect:
    """
    Handles browser-based social media account connection.
    
    Opens the user's default browser for login.
    User confirms when done, and the account is marked as connected.
    """
    
    ACCOUNTS_FILE = PROJECT_ROOT / "data" / "connected_accounts.json"
    
    def __init__(self):
        self.encryption = get_encryption()
        self.accounts: dict[str, ConnectedAccount] = {}
        self._load_accounts()
    
    def _load_accounts(self):
        """Load saved accounts."""
        if not self.ACCOUNTS_FILE.exists():
            return
        
        try:
            data = json.loads(self.ACCOUNTS_FILE.read_text())
            
            for key, acc_data in data.items():
                self.accounts[key] = ConnectedAccount.from_dict(acc_data)
            
            logger.info(f"Loaded {len(self.accounts)} connected accounts")
        except Exception as e:
            logger.error(f"Failed to load accounts: {e}")
    
    def _save_accounts(self):
        """Save accounts to file."""
        try:
            self.ACCOUNTS_FILE.parent.mkdir(parents=True, exist_ok=True)
            
            data = {key: acc.to_dict() for key, acc in self.accounts.items()}
            self.ACCOUNTS_FILE.write_text(json.dumps(data, indent=2))
            
            logger.info("Accounts saved")
        except Exception as e:
            logger.error(f"Failed to save accounts: {e}")
    
    def get_connected_accounts(self) -> list[ConnectedAccount]:
        """Get all connected accounts."""
        return list(self.accounts.values())
    
    def is_connected(self, platform: SocialPlatform) -> bool:
        """Check if platform is connected."""
        return platform.value in self.accounts
    
    def open_login_page(self, platform: SocialPlatform) -> bool:
        """
        Open the platform's login page in the default browser.
        
        Args:
            platform: Platform to open
            
        Returns:
            True if browser was opened successfully
        """
        platform_config = PLATFORM_CONFIG.get(platform)
        if not platform_config:
            logger.error(f"Unsupported platform: {platform}")
            return False
        
        try:
            logger.info(f"Opening {platform.value} login in browser...")
            webbrowser.open(platform_config["login_url"])
            return True
        except Exception as e:
            logger.error(f"Failed to open browser: {e}")
            return False
    
    def confirm_connection(
        self,
        platform: SocialPlatform,
        display_name: str = "",
    ) -> ConnectedAccount:
        """
        Mark an account as connected after user confirms login.
        
        Args:
            platform: Platform that was connected
            display_name: Optional display name for the account
            
        Returns:
            The connected account object
        """
        config = PLATFORM_CONFIG.get(platform, {})
        
        account = ConnectedAccount(
            platform=platform,
            display_name=display_name or config.get("name", platform.value.title()),
            connected_at=datetime.now(),
        )
        
        self.accounts[platform.value] = account
        self._save_accounts()
        
        logger.info(f"Connected {platform.value}")
        return account
    
    def disconnect(self, platform: SocialPlatform):
        """Disconnect/remove an account."""
        if platform.value in self.accounts:
            del self.accounts[platform.value]
            self._save_accounts()
            logger.info(f"Disconnected {platform.value}")


# Singleton instance
_browser_connect: BrowserConnect | None = None


def get_browser_connect() -> BrowserConnect:
    """Get or create the browser connect instance."""
    global _browser_connect
    if _browser_connect is None:
        _browser_connect = BrowserConnect()
    return _browser_connect
