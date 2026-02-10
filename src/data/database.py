"""
Database - SQLite database operations.

Handles CRUD operations for accounts, posts, and logs.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from src.config import config, PROJECT_ROOT
from src.data.models import Account, ScheduledPost, LogEntry, PostStatusEnum
from src.data.encryption import get_encryption


class Database:
    """
    SQLite database manager.
    
    Handles all database operations for accounts, scheduled posts, and logs.
    """
    
    def __init__(self, db_path: Path | None = None):
        """
        Initialize database.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path or config.database.path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._connection: sqlite3.Connection | None = None
        self._init_database()
    
    @property
    def connection(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self._connection is None:
            self._connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False
            )
            self._connection.row_factory = sqlite3.Row
        return self._connection
    
    def _init_database(self):
        """Initialize database tables."""
        cursor = self.connection.cursor()
        
        # Accounts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                username TEXT NOT NULL,
                encrypted_password BLOB,
                is_active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                UNIQUE(platform, username)
            )
        """)
        
        # Scheduled posts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                scheduled_time TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                media_paths TEXT,
                result_message TEXT,
                post_url TEXT,
                created_at TEXT NOT NULL,
                executed_at TEXT,
                FOREIGN KEY (account_id) REFERENCES accounts(id)
            )
        """)
        
        # Logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                extra_data TEXT
            )
        """)
        
        self.connection.commit()
    
    # ==================== Account Operations ====================
    
    def add_account(self, account: Account) -> int:
        """
        Add a new account.
        
        Args:
            account: Account to add
            
        Returns:
            ID of the new account
        """
        cursor = self.connection.cursor()
        cursor.execute(
            """
            INSERT INTO accounts (platform, username, encrypted_password, is_active, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                account.platform,
                account.username,
                account.encrypted_password,
                1 if account.is_active else 0,
                account.created_at.isoformat(),
            )
        )
        self.connection.commit()
        return cursor.lastrowid
    
    def get_account(self, account_id: int) -> Account | None:
        """Get account by ID."""
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM accounts WHERE id = ?", (account_id,))
        row = cursor.fetchone()
        
        if row:
            return self._row_to_account(row)
        return None
    
    def get_accounts_by_platform(self, platform: str) -> list[Account]:
        """Get all accounts for a platform."""
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT * FROM accounts WHERE platform = ? AND is_active = 1",
            (platform,)
        )
        return [self._row_to_account(row) for row in cursor.fetchall()]
    
    def get_all_accounts(self, active_only: bool = True) -> list[Account]:
        """Get all accounts."""
        cursor = self.connection.cursor()
        if active_only:
            cursor.execute("SELECT * FROM accounts WHERE is_active = 1")
        else:
            cursor.execute("SELECT * FROM accounts")
        return [self._row_to_account(row) for row in cursor.fetchall()]
    
    def update_account(self, account: Account) -> bool:
        """Update an existing account."""
        if account.id is None:
            return False
        
        cursor = self.connection.cursor()
        cursor.execute(
            """
            UPDATE accounts 
            SET platform = ?, username = ?, encrypted_password = ?, is_active = ?
            WHERE id = ?
            """,
            (
                account.platform,
                account.username,
                account.encrypted_password,
                1 if account.is_active else 0,
                account.id,
            )
        )
        self.connection.commit()
        return cursor.rowcount > 0
    
    def delete_account(self, account_id: int) -> bool:
        """Delete an account (soft delete by setting inactive)."""
        cursor = self.connection.cursor()
        cursor.execute(
            "UPDATE accounts SET is_active = 0 WHERE id = ?",
            (account_id,)
        )
        self.connection.commit()
        return cursor.rowcount > 0
    
    def _row_to_account(self, row: sqlite3.Row) -> Account:
        """Convert database row to Account."""
        return Account(
            id=row["id"],
            platform=row["platform"],
            username=row["username"],
            encrypted_password=row["encrypted_password"],
            is_active=bool(row["is_active"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )
    
    # ==================== Scheduled Post Operations ====================
    
    def add_scheduled_post(self, post: ScheduledPost) -> int:
        """Add a new scheduled post."""
        cursor = self.connection.cursor()
        cursor.execute(
            """
            INSERT INTO scheduled_posts 
            (account_id, content, scheduled_time, status, media_paths, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                post.account_id,
                post.content,
                post.scheduled_time.isoformat(),
                post.status.value,
                json.dumps(post.media_paths),
                post.created_at.isoformat(),
            )
        )
        self.connection.commit()
        return cursor.lastrowid
    
    def get_scheduled_post(self, post_id: int) -> ScheduledPost | None:
        """Get scheduled post by ID."""
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM scheduled_posts WHERE id = ?", (post_id,))
        row = cursor.fetchone()
        
        if row:
            return self._row_to_post(row)
        return None
    
    def get_pending_posts(self) -> list[ScheduledPost]:
        """Get all pending posts."""
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT * FROM scheduled_posts WHERE status = 'pending' ORDER BY scheduled_time"
        )
        return [self._row_to_post(row) for row in cursor.fetchall()]
    
    def get_posts_by_account(self, account_id: int) -> list[ScheduledPost]:
        """Get all posts for an account."""
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT * FROM scheduled_posts WHERE account_id = ? ORDER BY scheduled_time DESC",
            (account_id,)
        )
        return [self._row_to_post(row) for row in cursor.fetchall()]
    
    def update_post_status(
        self, 
        post_id: int, 
        status: PostStatusEnum,
        result_message: str | None = None,
        post_url: str | None = None
    ):
        """Update post status after execution."""
        cursor = self.connection.cursor()
        cursor.execute(
            """
            UPDATE scheduled_posts 
            SET status = ?, result_message = ?, post_url = ?, executed_at = ?
            WHERE id = ?
            """,
            (
                status.value,
                result_message,
                post_url,
                datetime.now().isoformat(),
                post_id,
            )
        )
        self.connection.commit()
    
    def update_scheduled_post(self, post: ScheduledPost) -> bool:
        """Update a scheduled post content and time."""
        if post.id is None:
            return False
        
        cursor = self.connection.cursor()
        cursor.execute(
            """
            UPDATE scheduled_posts 
            SET content = ?, scheduled_time = ?, media_paths = ?
            WHERE id = ?
            """,
            (
                post.content,
                post.scheduled_time.isoformat(),
                json.dumps(post.media_paths) if post.media_paths else "[]",
                post.id,
            )
        )
        self.connection.commit()
        return cursor.rowcount > 0
    
    def delete_scheduled_post(self, post_id: int) -> bool:
        """Delete a scheduled post."""
        cursor = self.connection.cursor()
        cursor.execute("DELETE FROM scheduled_posts WHERE id = ?", (post_id,))
        self.connection.commit()
        return cursor.rowcount > 0
    
    def _row_to_post(self, row: sqlite3.Row) -> ScheduledPost:
        """Convert database row to ScheduledPost."""
        return ScheduledPost(
            id=row["id"],
            account_id=row["account_id"],
            content=row["content"],
            scheduled_time=datetime.fromisoformat(row["scheduled_time"]),
            status=PostStatusEnum(row["status"]),
            media_paths=json.loads(row["media_paths"] or "[]"),
            result_message=row["result_message"],
            post_url=row["post_url"],
            created_at=datetime.fromisoformat(row["created_at"]),
            executed_at=datetime.fromisoformat(row["executed_at"]) 
                        if row["executed_at"] else None,
        )
    
    # ==================== Log Operations ====================
    
    def add_log(self, entry: LogEntry) -> int:
        """Add a log entry."""
        cursor = self.connection.cursor()
        cursor.execute(
            """
            INSERT INTO logs (level, message, timestamp, extra_data)
            VALUES (?, ?, ?, ?)
            """,
            (
                entry.level,
                entry.message,
                entry.timestamp.isoformat(),
                json.dumps(entry.extra_data),
            )
        )
        self.connection.commit()
        return cursor.lastrowid
    
    def get_recent_logs(self, limit: int = 100) -> list[LogEntry]:
        """Get recent log entries."""
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT * FROM logs ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        )
        return [self._row_to_log(row) for row in cursor.fetchall()]
    
    def clear_old_logs(self, days: int = 30):
        """Delete logs older than specified days."""
        from datetime import timedelta
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor = self.connection.cursor()
        cursor.execute("DELETE FROM logs WHERE timestamp < ?", (cutoff,))
        self.connection.commit()
    
    def _row_to_log(self, row: sqlite3.Row) -> LogEntry:
        """Convert database row to LogEntry."""
        return LogEntry(
            id=row["id"],
            level=row["level"],
            message=row["message"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            extra_data=json.loads(row["extra_data"] or "{}"),
        )
    
    def close(self):
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None


# Singleton database instance
_database: Database | None = None


def get_database() -> Database:
    """Get or create the database instance."""
    global _database
    if _database is None:
        _database = Database()
    return _database
