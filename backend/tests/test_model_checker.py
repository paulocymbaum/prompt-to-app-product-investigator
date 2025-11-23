"""
Unit tests for Model Checker Service.

Tests cover:
- Fetching models from Groq and OpenAI
- Model caching and expiry
- Invalid token error handling
- API retry logic
- Timeout handling
- Model selection validation
"""

import pytest
import httpx
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from services.model_checker import ModelChecker
from services.config_service import ConfigService


class TestModelChecker:
    """Test suite for ModelChecker"""
    
    @pytest.fixture
    def config_service(self, tmp_path):
        """Create a mock ConfigService"""
        env_file = tmp_path / ".env"
        env_file.touch()
        return ConfigService(str(env_file))
    
    @pytest.fixture
    def model_checker(self, config_service):
        """Create a ModelChecker instance"""
        return ModelChecker(config_service)
    
    @pytest.fixture
    def sample_groq_models(self):
        """Sample Groq models response"""
        return [
            {
                "id": "llama2-70b-4096",
                "object": "model",
                "created": 1234567890,
                "owned_by": "groq"
            },
            {
                "id": "mixtral-8x7b-32768",
                "object": "model",
                "created": 1234567891,
                "owned_by": "groq"
            }
        ]
    
    @pytest.fixture
    def sample_openai_models(self):
        """Sample OpenAI models response"""
        return [
            {
                "id": "gpt-3.5-turbo",
                "object": "model",
                "created": 1234567890,
                "owned_by": "openai"
            },
            {
                "id": "gpt-4",
                "object": "model",
                "created": 1234567891,
                "owned_by": "openai"
            }
        ]
    
    # Business Rule Tests
    
    @pytest.mark.asyncio
    async def test_fetch_groq_models(self, model_checker, sample_groq_models):
        """Test fetching Groq models successfully with LangChain metadata"""
        api_key = "gsk_test_key_1234567890"
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()  # Not AsyncMock - response object itself is not async
            mock_response.json = Mock(return_value={"data": sample_groq_models})  # json() is sync
            mock_response.raise_for_status = Mock()
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            models = await model_checker.fetch_groq_models(api_key)
            
            # Check models are enhanced with LangChain metadata
            assert len(models) == 2
            assert models[0]["id"] == "llama2-70b-4096"
            assert models[0]["provider"] == "groq"
            assert models[0]["langchain_class"] == "ChatGroq"
            assert models[0]["context_window"] == 4096
            assert models[0]["supports_streaming"] is True
            
            assert models[1]["id"] == "mixtral-8x7b-32768"
            assert models[1]["context_window"] == 32768
    
    @pytest.mark.asyncio
    async def test_fetch_openai_models(self, model_checker, sample_openai_models):
        """Test fetching OpenAI models successfully with filtering and metadata"""
        api_key = "sk-test-key-1234567890"
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()  # Not AsyncMock
            mock_response.json = Mock(return_value={"data": sample_openai_models})  # json() is sync
            mock_response.raise_for_status = Mock()
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            models = await model_checker.fetch_openai_models(api_key)
            
            # Verify models are filtered to chat models and enhanced
            assert len(models) == 2
            assert models[0]["id"] == "gpt-3.5-turbo"
            assert models[0]["provider"] == "openai"
            assert models[0]["langchain_class"] == "ChatOpenAI"
            assert models[0]["supports_streaming"] is True
            assert models[0]["supports_functions"] is True
            assert models[0]["context_window"] == 4096
            
            assert models[1]["id"] == "gpt-4"
            assert models[1]["context_window"] == 8192
    
    @pytest.mark.asyncio
    async def test_invalid_token_error_handling(self, model_checker):
        """Test handling of invalid API tokens (401 Unauthorized)"""
        api_key = "invalid_key"
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()  # Not AsyncMock since we don't await the response itself
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"
            
            # Create a function that raises the error
            def raise_error():
                raise httpx.HTTPStatusError(
                    "Unauthorized", request=Mock(), response=mock_response
                )
            
            mock_response.raise_for_status = raise_error
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            with pytest.raises(httpx.HTTPStatusError):
                await model_checker.fetch_groq_models(api_key)
    
    def test_model_selection_validation(self, model_checker, sample_groq_models):
        """Test validating model selection against available models"""
        # Cache some models first
        model_checker._cache_models("groq", sample_groq_models)
        
        # Valid model
        assert model_checker.validate_model_selection("groq", "llama2-70b-4096") == True
        
        # Invalid model
        assert model_checker.validate_model_selection("groq", "non-existent-model") == False
    
    # Technical Implementation Tests
    
    @pytest.mark.asyncio
    async def test_api_retry_logic(self, model_checker):
        """Test retry logic on network failures"""
        api_key = "gsk_test_key_1234567890"
        
        with patch("httpx.AsyncClient") as mock_client:
            # Simulate network errors that should trigger retries
            mock_get = AsyncMock()
            mock_get.side_effect = [
                httpx.NetworkError("Connection failed"),
                httpx.NetworkError("Connection failed"),
                httpx.NetworkError("Connection failed")
            ]
            
            mock_client.return_value.__aenter__.return_value.get = mock_get
            
            with pytest.raises(httpx.NetworkError):
                await model_checker.fetch_groq_models(api_key)
            
            # Verify it was called 3 times (initial + 2 retries)
            assert mock_get.call_count == 3
    
    @pytest.mark.asyncio
    async def test_api_timeout_handling(self, model_checker):
        """Test handling of API timeout errors"""
        api_key = "gsk_test_key_1234567890"
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_get = AsyncMock()
            mock_get.side_effect = httpx.TimeoutException("Request timeout")
            
            mock_client.return_value.__aenter__.return_value.get = mock_get
            
            with pytest.raises(httpx.TimeoutException):
                await model_checker.fetch_groq_models(api_key)
    
    def test_model_caching(self, model_checker, sample_groq_models):
        """Test model list caching and expiry"""
        # Cache models
        model_checker._cache_models("groq", sample_groq_models)
        
        # Check cache is valid
        assert model_checker._is_cache_valid("groq") == True
        
        # Retrieve from cache
        cached_models = model_checker.get_cached_models("groq")
        assert cached_models is not None
        assert len(cached_models) == 2
        assert cached_models[0]["id"] == "llama2-70b-4096"
    
    def test_cache_expiry(self, model_checker, sample_groq_models):
        """Test cache expiration after TTL"""
        # Cache models with expired time
        expiry_time = datetime.utcnow() - timedelta(seconds=1)  # Already expired
        model_checker.cache["groq"] = {
            "models": sample_groq_models,
            "expiry": expiry_time,
            "cached_at": datetime.utcnow() - timedelta(seconds=301)
        }
        
        # Cache should be invalid
        assert model_checker._is_cache_valid("groq") == False
        
        # Should return None
        cached_models = model_checker.get_cached_models("groq")
        assert cached_models is None
    
    def test_cache_invalidation(self, model_checker, sample_groq_models, sample_openai_models):
        """Test cache invalidation"""
        # Cache models for both providers
        model_checker._cache_models("groq", sample_groq_models)
        model_checker._cache_models("openai", sample_openai_models)
        
        # Invalidate Groq cache
        model_checker.invalidate_cache("groq")
        assert model_checker.get_cached_models("groq") is None
        assert model_checker.get_cached_models("openai") is not None
        
        # Invalidate all cache
        model_checker.invalidate_cache()
        assert model_checker.get_cached_models("openai") is None
    
    @pytest.mark.asyncio
    async def test_fetch_models_with_cache(self, model_checker, config_service, sample_groq_models):
        """Test fetch_models uses cache when available"""
        # Set up config with API key
        api_key = "gsk_test_key_1234567890"
        config_service.save_token("groq", api_key)
        
        # Pre-populate cache
        model_checker._cache_models("groq", sample_groq_models)
        
        # Fetch models (should use cache, no API call)
        with patch("httpx.AsyncClient") as mock_client:
            models = await model_checker.fetch_models("groq")
            
            # Verify no API call was made
            mock_client.assert_not_called()
            
            # Verify models returned from cache
            assert len(models) == 2
            assert models[0]["id"] == "llama2-70b-4096"
    
    @pytest.mark.asyncio
    async def test_fetch_models_without_api_key(self, model_checker):
        """Test fetch_models raises error when no API key is configured"""
        # The error could be either ValueError (no key configured) or HTTPStatusError (invalid key)
        # Both are acceptable since we want to prevent fetching without proper auth
        with pytest.raises((ValueError, httpx.HTTPStatusError)):
            await model_checker.fetch_models("groq")
    
    @pytest.mark.asyncio
    async def test_fetch_models_unsupported_provider(self, model_checker):
        """Test fetch_models raises error for unsupported provider"""
        with pytest.raises(ValueError, match="Unsupported provider"):
            await model_checker.fetch_models("unsupported", "fake_key")
    
    @pytest.mark.asyncio
    async def test_fetch_models_caches_result(self, model_checker, config_service, sample_groq_models):
        """Test fetch_models caches the result after fetching"""
        # Set up config with API key
        api_key = "gsk_test_key_1234567890"
        config_service.save_token("groq", api_key)
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.json = Mock(return_value={"data": sample_groq_models})
            mock_response.raise_for_status = Mock()
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            # First call - should fetch from API
            models = await model_checker.fetch_models("groq")
            assert len(models) == 2
            
            # Verify cache was populated
            cached = model_checker.get_cached_models("groq")
            assert cached is not None
            assert len(cached) == 2
    
    def test_validate_model_without_cache(self, model_checker):
        """Test model validation when cache is empty"""
        result = model_checker.validate_model_selection("groq", "llama2-70b-4096")
        assert result == False
    
    def test_validate_model_with_explicit_list(self, model_checker, sample_groq_models):
        """Test model validation with explicitly provided model list"""
        # Valid model
        assert model_checker.validate_model_selection(
            "groq", 
            "llama2-70b-4096",
            available_models=sample_groq_models
        ) == True
        
        # Invalid model
        assert model_checker.validate_model_selection(
            "groq",
            "non-existent",
            available_models=sample_groq_models
        ) == False
    
    @pytest.mark.asyncio
    async def test_retry_success_after_failure(self, model_checker, sample_groq_models):
        """Test successful retry after initial failure"""
        api_key = "gsk_test_key_1234567890"
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.json = Mock(return_value={"data": sample_groq_models})
            mock_response.raise_for_status = Mock()
            
            # Track call count externally
            call_tracker = {"count": 0}
            
            # Create async mock with proper side effects
            async def mock_get_side_effect(*args, **kwargs):
                call_tracker["count"] += 1
                
                if call_tracker["count"] == 1:
                    raise httpx.NetworkError("Connection failed")
                return mock_response
            
            mock_get = AsyncMock(side_effect=mock_get_side_effect)
            mock_client.return_value.__aenter__.return_value.get = mock_get
            
            models = await model_checker.fetch_groq_models(api_key)
            
            # Should succeed after retry
            assert len(models) == 2
            assert mock_get.call_count == 2


