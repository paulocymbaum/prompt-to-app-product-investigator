"""
Unit tests for LLM Service.

Tests cover:
- Provider initialization
- Response generation
- Streaming responses
- Token counting
- Error handling and retries
- Parameter overrides
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from services.llm_service import LLMService, get_llm_service
from services.config_service import ConfigService
from services.model_checker import ModelChecker


@pytest.fixture
def mock_config_service():
    """Create a mock ConfigService"""
    mock = Mock(spec=ConfigService)
    mock.get_active_provider.return_value = "groq"
    mock.get_selected_model.return_value = "llama2-70b-4096"
    mock.get_token.return_value = "gsk_" + "a" * 40
    return mock


@pytest.fixture
def mock_model_checker():
    """Create a mock ModelChecker"""
    mock = Mock(spec=ModelChecker)
    
    # Create a mock LangChain model
    mock_llm = MagicMock()
    mock_llm.temperature = 0.7
    mock_llm.max_tokens = 2000
    mock_llm.streaming = False
    mock_llm.get_num_tokens.return_value = 10
    
    # Mock agenerate response
    mock_generation = Mock()
    mock_generation.text = "This is a test response from the LLM."
    mock_response = Mock()
    mock_response.generations = [[mock_generation]]
    mock_llm.agenerate = AsyncMock(return_value=mock_response)
    
    # Mock astream response
    async def mock_astream(messages):
        chunks = ["This ", "is ", "a ", "test ", "response."]
        for chunk in chunks:
            mock_chunk = Mock()
            mock_chunk.content = chunk
            yield mock_chunk
    
    mock_llm.astream = mock_astream
    
    mock.get_langchain_model.return_value = mock_llm
    return mock


@pytest.fixture
def llm_service(mock_config_service, mock_model_checker):
    """Create LLMService instance with mocked dependencies"""
    return LLMService(mock_config_service, mock_model_checker)


class TestLLMServiceInitialization:
    """Test suite for LLM service initialization"""
    
    def test_service_creation(self, llm_service):
        """Test that LLMService can be created"""
        assert llm_service.llm is None
        assert llm_service.provider is None
        assert llm_service.model_id is None
        assert llm_service.temperature == 0.7
        assert llm_service.max_tokens == 2000
    
    def test_initialize_provider_with_defaults(self, llm_service, mock_config_service, mock_model_checker):
        """Test initializing provider with default config"""
        llm_service.initialize_provider()
        
        # Verify config service was called
        mock_config_service.get_active_provider.assert_called_once()
        mock_config_service.get_selected_model.assert_called_once()
        mock_config_service.get_token.assert_called_with("groq")
        
        # Verify model checker was called
        mock_model_checker.get_langchain_model.assert_called_once()
        call_args = mock_model_checker.get_langchain_model.call_args
        assert call_args.kwargs["provider"] == "groq"
        assert call_args.kwargs["model_id"] == "llama2-70b-4096"
        assert call_args.kwargs["temperature"] == 0.7
        assert call_args.kwargs["max_tokens"] == 2000
        assert call_args.kwargs["streaming"] is False
        
        # Verify service state
        assert llm_service.llm is not None
        assert llm_service.provider == "groq"
        assert llm_service.model_id == "llama2-70b-4096"
    
    def test_initialize_provider_with_explicit_params(self, llm_service, mock_model_checker):
        """Test initializing provider with explicit parameters"""
        llm_service.initialize_provider(
            provider="openai",
            model_id="gpt-4",
            temperature=0.3,
            max_tokens=1000,
            streaming=True
        )
        
        # Verify model checker was called with correct params
        call_args = mock_model_checker.get_langchain_model.call_args
        assert call_args.kwargs["provider"] == "openai"
        assert call_args.kwargs["model_id"] == "gpt-4"
        assert call_args.kwargs["temperature"] == 0.3
        assert call_args.kwargs["max_tokens"] == 1000
        assert call_args.kwargs["streaming"] is True
    
    def test_initialize_provider_no_active_provider(self, llm_service, mock_config_service):
        """Test error when no active provider is configured"""
        mock_config_service.get_active_provider.return_value = None
        
        with pytest.raises(RuntimeError, match="No active provider configured"):
            llm_service.initialize_provider()
    
    def test_initialize_provider_no_selected_model(self, llm_service, mock_config_service):
        """Test error when no model is selected"""
        mock_config_service.get_selected_model.return_value = None
        
        with pytest.raises(RuntimeError, match="No model selected"):
            llm_service.initialize_provider()
    
    def test_initialize_provider_no_api_key(self, llm_service, mock_config_service):
        """Test error when no API key is configured"""
        mock_config_service.get_token.return_value = None
        
        with pytest.raises(RuntimeError, match="No API key configured"):
            llm_service.initialize_provider()


class TestLLMServiceResponseGeneration:
    """Test suite for response generation"""
    
    @pytest.mark.asyncio
    async def test_generate_response_success(self, llm_service):
        """Test successful response generation"""
        llm_service.initialize_provider()
        
        response = await llm_service.generate_response(
            system_prompt="You are a helpful assistant.",
            user_message="Hello, how are you?"
        )
        
        assert response == "This is a test response from the LLM."
        assert llm_service.llm.agenerate.called
    
    @pytest.mark.asyncio
    async def test_generate_response_not_initialized(self, llm_service):
        """Test error when generating response without initialization"""
        with pytest.raises(RuntimeError, match="LLM provider not initialized"):
            await llm_service.generate_response(
                system_prompt="Test",
                user_message="Test"
            )
    
    @pytest.mark.asyncio
    async def test_generate_response_with_overrides(self, llm_service, mock_model_checker):
        """Test response generation with parameter overrides"""
        llm_service.initialize_provider()
        
        response = await llm_service.generate_response(
            system_prompt="You are a helpful assistant.",
            user_message="Hello!",
            temperature=0.9,
            max_tokens=500
        )
        
        assert response == "This is a test response from the LLM."
        # Verify override was used (model checker called twice: init + override)
        assert mock_model_checker.get_langchain_model.call_count == 2
    
    @pytest.mark.asyncio
    async def test_generate_response_retry_on_error(self, llm_service):
        """Test retry logic on error"""
        llm_service.initialize_provider()
        
        # Make first 2 calls fail, third succeed
        llm_service.llm.agenerate.side_effect = [
            Exception("Network error"),
            Exception("Network error"),
            llm_service.llm.agenerate.return_value
        ]
        
        response = await llm_service.generate_response(
            system_prompt="Test",
            user_message="Test"
        )
        
        # Should succeed after retries
        assert response == "This is a test response from the LLM."
        assert llm_service.llm.agenerate.call_count == 3
    
    @pytest.mark.asyncio
    async def test_generate_response_max_retries_exceeded(self, llm_service):
        """Test failure after max retries"""
        llm_service.initialize_provider()
        
        # Make all calls fail
        llm_service.llm.agenerate.side_effect = Exception("Persistent network error")
        
        with pytest.raises(Exception, match="Persistent network error"):
            await llm_service.generate_response(
                system_prompt="Test",
                user_message="Test"
            )
        
        # Should have tried 3 times
        assert llm_service.llm.agenerate.call_count == 3


class TestLLMServiceStreaming:
    """Test suite for streaming responses"""
    
    @pytest.mark.asyncio
    async def test_stream_response_success(self, llm_service):
        """Test successful streaming response"""
        llm_service.initialize_provider()
        
        chunks = []
        async for chunk in llm_service.stream_response(
            system_prompt="You are a helpful assistant.",
            user_message="Hello!"
        ):
            chunks.append(chunk)
        
        assert chunks == ["This ", "is ", "a ", "test ", "response."]
    
    @pytest.mark.asyncio
    async def test_stream_response_not_initialized(self, llm_service):
        """Test error when streaming without initialization"""
        with pytest.raises(RuntimeError, match="LLM provider not initialized"):
            async for _ in llm_service.stream_response(
                system_prompt="Test",
                user_message="Test"
            ):
                pass
    
    @pytest.mark.asyncio
    async def test_stream_response_with_overrides(self, llm_service, mock_model_checker):
        """Test streaming with parameter overrides"""
        llm_service.initialize_provider()
        
        chunks = []
        async for chunk in llm_service.stream_response(
            system_prompt="Test",
            user_message="Test",
            temperature=0.1,
            max_tokens=100
        ):
            chunks.append(chunk)
        
        assert len(chunks) == 5
        # Verify override was used
        assert mock_model_checker.get_langchain_model.call_count == 2


class TestLLMServiceTokenCounting:
    """Test suite for token counting"""
    
    def test_count_tokens_success(self, llm_service):
        """Test successful token counting"""
        llm_service.initialize_provider()
        llm_service.llm.get_num_tokens.return_value = 42
        
        count = llm_service.count_tokens("This is a test message.")
        
        assert count == 42
        llm_service.llm.get_num_tokens.assert_called_once_with("This is a test message.")
    
    def test_count_tokens_not_initialized(self, llm_service):
        """Test error when counting tokens without initialization"""
        with pytest.raises(RuntimeError, match="LLM provider not initialized"):
            llm_service.count_tokens("Test")
    
    def test_count_tokens_fallback_on_error(self, llm_service):
        """Test fallback token counting on error"""
        llm_service.initialize_provider()
        llm_service.llm.get_num_tokens.side_effect = Exception("Token counting error")
        
        # Should fall back to character-based estimation
        count = llm_service.count_tokens("This is a test message.")
        
        # Rough estimate: 23 characters / 4 = 5 tokens
        assert count == 5


class TestLLMServiceConfigInfo:
    """Test suite for configuration info"""
    
    def test_get_config_info_uninitialized(self, llm_service):
        """Test getting config info before initialization"""
        info = llm_service.get_config_info()
        
        assert info["provider"] is None
        assert info["model_id"] is None
        assert info["temperature"] == 0.7
        assert info["max_tokens"] == 2000
        assert info["initialized"] is False
    
    def test_get_config_info_initialized(self, llm_service):
        """Test getting config info after initialization"""
        llm_service.initialize_provider()
        
        info = llm_service.get_config_info()
        
        assert info["provider"] == "groq"
        assert info["model_id"] == "llama2-70b-4096"
        assert info["temperature"] == 0.7
        assert info["max_tokens"] == 2000
        assert info["initialized"] is True


class TestLLMServiceDependencyInjection:
    """Test suite for dependency injection"""
    
    def test_get_llm_service(self):
        """Test dependency injection helper"""
        service = get_llm_service()
        
        assert isinstance(service, LLMService)
        assert isinstance(service.config, ConfigService)
        assert isinstance(service.model_checker, ModelChecker)
