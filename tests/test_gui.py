"""
Test GUI - PyQt5 GUI component tests.

Uses pytest-qt for PyQt5 testing.
"""

import pytest
from unittest.mock import patch, MagicMock


# Skip all tests if PyQt5 not available
pytestmark = pytest.mark.skipif(
    not pytest.importorskip("PyQt5", reason="PyQt5 not installed"),
    reason="PyQt5 not installed"
)


class TestMainWindow:
    """Test main window functionality."""
    
    @pytest.fixture
    def qtbot(self, qapp):
        """Create Qt bot for testing."""
        from pytestqt.qtbot import QtBot
        return QtBot(qapp)
    
    @pytest.fixture
    def qapp(self):
        """Create QApplication for tests."""
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance()
        if not app:
            app = QApplication([])
        yield app
    
    @pytest.fixture
    def mock_scheduler(self):
        """Mock scheduler to avoid background processes."""
        with patch("src.gui.main_window.get_scheduler") as mock:
            mock_instance = MagicMock()
            mock.return_value = mock_instance
            yield mock_instance
    
    def test_main_window_creates(self, qapp, mock_scheduler):
        """Test main window creation."""
        with patch("src.gui.main_window.AccountManagerWidget"), \
             patch("src.gui.main_window.ContentEditorWidget"), \
             patch("src.gui.main_window.SchedulerWidget"), \
             patch("src.gui.main_window.LogViewerWidget"):
            
            from src.gui.main_window import MainWindow
            window = MainWindow()
            
            assert window is not None
            assert window.windowTitle() == "AIOperator - Social Media Automation"
    
    def test_main_window_has_menu_bar(self, qapp, mock_scheduler):
        """Test main window has menu bar."""
        with patch("src.gui.main_window.AccountManagerWidget"), \
             patch("src.gui.main_window.ContentEditorWidget"), \
             patch("src.gui.main_window.SchedulerWidget"), \
             patch("src.gui.main_window.LogViewerWidget"):
            
            from src.gui.main_window import MainWindow
            window = MainWindow()
            
            menubar = window.menuBar()
            assert menubar is not None


class TestAccountManagerWidget:
    """Test account manager widget."""
    
    @pytest.fixture
    def qapp(self):
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance()
        if not app:
            app = QApplication([])
        yield app
    
    def test_widget_creates(self, qapp):
        """Test widget creation."""
        with patch("src.gui.widgets.account_manager.get_database") as mock_db:
            mock_db.return_value.get_all_accounts.return_value = []
            
            from src.gui.widgets.account_manager import AccountManagerWidget
            widget = AccountManagerWidget()
            
            assert widget is not None
    
    def test_widget_has_add_button(self, qapp):
        """Test widget has add button."""
        with patch("src.gui.widgets.account_manager.get_database") as mock_db:
            mock_db.return_value.get_all_accounts.return_value = []
            
            from src.gui.widgets.account_manager import AccountManagerWidget
            widget = AccountManagerWidget()
            
            assert widget.add_button is not None
            assert widget.add_button.text() == "+ Add"


class TestContentEditorWidget:
    """Test content editor widget."""
    
    @pytest.fixture
    def qapp(self):
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance()
        if not app:
            app = QApplication([])
        yield app
    
    def test_widget_creates(self, qapp):
        """Test widget creation."""
        with patch("src.gui.widgets.content_editor.LLMClient"):
            from src.gui.widgets.content_editor import ContentEditorWidget
            widget = ContentEditorWidget()
            
            assert widget is not None
    
    def test_widget_has_text_area(self, qapp):
        """Test widget has content text area."""
        with patch("src.gui.widgets.content_editor.LLMClient"):
            from src.gui.widgets.content_editor import ContentEditorWidget
            widget = ContentEditorWidget()
            
            assert widget.content_edit is not None
    
    def test_widget_has_generate_button(self, qapp):
        """Test widget has AI generate button."""
        with patch("src.gui.widgets.content_editor.LLMClient"):
            from src.gui.widgets.content_editor import ContentEditorWidget
            widget = ContentEditorWidget()
            
            assert widget.generate_btn is not None
            assert "Generate" in widget.generate_btn.text()


class TestSchedulerWidget:
    """Test scheduler widget."""
    
    @pytest.fixture
    def qapp(self):
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance()
        if not app:
            app = QApplication([])
        yield app
    
    def test_widget_creates(self, qapp):
        """Test widget creation."""
        with patch("src.gui.widgets.scheduler_widget.get_database") as mock_db, \
             patch("src.gui.widgets.scheduler_widget.get_scheduler"):
            mock_db.return_value.get_pending_posts.return_value = []
            
            from src.gui.widgets.scheduler_widget import SchedulerWidget
            widget = SchedulerWidget()
            
            assert widget is not None
    
    def test_widget_has_drop_zone(self, qapp):
        """Test widget has drag-drop zone."""
        with patch("src.gui.widgets.scheduler_widget.get_database") as mock_db, \
             patch("src.gui.widgets.scheduler_widget.get_scheduler"):
            mock_db.return_value.get_pending_posts.return_value = []
            
            from src.gui.widgets.scheduler_widget import SchedulerWidget
            widget = SchedulerWidget()
            
            assert widget.drop_zone is not None
    
    def test_drop_zone_accepts_drops(self, qapp):
        """Test drop zone accepts file drops."""
        from src.gui.widgets.scheduler_widget import DropZone
        
        drop_zone = DropZone()
        assert drop_zone.acceptDrops()
