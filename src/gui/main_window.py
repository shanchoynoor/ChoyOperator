"""
Main Window - Primary application window.

Contains the main layout with sidebar and content panels.
"""

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QSplitter, QStatusBar, QMenuBar,
    QMenu, QAction, QMessageBox, QLabel, QPushButton,
    QFrame
)
from PyQt5.QtCore import Qt, QTimer, pyqtSlot
from PyQt5.QtGui import QIcon, QFont

from src.gui.widgets.account_manager import AccountManagerWidget
from src.gui.widgets.content_editor import ContentEditorWidget
from src.gui.widgets.scheduler_widget import SchedulerWidget
from src.gui.widgets.log_viewer import LogViewerWidget
from src.gui.widgets.settings_dialog import SettingsDialog
from src.gui.widgets.simple_connect_dialog import SimpleConnectDialog
from src.gui.widgets.post_history import PostHistoryWidget, get_post_history
from src.gui.widgets.toast_notifications import (
    toast_success, toast_error, toast_warning, toast_info
)
from src.gui.threads.post_thread import FacebookPostWorker
from src.gui.styles.dark_theme import get_dark_stylesheet
from src.utils.logger import get_logger, GUILogHandler, QtLogEmitter
from src.core.scheduler import get_scheduler
from src.data.database import get_database
from src.utils.helpers import contains_video_media

