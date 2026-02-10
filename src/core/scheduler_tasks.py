"""
Scheduler Tasks - Executable functions for scheduled jobs.

These functions are called by the scheduler when jobs execute.
"""

import logging
from pathlib import Path

from src.core.platforms import FacebookPlatform, XPlatform, LinkedInPlatform, YouTubePlatform
from src.core.platforms.base import Credentials, PostStatus
from src.core.social_poster import get_poster
from src.data.database import get_database
from src.data.models import Account, ScheduledPost, PostStatusEnum
from src.data.encryption import get_encryption


logger = logging.getLogger(__name__)


PLATFORM_CLASSES = {
    "facebook": FacebookPlatform,
    "x": XPlatform,
    "linkedin": LinkedInPlatform,
    "youtube": YouTubePlatform,
}


def execute_scheduled_post(
    platform: str,
    account_id: int,
    content: str,
    media_paths: list[str],
) -> dict:
    """
    Execute a scheduled post.
    
    This function is called by the scheduler when a job fires.
    
    Args:
        platform: Target platform name
        account_id: Account ID to use
        content: Post content
        media_paths: List of media file paths
        
    Returns:
        Result dict with status and message
    """
    platform_key = (platform or "").lower()
    logger.info(f"Executing scheduled post for {platform_key or platform}, account {account_id}")
    
    try:
        if platform_key == "facebook":
            poster = get_poster()
            success, message = poster.post_to_facebook(content, media_paths, headless=True)
            return {
                "status": "success" if success else "failed",
                "message": message,
                "post_url": None,
            }
        
        # Get the platform class
        platform_class = PLATFORM_CLASSES.get(platform_key)
        if not platform_class:
            return {
                "status": "failed",
                "message": f"Unknown platform: {platform}"
            }
        
        # Get account credentials from database
        db = get_database()
        account = db.get_account(account_id)
        
        if not account:
            return {
                "status": "failed",
                "message": f"Account {account_id} not found"
            }
        
        # Initialize platform driver
        driver = platform_class()
        session_restored = False
        try:
            session_restored = driver.try_restore_session()
        except Exception as restore_err:
            logger.warning("Failed to restore %s session: %s", platform_key, restore_err)
        
        if not session_restored:
            if not account.encrypted_password:
                return {
                    "status": "failed",
                    "message": "Account has no stored credentials. Please reconnect and save login info."
                }
            encryption = get_encryption()
            credentials = Credentials(
                username=account.username,
                password=account.get_decrypted_password(encryption)
            )
            if not driver.login(credentials):
                return {
                    "status": "failed",
                    "message": "Failed to login to platform"
                }
        
        # Convert media paths to Path objects
        media = [Path(p) for p in media_paths if Path(p).exists()]
        
        # Create the post
        result = driver.create_post(content, media)
        
        # Close browser
        driver.browser.close()
        
        # Return result
        return {
            "status": result.status.value,
            "message": result.message,
            "post_url": result.post_url,
        }
        
    except Exception as e:
        logger.exception(f"Error executing scheduled post: {e}")
        return {
            "status": "failed",
            "message": str(e)
        }
