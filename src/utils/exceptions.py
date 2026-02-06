"""
Exceptions - Custom exception classes for AIOperator.

Provides structured error handling with context and recovery hints.
"""

from enum import Enum
from typing import Any


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"           # Recoverable, user can retry
    MEDIUM = "medium"     # Needs attention, may need config change
    HIGH = "high"         # Critical, action required
    CRITICAL = "critical" # App may need restart


class ErrorCategory(Enum):
    """Error categories for classification."""
    AUTHENTICATION = "auth"
    NETWORK = "network"
    RATE_LIMIT = "rate_limit"
    CONFIGURATION = "config"
    PLATFORM = "platform"
    AUTOMATION = "automation"
    DATABASE = "database"
    ENCRYPTION = "encryption"
    LLM = "llm"
    SCHEDULER = "scheduler"
    GUI = "gui"


class AIOperatorError(Exception):
    """
    Base exception for all AIOperator errors.
    
    Provides structured context for error handling and reporting.
    """
    
    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.AUTOMATION,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        details: dict[str, Any] | None = None,
        recovery_hint: str | None = None,
        original_error: Exception | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.details = details or {}
        self.recovery_hint = recovery_hint
        self.original_error = original_error
    
    def to_dict(self) -> dict:
        """Convert to dictionary for logging/serialization."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "details": self.details,
            "recovery_hint": self.recovery_hint,
            "original_error": str(self.original_error) if self.original_error else None,
        }
    
    def __str__(self) -> str:
        parts = [self.message]
        if self.recovery_hint:
            parts.append(f" (Hint: {self.recovery_hint})")
        return "".join(parts)


# Authentication Errors

class AuthenticationError(AIOperatorError):
    """Failed to authenticate with a platform."""
    
    def __init__(
        self,
        platform: str,
        message: str = "Authentication failed",
        **kwargs
    ):
        super().__init__(
            message=f"{platform}: {message}",
            category=ErrorCategory.AUTHENTICATION,
            severity=ErrorSeverity.HIGH,
            details={"platform": platform},
            recovery_hint="Check credentials and try logging in again",
            **kwargs
        )


class SessionExpiredError(AuthenticationError):
    """Session has expired and needs re-authentication."""
    
    def __init__(self, platform: str, **kwargs):
        super().__init__(
            platform=platform,
            message="Session expired",
            recovery_hint="Please log in again to refresh your session",
            **kwargs
        )


# Network Errors

class NetworkError(AIOperatorError):
    """Network-related error."""
    
    def __init__(self, message: str = "Network error occurred", **kwargs):
        super().__init__(
            message=message,
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            recovery_hint="Check your internet connection and try again",
            **kwargs
        )


class TimeoutError(NetworkError):
    """Operation timed out."""
    
    def __init__(self, operation: str, timeout: int, **kwargs):
        super().__init__(
            message=f"Operation '{operation}' timed out after {timeout}s",
            details={"operation": operation, "timeout": timeout},
            **kwargs
        )


# Rate Limiting

class RateLimitError(AIOperatorError):
    """Rate limit exceeded."""
    
    def __init__(
        self,
        platform: str,
        retry_after: int | None = None,
        **kwargs
    ):
        hint = f"Wait {retry_after} seconds before retrying" if retry_after else "Wait before retrying"
        super().__init__(
            message=f"{platform}: Rate limit exceeded",
            category=ErrorCategory.RATE_LIMIT,
            severity=ErrorSeverity.MEDIUM,
            details={"platform": platform, "retry_after": retry_after},
            recovery_hint=hint,
            **kwargs
        )


# Platform Errors

class PlatformError(AIOperatorError):
    """Platform-specific error."""
    
    def __init__(self, platform: str, message: str, **kwargs):
        super().__init__(
            message=f"{platform}: {message}",
            category=ErrorCategory.PLATFORM,
            severity=ErrorSeverity.MEDIUM,
            details={"platform": platform},
            **kwargs
        )


class ContentRejectedError(PlatformError):
    """Content was rejected by the platform."""
    
    def __init__(self, platform: str, reason: str = "Unknown", **kwargs):
        super().__init__(
            platform=platform,
            message=f"Content rejected: {reason}",
            recovery_hint="Modify content and try again",
            **kwargs
        )


class ElementNotFoundError(PlatformError):
    """UI element not found during automation."""
    
    def __init__(self, platform: str, element: str, **kwargs):
        super().__init__(
            platform=platform,
            message=f"Element not found: {element}",
            details={"element": element},
            recovery_hint="Platform UI may have changed. Check for updates.",
            **kwargs
        )


# LLM Errors

class LLMError(AIOperatorError):
    """LLM API error."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            category=ErrorCategory.LLM,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )


class LLMAPIKeyError(LLMError):
    """Invalid or missing API key."""
    
    def __init__(self, **kwargs):
        super().__init__(
            message="Invalid or missing OpenRouter API key",
            severity=ErrorSeverity.HIGH,
            recovery_hint="Add your OpenRouter API key in Settings > API",
            **kwargs
        )


class LLMQuotaExceededError(LLMError):
    """LLM API quota exceeded."""
    
    def __init__(self, **kwargs):
        super().__init__(
            message="API quota exceeded",
            recovery_hint="Check your OpenRouter usage and billing",
            **kwargs
        )


# Database Errors

class DatabaseError(AIOperatorError):
    """Database operation error."""
    
    def __init__(self, operation: str, message: str, **kwargs):
        super().__init__(
            message=f"Database {operation} failed: {message}",
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.HIGH,
            details={"operation": operation},
            **kwargs
        )


# Configuration Errors

class ConfigurationError(AIOperatorError):
    """Configuration error."""
    
    def __init__(self, setting: str, message: str, **kwargs):
        super().__init__(
            message=f"Configuration error ({setting}): {message}",
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.HIGH,
            details={"setting": setting},
            recovery_hint="Check your .env file and settings",
            **kwargs
        )


# Scheduler Errors

class SchedulerError(AIOperatorError):
    """Scheduler operation error."""
    
    def __init__(self, job_id: str, message: str, **kwargs):
        super().__init__(
            message=f"Scheduler error (job {job_id}): {message}",
            category=ErrorCategory.SCHEDULER,
            severity=ErrorSeverity.MEDIUM,
            details={"job_id": job_id},
            **kwargs
        )