logger = get_logger(__name__)


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AIOperator - Social Media Automation")
        self.setMinimumSize(1200, 800)
        self.db = get_database()
        
        # Apply dark theme
        self.setStyleSheet(get_dark_stylesheet() + """
            /* Override dark theme for log display */
            QTextEdit#LogDisplay {
                color: #f5f5f5 !important;
            }
            QTextEdit#LogDisplay::html {
                color: #f5f5f5 !important;
            }
        """)
        
        # Initialize components
        self._init_menu_bar()
        self._init_central_widget()
        self._init_status_bar()
        self._init_logging()
        
        # Start scheduler
        self.scheduler = get_scheduler()
        self.scheduler.start()
        
        logger.info("AIOperator started successfully")
    
    def _init_menu_bar(self):
        """Initialize the menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        settings_action = QAction("&Settings", self)
        settings_action.setShortcut("Ctrl+,")
        settings_action.triggered.connect(self._show_settings)
        file_menu.addAction(settings_action)
        
        # OAuth Connect
        oauth_action = QAction("🔗 &Connect Accounts...", self)
        oauth_action.triggered.connect(self._show_oauth_dialog)
        file_menu.addAction(oauth_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Alt+F4")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View menu
        view_menu = menubar.addMenu("&View")
        
        refresh_action = QAction("&Refresh", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self._refresh_data)
        view_menu.addAction(refresh_action)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _init_central_widget(self):
        """Initialize the central widget with layout."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Horizontal)
        
        # Left sidebar - Account management + Post History
        sidebar = QWidget()
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)
        
        # Accounts section
        self.account_widget = AccountManagerWidget()
        sidebar_layout.addWidget(self.account_widget, stretch=1)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("background: #334155;")
        sidebar_layout.addWidget(separator)
        
        # Post History section
        self.post_history = PostHistoryWidget()
        sidebar_layout.addWidget(self.post_history, stretch=2)
        
        sidebar.setMaximumWidth(300)
        sidebar.setMinimumWidth(240)
        splitter.addWidget(sidebar)
        
        # Center - Main content area
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(10, 10, 10, 10)
        center_layout.setSpacing(8)
        
        # Scheduler - Scheduled Posts (moved above Content Editor)
        self.scheduler_widget = SchedulerWidget()
        center_layout.addWidget(self.scheduler_widget, stretch=1)
        
        # Content editor
        self.content_editor = ContentEditorWidget()
        center_layout.addWidget(self.content_editor, stretch=4)
        
        splitter.addWidget(center_widget)
        
        # Right panel - Logs
        self.log_viewer = LogViewerWidget()
        self.log_viewer.setMaximumWidth(350)
        self.log_viewer.setMinimumWidth(220)
        splitter.addWidget(self.log_viewer)
        
        # Set splitter sizes - more balanced
        splitter.setSizes([260, 550, 300])
        
        main_layout.addWidget(splitter)
        
        # Connect signals
        self.content_editor.post_requested.connect(self._handle_post)
        self.content_editor.schedule_requested.connect(self._handle_schedule)
        self.account_widget.account_selected.connect(self._on_account_selected)
    
    def _init_status_bar(self):
        """Initialize the status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Status label
        self.status_label = QLabel("Ready")
        self.status_bar.addWidget(self.status_label)
        
        # Scheduler status
        self.scheduler_status = QLabel("Scheduler: Active")
        self.scheduler_status.setStyleSheet("color: #4CAF50;")
        self.status_bar.addPermanentWidget(self.scheduler_status)
    
    def _init_logging(self):
        """Set up GUI log handler."""
        import logging
        
        self.log_emitter = QtLogEmitter(self)
        self.log_emitter.log_message.connect(self._on_log_message)

        gui_handler = GUILogHandler(self.log_emitter)
        gui_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", "%H:%M:%S")
        )
        gui_handler.setLevel(logging.INFO)
        
        logging.getLogger().addHandler(gui_handler)
    
    @pyqtSlot(str, str)
    def _on_log_message(self, level: str, message: str):
        """Handle log messages for GUI display."""
        self.log_viewer.add_log(level, message)
    
    def _on_account_selected(self, account_id: int):
        """Handle account selection."""
        self.content_editor.set_current_account(account_id)
        self.status_label.setText(f"Selected account: {account_id}")
    
    def _handle_post(self, content: str, media_paths: list):
        """Handle immediate post request."""
        account = self.account_widget.get_selected_account()
        if not account:
            toast_warning("No Account", "Please select a connected account first")
            return
        
        if not content.strip():
            toast_warning("No Content", "Please write something to post")
            return
        
        platform = account.platform.value if hasattr(account.platform, 'value') else str(account.platform)
        
        self.status_label.setText("Posting...")
        logger.info(f"Posting to {platform}: {content[:50]}...")
        
        # Use real poster for Facebook
        if platform.lower() == "facebook":
            is_reel = contains_video_media(media_paths)
            # Create and start background worker
            self.post_worker = FacebookPostWorker(
                content=content,
                media_paths=media_paths,
                headless=True,
                post_type="reel" if is_reel else "feed"
            )
            
            # Connect signals
            self.post_worker.status_update.connect(lambda msg: self.status_label.setText(msg))
            self.post_worker.finished.connect(lambda success, msg: self._on_post_finished(platform, content, success, msg))
            
            # Disable post button to prevent double-click
            self.content_editor.post_btn.setEnabled(False)
            
            self.post_worker.start()
        else:
            # For other platforms, just record in history for now
            self.post_history.add_post(platform, content, "success")
            toast_info("Recorded", f"Post saved for {platform.title()}")
            self.status_label.setText("Post recorded")
    
    def _on_post_finished(self, platform: str, content: str, success: bool, message: str):
        """Handle completion of background posting."""
        self.content_editor.post_btn.setEnabled(True)
        
        if success:
            self.post_history.add_post(platform, content, "success")
            toast_success("Posted!", message)
            self.status_label.setText("Posted successfully")
            logger.info(f"Facebook post successful")
        else:
            self.post_history.add_post(platform, content, "failed")
            toast_error("Post Failed", message)
            self.status_label.setText("Post failed")
            logger.error(f"Facebook post failed: {message}")
    
    def _handle_schedule(self, content: str, scheduled_time, media_paths: list):
        """Handle scheduled post request."""
        account = self.account_widget.get_selected_account()
        if not account:
            toast_warning("No Account", "Please select an account first")
            return
        
        # Allow scheduling with just content (no media required)
        if not content.strip():
            toast_warning("No Content", "Please write some content to schedule")
            return
        
        logger.info(f"Scheduling post for {scheduled_time}")
        self.status_label.setText("Scheduling post...")
        
        try:
            # Get platform name from connected account (it's a SocialPlatform enum)
            platform_name = account.platform.value.lower()
            
            # Find database account that matches the connected account
            db_accounts = self.db.get_all_accounts()
            
            # Find database account with matching platform (case-insensitive)
            db_account = None
            for acc in db_accounts:
                if acc.platform.lower() == platform_name:
                    db_account = acc
                    break
            
            # If no database account found, create one
            if not db_account:
                logger.info(f"No database account found for {platform_name}, creating one...")
                from src.data.models import Account
                
                new_account = Account(
                    id=None,  # Auto-generated
                    platform=platform_name,
                    username=account.display_name,
                    is_active=True,
                )
                
                try:
                    account_id = self.db.add_account(new_account)
                    db_account = self.db.get_account(account_id)
                    logger.info(f"Created database account with ID {account_id}")
                except Exception as e:
                    # Handle UNIQUE constraint violation - account may already exist
                    logger.warning(f"Could not create account (may already exist): {e}")
                    # Try to find by username as well
                    for acc in db_accounts:
                        if acc.username.lower() == account.display_name.lower():
                            db_account = acc
                            break
            
            if not db_account:
                toast_error("Account Error", "Could not find or create database account for scheduling.")
                self.status_label.setText("Account error")
                return
            
            # Save to database
            from src.data.models import ScheduledPost, PostStatusEnum
            from src.core.scheduler import get_scheduler
            
            scheduler = get_scheduler()
            
            # Create scheduled post
            post = ScheduledPost(
                id=None,  # Auto-generated
                account_id=db_account.id,
                content=content,
                scheduled_time=scheduled_time,
                status=PostStatusEnum.PENDING,
                media_paths=media_paths or [],
            )
            
            # Save to database
            post_id = self.db.add_scheduled_post(post)
            
            # Schedule the job
            job_id = f"post_{post_id}"
            scheduler.schedule_post(
                job_id=job_id,
                run_at=scheduled_time,
                platform=platform_name,
                account_id=db_account.id,
                content=content,
                media_paths=media_paths or [],
            )
            
            # Refresh scheduler widget to show new post
            self.scheduler_widget.refresh()
            
            self.status_label.setText("Post scheduled")
            toast_success("Scheduled", f"Post scheduled for {scheduled_time.strftime('%Y-%m-%d %H:%M')}")
            
            logger.info(f"Successfully scheduled post {post_id} for {scheduled_time}")
            
        except Exception as e:
            self.status_label.setText("Scheduling failed")
            toast_error("Scheduling Failed", f"Failed to schedule post: {e}")
            logger.error(f"Failed to schedule post: {e}")
    
    def _show_settings(self):
        """Show settings dialog."""
        dialog = SettingsDialog(self)
        dialog.exec_()
    
    def _show_oauth_dialog(self):
        """Show account connection dialog."""
        dialog = SimpleConnectDialog(self)
        dialog.account_connected.connect(self.account_widget.refresh)
        dialog.exec_()
    
    def _show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About AIOperator",
            "AIOperator - Social Media Automation\n\n"
            "Version 1.0.0\n\n"
            "Automate your social media posts with AI-generated content.\n\n"
            "© 2024 AIOperator"
        )
    
    def _refresh_data(self):
        """Refresh all data."""
        self.account_widget.refresh()
        self.post_history.refresh()
        self.scheduler_widget.refresh()
        self.status_label.setText("Refreshed")
        logger.info("Data refreshed")
    
    def closeEvent(self, event):
        """Handle window close."""
        self.scheduler.stop()
        logger.info("AIOperator shutting down")
        event.accept()
