import pytest
import os
from services.config_service import ConfigService
from services.model_checker import ModelChecker
from services.llm_service import LLMService

@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("GROQ_API_KEY"),
    reason="Requires real GROQ_API_KEY"
)
class TestGroqIntegration:
    """Integration tests with real Groq API"""
    
    def test_groq_token_validation(self):
        """Test real Groq token validation"""
        config = ConfigService()
        token = os.getenv("GROQ_API_KEY")
        
        # Should validate format
        is_valid = config.validate_token_format("groq", token)
        assert is_valid
        
    async def test_groq_model_fetching(self):
        """Test fetching real models from Groq"""
        config = ConfigService()
        checker = ModelChecker(config)
        
        models = await checker.fetch_models("groq")
        
        assert len(models) > 0
        assert any("llama" in m["id"].lower() for m in models)
        
    async def test_groq_llm_generation(self):
        """Test real LLM generation with Groq"""
        config = ConfigService()
        config.save_token("groq", os.getenv("GROQ_API_KEY"))
        # Use a model that is likely to exist. The backlog suggested llama2-70b-4096 but models change.
        # We'll stick to the backlog suggestion but maybe we should fetch first? 
        # For now, let's stick to the backlog code.
        config.save_selected_model("groq", "llama2-70b-4096")
        config.switch_provider("groq")
        
        llm_service = LLMService(config)
        
        response = await llm_service.generate(
            prompt="What is 2+2? Answer in one word.",
            max_tokens=10
        )
        
        assert response
        assert "4" in response.lower() or "four" in response.lower()


@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="Requires real OPENAI_API_KEY"
)
class TestOpenAIIntegration:
    """Integration tests with real OpenAI API"""
    
    def test_openai_token_validation(self):
        """Test real OpenAI token validation"""
        config = ConfigService()
        token = os.getenv("OPENAI_API_KEY")
        
        is_valid = config.validate_token_format("openai", token)
        assert is_valid
        
    async def test_openai_model_fetching(self):
        """Test fetching real models from OpenAI"""
        config = ConfigService()
        checker = ModelChecker(config)
        
        models = await checker.fetch_models("openai")
        
        assert len(models) > 0
        assert any("gpt" in m["id"].lower() for m in models)
        
    async def test_openai_llm_generation(self):
        """Test real LLM generation with OpenAI"""
        config = ConfigService()
        config.save_token("openai", os.getenv("OPENAI_API_KEY"))
        config.save_selected_model("openai", "gpt-3.5-turbo")
        config.switch_provider("openai")
        
        llm_service = LLMService(config)
        
        response = await llm_service.generate(
            prompt="What is 2+2? Answer in one word.",
            max_tokens=10
        )
        
        assert response
        assert "4" in response.lower() or "four" in response.lower()
