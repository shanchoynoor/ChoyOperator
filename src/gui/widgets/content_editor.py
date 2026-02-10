"""
Content Editor Widget - Create and edit post content.

Includes LLM integration for content generation.
"""

from pathlib import Path

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QLabel, QComboBox, QFileDialog, QListWidget, QListWidgetItem,
    QGroupBox, QProgressBar, QMessageBox, QLineEdit, QDateTimeEdit,
    QDialog, QFormLayout
)
from PyQt5.QtCore import pyqtSignal, Qt, QThread, pyqtSlot, QDateTime
from PyQt5.QtGui import QFont, QDragEnterEvent, QDropEvent

from src.core.llm_client import LLMClient, Platform, Tone
from src.config import config
from src.utils.logger import get_logger


logger = get_logger(__name__)


class GenerateWorker(QThread):
    """Background worker for LLM content generation."""
    
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    
    def __init__(self, llm_client: LLMClient, prompt: str, platform: Platform, tone: Tone):
        super().__init__()
        self.llm_client = llm_client
        self.prompt = prompt
        self.platform = platform
        self.tone = tone
    
    def run(self):
        try:
            result = self.llm_client.generate_post(
                self.prompt,
                self.platform,
                self.tone
            )
            self.finished.emit(result.content)
        except Exception as e:
            self.error.emit(str(e))


