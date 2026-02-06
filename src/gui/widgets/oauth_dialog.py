"""
OAuth Connect Dialog - GUI for OAuth authentication.

Provides a dialog for users to connect social media accounts via OAuth.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QGroupBox, QFormLayout, QMessageBox,
    QListWidget, QListWidgetItem, QFrame
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont

from src.core.oauth_manager import get_oauth_manager, OAuthPlatform
from src.core.platforms.facebook_oauth import FacebookOAuthPoster


class OAuthWorker(QThread):
    """Background worker for OAuth authentication."""
    
    finished = pyqtSignal(bool, str)  # success, message
    
    def __init__(
        self, 
        platform: OAuthPlatform, 
        client_id: str, 
        client_secret: str
    ):
        super().__init__()
        self.platform = platform
        self.client_id = client_id
        self.client_secret = client_secret
    
    def run(self):
        """Execute OAuth flow in background."""
        oauth = get_oauth_manager()
        
        def on_success(token):
            self.finished.emit(True, f"Connected to {self.platform.value}!")
        
        def on_error(error):
            self.finished.emit(False, f"Failed: {error}")
        
        token = oauth.authenticate(
            platform=self.platform,
            client_id=self.client_id,
            client_secret=self.client_secret,
            on_success=on_success,
            on_error=on_error,
        )
        
        if token is None:
            self.finished.emit(False, "Authentication failed or was cancelled")


class OAuthConnectDialog(QDialog):
    """
    Dialog for connecting social media accounts via OAuth.
    
    Opens browser for login, captures callback, stores tokens.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Connect Social Media Accounts")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        self.oauth_manager = get_oauth_manager()
        self.worker = None
        
        self._setup_ui()
        self._load_connected_accounts()
    
    def _setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        # Header
        header = QLabel("Connect Your Social Media Accounts")
        header.setFont(QFont("", 14, QFont.Bold))
        layout.addWidget(header)
        
        info = QLabel(
            "Connect your accounts using OAuth for secure posting.\n"
            "Your browser will open for you to log in and approve access."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #94a3b8;")
        layout.addWidget(info)
        
        # Connected accounts section
        connected_group = QGroupBox("Connected Accounts")
        connected_layout = QVBoxLayout(connected_group)
        
        self.accounts_list = QListWidget()
        self.accounts_list.setMaximumHeight(100)
        connected_layout.addWidget(self.accounts_list)
        
        disconnect_btn = QPushButton("Disconnect Selected")
        disconnect_btn.clicked.connect(self._disconnect_account)
        connected_layout.addWidget(disconnect_btn)
        
        layout.addWidget(connected_group)
        
        # Connect new account section
        connect_group = QGroupBox("Connect New Account")
        connect_layout = QFormLayout(connect_group)
        
        # Platform selector
        self.platform_combo = QComboBox()
        self.platform_combo.addItem("Facebook", OAuthPlatform.FACEBOOK)
        self.platform_combo.addItem("Twitter/X", OAuthPlatform.TWITTER)
        self.platform_combo.addItem("LinkedIn", OAuthPlatform.LINKEDIN)
        self.platform_combo.addItem("YouTube (Google)", OAuthPlatform.YOUTUBE)
        self.platform_combo.currentIndexChanged.connect(self._on_platform_changed)
        connect_layout.addRow("Platform:", self.platform_combo)
        
        # App credentials
        self.client_id_input = QLineEdit()
        self.client_id_input.setPlaceholderText("Enter App ID / Client ID")
        connect_layout.addRow("App ID:", self.client_id_input)
        
        self.client_secret_input = QLineEdit()
        self.client_secret_input.setPlaceholderText("Enter App Secret / Client Secret")
        self.client_secret_input.setEchoMode(QLineEdit.Password)
        connect_layout.addRow("App Secret:", self.client_secret_input)
        
        # Help text
        self.help_label = QLabel()
        self.help_label.setWordWrap(True)
        self.help_label.setStyleSheet("color: #64748b; font-size: 11px;")
        self._update_help_text()
        connect_layout.addRow("", self.help_label)
        
        layout.addWidget(connect_group)
        
        # Connect button
        self.connect_btn = QPushButton("🔗 Connect Account")
        self.connect_btn.setMinimumHeight(40)
        self.connect_btn.setStyleSheet("""
            QPushButton {
                background: #3b82f6;
                color: white;
                font-weight: bold;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: #2563eb;
            }
            QPushButton:disabled {
                background: #475569;
            }
        """)
        self.connect_btn.clicked.connect(self._start_oauth)
        layout.addWidget(self.connect_btn)
        
        # Status label
        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
    
    def _on_platform_changed(self):
        """Handle platform selection change."""
        self._update_help_text()
    
    def _update_help_text(self):
        """Update help text based on selected platform."""
        platform = self.platform_combo.currentData()
        
        help_texts = {
            OAuthPlatform.FACEBOOK: 
                "Create a Facebook App at developers.facebook.com.\n"
                "Enable 'pages_manage_posts' permission.",
            OAuthPlatform.TWITTER:
                "Create a Twitter App at developer.twitter.com.\n"
                "Enable OAuth 2.0 with 'tweet.write' scope.",
            OAuthPlatform.LINKEDIN:
                "Create a LinkedIn App at linkedin.com/developers.\n"
                "Request 'w_member_social' permission.",
            OAuthPlatform.YOUTUBE:
                "Create credentials at console.cloud.google.com.\n"
                "Enable YouTube Data API v3.",
        }
        
        self.help_label.setText(help_texts.get(platform, ""))
    
    def _load_connected_accounts(self):
        """Load and display connected accounts."""
        self.accounts_list.clear()
        
        for platform in OAuthPlatform:
            if self.oauth_manager.has_valid_token(platform):
                item = QListWidgetItem(f"✓ {platform.value.title()}")
                item.setData(Qt.UserRole, platform)
                self.accounts_list.addItem(item)
        
        if self.accounts_list.count() == 0:
            item = QListWidgetItem("No accounts connected")
            item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
            self.accounts_list.addItem(item)
    
    def _disconnect_account(self):
        """Disconnect selected account."""
        item = self.accounts_list.currentItem()
        if not item:
            return
        
        platform = item.data(Qt.UserRole)
        if not platform:
            return
        
        reply = QMessageBox.question(
            self,
            "Disconnect Account",
            f"Disconnect {platform.value.title()} account?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.oauth_manager.revoke_token(platform)
            self._load_connected_accounts()
            self.status_label.setText(f"Disconnected {platform.value}")
    
    def _start_oauth(self):
        """Start OAuth authentication flow."""
        platform = self.platform_combo.currentData()
        client_id = self.client_id_input.text().strip()
        client_secret = self.client_secret_input.text().strip()
        
        if not client_id or not client_secret:
            QMessageBox.warning(
                self,
                "Missing Credentials",
                "Please enter both App ID and App Secret."
            )
            return
        
        self.connect_btn.setEnabled(False)
        self.connect_btn.setText("Opening browser...")
        self.status_label.setText("Waiting for authorization...")
        
        # Start OAuth in background thread
        self.worker = OAuthWorker(platform, client_id, client_secret)
        self.worker.finished.connect(self._on_oauth_complete)
        self.worker.start()
    
    def _on_oauth_complete(self, success: bool, message: str):
        """Handle OAuth completion."""
        self.connect_btn.setEnabled(True)
        self.connect_btn.setText("🔗 Connect Account")
        
        if success:
            self.status_label.setText(f"✓ {message}")
            self.status_label.setStyleSheet("color: #4ade80;")
            self._load_connected_accounts()
            
            # Clear inputs
            self.client_id_input.clear()
            self.client_secret_input.clear()
        else:
            self.status_label.setText(f"✗ {message}")
            self.status_label.setStyleSheet("color: #ef4444;")
