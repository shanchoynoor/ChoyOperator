"""
Error Handler - Centralized error handling and reporting.

Provides error logging, user notification, and recovery suggestions.
"""

import logging
import traceback
from datetime import datetime
from pathlib import Path
from typing import Callable

from src.utils.exceptions import (
    AIOperatorError, ErrorSeverity, ErrorCategory
)
from src.config import PROJECT_ROOT


logger = logging.getLogger(__name__)


class ErrorHandler:
    """
    Centralized error handler for the application.
    
    Features:
    - Structured error logging
    - Error report generation
    - GUI notification callbacks
    - Recovery suggestions
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self.error_log: list[dict] = []
        self.notify_callback: Callable | None = None
        self.error_log_path = PROJECT_ROOT / "logs" / "errors.log"
        
        # Ensure logs directory exists
        self.error_log_path.parent.mkdir(parents=True, exist_ok=True)
    
    def set_notify_callback(self, callback: Callable[[str, str, str], None]):
        """
        Set callback for GUI error notifications.
        
        Args:
            callback: Function(title, message, severity)
        """
        self.notify_callback = callback
    
    def handle(
        self,
        error: Exception,
        context: str = "",
        show_notification: bool = True,
    ) -> dict:
        """
        Handle an error with logging and optional notification.
        
        Args:
            error: The exception to handle
            context: Additional context about where the error occurred
            show_notification: Whether to show GUI notification
            
        Returns:
            Error report dictionary
        """
        # Build error report
        if isinstance(error, AIOperatorError):
            report = error.to_dict()
        else:
            report = {
                "error_type": type(error).__name__,
                "message": str(error),
                "category": ErrorCategory.AUTOMATION.value,
                "severity": ErrorSeverity.MEDIUM.value,
                "details": {},
                "recovery_hint": None,
                "original_error": None,
            }
        
        report["timestamp"] = datetime.now().isoformat()
        report["context"] = context
        report["traceback"] = traceback.format_exc()
        
        # Log to file
        self._log_error(report)
        
        # Add to in-memory log
        self.error_log.append(report)
        if len(self.error_log) > 100:
            self.error_log.pop(0)
        
        # Log with appropriate level
        severity = ErrorSeverity(report["severity"])
        log_msg = f"[{report['category']}] {report['message']}"
        if context:
            log_msg = f"{context}: {log_msg}"
        
        if severity in (ErrorSeverity.CRITICAL, ErrorSeverity.HIGH):
            logger.error(log_msg)
        elif severity == ErrorSeverity.MEDIUM:
            logger.warning(log_msg)
        else:
            logger.info(log_msg)
        
        # Show notification
        if show_notification and self.notify_callback:
            self._notify_user(report)
        
        return report
    
    def _log_error(self, report: dict):
        """Write error to log file."""
        try:
            with open(self.error_log_path, "a", encoding="utf-8") as f:
                f.write(f"\n{'='*60}\n")
                f.write(f"Timestamp: {report['timestamp']}\n")
                f.write(f"Type: {report['error_type']}\n")
                f.write(f"Category: {report['category']}\n")
                f.write(f"Severity: {report['severity']}\n")
                f.write(f"Context: {report.get('context', 'N/A')}\n")
                f.write(f"Message: {report['message']}\n")
                if report.get('recovery_hint'):
                    f.write(f"Recovery: {report['recovery_hint']}\n")
                if report.get('details'):
                    f.write(f"Details: {report['details']}\n")
                f.write(f"\nTraceback:\n{report.get('traceback', 'N/A')}\n")
        except Exception as e:
            logger.error(f"Failed to write error log: {e}")
    
    def _notify_user(self, report: dict):
        """Send error notification to GUI."""
        if not self.notify_callback:
            return
        
        title = f"Error: {report['error_type']}"
        message = report['message']
        if report.get('recovery_hint'):
            message += f"\n\nSuggestion: {report['recovery_hint']}"
        
        self.notify_callback(title, message, report['severity'])
    
    def get_recent_errors(self, count: int = 10) -> list[dict]:
        """Get recent errors from memory."""
        return self.error_log[-count:]
    
    def generate_error_report(self) -> str:
        """Generate a full error report for debugging."""
        report_path = PROJECT_ROOT / "logs" / f"error_report_{datetime.now():%Y%m%d_%H%M%S}.txt"
        
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("AIOperator Error Report\n")
            f.write(f"Generated: {datetime.now()}\n")
            f.write("="*60 + "\n\n")
            
            if not self.error_log:
                f.write("No errors recorded in this session.\n")
            else:
                for i, err in enumerate(self.error_log, 1):
                    f.write(f"Error #{i}\n")
                    f.write(f"  Time: {err['timestamp']}\n")
                    f.write(f"  Type: {err['error_type']}\n")
                    f.write(f"  Message: {err['message']}\n")
                    f.write(f"  Category: {err['category']}\n")
                    f.write(f"  Severity: {err['severity']}\n")
                    f.write("\n")
        
        return str(report_path)
    
    def clear_errors(self):
        """Clear in-memory error log."""
        self.error_log.clear()


def get_error_handler() -> ErrorHandler:
    """Get the singleton error handler instance."""
    return ErrorHandler()


def handle_error(
    error: Exception,
    context: str = "",
    show_notification: bool = True,
) -> dict:
    """
    Convenience function to handle errors.
    
    Args:
        error: The exception to handle
        context: Additional context
        show_notification: Show GUI notification
        
    Returns:
        Error report dictionary
    """
    return get_error_handler().handle(error, context, show_notification)
