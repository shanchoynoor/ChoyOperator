"""
Facebook OAuth Poster - Uses Facebook Graph API with OAuth tokens.

Posts to Facebook Pages using proper OAuth authentication.
"""

import logging
import requests
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

from src.core.oauth_manager import get_oauth_manager, OAuthPlatform, OAuthToken

logger = logging.getLogger(__name__)


class PostType(Enum):
    """Facebook post types."""
    TEXT = "text"
    PHOTO = "photo"
    VIDEO = "video"
    LINK = "link"


@dataclass
class FacebookPostResult:
    """Result of a Facebook post attempt."""
    success: bool
    post_id: str | None = None
    message: str = ""
    error_code: str | None = None


class FacebookOAuthPoster:
    """
    Posts to Facebook using Graph API with OAuth tokens.
    
    Requires a Facebook App with the following permissions:
    - pages_manage_posts
    - pages_read_engagement
    """
    
    GRAPH_API_URL = "https://graph.facebook.com/v18.0"
    
    def __init__(self, access_token: str | None = None):
        """
        Initialize Facebook poster.
        
        Args:
            access_token: Optional OAuth access token. If not provided,
                         will try to get from OAuth manager.
        """
        self.oauth_manager = get_oauth_manager()
        self._access_token = access_token
        self._page_tokens: dict[str, str] = {}  # page_id -> page_token
    
    @property
    def access_token(self) -> str | None:
        """Get the current access token."""
        if self._access_token:
            return self._access_token
        
        token = self.oauth_manager.get_token(OAuthPlatform.FACEBOOK)
        return token.access_token if token else None
    
    def is_authenticated(self) -> bool:
        """Check if we have a valid access token."""
        return self.access_token is not None
    
    def authenticate(
        self, 
        app_id: str, 
        app_secret: str,
        on_complete: callable = None
    ) -> bool:
        """
        Start OAuth authentication flow.
        
        Opens browser for user to login to Facebook.
        
        Args:
            app_id: Facebook App ID
            app_secret: Facebook App Secret
            on_complete: Callback when auth completes
            
        Returns:
            True if authentication successful
        """
        def on_success(token):
            self._access_token = token.access_token
            if on_complete:
                on_complete(True, None)
        
        def on_error(error):
            if on_complete:
                on_complete(False, error)
        
        token = self.oauth_manager.authenticate(
            platform=OAuthPlatform.FACEBOOK,
            client_id=app_id,
            client_secret=app_secret,
            on_success=on_success,
            on_error=on_error,
        )
        
        return token is not None
    
    def get_pages(self) -> list[dict]:
        """
        Get list of Facebook Pages the user manages.
        
        Returns:
            List of page info dicts with 'id', 'name', 'access_token'
        """
        if not self.access_token:
            logger.error("Not authenticated")
            return []
        
        try:
            response = requests.get(
                f"{self.GRAPH_API_URL}/me/accounts",
                params={
                    "access_token": self.access_token,
                    "fields": "id,name,access_token",
                },
                timeout=30,
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to get pages: {response.text}")
                return []
            
            data = response.json()
            pages = data.get("data", [])
            
            # Cache page tokens
            for page in pages:
                self._page_tokens[page["id"]] = page["access_token"]
            
            return pages
            
        except Exception as e:
            logger.error(f"Error getting pages: {e}")
            return []
    
    def post_to_page(
        self,
        page_id: str,
        message: str,
        link: str | None = None,
        photo_path: Path | None = None,
    ) -> FacebookPostResult:
        """
        Post to a Facebook Page.
        
        Args:
            page_id: The Page ID to post to
            message: Post text content
            link: Optional link to share
            photo_path: Optional photo to upload
            
        Returns:
            FacebookPostResult with success status and post ID
        """
        # Get page access token
        page_token = self._page_tokens.get(page_id)
        if not page_token:
            # Try to fetch pages to get token
            self.get_pages()
            page_token = self._page_tokens.get(page_id)
        
        if not page_token:
            return FacebookPostResult(
                success=False,
                message=f"No access token for page {page_id}",
                error_code="NO_PAGE_TOKEN"
            )
        
        try:
            if photo_path and photo_path.exists():
                return self._post_photo(page_id, page_token, message, photo_path)
            else:
                return self._post_text(page_id, page_token, message, link)
                
        except Exception as e:
            logger.error(f"Error posting to page: {e}")
            return FacebookPostResult(
                success=False,
                message=str(e),
                error_code="POST_ERROR"
            )
    
    def _post_text(
        self,
        page_id: str,
        page_token: str,
        message: str,
        link: str | None = None,
    ) -> FacebookPostResult:
        """Post text/link to page."""
        data = {
            "message": message,
            "access_token": page_token,
        }
        
        if link:
            data["link"] = link
        
        response = requests.post(
            f"{self.GRAPH_API_URL}/{page_id}/feed",
            data=data,
            timeout=30,
        )
        
        result = response.json()
        
        if "id" in result:
            return FacebookPostResult(
                success=True,
                post_id=result["id"],
                message="Post created successfully"
            )
        else:
            error = result.get("error", {})
            return FacebookPostResult(
                success=False,
                message=error.get("message", "Unknown error"),
                error_code=str(error.get("code", "UNKNOWN"))
            )
    
    def _post_photo(
        self,
        page_id: str,
        page_token: str,
        message: str,
        photo_path: Path,
    ) -> FacebookPostResult:
        """Post photo to page."""
        with open(photo_path, "rb") as photo:
            response = requests.post(
                f"{self.GRAPH_API_URL}/{page_id}/photos",
                data={
                    "message": message,
                    "access_token": page_token,
                },
                files={"source": photo},
                timeout=60,
            )
        
        result = response.json()
        
        if "id" in result:
            return FacebookPostResult(
                success=True,
                post_id=result["id"],
                message="Photo posted successfully"
            )
        else:
            error = result.get("error", {})
            return FacebookPostResult(
                success=False,
                message=error.get("message", "Unknown error"),
                error_code=str(error.get("code", "UNKNOWN"))
            )
    
    def verify_token(self) -> dict | None:
        """
        Verify the current access token is valid.
        
        Returns:
            Token debug info if valid, None if invalid
        """
        if not self.access_token:
            return None
        
        try:
            response = requests.get(
                f"{self.GRAPH_API_URL}/debug_token",
                params={
                    "input_token": self.access_token,
                    "access_token": self.access_token,
                },
                timeout=30,
            )
            
            if response.status_code == 200:
                data = response.json().get("data", {})
                if data.get("is_valid"):
                    return data
            
            return None
            
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            return None


# Convenience function
def get_facebook_poster() -> FacebookOAuthPoster:
    """Get a Facebook OAuth poster instance."""
    return FacebookOAuthPoster()