class ContentEditorWidget(QWidget):
    """Widget for creating and editing post content."""
    
    post_requested = pyqtSignal(str, list)  # content, media_paths
    schedule_requested = pyqtSignal(str, object, list)  # content, datetime, media_paths
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_account_id = None
        self.media_paths = []
        self.llm_client = None
        self._init_ui()
        self._init_llm()
    
    def _init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        header = QLabel("Content Editor")
        header.setStyleSheet("font-size: 16px; font-weight: bold;")
        header_layout.addWidget(header)
        
        # Character counter
        self.char_counter = QLabel("0 / 280")
        self.char_counter.setStyleSheet("color: #888;")
        header_layout.addStretch()
        header_layout.addWidget(self.char_counter)
        
        layout.addLayout(header_layout)
        
        # AI Generation controls - compact
        ai_group = QGroupBox("AI Content Generation")
        ai_layout = QVBoxLayout(ai_group)
        ai_layout.setContentsMargins(6, 8, 6, 6)
        ai_layout.setSpacing(4)
        
        # Topic + Tone + Platform in one row
        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("Topic:"))
        self.topic_input = QLineEdit()
        self.topic_input.setPlaceholderText("Enter topic...")
        top_row.addWidget(self.topic_input, stretch=1)
        
        top_row.addWidget(QLabel("Tone:"))
        self.tone_combo = QComboBox()
        self.tone_combo.addItems([t.value.title() for t in Tone])
        self.tone_combo.setCurrentIndex(2)
        top_row.addWidget(self.tone_combo)
        
        top_row.addWidget(QLabel("Platform:"))
        self.platform_combo = QComboBox()
        self.platform_combo.addItems([p.value.title() for p in Platform])
        self.platform_combo.currentIndexChanged.connect(self._on_platform_changed)
        top_row.addWidget(self.platform_combo)
        ai_layout.addLayout(top_row)
        
        # Generate buttons row
        gen_buttons_layout = QHBoxLayout()
        self.generate_btn = QPushButton("🤖 Generate")
        self.generate_btn.clicked.connect(self._generate_content)
        gen_buttons_layout.addWidget(self.generate_btn)
        
        self.improve_btn = QPushButton("✨ Improve")
        self.improve_btn.clicked.connect(self._improve_content)
        gen_buttons_layout.addWidget(self.improve_btn)
        
        self.hashtag_btn = QPushButton("Hashtag")
        self.hashtag_btn.clicked.connect(self._add_hashtags)
        gen_buttons_layout.addWidget(self.hashtag_btn)
        
        gen_buttons_layout.addStretch()
        ai_layout.addLayout(gen_buttons_layout)
        
        # Progress bar (compact)
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setMaximumHeight(12)
        ai_layout.addWidget(self.progress)
        
        layout.addWidget(ai_group)
        
        # Media attachments
        media_group = QGroupBox("Media Attachments")
        media_layout = QHBoxLayout(media_group)
        media_layout.setContentsMargins(8, 10, 8, 8)
        
        self.media_list = QListWidget()
        self.media_list.setMaximumHeight(60)
        media_layout.addWidget(self.media_list)
        
        media_btn_layout = QVBoxLayout()
        add_media_btn = QPushButton("Add")
        add_media_btn.clicked.connect(self._add_media)
        media_btn_layout.addWidget(add_media_btn)
        
        remove_media_btn = QPushButton("Remove")
        remove_media_btn.clicked.connect(self._remove_media)
        media_btn_layout.addWidget(remove_media_btn)
        
        media_layout.addLayout(media_btn_layout)
        layout.addWidget(media_group)
        
        # Title input (for YouTube and other platforms that need separate title)
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Post title (optional, for YouTube, etc.)...")
        self.title_edit.setStyleSheet("""
            QLineEdit {
                background-color: #1e1e1e;
                color: #e0e0e0;
                border: 1px solid #333;
                border-radius: 5px;
                padding: 8px;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.title_edit)
        
        # Content text area (description) - flexible height
        self.content_edit = QTextEdit()
        self.content_edit.setPlaceholderText("Write your post description here...")
        self.content_edit.setFont(QFont("Segoe UI", 11))
        self.content_edit.textChanged.connect(self._update_char_count)
        self.content_edit.setMinimumHeight(60)
        layout.addWidget(self.content_edit, stretch=1)
        
        # Action buttons
        action_layout = QHBoxLayout()
        
        self.preview_btn = QPushButton("👁️ Preview")
        self.preview_btn.clicked.connect(self._preview_content)
        action_layout.addWidget(self.preview_btn)
        
        action_layout.addStretch()
        
        self.schedule_btn = QPushButton("📅 Schedule")
        self.schedule_btn.clicked.connect(self._show_schedule_dialog)
        self.schedule_btn.setStyleSheet("padding: 10px 20px;")
        action_layout.addWidget(self.schedule_btn)
        
        self.post_btn = QPushButton("📤 Post Now")
        self.post_btn.clicked.connect(self._request_post)
        self.post_btn.setStyleSheet("background-color: #1a73e8; color: white; padding: 10px 20px;")
        action_layout.addWidget(self.post_btn)
        
        layout.addLayout(action_layout)
    
    def _init_llm(self):
        """Initialize LLM client if API key is configured."""
        if config.llm.api_key:
            try:
                self.llm_client = LLMClient()
                logger.info("LLM client initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize LLM client: {e}")
    
    def _update_char_count(self):
        """Update character counter."""
        content = self.content_edit.toPlainText()
        length = len(content)
        
        # Get limit for current platform
        platform = list(Platform)[self.platform_combo.currentIndex()]
        limits = {
            Platform.TWITTER: 280,
            Platform.FACEBOOK: 500,
            Platform.LINKEDIN: 700,
            Platform.YOUTUBE: 500,
        }
        limit = limits.get(platform, 500)
        
        self.char_counter.setText(f"{length} / {limit}")
        
        # Color based on length
        if length > limit:
            self.char_counter.setStyleSheet("color: #f44336;")
        elif length > limit * 0.9:
            self.char_counter.setStyleSheet("color: #ff9800;")
        else:
            self.char_counter.setStyleSheet("color: #888;")
    
    def _on_platform_changed(self, index: int):
        """Handle platform selection change."""
        self._update_char_count()
    
    def set_current_account(self, account_id: int):
        """Set the current account for posting."""
        self.current_account_id = account_id
    
    def _generate_content(self):
        """Generate content using LLM."""
        if not self.llm_client:
            QMessageBox.warning(
                self, 
                "LLM Not Configured",
                "Please set your OpenRouter API key in settings."
            )
            return
        
        topic = self.topic_input.toPlainText().strip()
        if not topic:
            QMessageBox.warning(self, "No Topic", "Please enter a topic for content generation.")
            return
        
        platform = list(Platform)[self.platform_combo.currentIndex()]
        tone = list(Tone)[self.tone_combo.currentIndex()]
        
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)  # Indeterminate
        self.generate_btn.setEnabled(False)
        
        self.worker = GenerateWorker(self.llm_client, topic, platform, tone)
        self.worker.finished.connect(self._on_generate_finished)
        self.worker.error.connect(self._on_generate_error)
        self.worker.start()
    
    @pyqtSlot(str)
    def _on_generate_finished(self, content: str):
        """Handle generation complete."""
        self.content_edit.setPlainText(content)
        self.progress.setVisible(False)
        self.generate_btn.setEnabled(True)
        logger.info("Content generated successfully")
    
    @pyqtSlot(str)
    def _on_generate_error(self, error: str):
        """Handle generation error."""
        self.progress.setVisible(False)
        self.generate_btn.setEnabled(True)
        QMessageBox.critical(self, "Generation Error", f"Failed to generate content:\n{error}")
    
    def _improve_content(self):
        """Improve existing content using LLM."""
        if not self.llm_client:
            QMessageBox.warning(self, "LLM Not Configured", "Please set your OpenRouter API key.")
            return
        
        content = self.content_edit.toPlainText().strip()
        if not content:
            QMessageBox.warning(self, "No Content", "Please write some content to improve.")
            return
        
        try:
            self.progress.setVisible(True)
            self.progress.setRange(0, 0)
            improved = self.llm_client.improve_content(content)
            self.content_edit.setPlainText(improved)
            self.progress.setVisible(False)
            logger.info("Content improved successfully")
        except Exception as e:
            self.progress.setVisible(False)
            QMessageBox.critical(self, "Error", f"Failed to improve content:\n{e}")
    
    def _add_hashtags(self):
        """Add AI-generated hashtags."""
        if not self.llm_client:
            QMessageBox.warning(self, "LLM Not Configured", "Please set your OpenRouter API key.")
            return
        
        # Check if content indicates gibberish filenames (No caption)
        content = self.content_edit.toPlainText().strip()
        if content == "No caption" or content == "No caption\nNo title":
            logger.info("Skipping hashtags - gibberish filenames detected")
            QMessageBox.information(
                self,
                "Hashtags Skipped",
                "Hashtags not generated because the media files have gibberish filenames.\n"
                "Rename your files with meaningful names to get AI-generated content."
            )
            return
        
        if not content:
            QMessageBox.warning(self, "No Content", "Please write some content first.")
            return
        
        try:
            hashtags = self.llm_client.generate_hashtags(content)
            if hashtags:
                current = self.content_edit.toPlainText()
                new_content = f"{current}\n\n{' '.join(hashtags)}"
                self.content_edit.setPlainText(new_content)
                logger.info(f"Added {len(hashtags)} hashtags")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate hashtags:\n{e}")
    
    def _is_meaningful_filename(self, filename: str) -> bool:
        """
        Check if filename is meaningful (not gibberish/random).
        
        Returns True if filename contains actual words, False if random chars/numbers.
        """
        import re
        
        # Remove extension
        name = Path(filename).stem
        
        # Check for common gibberish patterns
        # Pattern 1: Only numbers or mostly numbers (e.g., "123456", "IMG_2024_01")
        if re.match(r'^[0-9_\-\.]+$', name):
            return False
        
        # Pattern 2: Random alphanumeric strings without vowels (e.g., "xkcdjq", "btrfs")
        vowels = set('aeiouAEIOU')
        letters_only = re.sub(r'[^a-zA-Z]', '', name)
        if len(letters_only) >= 4 and not any(v in letters_only for v in vowels):
            return False
        
        # Pattern 3: Long random strings (10+ chars with no recognizable words)
        if len(name) >= 10:
            # Check if it looks like a hash or random ID
            if re.match(r'^[a-f0-9]{8,}$', name, re.IGNORECASE):  # hex-like
                return False
            if re.match(r'^[a-z0-9]{12,}$', name, re.IGNORECASE):  # random alphanumeric
                # Check for common camera patterns
                if re.match(r'^(IMG|DSC|PANO|VID)_[0-9]+', name, re.IGNORECASE):
                    return False
                return False
        
        # Pattern 4: Very short names (1-2 chars)
        if len(name) <= 2:
            return False
        
        # Pattern 5: Common default camera names
        camera_patterns = [
            r'^IMG_?[0-9]+',
            r'^DSC_?[0-9]+',
            r'^PANO_?[0-9]+',
            r'^VID_?[0-9]+',
            r'^PHOTO_?[0-9]+',
            r'^SCREENSHOT',
            r'^Capture',
            r'^image-[0-9]+',
        ]
        for pattern in camera_patterns:
            if re.match(pattern, name, re.IGNORECASE):
                return False
        
        return True
    
    def _generate_from_filename(self, filename: str) -> tuple[str, str]:
        """
        Generate title and description from meaningful filename.
        
        Returns (title, description) where:
        - title: max 1 line
        - description: max 2 lines
        """
        name = Path(filename).stem
        
        # Clean up the filename
        clean_name = name.replace('_', ' ').replace('-', ' ').replace('.', ' ')
        clean_name = ' '.join(clean_name.split())  # Remove extra spaces
        
        # Capitalize properly
        clean_name = clean_name.title()
        
        # Generate title (1 line, max 60 chars)
        title = clean_name[:60] if len(clean_name) > 60 else clean_name
        
        # Generate description (2 lines max, ~100 chars)
        description = f"Sharing: {clean_name}"
        if len(description) > 100:
            description = description[:97] + "..."
        
        return title, description
    
    def _add_media(self):
        """Add media files and auto-generate content if filenames are meaningful."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Media",
            "",
            "Images & Videos (*.jpg *.jpeg *.png *.gif *.mp4 *.mov)"
        )
        
        meaningful_files = []
        gibberish_files = []
        
        for file_path in files:
            path = Path(file_path)
            self.media_paths.append(path)
            self.media_list.addItem(path.name)
            
            # Check if filename is meaningful
            if self._is_meaningful_filename(path.name):
                meaningful_files.append(path)
            else:
                gibberish_files.append(path)
        
        # Auto-generate content for meaningful files
        if meaningful_files and self.llm_client:
            # Use the first meaningful file for content generation
            first_file = meaningful_files[0]
            title, description = self._generate_from_filename(first_file.name)
            
            # Set the title and description
            self.title_edit.setText(title)
            self.content_edit.setPlainText(description)
            
            # Update topic input for AI context
            self.topic_input.setText(Path(first_file.name).stem.replace('_', ' ').replace('-', ' '))
            
            logger.info(f"Auto-generated content from: {first_file.name}")
        elif gibberish_files:
            # Set defaults for gibberish filenames
            self.title_edit.setText("No title")
            self.content_edit.setPlainText("No caption")
            logger.info(f"Gibberish filenames detected, set defaults for {len(gibberish_files)} files")
    
    def _remove_media(self):
        """Remove selected media."""
        row = self.media_list.currentRow()
        if row >= 0:
            self.media_list.takeItem(row)
            self.media_paths.pop(row)
    
    def _preview_content(self):
        """Preview the post content."""
        content = self.content_edit.toPlainText()
        platform = list(Platform)[self.platform_combo.currentIndex()]
        
        QMessageBox.information(
            self,
            f"Preview - {platform.value.title()}",
            f"{content}\n\n---\nMedia: {len(self.media_paths)} file(s)"
        )
    
    def _request_post(self):
        """Request to post the content."""
        content = self.content_edit.toPlainText().strip()
        if not content:
            QMessageBox.warning(self, "No Content", "Please write some content.")
            return
        
        self.post_requested.emit(content, [str(p) for p in self.media_paths])
    
    def _show_schedule_dialog(self):
        """Show schedule dialog with calendar for date/time selection."""
        content = self.content_edit.toPlainText().strip()
        
        # Allow scheduling with just content (no media required)
        if not content:
            QMessageBox.warning(self, "No Content", "Please write some content to schedule.")
            return
        
        # Create dialog - keep reference to prevent GC
        self._schedule_dialog = QDialog(self)
        dialog = self._schedule_dialog
        dialog.setWindowTitle("📅 Schedule Post")
        dialog.setMinimumWidth(420)
        dialog.setMinimumHeight(200)
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Header with info
        header_layout = QHBoxLayout()
        
        info_icon = QLabel("📅")
        info_icon.setStyleSheet("font-size: 24px;")
        header_layout.addWidget(info_icon)
        
        info_text = QLabel("Schedule Your Post")
        info_text.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #1a73e8;
        """)
        header_layout.addWidget(info_text)
        
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Info label
        info_label = QLabel("Select when to automatically publish your post:")
        info_label.setStyleSheet("color: #666; margin-bottom: 10px;")
        layout.addWidget(info_label)
        
        # DateTime picker section
        datetime_group = QGroupBox("Post Date & Time")
        datetime_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ddd;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        datetime_layout = QVBoxLayout(datetime_group)
        datetime_layout.setContentsMargins(15, 20, 15, 15)
        
        # DateTime edit
        datetime_edit = QDateTimeEdit()
        datetime_edit.setDateTime(QDateTime.currentDateTime().addSecs(3600))  # Default: 1 hour from now
        datetime_edit.setCalendarPopup(True)
        datetime_edit.setMinimumDateTime(QDateTime.currentDateTime())
        datetime_edit.setDisplayFormat("ddd, MMM d, yyyy 'at' h:mm AP")
        datetime_edit.setStyleSheet("""
            QDateTimeEdit {
                font-size: 14px;
                padding: 10px;
                border: 2px solid #38bdf8;
                border-radius: 8px;
                background-color: #0f172a;
                color: #f8fafc;
                min-height: 20px;
            }
            QDateTimeEdit:focus {
                border-color: #0ea5e9;
                background-color: #1e293b;
            }
            QDateTimeEdit::drop-down {
                border: none;
                background-color: #1d4ed8;
                border-top-right-radius: 6px;
                border-bottom-right-radius: 6px;
            }
            QDateTimeEdit::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #f8fafc;
                margin-top: 2px;
            }
            QDateTimeEdit QAbstractItemView {
                background-color: #0f172a;
                color: #e2e8f0;
                border: 1px solid #38bdf8;
                selection-background-color: #1d4ed8;
                selection-color: #f8fafc;
            }
            QCalendarWidget QWidget {
                alternate-background-color: #111827;
            }
            QCalendarWidget QToolButton {
                color: #f8fafc;
                background-color: transparent;
            }
            QCalendarWidget QMenu {
                background-color: #111827;
                color: #f8fafc;
            }
            QCalendarWidget QSpinBox {
                background-color: #111827;
                color: #f8fafc;
            }
            QCalendarWidget QTableView {
                background-color: #0f172a;
                color: #e2e8f0;
                selection-background-color: #1d4ed8;
                selection-color: #f8fafc;
                gridline-color: #1e293b;
            }
            QCalendarWidget QTableView::item:hover {
                background-color: #1e293b;
            }
        """)
        datetime_layout.addWidget(datetime_edit)
        
        layout.addWidget(datetime_group)
        
        # Quick schedule buttons
        quick_group = QGroupBox("Quick Schedule")
        quick_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ddd;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        quick_layout = QHBoxLayout(quick_group)
        quick_layout.setContentsMargins(15, 20, 15, 15)
        quick_layout.setSpacing(10)
        
        for label, hours, icon in [
            ("In 1 hour", 1, "⏰"),
            ("In 3 hours", 3, "🕒"),
            ("Tomorrow 9AM", 24, "🌅")
        ]:
            btn = QPushButton(f"{icon} {label}")
            btn.setMinimumHeight(40)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #f8f9fa;
                    border: 1px solid #ddd;
                    border-radius: 6px;
                    color: #333;
                    font-weight: 500;
                    padding: 8px 12px;
                }
                QPushButton:hover {
                    background-color: #e3f2fd;
                    border-color: #1a73e8;
                }
                QPushButton:pressed {
                    background-color: #bbdefb;
                }
            """)
            # Use functools.partial to properly capture variables
            from functools import partial
            btn.clicked.connect(partial(self._set_quick_schedule_time, datetime_edit, hours))
            quick_layout.addWidget(btn)
        
        layout.addWidget(quick_group)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("❌ Cancel")
        cancel_btn.setMinimumHeight(40)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 6px;
                color: #666;
                font-weight: 500;
                padding: 10px 20px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #e8e8e8;
            }
        """)
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(cancel_btn)
        
        schedule_btn = QPushButton("📅 Schedule Post")
        schedule_btn.setMinimumHeight(40)
        schedule_btn.setStyleSheet("""
            QPushButton {
                background-color: #1a73e8;
                border: none;
                border-radius: 6px;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                min-width: 140px;
            }
            QPushButton:hover {
                background-color: #1565c0;
            }
            QPushButton:pressed {
                background-color: #0d47a1;
            }
        """)
        schedule_btn.clicked.connect(dialog.accept)
        btn_layout.addWidget(schedule_btn)
        
        layout.addLayout(btn_layout)
        
        # Show dialog
        result = dialog.exec_()
        
        # Clear reference after dialog closes
        self._schedule_dialog = None
        
        if result == QDialog.Accepted:
            from datetime import datetime
            qdatetime = datetime_edit.dateTime()
            scheduled_time = datetime(
                qdatetime.date().year(),
                qdatetime.date().month(),
                qdatetime.date().day(),
                qdatetime.time().hour(),
                qdatetime.time().minute()
            )
            self.schedule_requested.emit(content, scheduled_time, [str(p) for p in self.media_paths])
    
    def _set_quick_schedule_time(self, datetime_edit: QDateTimeEdit, hours: int):
        """Set quick schedule time."""
        from datetime import datetime, timedelta
        if hours == 24:
            # Tomorrow 9 AM
            tomorrow = datetime.now() + timedelta(days=1)
            from PyQt5.QtCore import QDate, QTime
            datetime_edit.setDate(QDate(tomorrow.year, tomorrow.month, tomorrow.day))
            datetime_edit.setTime(QTime(9, 0))
        else:
            dt = datetime.now() + timedelta(hours=hours)
            from PyQt5.QtCore import QDate, QTime
            datetime_edit.setDate(QDate(dt.year, dt.month, dt.day))
            datetime_edit.setTime(QTime(dt.hour, dt.minute))
