"""
Data Models - Dataclasses for application entities.

Defines the structure of accounts, posts, and logs.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from src.data.encryption import CredentialEncryption


class PostStatusEnum(Enum):
    """Status of a scheduled post."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Account:
    """Social media account."""
    
    id: int | None
    platform: str
    username: str
    encrypted_password: bytes | None = None
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    
    _plain_password: str | None = field(default=None, repr=False)
    
    def set_password(self, password: str, encryption: CredentialEncryption):
        """Encrypt and store password."""
        self.encrypted_password = encryption.encrypt(password)
        self._plain_password = None
    
    def get_decrypted_password(self, encryption: CredentialEncryption | None = None) -> str:
        """Get decrypted password."""
        if self._plain_password:
            return self._plain_password
        
        if self.encrypted_password and encryption:
            return encryption.decrypt(self.encrypted_password)
        
        raise ValueError("No password available")
    
    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "platform": self.platform,
            "username": self.username,
            "encrypted_password": self.encrypted_password,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Account":
        """Create from dictionary."""
        return cls(
            id=data.get("id"),
            platform=data["platform"],
            username=data["username"],
            encrypted_password=data.get("encrypted_password"),
            is_active=data.get("is_active", True),
            created_at=datetime.fromisoformat(data["created_at"]) 
                       if "created_at" in data else datetime.now(),
        )


@dataclass
class ScheduledPost:
    """A scheduled social media post."""
    
    id: int | None
    account_id: int
    content: str
    scheduled_time: datetime
    status: PostStatusEnum = PostStatusEnum.PENDING
    media_paths: list[str] = field(default_factory=list)
    result_message: str | None = None
    post_url: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
    executed_at: datetime | None = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "account_id": self.account_id,
            "content": self.content,
            "scheduled_time": self.scheduled_time.isoformat(),
            "status": self.status.value,
            "media_paths": self.media_paths,
            "result_message": self.result_message,
            "post_url": self.post_url,
            "created_at": self.created_at.isoformat(),
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ScheduledPost":
        """Create from dictionary."""
        return cls(
            id=data.get("id"),
            account_id=data["account_id"],
            content=data["content"],
            scheduled_time=datetime.fromisoformat(data["scheduled_time"]),
            status=PostStatusEnum(data.get("status", "pending")),
            media_paths=data.get("media_paths", []),
            result_message=data.get("result_message"),
            post_url=data.get("post_url"),
            created_at=datetime.fromisoformat(data["created_at"]) 
                       if "created_at" in data else datetime.now(),
            executed_at=datetime.fromisoformat(data["executed_at"]) 
                        if data.get("executed_at") else None,
        )


@dataclass
class LogEntry:
    """Application log entry."""
    
    id: int | None
    level: str
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    extra_data: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "level": self.level,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "extra_data": self.extra_data,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "LogEntry":
        """Create from dictionary."""
        return cls(
            id=data.get("id"),
            level=data["level"],
            message=data["message"],
            timestamp=datetime.fromisoformat(data["timestamp"]) 
                      if "timestamp" in data else datetime.now(),
            extra_data=data.get("extra_data", {}),
        )