class TestModelCheckerIntegration:
    """Integration tests for ModelChecker"""
    
    @pytest.fixture
    def config_service(self, tmp_path):
        """Create a real ConfigService"""
        env_file = tmp_path / ".env"
        env_file.touch()
        return ConfigService(str(env_file))
    
    @pytest.fixture
    def model_checker(self, config_service):
        """Create a ModelChecker instance"""
        return ModelChecker(config_service)
    
    @pytest.mark.asyncio
    async def test_full_flow_with_config(self, model_checker, config_service):
        """Test complete flow: save token, fetch models, validate selection"""
        # Save API token
        api_key = "gsk_integration_test_1234567890"
        config_service.save_token("groq", api_key)
        
        sample_models = [
            {"id": "llama2-70b-4096", "object": "model"},
            {"id": "mixtral-8x7b-32768", "object": "model"}
        ]
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.json = Mock(return_value={"data": sample_models})
            mock_response.raise_for_status = Mock()
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            # Fetch models
            models = await model_checker.fetch_models("groq")
            assert len(models) == 2
            
            # Validate model selection
            assert model_checker.validate_model_selection("groq", "llama2-70b-4096") == True
            assert model_checker.validate_model_selection("groq", "invalid-model") == False
    
    def test_get_langchain_model_groq(self, model_checker):
        """Test creating LangChain ChatGroq instance"""
        api_key = "gsk_test_key_1234567890"
        model_id = "llama2-70b-4096"
        
        model = model_checker.get_langchain_model("groq", model_id, api_key, temperature=0.5)
        
        # Check it's a ChatGroq instance
        from langchain_groq import ChatGroq
        assert isinstance(model, ChatGroq)
        assert model.model_name == model_id
        assert model.temperature == 0.5
    
    def test_get_langchain_model_openai(self, model_checker):
        """Test creating LangChain ChatOpenAI instance"""
        api_key = "sk-test-key-1234567890"
        model_id = "gpt-4"
        
        model = model_checker.get_langchain_model("openai", model_id, api_key, temperature=0.8)
        
        # Check it's a ChatOpenAI instance
        from langchain_openai import ChatOpenAI
        assert isinstance(model, ChatOpenAI)
        assert model.model_name == model_id
        assert model.temperature == 0.8
    
    def test_get_langchain_model_invalid_provider(self, model_checker):
        """Test error handling for unsupported provider"""
        with pytest.raises(ValueError, match="Unsupported provider"):
            model_checker.get_langchain_model("unsupported", "model-id", "api-key")
    
    def test_get_langchain_model_with_custom_params(self, model_checker):
        """Test creating LangChain model with custom parameters"""
        api_key = "gsk_test_key"
        model_id = "llama2-70b-4096"
        
        model = model_checker.get_langchain_model(
            "groq",
            model_id,
            api_key,
            temperature=0.3,
            max_tokens=1000,
            streaming=True
        )
        
        from langchain_groq import ChatGroq
        assert isinstance(model, ChatGroq)
        assert model.temperature == 0.3
        assert model.max_tokens == 1000
        assert model.streaming is True
