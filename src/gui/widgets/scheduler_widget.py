"""
Scheduler Widget - Schedule posts with drag-drop and folder watching.

Features:
- Drag and drop media files like OBS
- AI-generated titles, captions, descriptions, hashtags
- Set post time for each item
- Folder watcher for automatic scheduling
"""

from datetime import datetime, timedelta
from pathlib import Path
from functools import partial

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QDateTimeEdit, QComboBox, QGroupBox,
    QFileDialog, QMessageBox, QHeaderView, QAbstractItemView,
    QLineEdit, QCheckBox, QSpinBox, QDialog, QFormLayout, QTextEdit,
    QListWidget
)
from PyQt5.QtCore import (
    pyqtSignal, Qt, QDateTime, QTimer, QFileSystemWatcher, QMimeData
)
from PyQt5.QtGui import QDragEnterEvent, QDropEvent, QFont

from src.data.database import get_database
from src.data.models import ScheduledPost, PostStatusEnum
from src.core.scheduler import get_scheduler
from src.core.llm_client import LLMClient, Platform
from src.core.browser_connect import get_browser_connect
from src.gui.widgets.platform_icons import get_platform_icon
from src.config import config, PROJECT_ROOT
from src.utils.logger import get_logger
from src.utils.helpers import get_media_type


logger = get_logger(__name__)


