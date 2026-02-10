"""
Account Manager Widget - Manage social media accounts.

Displays list of accounts and allows adding/removing accounts via browser login.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QMessageBox
)
from PyQt5.QtCore import pyqtSignal, Qt

from src.core.browser_connect import get_browser_connect, SocialPlatform, PLATFORM_CONFIG
from src.gui.widgets.simple_connect_dialog import SimpleConnectDialog
from src.gui.widgets.toast_notifications import toast_success, toast_error
from src.gui.widgets.platform_icons import get_platform_icon
from src.utils.logger import get_logger


logger = get_logger(__name__)


class AccountManagerWidget(QWidget):
    """Widget for managing social media accounts."""
    
    account_selected = pyqtSignal(int)  # Emits account index
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.connector = get_browser_connect()
        self._init_ui()
        self.refresh()
    
    def _init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Header
        header = QLabel("Connected Accounts")
        header.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(header)
        
        # Account list
        self.account_list = QListWidget()
        self.account_list.itemClicked.connect(self._on_item_clicked)
        self.account_list.setStyleSheet("""
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #333;
            }
            QListWidget::item:selected {
                background-color: #1a73e8;
            }
        """)
        layout.addWidget(self.account_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.add_button = QPushButton("🌐 Connect")
        self.add_button.setMinimumHeight(36)
        self.add_button.setStyleSheet("""
            QPushButton {
                background: #3b82f6;
                color: white;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover { background: #2563eb; }
        """)
        self.add_button.clicked.connect(self._show_connect_dialog)
        button_layout.addWidget(self.add_button)
        
        self.remove_button = QPushButton("Remove")
        self.remove_button.setMinimumHeight(36)
        self.remove_button.clicked.connect(self._remove_account)
        self.remove_button.setEnabled(False)
        button_layout.addWidget(self.remove_button)
        
        layout.addLayout(button_layout)
    
    def refresh(self):
        """Refresh the account list from browser connect."""
        self.account_list.clear()
        
        accounts = self.connector.get_connected_accounts()
        
        if not accounts:
            item = QListWidgetItem("No accounts connected")
            item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
            item.setForeground(Qt.gray)
            self.account_list.addItem(item)
        else:
            for idx, account in enumerate(accounts):
                item = QListWidgetItem(account.display_name)
                item.setIcon(get_platform_icon(account.platform.value, 20))
                item.setData(Qt.UserRole, account.platform)
                item.setData(Qt.UserRole + 1, idx)
                self.account_list.addItem(item)
            
            # Auto-select first account if nothing is selected
            if self.account_list.count() > 0:
                self.account_list.setCurrentRow(0)
                self.remove_button.setEnabled(True)
        
        # If still no selection (e.g. empty list), disable remove button
        if not self.account_list.currentItem() or self.account_list.currentItem().text() == "No accounts connected":
            self.remove_button.setEnabled(False)
    
    def _on_item_clicked(self, item: QListWidgetItem):
        """Handle account item click."""
        platform = item.data(Qt.UserRole)
        if platform:
            idx = item.data(Qt.UserRole + 1)
            self.account_selected.emit(idx if idx else 0)
            self.remove_button.setEnabled(True)
    
    def get_selected_account(self):
        """Get the currently selected account."""
        item = self.account_list.currentItem()
        if item:
            platform = item.data(Qt.UserRole)
            if platform:
                accounts = self.connector.get_connected_accounts()
                for acc in accounts:
                    if acc.platform == platform:
                        return acc
        return None
    
    def _show_connect_dialog(self):
        """Show dialog to connect new account."""
        dialog = SimpleConnectDialog(self)
        dialog.account_connected.connect(self.refresh)
        dialog.exec_()
    
    def _remove_account(self):
        """Remove selected account."""
        item = self.account_list.currentItem()
        if not item:
            return
        
        platform = item.data(Qt.UserRole)
        if not platform:
            return
        
        reply = QMessageBox.question(
            self,
            "Confirm Remove",
            f"Disconnect your {platform.value.title()} account?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.connector.disconnect(platform)
            self.refresh()
            toast_success("Account Removed", f"{platform.value.title()} disconnected")
            logger.info(f"Disconnected {platform.value}")

