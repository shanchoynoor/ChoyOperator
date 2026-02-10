"""
OAuth Manager - Browser-based OAuth authentication for social media platforms.

Opens the user's default browser for login, captures the OAuth callback,
and stores access tokens securely.
"""

import webbrowser
import http.server
import socketserver
import threading
import urllib.parse
import logging
import json
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable
from enum import Enum

from src.config import PROJECT_ROOT
from src.data.encryption import get_encryption

logger = logging.getLogger(__name__)


class OAuthPlatform(Enum):
    """Supported OAuth platforms."""
    FACEBOOK = "facebook"
    X = "x"
    LINKEDIN = "linkedin"
    YOUTUBE = "youtube"


@dataclass
class OAuthToken:
    """OAuth token container."""
    access_token: str
    token_type: str = "Bearer"
    expires_at: datetime | None = None
    refresh_token: str | None = None
    scope: str | None = None
    platform: OAuthPlatform | None = None
    
    @property
    def is_expired(self) -> bool:
        if not self.expires_at:
            return False
        return datetime.now() >= self.expires_at
    
    def to_dict(self) -> dict:
        return {
            "access_token": self.access_token,
            "token_type": self.token_type,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "refresh_token": self.refresh_token,
            "scope": self.scope,
            "platform": self.platform.value if self.platform else None,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "OAuthToken":
        expires_at = None
        if data.get("expires_at"):
            expires_at = datetime.fromisoformat(data["expires_at"])
        
        platform = None
        if data.get("platform"):
            platform = OAuthPlatform(data["platform"])
        
        return cls(
            access_token=data["access_token"],
            token_type=data.get("token_type", "Bearer"),
            expires_at=expires_at,
            refresh_token=data.get("refresh_token"),
            scope=data.get("scope"),
            platform=platform,
        )


class OAuthCallbackHandler(http.server.BaseHTTPRequestHandler):
    """HTTP handler for OAuth callbacks."""
    
    callback_received = threading.Event()
    auth_code: str | None = None
    error: str | None = None
    
    def log_message(self, format, *args):
        """Suppress HTTP server logs."""
        pass
    
    def do_GET(self):
        """Handle OAuth callback GET request."""
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        
        if "code" in params:
            OAuthCallbackHandler.auth_code = params["code"][0]
            self._send_success_page()
        elif "error" in params:
            OAuthCallbackHandler.error = params.get("error_description", ["Authorization denied"])[0]
            self._send_error_page()
        else:
            self._send_error_page("Invalid callback")
        
        OAuthCallbackHandler.callback_received.set()
    
    def _send_success_page(self):
        """Send success HTML page."""
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>AIOperator - Authorization Successful</title>
            <style>
                body { 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                    display: flex; justify-content: center; align-items: center;
                    height: 100vh; margin: 0;
                    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                    color: white;
                }
                .container { text-align: center; padding: 40px; }
                .success { font-size: 64px; margin-bottom: 20px; }
                h1 { color: #4ade80; margin-bottom: 10px; }
                p { color: #94a3b8; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="success">✓</div>
                <h1>Authorization Successful!</h1>
                <p>You can close this window and return to AIOperator.</p>
            </div>
        </body>
        </html>
        """
        self.wfile.write(html.encode())
    
    def _send_error_page(self, message: str = "Authorization failed"):
        """Send error HTML page."""
        self.send_response(400)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>AIOperator - Authorization Failed</title>
            <style>
                body {{ 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                    display: flex; justify-content: center; align-items: center;
                    height: 100vh; margin: 0;
                    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                    color: white;
                }}
                .container {{ text-align: center; padding: 40px; }}
                .error {{ font-size: 64px; margin-bottom: 20px; }}
                h1 {{ color: #ef4444; margin-bottom: 10px; }}
                p {{ color: #94a3b8; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="error">✗</div>
                <h1>Authorization Failed</h1>
                <p>{message}</p>
            </div>
        </body>
        </html>
        """
        self.wfile.write(html.encode())


class OAuthManager:
    """
    Manages OAuth authentication flows for social media platforms.
    
    Opens browser for user login, captures callback, and manages tokens.
    """
    
    CALLBACK_PORT = 8765
    CALLBACK_URL = f"http://localhost:{CALLBACK_PORT}/callback"
    TOKEN_FILE = PROJECT_ROOT / "data" / "oauth_tokens.enc"
    
    # Platform OAuth endpoints
    OAUTH_CONFIG = {
        OAuthPlatform.FACEBOOK: {
            "auth_url": "https://www.facebook.com/v18.0/dialog/oauth",
            "token_url": "https://graph.facebook.com/v18.0/oauth/access_token",
            "scope": "pages_manage_posts,pages_read_engagement,public_profile",
            "client_id_env": "FACEBOOK_APP_ID",
            "client_secret_env": "FACEBOOK_APP_SECRET",
        },
        OAuthPlatform.X: {
            "auth_url": "https://twitter.com/i/oauth2/authorize",
            "token_url": "https://api.twitter.com/2/oauth2/token",
            "scope": "tweet.read tweet.write users.read offline.access",
            "client_id_env": "TWITTER_CLIENT_ID",
            "client_secret_env": "TWITTER_CLIENT_SECRET",
        },
        OAuthPlatform.LINKEDIN: {
            "auth_url": "https://www.linkedin.com/oauth/v2/authorization",
            "token_url": "https://www.linkedin.com/oauth/v2/accessToken",
            "scope": "w_member_social r_liteprofile",
            "client_id_env": "LINKEDIN_CLIENT_ID",
            "client_secret_env": "LINKEDIN_CLIENT_SECRET",
        },
        OAuthPlatform.YOUTUBE: {
            "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_url": "https://oauth2.googleapis.com/token",
            "scope": "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube",
            "client_id_env": "GOOGLE_CLIENT_ID",
            "client_secret_env": "GOOGLE_CLIENT_SECRET",
        },
    }
    
    def __init__(self):
        self.encryption = get_encryption()
        self.tokens: dict[str, OAuthToken] = {}
        self._load_tokens()
    
    def _load_tokens(self):
        """Load saved tokens from encrypted file."""
        if not self.TOKEN_FILE.exists():
            return
        
        try:
            encrypted = self.TOKEN_FILE.read_text()
            decrypted = self.encryption.decrypt(encrypted)
            data = json.loads(decrypted)
            
            for platform_key, token_data in data.items():
                self.tokens[platform_key] = OAuthToken.from_dict(token_data)
                
            logger.info(f"Loaded {len(self.tokens)} OAuth tokens")
        except Exception as e:
            logger.error(f"Failed to load OAuth tokens: {e}")
    
    def _save_tokens(self):
        """Save tokens to encrypted file."""
        try:
            self.TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                key: token.to_dict() 
                for key, token in self.tokens.items()
            }
            
            encrypted = self.encryption.encrypt(json.dumps(data))
            self.TOKEN_FILE.write_text(encrypted)
            
            logger.info("OAuth tokens saved")
        except Exception as e:
            logger.error(f"Failed to save OAuth tokens: {e}")
    
    def authenticate(
        self, 
        platform: OAuthPlatform,
        client_id: str,
        client_secret: str,
        on_success: Callable | None = None,
        on_error: Callable | None = None,
    ) -> OAuthToken | None:
        """
        Start OAuth authentication flow.
        
        Opens browser for user to login and approve, then captures
        the authorization code via local callback server.
        
        Args:
            platform: The platform to authenticate with
            client_id: OAuth client/app ID
            client_secret: OAuth client secret
            on_success: Callback on successful auth
            on_error: Callback on auth error
            
        Returns:
            OAuthToken if successful, None otherwise
        """
        config = self.OAUTH_CONFIG.get(platform)
        if not config:
            logger.error(f"Unsupported OAuth platform: {platform}")
            return None
        
        # Reset callback handler state
        OAuthCallbackHandler.callback_received.clear()
        OAuthCallbackHandler.auth_code = None
        OAuthCallbackHandler.error = None
        
        # Start callback server in background
        server_thread = threading.Thread(
            target=self._run_callback_server,
            daemon=True
        )
        server_thread.start()
        
        # Build authorization URL
        auth_params = {
            "client_id": client_id,
            "redirect_uri": self.CALLBACK_URL,
            "response_type": "code",
            "scope": config["scope"],
            "state": f"aioperator_{platform.value}",
        }
        
        # Add platform-specific params
        if platform == OAuthPlatform.TWITTER:
            auth_params["code_challenge"] = "challenge"
            auth_params["code_challenge_method"] = "plain"
        
        auth_url = f"{config['auth_url']}?{urllib.parse.urlencode(auth_params)}"
        
        # Open browser for user login
        logger.info(f"Opening browser for {platform.value} authentication...")
        webbrowser.open(auth_url)
        
        # Wait for callback (timeout after 5 minutes)
        if not OAuthCallbackHandler.callback_received.wait(timeout=300):
            logger.error("OAuth timeout - no callback received")
            if on_error:
                on_error("Authentication timed out")
            return None
        
        # Check for errors
        if OAuthCallbackHandler.error:
            logger.error(f"OAuth error: {OAuthCallbackHandler.error}")
            if on_error:
                on_error(OAuthCallbackHandler.error)
            return None
        
        # Exchange auth code for access token
        token = self._exchange_code_for_token(
            platform=platform,
            auth_code=OAuthCallbackHandler.auth_code,
            client_id=client_id,
            client_secret=client_secret,
        )
        
        if token:
            token.platform = platform
            self.tokens[platform.value] = token
            self._save_tokens()
            
            if on_success:
                on_success(token)
            
            logger.info(f"Successfully authenticated with {platform.value}")
        
        return token
    
    def _run_callback_server(self):
        """Run the OAuth callback HTTP server."""
        try:
            with socketserver.TCPServer(
                ("localhost", self.CALLBACK_PORT), 
                OAuthCallbackHandler
            ) as httpd:
                httpd.handle_request()  # Handle single request then stop
        except Exception as e:
            logger.error(f"Callback server error: {e}")
    
    def _exchange_code_for_token(
        self,
        platform: OAuthPlatform,
        auth_code: str,
        client_id: str,
        client_secret: str,
    ) -> OAuthToken | None:
        """Exchange authorization code for access token."""
        import requests
        
        config = self.OAUTH_CONFIG[platform]
        
        token_data = {
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": self.CALLBACK_URL,
            "client_id": client_id,
            "client_secret": client_secret,
        }
        
        try:
            response = requests.post(
                config["token_url"],
                data=token_data,
                headers={"Accept": "application/json"},
                timeout=30,
            )
            
            if response.status_code != 200:
                logger.error(f"Token exchange failed: {response.text}")
                return None
            
            data = response.json()
            
            # Calculate expiration time
            expires_at = None
            if "expires_in" in data:
                expires_at = datetime.now() + timedelta(seconds=data["expires_in"])
            
            return OAuthToken(
                access_token=data["access_token"],
                token_type=data.get("token_type", "Bearer"),
                expires_at=expires_at,
                refresh_token=data.get("refresh_token"),
                scope=data.get("scope"),
            )
            
        except Exception as e:
            logger.error(f"Token exchange error: {e}")
            return None
    
    def get_token(self, platform: OAuthPlatform) -> OAuthToken | None:
        """Get stored token for a platform."""
        token = self.tokens.get(platform.value)
        
        if token and token.is_expired and token.refresh_token:
            # TODO: Implement token refresh
            logger.warning(f"Token for {platform.value} is expired")
            return None
        
        return token
    
    def has_valid_token(self, platform: OAuthPlatform) -> bool:
        """Check if we have a valid (non-expired) token."""
        token = self.get_token(platform)
        return token is not None and not token.is_expired
    
    def revoke_token(self, platform: OAuthPlatform):
        """Remove stored token for a platform."""
        if platform.value in self.tokens:
            del self.tokens[platform.value]
            self._save_tokens()
            logger.info(f"Revoked token for {platform.value}")


# Singleton instance
_oauth_manager: OAuthManager | None = None


def get_oauth_manager() -> OAuthManager:
    """Get or create the OAuth manager instance."""
    global _oauth_manager
    if _oauth_manager is None:
        _oauth_manager = OAuthManager()
    return _oauth_manager
