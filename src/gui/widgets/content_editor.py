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
from PyQt5.QtGui import QFont

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
        
        # Content text area (description)
        self.content_edit = QTextEdit()
        self.content_edit.setPlaceholderText("Write your post description here...")
        self.content_edit.setFont(QFont("Segoe UI", 11))
        self.content_edit.textChanged.connect(self._update_char_count)
        self.content_edit.setMinimumHeight(80)
        self.content_edit.setMaximumHeight(140)
        layout.addWidget(self.content_edit)
        
        # AI Generation controls
        ai_group = QGroupBox("AI Content Generation")
        ai_layout = QVBoxLayout(ai_group)
        ai_layout.setContentsMargins(8, 10, 8, 8)
        ai_layout.setSpacing(6)
        
        # Topic input
        topic_layout = QHBoxLayout()
        topic_layout.addWidget(QLabel("Topic:"))
        self.topic_input = QLineEdit()
        self.topic_input.setPlaceholderText("Enter topic/keywords for AI to generate content...")
        topic_layout.addWidget(self.topic_input)
        ai_layout.addLayout(topic_layout)
        
        # Tone and platform
        options_layout = QHBoxLayout()
        
        options_layout.addWidget(QLabel("Tone:"))
        self.tone_combo = QComboBox()
        self.tone_combo.addItems([t.value.title() for t in Tone])
        self.tone_combo.setCurrentIndex(2)  # Engaging
        options_layout.addWidget(self.tone_combo)
        
        options_layout.addWidget(QLabel("Platform:"))
        self.platform_combo = QComboBox()
        self.platform_combo.addItems([p.value.title() for p in Platform])
        self.platform_combo.currentIndexChanged.connect(self._on_platform_changed)
        options_layout.addWidget(self.platform_combo)
        
        options_layout.addStretch()
        ai_layout.addLayout(options_layout)
        
        # Generate buttons
        gen_buttons_layout = QHBoxLayout()
        
        self.generate_btn = QPushButton("🤖 Generate")
        self.generate_btn.clicked.connect(self._generate_content)
        gen_buttons_layout.addWidget(self.generate_btn)
        
        self.improve_btn = QPushButton("✨ Improve")
        self.improve_btn.clicked.connect(self._improve_content)
        gen_buttons_layout.addWidget(self.improve_btn)
        
        self.hashtag_btn = QPushButton("#️⃣ Add Hashtags")
        self.hashtag_btn.clicked.connect(self._add_hashtags)
        gen_buttons_layout.addWidget(self.hashtag_btn)
        
        gen_buttons_layout.addStretch()
        ai_layout.addLayout(gen_buttons_layout)
        
        # Progress bar
        self.progress = QProgressBar()
        self.progress.setVisible(False)
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
        
        content = self.content_edit.toPlainText().strip()
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
    
    def _add_media(self):
        """Add media files."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Media",
            "",
            "Images & Videos (*.jpg *.jpeg *.png *.gif *.mp4 *.mov)"
        )
        
        for file_path in files:
            path = Path(file_path)
            self.media_paths.append(path)
            self.media_list.addItem(path.name)
    
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
        if not content:
            QMessageBox.warning(self, "No Content", "Please write some content to schedule.")
            return
        
        # Create dialog - keep reference to prevent GC
        self._schedule_dialog = QDialog(self)
        dialog = self._schedule_dialog
        dialog.setWindowTitle("Schedule Post")
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout(dialog)
        
        # Info label
        info_label = QLabel("Select when to post:")
        layout.addWidget(info_label)
        
        # DateTime picker
        form_layout = QFormLayout()
        
        datetime_edit = QDateTimeEdit()
        datetime_edit.setDateTime(QDateTime.currentDateTime().addSecs(3600))  # Default: 1 hour from now
        datetime_edit.setCalendarPopup(True)
        datetime_edit.setMinimumDateTime(QDateTime.currentDateTime())
        datetime_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        form_layout.addRow("Post at:", datetime_edit)
        
        layout.addLayout(form_layout)
        
        # Quick schedule buttons
        quick_layout = QHBoxLayout()
        for label, hours in [("In 1 hour", 1), ("In 3 hours", 3), ("Tomorrow 9AM", 24)]:
            btn = QPushButton(label)
            # Use functools.partial to properly capture variables
            from functools import partial
            btn.clicked.connect(partial(self._set_quick_schedule_time, datetime_edit, hours))
            quick_layout.addWidget(btn)
        layout.addLayout(quick_layout)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(cancel_btn)
        
        schedule_btn = QPushButton("📅 Schedule")
        schedule_btn.setStyleSheet("background-color: #1a73e8; color: white;")
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
