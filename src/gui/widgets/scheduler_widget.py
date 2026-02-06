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

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QDateTimeEdit, QComboBox, QGroupBox,
    QFileDialog, QMessageBox, QHeaderView, QAbstractItemView,
    QLineEdit, QCheckBox, QSpinBox, QDialog, QFormLayout, QTextEdit
)
from PyQt5.QtCore import (
    pyqtSignal, Qt, QDateTime, QTimer, QFileSystemWatcher, QMimeData
)
from PyQt5.QtGui import QDragEnterEvent, QDropEvent

from src.data.database import get_database
from src.data.models import ScheduledPost, PostStatusEnum
from src.core.scheduler import get_scheduler
from src.core.llm_client import LLMClient, Platform
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
        
        # Content fields with AI generation
        content_group = QGroupBox("Content (AI-Assisted)")
        content_layout = QVBoxLayout(content_group)
        
        # Title (for YouTube videos)
        title_layout = QHBoxLayout()
        title_layout.addWidget(QLabel("Title:"))
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Video/post title...")
        title_layout.addWidget(self.title_input)
        gen_title_btn = QPushButton("🤖 Generate")
        gen_title_btn.clicked.connect(self._generate_title)
        title_layout.addWidget(gen_title_btn)
        content_layout.addLayout(title_layout)
        
        # Description/Caption
        content_layout.addWidget(QLabel("Description/Caption:"))
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Post description or caption...")
        self.description_input.setMaximumHeight(100)
        content_layout.addWidget(self.description_input)
        
        desc_btn_layout = QHBoxLayout()
        gen_desc_btn = QPushButton("🤖 Generate Description")
        gen_desc_btn.clicked.connect(self._generate_description)
        desc_btn_layout.addWidget(gen_desc_btn)
        
        gen_hashtags_btn = QPushButton("#️⃣ Add Hashtags")
        gen_hashtags_btn.clicked.connect(self._generate_hashtags)
        desc_btn_layout.addWidget(gen_hashtags_btn)
        desc_btn_layout.addStretch()
        content_layout.addLayout(desc_btn_layout)
        
        layout.addWidget(content_group)
        
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
        
        # Header
        header_layout = QHBoxLayout()
        header = QLabel("📅 Scheduled Posts")
        header.setStyleSheet("font-size: 16px; font-weight: bold;")
        header_layout.addWidget(header)
        header_layout.addStretch()
        
        # Folder watch toggle
        self.watch_checkbox = QCheckBox("📂 Watch Folder")
        self.watch_checkbox.toggled.connect(self._toggle_folder_watch)
        header_layout.addWidget(self.watch_checkbox)
        
        self.folder_btn = QPushButton("Set Folder")
        self.folder_btn.clicked.connect(self._select_watch_folder)
        self.folder_btn.setEnabled(False)
        header_layout.addWidget(self.folder_btn)
        
        layout.addLayout(header_layout)
        
        # Watch folder path display
        self.folder_label = QLabel("")
        self.folder_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self.folder_label)
        
        # Drag and drop zone
        self.drop_zone = DropZone()
        self.drop_zone.files_dropped.connect(self._on_files_dropped)
        layout.addWidget(self.drop_zone)
        
        # Scheduled posts table - increased size
        self.schedule_table = QTableWidget()
        self.schedule_table.setColumnCount(5)
        self.schedule_table.setHorizontalHeaderLabels([
            "Platform", "Content", "Scheduled Time", "Status", "Actions"
        ])
        self.schedule_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.schedule_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.schedule_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.schedule_table.setMinimumHeight(250)  # Increased table height
        layout.addWidget(self.schedule_table, stretch=1)
        
        # Action buttons
        btn_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.refresh)
        btn_layout.addWidget(refresh_btn)
        
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("❌ Cancel Selected")
        cancel_btn.clicked.connect(self._cancel_selected)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
    
    def _toggle_folder_watch(self, enabled: bool):
        """Toggle folder watching."""
        self.folder_btn.setEnabled(enabled)
        if not enabled:
            self.folder_watcher.stop()
            self.folder_label.setText("")
    
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
        
        db = get_database()
        accounts = db.get_all_accounts()
        
        if not accounts:
            QMessageBox.warning(self, "No Accounts", "Please connect an account first.")
            return
        
        # Use first available account
        default_account = accounts[0]
        
        for file_path in files:
            # Auto-schedule for 1 hour from now
            scheduled_time = datetime.now() + timedelta(hours=1)
            
            # Create data dict for auto-scheduling
            data = {
                "file_path": str(file_path),
                "platform": default_account.platform,
                "account_id": default_account.id,
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
        
        for post in posts:
            row = self.schedule_table.rowCount()
            self.schedule_table.insertRow(row)
            
            # Get account info
            account = db.get_account(post.account_id)
            platform = account.platform.title() if account else "Unknown"
            
            self.schedule_table.setItem(row, 0, QTableWidgetItem(platform))
            self.schedule_table.setItem(row, 1, QTableWidgetItem(post.content[:50] + "..."))
            self.schedule_table.setItem(row, 2, QTableWidgetItem(
                post.scheduled_time.strftime("%Y-%m-%d %H:%M")
            ))
            self.schedule_table.setItem(row, 3, QTableWidgetItem(post.status.value.title()))
            
            # Store post ID for actions
            self.schedule_table.item(row, 0).setData(Qt.UserRole, post.id)
    
    def _cancel_selected(self):
        """Cancel selected scheduled posts."""
        rows = set(item.row() for item in self.schedule_table.selectedItems())
        
        if not rows:
            return
        
        reply = QMessageBox.question(
            self, "Confirm Cancel",
            f"Cancel {len(rows)} scheduled post(s)?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            db = get_database()
            scheduler = get_scheduler()
            
            for row in rows:
                post_id = self.schedule_table.item(row, 0).data(Qt.UserRole)
                db.delete_scheduled_post(post_id)
                scheduler.cancel_job(f"post_{post_id}")
            
            self.refresh()
