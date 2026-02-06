"""
Configuration management for AIOperator.
Loads settings from environment variables and .env file.
"""

import os
from pathlib import Path
from dataclasses import dataclass
from dotenv import load_dotenv

# Load .env file from project root
PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")


@dataclass
class LLMConfig:
    """LLM (OpenRouter) configuration."""
    api_key: str
    model: str
    base_url: str = "https://openrouter.ai/api/v1"
    max_tokens: int = 2048
    temperature: float = 0.7


@dataclass
class BrowserConfig:
    """Browser automation configuration."""
    browser_type: str  # chrome, firefox
    headless: bool
    implicit_wait: int = 10
    page_load_timeout: int = 30


@dataclass
class DatabaseConfig:
    """Database configuration."""
    path: Path


@dataclass
class LogConfig:
    """Logging configuration."""
    level: str
    file_path: Path


class Config:
    """Application configuration singleton."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Load configuration from environment."""
        self.llm = LLMConfig(
            api_key=os.getenv("OPENROUTER_API_KEY", ""),
            model=os.getenv("LLM_MODEL", "anthropic/claude-3.5-sonnet"),
        )
        
        self.browser = BrowserConfig(
            browser_type=os.getenv("BROWSER_TYPE", "chrome"),
            headless=os.getenv("BROWSER_HEADLESS", "false").lower() == "true",
        )
        
        db_path = os.getenv("DATABASE_PATH", "./data/aioperator.db")
        self.database = DatabaseConfig(
            path=Path(db_path) if not Path(db_path).is_absolute() 
                 else PROJECT_ROOT / db_path
        )
        
        log_path = os.getenv("LOG_FILE", "./logs/aioperator.log")
        self.logging = LogConfig(
            level=os.getenv("LOG_LEVEL", "INFO"),
            file_path=Path(log_path) if not Path(log_path).is_absolute() 
                      else PROJECT_ROOT / log_path
        )
        
        self.encryption_key = os.getenv("ENCRYPTION_KEY")
    
    def validate(self) -> list[str]:
        """Validate configuration. Returns list of errors."""
        errors = []
        
        if not self.llm.api_key:
            errors.append("OPENROUTER_API_KEY is not set")
        
        if self.browser.browser_type not in ("chrome", "firefox", "brave", "edge"):
            errors.append(f"Invalid BROWSER_TYPE: {self.browser.browser_type}")
        
        return errors


# Global config instance
config = Config()
