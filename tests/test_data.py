"""
Test Data Layer - Database and encryption tests.
"""

import pytest
from pathlib import Path
from datetime import datetime
import tempfile


class TestDatabase:
    """Test database operations."""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)
        
        from src.data.database import Database
        db = Database(db_path)
        yield db
        
        # Cleanup
        db_path.unlink(missing_ok=True)
    
    def test_database_creates_tables(self, temp_db):
        """Test that database creates required tables."""
        # Tables should be created on init
        import sqlite3
        conn = sqlite3.connect(str(temp_db.db_path))
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        assert "accounts" in tables
        assert "scheduled_posts" in tables
        assert "logs" in tables
    
    def test_add_and_get_account(self, temp_db):
        """Test adding and retrieving an account."""
        from src.data.models import Account
        
        account = Account(
            id=None,
            platform="twitter",
            username="testuser",
        )
        
        account_id = temp_db.add_account(account)
        assert account_id is not None
        assert account_id > 0
        
        retrieved = temp_db.get_account(account_id)
        assert retrieved is not None
        assert retrieved.username == "testuser"
        assert retrieved.platform == "twitter"
    
    def test_get_all_accounts(self, temp_db):
        """Test getting all accounts."""
        from src.data.models import Account
        
        for i in range(3):
            account = Account(
                id=None,
                platform="facebook",
                username=f"user{i}",
            )
            temp_db.add_account(account)
        
        accounts = temp_db.get_all_accounts()
        assert len(accounts) == 3
    
    def test_delete_account(self, temp_db):
        """Test account deletion."""
        from src.data.models import Account
        
        account = Account(
            id=None,
            platform="linkedin",
            username="toDelete",
        )
        account_id = temp_db.add_account(account)
        
        temp_db.delete_account(account_id)
        
        retrieved = temp_db.get_account(account_id)
        assert retrieved is None
    
    def test_add_scheduled_post(self, temp_db):
        """Test adding a scheduled post."""
        from src.data.models import Account, ScheduledPost
        
        # First add an account
        account = Account(id=None, platform="twitter", username="test")
        account_id = temp_db.add_account(account)
        
        # Add scheduled post
        post = ScheduledPost(
            id=None,
            account_id=account_id,
            content="Test post content",
            scheduled_time=datetime.now(),
        )
        post_id = temp_db.add_scheduled_post(post)
        
        assert post_id is not None
        assert post_id > 0


class TestEncryption:
    """Test credential encryption."""
    
    def test_encrypt_decrypt_roundtrip(self):
        """Test that encrypt then decrypt returns original."""
        from src.data.encryption import CredentialEncryption
        
        enc = CredentialEncryption()
        original = "my_secret_password_123!"
        
        encrypted = enc.encrypt(original)
        decrypted = enc.decrypt(encrypted)
        
        assert decrypted == original
        assert encrypted != original
    
    def test_encrypted_is_different_from_original(self):
        """Verify encrypted value differs from original."""
        from src.data.encryption import CredentialEncryption
        
        enc = CredentialEncryption()
        original = "password"
        encrypted = enc.encrypt(original)
        
        assert encrypted != original
        assert len(encrypted) > len(original)
    
    def test_encrypt_dict_credentials(self):
        """Test encrypting dictionary of credentials."""
        from src.data.encryption import CredentialEncryption
        
        enc = CredentialEncryption()
        creds = {
            "username": "testuser",
            "password": "testpass123",
        }
        
        encrypted = enc.encrypt_dict(creds)
        decrypted = enc.decrypt_dict(encrypted)
        
        assert decrypted["username"] == "testuser"
        assert decrypted["password"] == "testpass123"


class TestModels:
    """Test data models."""
    
    def test_account_model_creation(self):
        """Test Account model creation."""
        from src.data.models import Account
        
        account = Account(
            id=1,
            platform="twitter",
            username="testuser",
        )
        
        assert account.id == 1
        assert account.platform == "twitter"
        assert account.username == "testuser"
    
    def test_scheduled_post_model_creation(self):
        """Test ScheduledPost model creation."""
        from src.data.models import ScheduledPost, PostStatusEnum
        
        post = ScheduledPost(
            id=1,
            account_id=1,
            content="Test content",
            scheduled_time=datetime.now(),
        )
        
        assert post.status == PostStatusEnum.PENDING
        assert post.content == "Test content"
    
    def test_account_to_dict(self):
        """Test Account serialization."""
        from src.data.models import Account
        
        account = Account(
            id=1,
            platform="facebook",
            username="user",
        )
        
        data = account.to_dict()
        assert data["id"] == 1
        assert data["platform"] == "facebook"
