"""
AIOperator - Main Entry Point

Windows Desktop Automation with LLM & Browser DOM
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.logger import setup_logging, get_logger
from src.config import config


def main():
    """Application entry point."""
    # Setup logging
    setup_logging()
    logger = get_logger(__name__)
    
    logger.info("Starting AIOperator...")
    
    # Validate configuration
    errors = config.validate()
    if errors:
        for error in errors:
            logger.warning(f"Config warning: {error}")
    
    # Import and launch GUI
    try:
        from PyQt5.QtWidgets import QApplication
        from src.gui.main_window import MainWindow
        
        app = QApplication(sys.argv)
        app.setApplicationName("AIOperator")
        app.setOrganizationName("AIOperator")
        
        # Apply dark theme
        app.setStyle("Fusion")
        
        window = MainWindow()
        window.show()
        
        logger.info("GUI initialized successfully")
        sys.exit(app.exec_())
        
    except ImportError as e:
        logger.error(f"Failed to import GUI components: {e}")
        logger.error("Make sure PyQt5 is installed: pip install PyQt5")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Application error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
