"""
Simple Account Connect Dialog - Just select platform and login via browser.

No username/password fields - user logs in directly in their browser.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QGroupBox, QListWidget, QListWidgetItem,
    QMessageBox, QLineEdit
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from src.data.database import get_database
from src.data.models import Account
from src.core.browser_connect import get_browser_connect, SocialPlatform
from src.gui.widgets.toast_notifications import toast_success, toast_error
from src.gui.widgets.platform_icons import get_platform_icon


class SimpleConnectDialog(QDialog):
    """
    Simple dialog to connect social media accounts.
    
    Select platform → Open Browser → Login → Confirm.
    """
    
    account_connected = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Connect Social Media")
        self.setMinimumWidth(420)
        self.setMinimumHeight(500)
        
        self.connector = get_browser_connect()
        self.pending_platform = None
        
        self._setup_ui()
        self._load_accounts()
    
    def _setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # Header
        header = QLabel("🔗 Connect Your Accounts")
        header.setFont(QFont("", 14, QFont.Bold))
        layout.addWidget(header)
        
        # Connected accounts section
        connected_group = QGroupBox("Connected Accounts")
        connected_layout = QVBoxLayout(connected_group)
        
        self.accounts_list = QListWidget()
        self.accounts_list.setMaximumHeight(80)
        connected_layout.addWidget(self.accounts_list)
        
        disconnect_btn = QPushButton("🗑 Disconnect Selected")
        disconnect_btn.clicked.connect(self._disconnect_account)
        connected_layout.addWidget(disconnect_btn)
        
        layout.addWidget(connected_group)
        
        # Connect new account section
        connect_group = QGroupBox("Add New Account")
        connect_layout = QVBoxLayout(connect_group)
        connect_layout.setSpacing(12)
        
        # Platform selector
        platform_layout = QHBoxLayout()
        platform_label = QLabel("Platform:")
        platform_label.setMinimumWidth(70)
        
        self.platform_combo = QComboBox()
        self.platform_combo.setMinimumHeight(36)
        self.platform_combo.addItem("📘 Facebook", SocialPlatform.FACEBOOK)
        self.platform_combo.addItem("🐦 X", SocialPlatform.X)
        self.platform_combo.addItem("💼 LinkedIn", SocialPlatform.LINKEDIN)
        self.platform_combo.addItem("🎬 YouTube", SocialPlatform.YOUTUBE)
        
        platform_layout.addWidget(platform_label)
        platform_layout.addWidget(self.platform_combo, stretch=1)
        connect_layout.addLayout(platform_layout)
        
        # STEP 1: Open browser
        step1_label = QLabel("Step 1: Open the login page")
        step1_label.setStyleSheet("font-weight: bold; margin-top: 8px;")
        connect_layout.addWidget(step1_label)
        
        self.open_btn = QPushButton("🌐 Open Login Page in Browser")
        self.open_btn.setMinimumHeight(42)
        self.open_btn.setStyleSheet("""
            QPushButton {
                background: #3b82f6;
                color: white;
                font-weight: bold;
                border-radius: 6px;
            }
            QPushButton:hover { background: #2563eb; }
        """)
        self.open_btn.clicked.connect(self._open_browser)
        connect_layout.addWidget(self.open_btn)
        
        # STEP 2: Confirm (always visible)
        step2_label = QLabel("Step 2: After logging in, enter your name and click Save")
        step2_label.setStyleSheet("font-weight: bold; margin-top: 12px;")
        connect_layout.addWidget(step2_label)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Your name or page name (optional)")
        self.name_input.setMinimumHeight(36)
        connect_layout.addWidget(self.name_input)
        
        self.save_btn = QPushButton("✓ Save Account")
        self.save_btn.setMinimumHeight(42)
        self.save_btn.setEnabled(False)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background: #10b981;
                color: white;
                font-weight: bold;
                border-radius: 6px;
            }
            QPushButton:hover { background: #059669; }
            QPushButton:disabled { background: #475569; color: #94a3b8; }
        """)
        self.save_btn.clicked.connect(self._save_account)
        connect_layout.addWidget(self.save_btn)
        
        # Status
        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setWordWrap(True)
        connect_layout.addWidget(self.status_label)
        
        layout.addWidget(connect_group)
        
        # Close button
        close_btn = QPushButton("Done")
        close_btn.setMinimumHeight(36)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
    
    def _load_accounts(self):
        """Load and display connected accounts with platform icons."""
        self.accounts_list.clear()
        
        accounts = self.connector.get_connected_accounts()
        
        if not accounts:
            item = QListWidgetItem("No accounts connected yet")
            item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
            item.setForeground(Qt.gray)
            self.accounts_list.addItem(item)
        else:
            for account in accounts:
                item = QListWidgetItem(account.display_name)
                item.setIcon(get_platform_icon(account.platform.value, 20))
                item.setData(Qt.UserRole, account.platform)
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
            f"Remove this {platform.value.title()} account?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.connector.disconnect(platform)
            self._load_accounts()
            toast_success("Account Removed", f"{platform.value.title()} disconnected")
            self.account_connected.emit()
    
    def _open_browser(self):
        """Open browser to login page."""
        platform = self.platform_combo.currentData()
        
        # Check if already connected
        if self.connector.is_connected(platform):
            reply = QMessageBox.question(
                self,
                "Already Connected",
                f"You already have a {platform.value.title()} account.\n"
                "Do you want to reconnect?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
        
        # Open browser
        success = self.connector.open_login_page(platform)
        
        if success:
            self.pending_platform = platform
            self.save_btn.setEnabled(True)
            self.status_label.setText(
                f"✓ Browser opened!\n"
                f"Log in to {platform.value.title()}, then come back and click 'Save Account'"
            )
            self.status_label.setStyleSheet("color: #4ade80;")
        else:
            toast_error("Failed", "Could not open browser")
            self.status_label.setText("Failed to open browser")
            self.status_label.setStyleSheet("color: #ef4444;")
    
    def _save_account(self):
        """Save the connected account."""
        if not self.pending_platform:
            # If no pending, use currently selected
            self.pending_platform = self.platform_combo.currentData()
        
        display_name = self.name_input.text().strip()
        
        # Save the connection
        account = self.connector.confirm_connection(
            platform=self.pending_platform,
            display_name=display_name,
        )
        
        # Also create database account record for scheduling
        db = get_database()
        db_account = Account(
            id=None,  # Auto-generated
            platform=self.pending_platform.value,
            username=account.display_name,
            is_active=True,
        )
        try:
            db.add_account(db_account)
        except Exception as e:
            # Handle UNIQUE constraint violation - account may already exist
            # This is fine, the account is already in the database
            pass
        
        # Reset state
        self.pending_platform = None
        self.save_btn.setEnabled(False)
        self.name_input.clear()
        self._load_accounts()
        
        self.status_label.setText(f"✓ Connected as {account.display_name}!")
        self.status_label.setStyleSheet("color: #4ade80;")
        
        toast_success("Account Connected", f"{account.display_name} saved!")
        self.account_connected.emit()