class DropZone(QWidget):
    """
    Drag and drop zone for media files (OBS-style).
    
    Accepts dropped files and emits signal with file paths.
    """
    
    files_dropped = pyqtSignal(list)  # List of file paths
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMaximumHeight(50)  # Smaller height
        self.setMinimumHeight(40)
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(5, 2, 5, 2)  # Smaller margins
        
        self.label = QLabel("📁 Drop Files Here")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("""
            QLabel {
                border: 2px dashed #555;
                border-radius: 6px;
                padding: 8px 15px;
                color: #888;
                font-size: 12px;
                background-color: #1e1e1e;
            }
        """)
        layout.addWidget(self.label)
        
        self.setStyleSheet("""
            DropZone {
                background-color: #1e1e1e;
                border-radius: 10px;
            }
        """)
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.label.setStyleSheet("""
                QLabel {
                    border: 2px dashed #1a73e8;
                    border-radius: 6px;
                    padding: 8px 15px;
                    color: #1a73e8;
                    font-size: 12px;
                    background-color: #1a3a5c;
                }
            """)
    
    def dragLeaveEvent(self, event):
        """Handle drag leave."""
        self.label.setStyleSheet("""
            QLabel {
                border: 2px dashed #555;
                border-radius: 6px;
                padding: 8px 15px;
                color: #888;
                font-size: 12px;
                background-color: #1e1e1e;
            }
        """)
    
    def dropEvent(self, event: QDropEvent):
        """Handle file drop."""
        files = []
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path:
                files.append(Path(file_path))
        
        if files:
            self.files_dropped.emit(files)
            logger.info(f"Dropped {len(files)} file(s)")
        
        # Reset style
        self.dragLeaveEvent(None)
    
    def mousePressEvent(self, event):
        """Handle click to browse files."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Media Files",
            "",
            "Media Files (*.jpg *.jpeg *.png *.gif *.mp4 *.mov *.avi)"
        )
        if files:
            self.files_dropped.emit([Path(f) for f in files])


class ScheduleItemDialog(QDialog):
    """Dialog for configuring a scheduled post with AI generation."""
    
    def __init__(self, file_path: Path, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.setWindowTitle(f"Schedule: {file_path.name}")
        self.setMinimumWidth(500)
        self.llm_client = None
        self._init_llm()
        self._init_ui()
    
    def _init_llm(self):
        """Initialize LLM client."""
        if config.llm.api_key:
            try:
                self.llm_client = LLMClient()
            except:
                pass
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # File info
        file_info = QLabel(f"📁 {self.file_path.name}")
        file_info.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(file_info)
        
        media_type = get_media_type(self.file_path)
        type_label = QLabel(f"Type: {'🎬 Video' if media_type == 'video' else '🖼️ Image'}")
        layout.addWidget(type_label)
        
        # Platform selection
        form = QFormLayout()
        
        self.platform_combo = QComboBox()
        self.platform_combo.addItems(["Facebook", "Twitter", "LinkedIn", "YouTube"])
        form.addRow("Platform:", self.platform_combo)
        
        # Account selection
        self.account_combo = QComboBox()
        self._load_accounts()
        form.addRow("Account:", self.account_combo)
        
        layout.addLayout(form)
        
        # AI Generation controls - compact
        ai_group = QGroupBox("AI Content Generation")
        ai_layout = QVBoxLayout(ai_group)
        ai_layout.setContentsMargins(8, 10, 8, 8)
        ai_layout.setSpacing(6)
        
        # Title (for YouTube videos)
        title_layout = QHBoxLayout()
        title_layout.addWidget(QLabel("Title:"))
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Video/post title...")
        title_layout.addWidget(self.title_input)
        gen_title_btn = QPushButton("🤖 Generate")
        gen_title_btn.clicked.connect(self._generate_title)
        title_layout.addWidget(gen_title_btn)
        ai_layout.addLayout(title_layout)
        
        # Description/Caption
        ai_layout.addWidget(QLabel("Description/Caption:"))
        # Content text area (description)
        self.content_edit = QTextEdit()
        self.content_edit.setPlaceholderText("Write your post description here...")
        self.content_edit.setFont(QFont("Segoe UI", 11))
        self.content_edit.textChanged.connect(self._update_char_count)
        self.content_edit.setMinimumHeight(100)
        self.content_edit.setMaximumHeight(150)  # Cap max height
        ai_layout.addWidget(self.content_edit)
        
        desc_btn_layout = QHBoxLayout()
        gen_desc_btn = QPushButton("🤖 Generate Description")
        gen_desc_btn.clicked.connect(self._generate_description)
        desc_btn_layout.addWidget(gen_desc_btn)
        
        gen_hashtags_btn = QPushButton("#️⃣ Add Hashtags")
        gen_hashtags_btn.clicked.connect(self._generate_hashtags)
        desc_btn_layout.addWidget(gen_hashtags_btn)
        desc_btn_layout.addStretch()
        ai_layout.addLayout(desc_btn_layout)
        
        layout.addWidget(ai_group)
        
        # Media attachments
        media_group = QGroupBox("Media Attachments")
        media_layout = QHBoxLayout(media_group)
        media_layout.setContentsMargins(8, 10, 8, 8)
        
        self.media_list = QListWidget()
        self.media_list.setMaximumHeight(60)  # Reduced from 80
        media_layout.addWidget(self.media_list)
        
        layout.addWidget(media_group)
        
        # Schedule time
        schedule_group = QGroupBox("Schedule")
        schedule_layout = QFormLayout(schedule_group)
        
        self.datetime_edit = QDateTimeEdit()
        self.datetime_edit.setDateTime(QDateTime.currentDateTime().addSecs(3600))  # +1 hour
        self.datetime_edit.setCalendarPopup(True)
        self.datetime_edit.setMinimumDateTime(QDateTime.currentDateTime())
        schedule_layout.addRow("Post at:", self.datetime_edit)
        
        # Quick schedule buttons
        quick_layout = QHBoxLayout()
        for label, hours in [("In 1 hour", 1), ("In 3 hours", 3), ("Tomorrow 9AM", 24)]:
            btn = QPushButton(label)
            btn.clicked.connect(lambda checked, h=hours: self._set_quick_time(h))
            quick_layout.addWidget(btn)
        schedule_layout.addRow("Quick:", quick_layout)
        
        layout.addWidget(schedule_group)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        schedule_btn = QPushButton("📅 Schedule Post")
        schedule_btn.clicked.connect(self.accept)
        schedule_btn.setStyleSheet("background-color: #1a73e8; color: white; padding: 10px 20px;")
        btn_layout.addWidget(schedule_btn)
        
        layout.addLayout(btn_layout)
    
    def _load_accounts(self):
        """Load accounts into combo box."""
        db = get_database()
        accounts = db.get_all_accounts()
        for acc in accounts:
            self.account_combo.addItem(f"{acc.platform}: {acc.username}", acc.id)
    
    def _set_quick_time(self, hours: int):
        """Set quick schedule time."""
        if hours == 24:
            # Tomorrow 9 AM
            tomorrow = datetime.now() + timedelta(days=1)
            dt = tomorrow.replace(hour=9, minute=0, second=0)
        else:
            dt = datetime.now() + timedelta(hours=hours)
        self.datetime_edit.setDateTime(QDateTime(dt))
    
    def _generate_title(self):
        """Generate title using AI based on filename."""
        if not self.llm_client:
            QMessageBox.warning(self, "LLM Not Configured", "Set OpenRouter API key in settings.")
            return
        
        try:
            # Use filename as hint
            hint = self.file_path.stem.replace('_', ' ').replace('-', ' ')
            result = self.llm_client.generate_post(
                f"Create a catchy short title (max 10 words) for content about: {hint}",
                Platform.YOUTUBE,
            )
            # Extract just the title (first line, no hashtags)
            title = result.content.split('\n')[0].strip('#').strip()
            self.title_input.setText(title[:100])
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
    
    def _generate_description(self):
        """Generate description using AI."""
        if not self.llm_client:
            QMessageBox.warning(self, "LLM Not Configured", "Set OpenRouter API key in settings.")
            return
        
        try:
            platform = list(Platform)[self.platform_combo.currentIndex()]
            title = self.title_input.text() or self.file_path.stem
            result = self.llm_client.generate_post(
                f"Create an engaging description for: {title}",
                platform,
                include_hashtags=False
            )
            self.description_input.setPlainText(result.content)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
    
    def _generate_hashtags(self):
        """Add AI-generated hashtags."""
        if not self.llm_client:
            QMessageBox.warning(self, "LLM Not Configured", "Set OpenRouter API key in settings.")
            return
        
        try:
            content = self.description_input.toPlainText() or self.title_input.text()
            if content:
                hashtags = self.llm_client.generate_hashtags(content)
                current = self.description_input.toPlainText()
                self.description_input.setPlainText(f"{current}\n\n{' '.join(hashtags)}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
    
    def get_schedule_data(self) -> dict:
        """Get the scheduled post data."""
        return {
            "file_path": str(self.file_path),
            "platform": ["facebook", "twitter", "linkedin", "youtube"][self.platform_combo.currentIndex()],
            "account_id": self.account_combo.currentData(),
            "title": self.title_input.text(),
            "description": self.description_input.toPlainText(),
            "scheduled_time": self.datetime_edit.dateTime().toPyDateTime(),
        }


class FolderWatcher:
    """
    Watches a folder for new media files and creates schedule items.
    """
    
    def __init__(self, callback):
        self.callback = callback
        self.watcher = QFileSystemWatcher()
        self.watcher.directoryChanged.connect(self._on_directory_changed)
        self.watch_path = None
        self.known_files = set()
    
    def set_folder(self, folder_path: Path):
        """Set folder to watch."""
        if self.watch_path:
            self.watcher.removePath(str(self.watch_path))
        
        self.watch_path = folder_path
        self.watcher.addPath(str(folder_path))
        
        # Track existing files
        self.known_files = set(folder_path.iterdir())
        logger.info(f"Watching folder: {folder_path}")
    
    def stop(self):
        """Stop watching."""
        if self.watch_path:
            self.watcher.removePath(str(self.watch_path))
            self.watch_path = None
    
    def _on_directory_changed(self, path: str):
        """Handle new files in directory."""
        if not self.watch_path:
            return
        
        current_files = set(self.watch_path.iterdir())
        new_files = current_files - self.known_files
        
        media_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.mp4', '.mov', '.avi'}
        new_media = [
            f for f in new_files 
            if f.is_file() and f.suffix.lower() in media_extensions
        ]
        
        if new_media:
            logger.info(f"New files detected: {len(new_media)}")
            self.callback(new_media)
        
        self.known_files = current_files


class SchedulerWidget(QWidget):
    """Widget for managing scheduled posts with drag-drop and folder watching."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.folder_watcher = FolderWatcher(self._on_new_files)
        self._init_ui()
        self.refresh()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        
        # Header section
        header_layout = QHBoxLayout()
        
        header = QLabel("📅 Scheduled Posts")
        header.setStyleSheet("""
            font-size: 18px; 
            font-weight: bold; 
            color: #e2e8f0;
            padding: 4px 0;
        """)
        header_layout.addWidget(header)
        
        header_layout.addStretch()
        
        # Folder watch toggle
        self.watch_checkbox = QCheckBox("📂 Watch Folder")
        self.watch_checkbox.setStyleSheet("""
            QCheckBox {
                color: #94a3b8;
                font-size: 12px;
                padding: 4px 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }
        """)
        self.watch_checkbox.toggled.connect(self._toggle_folder_watch)
        header_layout.addWidget(self.watch_checkbox)
        
        self.folder_btn = QPushButton("📁 Set Folder")
        self.folder_btn.setStyleSheet("""
            QPushButton {
                background-color: #334155;
                color: #e2e8f0;
                border: 1px solid #475569;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #475569;
                border-color: #64748b;
            }
            QPushButton:disabled {
                background-color: #1e293b;
                color: #64748b;
                border-color: #334155;
            }
        """)
        self.folder_btn.clicked.connect(self._select_watch_folder)
        self.folder_btn.setEnabled(False)
        header_layout.addWidget(self.folder_btn)
        
        layout.addLayout(header_layout)
        
        # Watch folder path display
        self.folder_label = QLabel("")
        self.folder_label.setStyleSheet("color: #64748b; font-size: 11px; padding-left: 4px;")
        layout.addWidget(self.folder_label)
        
        # Scheduled posts table container
        self.table_container = QWidget()
        table_container_layout = QVBoxLayout(self.table_container)
        table_container_layout.setContentsMargins(0, 0, 0, 0)
        
        # Modern styled table
        self.schedule_table = QTableWidget()
        self.schedule_table.setColumnCount(6)
        self.schedule_table.setHorizontalHeaderLabels([
            "Platform", "Content", "Scheduled Time", "Status", "Media", "Actions"
        ])
        
        # Table styling - Refined for "Premium" look
        self.schedule_table.setStyleSheet("""
            QTableWidget {
                background-color: #1a1a1b;
                border: 1px solid #333335;
                border-radius: 8px;
                gridline-color: #2a2a2c;
                selection-background-color: #2563eb;
                selection-color: #ffffff;
                outline: none;
            }
            QTableWidget::item {
                padding: 10px 12px;
                border-bottom: 1px solid #2a2a2c;
                color: #e2e8f0;
            }
            QTableWidget::item:selected {
                background-color: #3b82f6;
                color: white;
            }
            QTableWidget::item:hover {
                background-color: #2a2a2c;
            }
            QHeaderView::section {
                background-color: #242426;
                color: #94a3b8;
                font-weight: bold;
                font-size: 11px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                padding: 12px;
                border: none;
                border-bottom: 2px solid #3b82f6;
            }
            QTableWidget::horizontalHeader {
                background-color: #242426;
            }
            QScrollBar:vertical {
                background-color: #1a1a1b;
                width: 12px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: #3f3f46;
                border-radius: 6px;
                min-height: 20px;
                margin: 2px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #52525b;
            }
        """)
        
        # Column widths
        header = self.schedule_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)  # Platform
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Content
        header.setSectionResizeMode(2, QHeaderView.Fixed)  # Time
        header.setSectionResizeMode(3, QHeaderView.Fixed)  # Status
        header.setSectionResizeMode(4, QHeaderView.Fixed)  # Media
        header.setSectionResizeMode(5, QHeaderView.Fixed)  # Actions
        
        self.schedule_table.setColumnWidth(0, 110)  # Platform
        self.schedule_table.setColumnWidth(2, 150)  # Time
        self.schedule_table.setColumnWidth(3, 90)   # Status
        self.schedule_table.setColumnWidth(4, 70)   # Media
        self.schedule_table.setColumnWidth(5, 140)  # Actions
        
        self.schedule_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.schedule_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.schedule_table.setMinimumHeight(300)
        self.schedule_table.setAlternatingRowColors(True)
        self.schedule_table.verticalHeader().setDefaultSectionSize(50)
        self.schedule_table.setShowGrid(False)
        
        # Enable drag and drop on the table itself
        self.schedule_table.setAcceptDrops(True)
        self.schedule_table.dragEnterEvent = self._table_drag_enter
        self.schedule_table.dragMoveEvent = self._table_drag_move
        self.schedule_table.dropEvent = self._table_drop
        table_container_layout.addWidget(self.schedule_table)
        
        # Watermark label for empty state
        self.watermark_label = QLabel("📁 Drop files here to schedule\nor use the Content Editor")
        self.watermark_label.setAlignment(Qt.AlignCenter)
        self.watermark_label.setStyleSheet("""
            QLabel {
                color: #475569;
                font-size: 14px;
                padding: 60px;
                background: transparent;
            }
        """)
        self.watermark_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        table_container_layout.addWidget(self.watermark_label)
        
        layout.addWidget(self.table_container, stretch=1)
        
        # Action buttons - modern styled
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e40af;
                color: #f8fafc;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
            QPushButton:pressed {
                background-color: #1e3a8a;
            }
        """)
        refresh_btn.clicked.connect(self.refresh)
        btn_layout.addWidget(refresh_btn)
        
        btn_layout.addStretch()
        
        # Edit button
        edit_btn = QPushButton("✏️ Edit Selected")
        edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #0f766e;
                color: #f8fafc;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #14b8a6;
            }
            QPushButton:pressed {
                background-color: #0d9488;
            }
        """)
        edit_btn.clicked.connect(self._edit_selected)
        btn_layout.addWidget(edit_btn)
        
        cancel_btn = QPushButton("🗑️ Remove")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #b91c1c;
                color: #f8fafc;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #dc2626;
            }
            QPushButton:pressed {
                background-color: #991b1b;
            }
        """)
        cancel_btn.clicked.connect(self._remove_selected)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
    
    def _toggle_folder_watch(self, enabled: bool):
        """Toggle folder watching."""
        self.folder_btn.setEnabled(enabled)
        if not enabled:
            self.folder_watcher.stop()
            self.folder_label.setText("")
    
    def _table_drag_enter(self, event):
        """Handle drag enter on table."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def _table_drag_move(self, event):
        """Handle drag move on table."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def _table_drop(self, event):
        """Handle file drop on table."""
        files = []
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path:
                files.append(Path(file_path))
        
        if files:
            self._on_files_dropped(files)
            logger.info(f"Dropped {len(files)} file(s) on table")
        event.acceptProposedAction()
    
    def _select_watch_folder(self):
        """Select folder to watch."""
        folder = QFileDialog.getExistingDirectory(self, "Select Folder to Watch")
        if folder:
            folder_path = Path(folder)
            self.folder_watcher.set_folder(folder_path)
            self.folder_label.setText(f"Watching: {folder}")
            
            # Save to config
            # TODO: Persist this setting
    
    def _on_new_files(self, files: list):
        """Handle new files from folder watcher."""
        self._on_files_dropped(files)
    
    def _on_files_dropped(self, files: list):
        """Handle dropped files - auto-add without showing dialog."""
        from datetime import datetime, timedelta
        
        # Check for accounts in both database and browser_connect
        db = get_database()
        db_accounts = db.get_all_accounts()
        
        browser_conn = get_browser_connect()
        connected_accounts = browser_conn.get_connected_accounts()
        
        # If no accounts anywhere, show warning
        if not db_accounts and not connected_accounts:
            QMessageBox.warning(self, "No Accounts", "Please connect an account first.")
            return
        
        # Use first available account (prefer browser_connect accounts)
        if connected_accounts:
            default_account = connected_accounts[0]
            platform_name = default_account.platform.value.lower()
            
            # Find matching database account
            db_acc = None
            for acc in db_accounts:
                if acc.platform.lower() == platform_name:
                    db_acc = acc
                    break
            
            # If no database account found, create one
            if not db_acc:
                from src.data.models import Account
                new_account = Account(
                    id=None,
                    platform=platform_name,
                    username=default_account.display_name,
                    is_active=True,
                )
                try:
                    account_id = db.add_account(new_account)
                    db_acc = db.get_account(account_id)
                except Exception:
                    # Might already exist, try to find by username
                    for acc in db_accounts:
                        if acc.username.lower() == default_account.display_name.lower():
                            db_acc = acc
                            break
            
            if not db_acc:
                QMessageBox.warning(self, "Account Error", "Could not find or create database account.")
                return
            
            acc = db_acc
        elif db_accounts:
            acc = db_accounts[0]
        else:
            return
        
        for file_path in files:
            # Auto-schedule for 1 hour from now
            scheduled_time = datetime.now() + timedelta(hours=1)
            
            # Create data dict for auto-scheduling
            data = {
                "file_path": str(file_path),
                "platform": acc.platform,
                "account_id": acc.id,
                "title": file_path.stem.replace('_', ' ').replace('-', ' '),
                "description": f"Auto-scheduled: {file_path.name}",
                "scheduled_time": scheduled_time,
            }
            
            self._create_scheduled_post(data)
        
        logger.info(f"Auto-scheduled {len(files)} file(s)")
        QMessageBox.information(self, "Files Added", f"{len(files)} file(s) scheduled for 1 hour from now.")
    
    def _create_scheduled_post(self, data: dict):
        """Create a new scheduled post."""
        db = get_database()
        
        content = data.get("title", "")
        if data.get("description"):
            content = f"{content}\n\n{data['description']}" if content else data["description"]
        
        post = ScheduledPost(
            id=None,
            account_id=data["account_id"],
            content=content,
            scheduled_time=data["scheduled_time"],
            media_paths=[data["file_path"]] if data.get("file_path") else [],
        )
        
        post_id = db.add_scheduled_post(post)
        
        # Register with scheduler
        scheduler = get_scheduler()
        scheduler.schedule_post(
            job_id=f"post_{post_id}",
            run_at=data["scheduled_time"],
            platform=data["platform"],
            account_id=data["account_id"],
            content=content,
            media_paths=post.media_paths,
        )
        
        logger.info(f"Scheduled post for {data['scheduled_time']}")
        self.refresh()
    
    def refresh(self):
        """Refresh the schedule table."""
        self.schedule_table.setRowCount(0)
        
        db = get_database()
        posts = db.get_pending_posts()
        
        # Show/hide watermark based on whether there are posts
        if posts:
            self.watermark_label.hide()
        else:
            self.watermark_label.show()
        
        for post in posts:
            row = self.schedule_table.rowCount()
            self.schedule_table.insertRow(row)
            
            # Get account info
            account = db.get_account(post.account_id)
            platform_name = account.platform.title() if account else "Unknown"
            
            # Platform cell with icon
            platform_item = QTableWidgetItem(f"  {platform_name}")
            platform_item.setIcon(get_platform_icon(platform_name, 20))
            self.schedule_table.setItem(row, 0, platform_item)
            
            # Content preview
            content_preview = post.content[:60] + "..." if len(post.content) > 60 else post.content
            content_preview = content_preview.replace("\n", " ")
            content_item = QTableWidgetItem(content_preview)
            content_item.setToolTip(post.content)  # Full content on hover
            self.schedule_table.setItem(row, 1, content_item)
            
            # Scheduled time - formatted nicely
            time_str = post.scheduled_time.strftime("%b %d, %Y  %I:%M %p")
            time_item = QTableWidgetItem(time_str)
            self.schedule_table.setItem(row, 2, time_item)
            
            # Status with colored indicator
            status_text = post.status.value.title()
            status_item = QTableWidgetItem(f"  {status_text}")
            if status_text.lower() == "pending":
                status_item.setForeground(Qt.yellow)
            elif status_text.lower() == "posted":
                status_item.setForeground(Qt.green)
            elif status_text.lower() == "failed":
                status_item.setForeground(Qt.red)
            self.schedule_table.setItem(row, 3, status_item)
            
            # Media count
            media_count = len(post.media_paths) if post.media_paths else 0
            media_text = f"📎 {media_count}" if media_count > 0 else "—"
            media_item = QTableWidgetItem(media_text)
            media_item.setTextAlignment(Qt.AlignCenter)
            self.schedule_table.setItem(row, 4, media_item)
            
            # Actions - Edit and Delete button widget
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 4, 4, 4)
            actions_layout.setSpacing(6)
            
            # Inline Edit button
            edit_btn = QPushButton("✏️")
            edit_btn.setToolTip("Edit Post")
            edit_btn.setStyleSheet("""
                QPushButton {
                    background-color: #0f766e;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #14b8a6;
                }
            """)
            edit_btn.clicked.connect(lambda checked, pid=post.id: self._edit_post(pid))
            actions_layout.addWidget(edit_btn)
            
            # Inline Delete button
            del_btn = QPushButton("🗑️")
            del_btn.setToolTip("Delete Post")
            del_btn.setStyleSheet("""
                QPushButton {
                    background-color: #991b1b;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #dc2626;
                }
            """)
            del_btn.clicked.connect(lambda checked, pid=post.id: self._delete_post_by_id(pid))
            actions_layout.addWidget(del_btn)
            
            actions_layout.addStretch()
            self.schedule_table.setCellWidget(row, 5, actions_widget)
            
            # Store post ID for actions
            self.schedule_table.item(row, 0).setData(Qt.UserRole, post.id)
    
    def _remove_selected(self):
        """Remove selected scheduled posts and delete their files."""
        rows = set(item.row() for item in self.schedule_table.selectedItems())
        
        if not rows:
            return
        
        reply = QMessageBox.question(
            self, "Confirm Remove",
            f"Remove {len(rows)} scheduled post(s) and delete their files?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            db = get_database()
            scheduler = get_scheduler()
            
            for row in rows:
                post_id = self.schedule_table.item(row, 0).data(Qt.UserRole)
                
                # Get post details to find files to delete
                post = db.get_scheduled_post(post_id)
                if post and post.media_paths:
                    # Delete the media files
                    for file_path_str in post.media_paths:
                        try:
                            file_path = Path(file_path_str)
                            if file_path.exists():
                                file_path.unlink()
                                logger.info(f"Deleted file: {file_path}")
                        except Exception as e:
                            logger.error(f"Failed to delete file {file_path_str}: {e}")
                
                # Remove from database and scheduler
                db.delete_scheduled_post(post_id)
                scheduler.cancel_job(f"post_{post_id}")
            
            self.refresh()
    
    def _delete_post_by_id(self, post_id: int):
        """Delete a single post by ID."""
        reply = QMessageBox.question(
            self, "Confirm Delete",
            "Are you sure you want to delete this scheduled post and its media?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            db = get_database()
            scheduler = get_scheduler()
            
            post = db.get_scheduled_post(post_id)
            if post and post.media_paths:
                for file_path_str in post.media_paths:
                    try:
                        file_path = Path(file_path_str)
                        if file_path.exists():
                            file_path.unlink()
                            logger.info(f"Deleted file: {file_path}")
                    except Exception as e:
                        logger.error(f"Failed to delete file {file_path_str}: {e}")
            
            db.delete_scheduled_post(post_id)
            scheduler.cancel_job(f"post_{post_id}")
            self.refresh()
            
            from src.gui.widgets.toast_notifications import toast_success
            toast_success("Deleted", "Post removed")

    def _edit_selected(self):
        """Edit selected post from table."""
        rows = set(item.row() for item in self.schedule_table.selectedItems())
        
        if not rows:
            from src.gui.widgets.toast_notifications import toast_warning
            toast_warning("No Selection", "Please select a post to edit")
            return
        
        # Edit the first selected post
        row = list(rows)[0]
        post_id = self.schedule_table.item(row, 0).data(Qt.UserRole)
        self._edit_post(post_id)
    
    def _edit_post(self, post_id: int):
        """Open edit dialog for a specific post."""
        db = get_database()
        post = db.get_scheduled_post(post_id)
        
        if not post:
            from src.gui.widgets.toast_notifications import toast_error
            toast_error("Error", "Post not found")
            return
        
        # Create and show edit dialog
        dialog = EditPostDialog(post, self)
        if dialog.exec_() == QDialog.Accepted:
            # Get updated data from dialog
            updated_data = dialog.get_data()
            
            # Update the post in database
            post.content = updated_data["content"]
            post.scheduled_time = updated_data["scheduled_time"]
            
            # Update database
            db.update_scheduled_post(post)
            
            # Reschedule the job
            scheduler = get_scheduler()
            scheduler.cancel_job(f"post_{post_id}")
            
            account = db.get_account(post.account_id)
            platform_name = account.platform if account else "facebook"
            
            scheduler.schedule_post(
                job_id=f"post_{post_id}",
                run_at=updated_data["scheduled_time"],
                platform=platform_name,
                account_id=post.account_id,
                content=updated_data["content"],
                media_paths=post.media_paths or [],
            )
            
            from src.gui.widgets.toast_notifications import toast_success
            toast_success("Updated", "Post updated successfully")
            
            self.refresh()


class EditPostDialog(QDialog):
    """Dialog for editing a scheduled post."""
    
    def __init__(self, post, parent=None):
        super().__init__(parent)
        self.post = post
        self.setWindowTitle("✏️ Edit Scheduled Post")
        self.setMinimumWidth(550)
        self.setMinimumHeight(450)
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # Apply refined styling
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1a1b;
                color: #e2e8f0;
            }
            QLabel {
                color: #94a3b8;
                font-size: 13px;
            }
            QGroupBox {
                color: #e2e8f0;
                font-weight: bold;
                border: 1px solid #333335;
                border-radius: 8px;
                margin-top: 20px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px;
                color: #3b82f6;
            }
        """)
        
        # Header
        header = QLabel("✏️ Edit Scheduled Post")
        header.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: #f8fafc;
            padding-bottom: 5px;
        """)
        layout.addWidget(header)
        
        # Content section
        content_group = QGroupBox("Post Content")
        content_layout = QVBoxLayout(content_group)
        content_layout.setContentsMargins(15, 25, 15, 15)
        
        self.content_edit = QTextEdit()
        self.content_edit.setPlainText(self.post.content)
        self.content_edit.setStyleSheet("""
            QTextEdit {
                background-color: #0f0f10;
                color: #f8fafc;
                border: 1px solid #333335;
                border-radius: 6px;
                padding: 12px;
                font-size: 14px;
                line-height: 1.5;
            }
            QTextEdit:focus {
                border-color: #3b82f6;
            }
        """)
        self.content_edit.setMinimumHeight(120)
        content_layout.addWidget(self.content_edit)
        
        # Character count
        self.char_label = QLabel(f"{len(self.post.content)} characters")
        self.char_label.setStyleSheet("color: #52525b; font-size: 11px;")
        self.content_edit.textChanged.connect(self._update_char_count)
        content_layout.addWidget(self.char_label)
        
        layout.addWidget(content_group)
        
        # Schedule section
        schedule_group = QGroupBox("Schedule Time")
        schedule_layout = QVBoxLayout(schedule_group)
        schedule_layout.setContentsMargins(15, 25, 15, 15)
        
        # DateTime picker
        self.datetime_edit = QDateTimeEdit()
        self.datetime_edit.setDateTime(QDateTime(
            self.post.scheduled_time.year,
            self.post.scheduled_time.month,
            self.post.scheduled_time.day,
            self.post.scheduled_time.hour,
            self.post.scheduled_time.minute
        ))
        self.datetime_edit.setCalendarPopup(True)
        self.datetime_edit.setMinimumDateTime(QDateTime.currentDateTime())
        self.datetime_edit.setDisplayFormat("ddd, MMM d, yyyy 'at' h:mm AP")
        self.datetime_edit.setStyleSheet("""
            QDateTimeEdit {
                background-color: #0f0f10;
                color: #f8fafc;
                border: 1px solid #333335;
                border-radius: 6px;
                padding: 10px 12px;
                font-size: 14px;
            }
            QDateTimeEdit:focus {
                border-color: #3b82f6;
            }
            QDateTimeEdit::drop-down {
                border: none;
                background-color: #27272a;
                border-top-right-radius: 5px;
                border-bottom-right-radius: 5px;
                width: 35px;
            }
        """)
        schedule_layout.addWidget(self.datetime_edit)
        
        # Quick time buttons
        quick_layout = QHBoxLayout()
        quick_layout.setSpacing(8)
        
        for label, hours, icon in [
            ("In 1 hour", 1, "⏰"),
            ("In 3 hours", 3, "🕒"),
            ("Tomorrow 9AM", 24, "🌅")
        ]:
            btn = QPushButton(f"{icon} {label}")
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #27272a;
                    color: #e2e8f0;
                    border: 1px solid #3f3f46;
                    border-radius: 6px;
                    padding: 10px 14px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #3f3f46;
                    border-color: #52525b;
                }
            """)
            from functools import partial
            btn.clicked.connect(partial(self._set_quick_time, hours))
            quick_layout.addWidget(btn)
        
        schedule_layout.addLayout(quick_layout)
        layout.addWidget(schedule_group)
        
        # Media info (read-only)
        if self.post.media_paths:
            media_group = QGroupBox("Attached Media")
            media_layout = QVBoxLayout(media_group)
            media_layout.setContentsMargins(15, 25, 15, 15)
            
            for path in self.post.media_paths:
                media_label = QLabel(f"  📎  {Path(path).name}")
                media_label.setStyleSheet("color: #71717a; font-size: 13px;")
                media_layout.addWidget(media_label)
            
            layout.addWidget(media_group)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #e2e8f0;
                border: 1px solid #3f3f46;
                border-radius: 8px;
                padding: 12px 24px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #27272a;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("Save Changes")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
            QPushButton:pressed {
                background-color: #1d4ed8;
            }
        """)
        save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(save_btn)
        
        layout.addLayout(btn_layout)
    
    def _update_char_count(self):
        """Update character count label."""
        count = len(self.content_edit.toPlainText())
        self.char_label.setText(f"{count} characters")
    
    def _set_quick_time(self, hours: int):
        """Set quick schedule time."""
        from datetime import datetime, timedelta
        if hours == 24:
            # Tomorrow 9 AM
            tomorrow = datetime.now() + timedelta(days=1)
            from PyQt5.QtCore import QDate, QTime
            self.datetime_edit.setDate(QDate(tomorrow.year, tomorrow.month, tomorrow.day))
            self.datetime_edit.setTime(QTime(9, 0))
        else:
            dt = datetime.now() + timedelta(hours=hours)
            from PyQt5.QtCore import QDate, QTime
            self.datetime_edit.setDate(QDate(dt.year, dt.month, dt.day))
            self.datetime_edit.setTime(QTime(dt.hour, dt.minute))
    
    def get_data(self) -> dict:
        """Get the updated post data."""
        from datetime import datetime
        qdatetime = self.datetime_edit.dateTime()
        scheduled_time = datetime(
            qdatetime.date().year(),
            qdatetime.date().month(),
            qdatetime.date().day(),
            qdatetime.time().hour(),
            qdatetime.time().minute()
        )
        
        return {
            "content": self.content_edit.toPlainText(),
            "scheduled_time": scheduled_time,
        }
