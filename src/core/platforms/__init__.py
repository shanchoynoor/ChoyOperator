"""Platform-specific automation drivers."""

from src.core.platforms.base import BasePlatform
from src.core.platforms.facebook import FacebookPlatform
from src.core.platforms.twitter import TwitterPlatform
from src.core.platforms.linkedin import LinkedInPlatform
from src.core.platforms.youtube import YouTubePlatform

__all__ = [
    "BasePlatform",
    "FacebookPlatform", 
    "TwitterPlatform",
    "LinkedInPlatform",
    "YouTubePlatform",
]
