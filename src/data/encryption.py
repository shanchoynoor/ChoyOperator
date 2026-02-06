"""
Credential Encryption - Secure credential storage using Fernet.

Uses Fernet symmetric encryption (AES-128-CBC with HMAC).
"""

import os
import base64
from pathlib import Path

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from src.config import config, PROJECT_ROOT


class CredentialEncryption:
    """
    Handles encryption and decryption of sensitive credentials.
    
    Uses Fernet symmetric encryption with a key derived from
    either an environment variable or a generated key file.
    """
    
    KEY_FILE = PROJECT_ROOT / "data" / ".encryption_key"
    
    def __init__(self, key: bytes | None = None):
        """
        Initialize encryption with a key.
        
        Args:
            key: Optional encryption key. If not provided, will use
                 environment variable or generate one.
        """
        if key:
            self.fernet = Fernet(key)
        else:
            self.fernet = Fernet(self._get_or_create_key())
    
    def _get_or_create_key(self) -> bytes:
        """Get existing key or create a new one."""
        # First check environment variable
        env_key = config.encryption_key
        if env_key:
            return base64.urlsafe_b64decode(env_key)
        
        # Then check key file
        if self.KEY_FILE.exists():
            return self.KEY_FILE.read_bytes()
        
        # Generate new key
        key = Fernet.generate_key()
        
        # Save to file
        self.KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.KEY_FILE.write_bytes(key)
        
        # Restrict file permissions (Windows-compatible)
        try:
            import stat
            os.chmod(self.KEY_FILE, stat.S_IRUSR | stat.S_IWUSR)
        except Exception:
            pass  # Best effort on Windows
        
        return key
    
    @classmethod
    def derive_key_from_password(cls, password: str, salt: bytes | None = None) -> tuple[bytes, bytes]:
        """
        Derive an encryption key from a password.
        
        Args:
            password: User password
            salt: Optional salt. Generated if not provided.
            
        Returns:
            Tuple of (key, salt)
        """
        if salt is None:
            salt = os.urandom(16)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key, salt
    
    def encrypt(self, plaintext: str) -> bytes:
        """
        Encrypt a string.
        
        Args:
            plaintext: String to encrypt
            
        Returns:
            Encrypted bytes
        """
        return self.fernet.encrypt(plaintext.encode())
    
    def decrypt(self, ciphertext: bytes) -> str:
        """
        Decrypt bytes to string.
        
        Args:
            ciphertext: Encrypted bytes
            
        Returns:
            Decrypted string
        """
        return self.fernet.decrypt(ciphertext).decode()
    
    def encrypt_dict(self, data: dict) -> bytes:
        """Encrypt a dictionary (serialized as JSON)."""
        import json
        return self.encrypt(json.dumps(data))
    
    def decrypt_dict(self, ciphertext: bytes) -> dict:
        """Decrypt to a dictionary."""
        import json
        return json.loads(self.decrypt(ciphertext))


# Global encryption instance
_encryption: CredentialEncryption | None = None


def get_encryption() -> CredentialEncryption:
    """Get or create the encryption instance."""
    global _encryption
    if _encryption is None:
        _encryption = CredentialEncryption()
    return _encryption
