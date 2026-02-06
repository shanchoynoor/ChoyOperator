"""
LLM Client - Claude via OpenRouter API Integration.

Provides content generation capabilities for social media posts.
"""

import json
from dataclasses import dataclass
from enum import Enum
from openai import OpenAI

from src.config import config


class Tone(Enum):
    """Content tone options."""
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    ENGAGING = "engaging"
    HUMOROUS = "humorous"
    INFORMATIVE = "informative"


class Platform(Enum):
    """Supported social media platforms."""
    FACEBOOK = "facebook"
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    YOUTUBE = "youtube"


@dataclass
class GeneratedContent:
    """Structured payload returned from Claude caption generation."""
    title: str
    description: str
    hashtags: list[str]
    final_caption: str
    platform: Platform
    tokens_used: int
    raw: dict


class LLMClient:
    """
    Claude LLM client via OpenRouter API.
    
    Uses OpenAI-compatible interface to communicate with OpenRouter,
    which routes requests to Claude models.
    """
    
    def __init__(self):
        if not config.llm.api_key:
            raise ValueError("OpenRouter API key not configured. Set OPENROUTER_API_KEY.")
        
        self.client = OpenAI(
            base_url=config.llm.base_url,
            api_key=config.llm.api_key,
            default_headers={
                "HTTP-Referer": "https://aioperator.local",
                "X-Title": "AIOperator Desktop"
            }
        )
        self.model = config.llm.model
    
    def generate_post(
        self,
        topic: str,
        platform: Platform,
        tone: Tone = Tone.ENGAGING,
        language: str | None = None,
        audience: str | None = None,
    ) -> GeneratedContent:
        """
        Generate a social media post for the given topic.
        
        Args:
            topic: Subject/topic for the post
            platform: Target social media platform
            tone: Desired tone of the content
            include_hashtags: Whether to include hashtags
            max_length: Optional character limit
            
        Returns:
            GeneratedContent with the generated post
        """
        platform_limits = {
            Platform.TWITTER: 280,
            Platform.FACEBOOK: 500,
            Platform.LINKEDIN: 700,
        }
        
        char_limit = platform_limits.get(platform, 500)
        
        language_clause = f"Write in {language}." if language else ""
        audience_clause = f"Target audience: {audience}." if audience else ""
        
        system_prompt = (
            "You are an expert social media copywriter. "
            "Always respond with STRICT JSON using this schema: "
            '{"title": "string", "description": "string", "hashtags": ["#tag"], '
            '"final_caption": "string"}'
        )
        
        user_prompt = (
            "Generate a Facebook-ready post with the following constraints:\n"
            f"Platform: {platform.value}\n"
            f"Tone: {tone.value}\n"
            f"Media context: {topic}\n"
            f"{language_clause} {audience_clause}\n"
            "Title: <= 80 chars.\n"
            "Description: conversational, 2-3 sentences.\n"
            "Hashtags: 3-5 platform-appropriate tags as an array.\n"
            "final_caption MUST be description + two line breaks + space-separated hashtags."
        )
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=config.llm.max_tokens,
            temperature=config.llm.temperature,
        )
        
        raw_payload = response.choices[0].message.content.strip()
        try:
            parsed = json.loads(raw_payload)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "Claude returned non-JSON content. Prompt: "
                f"{raw_payload}"
            ) from exc
        
        title = parsed.get("title", "").strip()
        description = parsed.get("description", "").strip()
        hashtags = [tag.strip() for tag in parsed.get("hashtags", []) if tag.strip()]
        final_caption = parsed.get("final_caption") or self._compose_caption(description, hashtags)
        
        return GeneratedContent(
            title=title,
            description=description,
            hashtags=hashtags,
            final_caption=final_caption.strip(),
            platform=platform,
            tokens_used=response.usage.total_tokens if response.usage else 0,
            raw=parsed,
        )

    @staticmethod
    def _compose_caption(description: str, hashtags: list[str]) -> str:
        suffix = " ".join(hashtags)
        if description and suffix:
            return f"{description}\n\n{suffix}"
        if description:
            return description
        return suffix
    
    def generate_hashtags(self, content: str, count: int = 5) -> list[str]:
        """
        Generate relevant hashtags for given content.
        
        Args:
            content: The post content to generate hashtags for
            count: Number of hashtags to generate
            
        Returns:
            List of hashtag strings (with # prefix)
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system", 
                    "content": f"Generate {count} relevant hashtags for social media. Return ONLY the hashtags, one per line, each starting with #."
                },
                {"role": "user", "content": content}
            ],
            max_tokens=200,
            temperature=0.5,
        )
        
        result = response.choices[0].message.content.strip()
        hashtags = [
            line.strip() 
            for line in result.split("\n") 
            if line.strip().startswith("#")
        ]
        
        return hashtags[:count]
    
    def generate_caption(self, image_description: str) -> str:
        """
        Generate a caption for an image.
        
        Args:
            image_description: Description of the image
            
        Returns:
            Generated caption string
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system", 
                    "content": "Generate a catchy, engaging caption for a social media image. Keep it under 150 characters. Include 2-3 relevant emojis."
                },
                {"role": "user", "content": f"Image shows: {image_description}"}
            ],
            max_tokens=100,
            temperature=0.8,
        )
        
        return response.choices[0].message.content.strip()
    
    def improve_content(self, draft: str, instructions: str = "") -> str:
        """
        Improve/refine user-written draft content.
        
        Args:
            draft: Original draft content
            instructions: Optional specific improvement instructions
            
        Returns:
            Improved content string
        """
        improvement_prompt = instructions or "Make it more engaging, clear, and impactful while preserving the core message."
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system", 
                    "content": f"You are a content editor. Improve the given text: {improvement_prompt}\nReturn ONLY the improved text, nothing else."
                },
                {"role": "user", "content": draft}
            ],
            max_tokens=config.llm.max_tokens,
            temperature=0.6,
        )
        
        return response.choices[0].message.content.strip()


# Convenience function for quick access
def get_llm_client() -> LLMClient:
    """Get or create the LLM client instance."""
    return LLMClient()
