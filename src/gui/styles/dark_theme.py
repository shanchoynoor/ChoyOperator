"""
Dark Theme - PyQt stylesheet for dark mode UI.
"""


def get_dark_stylesheet() -> str:
    """Get the dark theme stylesheet."""
    return """
    /* Main Window */
    QMainWindow, QDialog {
        background-color: #121212;
        color: #e0e0e0;
    }
    
    /* Widgets */
    QWidget {
        background-color: #121212;
        color: #e0e0e0;
        font-family: 'Segoe UI', sans-serif;
        font-size: 13px;
    }
    
    /* Labels */
    QLabel {
        color: #e0e0e0;
        background-color: transparent;
    }
    
    /* Text Edit */
    QTextEdit, QPlainTextEdit {
        background-color: #1e1e1e;
        color: #e0e0e0;
        border: 1px solid #333;
        border-radius: 5px;
        padding: 8px;
        selection-background-color: #1a73e8;
    }
    
    QTextEdit:focus, QPlainTextEdit:focus {
        border-color: #1a73e8;
    }
    
    /* Line Edit */
    QLineEdit {
        background-color: #1e1e1e;
        color: #e0e0e0;
        border: 1px solid #333;
        border-radius: 5px;
        padding: 8px;
        selection-background-color: #1a73e8;
    }
    
    QLineEdit:focus {
        border-color: #1a73e8;
    }
    
    /* Buttons */
    QPushButton {
        background-color: #2d2d2d;
        color: #e0e0e0;
        border: 1px solid #444;
        border-radius: 5px;
        padding: 8px 16px;
        min-width: 80px;
    }
    
    QPushButton:hover {
        background-color: #3d3d3d;
        border-color: #555;
    }
    
    QPushButton:pressed {
        background-color: #1a1a1a;
    }
    
    QPushButton:disabled {
        background-color: #1a1a1a;
        color: #666;
        border-color: #333;
    }
    
    /* Primary Button (special class via object name or inline style) */
    QPushButton[primary="true"], QPushButton:default {
        background-color: #1a73e8;
        color: white;
        border-color: #1a73e8;
    }
    
    QPushButton[primary="true"]:hover, QPushButton:default:hover {
        background-color: #1557b0;
    }
    
    /* Combo Box */
    QComboBox {
        background-color: #1e1e1e;
        color: #e0e0e0;
        border: 1px solid #333;
        border-radius: 5px;
        padding: 6px 10px;
        min-width: 100px;
    }
    
    QComboBox::drop-down {
        border: none;
        width: 30px;
    }
    
    QComboBox::down-arrow {
        width: 12px;
        height: 12px;
    }
    
    QComboBox QAbstractItemView {
        background-color: #1e1e1e;
        color: #e0e0e0;
        border: 1px solid #333;
        selection-background-color: #1a73e8;
    }
    
    /* List Widget */
    QListWidget {
        background-color: #1e1e1e;
        color: #e0e0e0;
        border: 1px solid #333;
        border-radius: 5px;
        outline: none;
    }
    
    QListWidget::item {
        padding: 8px;
        border-bottom: 1px solid #2d2d2d;
    }
    
    QListWidget::item:selected {
        background-color: #1a73e8;
        color: white;
    }
    
    QListWidget::item:hover:!selected {
        background-color: #2d2d2d;
    }
    
    /* Table Widget */
    QTableWidget {
        background-color: #1e1e1e;
        color: #e0e0e0;
        border: 1px solid #333;
        border-radius: 5px;
        gridline-color: #2d2d2d;
    }
    
    QTableWidget::item {
        padding: 8px;
    }
    
    QTableWidget::item:selected {
        background-color: #1a73e8;
    }
    
    QHeaderView::section {
        background-color: #2d2d2d;
        color: #e0e0e0;
        padding: 8px;
        border: none;
        border-bottom: 1px solid #333;
    }
    
    /* Group Box */
    QGroupBox {
        border: 1px solid #333;
        border-radius: 5px;
        margin-top: 10px;
        padding-top: 10px;
        font-weight: bold;
    }
    
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 5px;
        color: #888;
    }
    
    /* Tab Widget */
    QTabWidget::pane {
        border: 1px solid #333;
        border-radius: 5px;
        background-color: #1a1a1a;
    }
    
    QTabBar::tab {
        background-color: #1e1e1e;
        color: #888;
        padding: 10px 20px;
        border: 1px solid #333;
        border-bottom: none;
        border-top-left-radius: 5px;
        border-top-right-radius: 5px;
    }
    
    QTabBar::tab:selected {
        background-color: #1a1a1a;
        color: #e0e0e0;
    }
    
    QTabBar::tab:hover:!selected {
        background-color: #2d2d2d;
    }
    
    /* Scroll Bars */
    QScrollBar:vertical {
        background-color: #1a1a1a;
        width: 12px;
        border-radius: 6px;
    }
    
    QScrollBar::handle:vertical {
        background-color: #444;
        border-radius: 6px;
        min-height: 30px;
    }
    
    QScrollBar::handle:vertical:hover {
        background-color: #555;
    }
    
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0;
    }
    
    QScrollBar:horizontal {
        background-color: #1a1a1a;
        height: 12px;
        border-radius: 6px;
    }
    
    QScrollBar::handle:horizontal {
        background-color: #444;
        border-radius: 6px;
        min-width: 30px;
    }
    
    /* Check Box */
    QCheckBox {
        spacing: 8px;
    }
    
    QCheckBox::indicator {
        width: 18px;
        height: 18px;
        border-radius: 3px;
        border: 1px solid #444;
        background-color: #1e1e1e;
    }
    
    QCheckBox::indicator:checked {
        background-color: #1a73e8;
        border-color: #1a73e8;
    }
    
    /* Spin Box */
    QSpinBox, QDoubleSpinBox {
        background-color: #1e1e1e;
        color: #e0e0e0;
        border: 1px solid #333;
        border-radius: 5px;
        padding: 6px;
    }
    
    /* Progress Bar */
    QProgressBar {
        background-color: #1e1e1e;
        border: 1px solid #333;
        border-radius: 5px;
        text-align: center;
        color: #e0e0e0;
    }
    
    QProgressBar::chunk {
        background-color: #1a73e8;
        border-radius: 4px;
    }
    
    /* Status Bar */
    QStatusBar {
        background-color: #1a1a1a;
        border-top: 1px solid #333;
        color: #888;
    }
    
    /* Menu Bar */
    QMenuBar {
        background-color: #1a1a1a;
        color: #e0e0e0;
        border-bottom: 1px solid #333;
    }
    
    QMenuBar::item {
        padding: 8px 12px;
    }
    
    QMenuBar::item:selected {
        background-color: #2d2d2d;
    }
    
    QMenu {
        background-color: #1e1e1e;
        color: #e0e0e0;
        border: 1px solid #333;
    }
    
    QMenu::item {
        padding: 8px 30px;
    }
    
    QMenu::item:selected {
        background-color: #1a73e8;
    }
    
    /* Splitter */
    QSplitter::handle {
        background-color: #333;
    }
    
    QSplitter::handle:horizontal {
        width: 2px;
    }
    
    QSplitter::handle:vertical {
        height: 2px;
    }
    
    /* DateTime Edit */
    QDateTimeEdit {
        background-color: #1e1e1e;
        color: #e0e0e0;
        border: 1px solid #333;
        border-radius: 5px;
        padding: 6px;
    }
    
    QDateTimeEdit::drop-down {
        border: none;
        width: 30px;
    }
    
    /* Calendar */
    QCalendarWidget {
        background-color: #1e1e1e;
    }
    
    QCalendarWidget QToolButton {
        color: #e0e0e0;
        background-color: #2d2d2d;
        border-radius: 5px;
    }
    
    QCalendarWidget QMenu {
        background-color: #1e1e1e;
    }
    
    QCalendarWidget QSpinBox {
        background-color: #1e1e1e;
        color: #e0e0e0;
    }
    
    /* Message Box */
    QMessageBox {
        background-color: #121212;
    }
    
    QMessageBox QLabel {
        color: #e0e0e0;
    }
    """
