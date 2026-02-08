"""
Worker threads for social media posting to prevent GUI hanging.
"""

import logging
from PyQt5.QtCore import QThread, pyqtSignal
from src.core.social_poster import get_poster

logger = logging.getLogger(__name__)

class FacebookPostWorker(QThread):
    """Worker thread for Facebook posting."""
    
    finished = pyqtSignal(bool, str)  # (success, message)
    status_update = pyqtSignal(str)   # Status message for UI
    
    def __init__(self, content, media_paths=None, headless=True):
        super().__init__()
        self.content = content
        self.media_paths = media_paths or []
        self.headless = headless
        
    def run(self):
        """Execute posting in background thread."""
        try:
            self.status_update.emit("Starting browser...")
            logger.info("Worker thread starting social poster...")
            poster = get_poster()
            
            # We wrap the poster call which might wait for login
            success, message = poster.post_to_facebook(
                content=self.content,
                media_paths=self.media_paths,
                headless=self.headless
            )
            
            logger.info(f"Worker thread finished with success={success}")
            self.finished.emit(success, message)
        except Exception as e:
            logger.exception(f"CRITICAL Worker error: {e}")
            self.finished.emit(False, f"Internal Error: {str(e)}")
