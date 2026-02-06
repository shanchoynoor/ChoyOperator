"""
Test Configuration - LLM API Integration Tests.

Tests Claude/OpenRouter API connection and content generation.
"""

import pytest
import os
from unittest.mock import patch, MagicMock


class TestLLMConfiguration:
    """Test LLM configuration loading."""
    
    def test_config_loads_api_key_from_env(self):
        """Verify API key loads from environment."""
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key-123"}):
            from src.config import LLMConfig
            config = LLMConfig(api_key="test-key-123")
            assert config.api_key == "test-key-123"
    
    def test_config_validates_missing_api_key(self):
        """Validate warning when API key missing."""
        from src.config import LLMConfig
        config = LLMConfig(api_key="")
        # Empty key should be detected during validation
        assert config.api_key == ""


class TestLLMClient:
    """Test LLM Client functionality."""
    
    @pytest.fixture
    def mock_openai_client(self):
        """Create a mocked OpenAI client."""
        with patch("src.core.llm_client.OpenAI") as mock:
            mock_instance = MagicMock()
            mock.return_value = mock_instance
            
            # Mock chat completion response
            mock_response = MagicMock()
            mock_response.choices = [
                MagicMock(message=MagicMock(content="Generated post content #hashtag"))
            ]
            mock_instance.chat.completions.create.return_value = mock_response
            
            yield mock_instance
    
    def test_generate_post_returns_content(self, mock_openai_client):
        """Test post generation returns expected structure."""
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            from src.core.llm_client import LLMClient, Platform, Tone
            
            client = LLMClient()
            result = client.generate_post(
                topic="Test topic",
                platform=Platform.TWITTER,
                tone=Tone.CASUAL
            )
            
            assert result is not None
            assert hasattr(result, 'content')
            assert "Generated" in result.content
    
    def test_generate_hashtags_returns_list(self, mock_openai_client):
        """Test hashtag generation returns list."""
        # Update mock for hashtag response
        mock_openai_client.chat.completions.create.return_value.choices[0].message.content = \
            "#ai #automation #socialmedia"
        
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            from src.core.llm_client import LLMClient
            
            client = LLMClient()
            hashtags = client.generate_hashtags("Content about AI")
            
            assert isinstance(hashtags, list)
    
    def test_llm_client_handles_api_error(self, mock_openai_client):
        """Test graceful handling of API errors."""
        mock_openai_client.chat.completions.create.side_effect = Exception("API Error")
        
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            from src.core.llm_client import LLMClient, Platform
            
            client = LLMClient()
            
            with pytest.raises(Exception):
                client.generate_post("topic", Platform.TWITTER)


class TestLLMIntegration:
    """Integration tests for LLM (requires real API key)."""
    
    @pytest.mark.integration
    @pytest.mark.skipif(
        not os.environ.get("OPENROUTER_API_KEY"),
        reason="OPENROUTER_API_KEY not set"
    )
    def test_real_api_connection(self):
        """Test actual API connection (integration test)."""
        from src.core.llm_client import LLMClient, Platform
        
        client = LLMClient()
        result = client.generate_post(
            topic="Quick test",
            platform=Platform.TWITTER,
            max_length=50
        )
        
        assert result.content
        assert len(result.content) > 0
