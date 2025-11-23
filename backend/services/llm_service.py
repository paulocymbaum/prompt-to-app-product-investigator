"""
LLM Service for interacting with LLM providers via LangChain.

This service handles:
- LangChain model initialization for Groq and OpenAI
- Synchronous and streaming response generation
- Token counting for cost and context management
- Error handling with retry logic
- Temperature and max_tokens configuration

SOLID Principles:
- Single Responsibility: Manages only LLM interactions
- Open/Closed: Extensible for new providers via LangChain
- Dependency Inversion: Depends on ConfigService and ModelChecker abstractions
"""

import os
from typing import Optional, AsyncGenerator
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import structlog
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage
from langchain_core.callbacks import StreamingStdOutCallbackHandler

from services.config_service import ConfigService
from services.model_checker import ModelChecker

logger = structlog.get_logger()


class LLMService:
    """
    Service for managing LLM provider interactions using LangChain.
    
    Supports both Groq and OpenAI providers with streaming capabilities,
    token counting, and configurable parameters.
    """
    
    def __init__(self, config_service: ConfigService, model_checker: ModelChecker):
        """
        Initialize the LLM service.
        
        Args:
            config_service: Service for managing API keys and configuration
            model_checker: Service for model validation and instance creation
        """
        self.config = config_service
        self.model_checker = model_checker
        self.llm = None
        self.provider = None
        self.model_id = None
        self.temperature = 0.7
        self.max_tokens = 2000
        
        logger.info("llm_service_initialized")
    
    def initialize_provider(
        self,
        provider: Optional[str] = None,
        model_id: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        streaming: bool = False
    ):
        """
        Initialize the LLM provider with specified configuration.
        
        If provider and model_id are not specified, uses active configuration
        from config service.
        
        Args:
            provider: Provider name ('groq' or 'openai'), defaults to active provider
            model_id: Model identifier, defaults to selected model
            temperature: Sampling temperature (0-1), defaults to 0.7
            max_tokens: Maximum tokens to generate, defaults to 2000
            streaming: Enable streaming responses, defaults to False
            
        Raises:
            ValueError: If provider or model_id is invalid
            RuntimeError: If API key is not configured
        """
        # Use active configuration if not specified
        if provider is None:
            provider = self.config.get_active_provider()
            if not provider:
                raise RuntimeError("No active provider configured")
        
        if model_id is None:
            model_id = self.config.get_selected_model()
            if not model_id:
                raise RuntimeError("No model selected")
        
        # Get API key from config
        api_key = self.config.get_token(provider)
        if not api_key:
            raise RuntimeError(f"No API key configured for provider: {provider}")
        
        logger.info(
            "initializing_llm_provider",
            provider=provider,
            model_id=model_id,
            temperature=temperature,
            max_tokens=max_tokens,
            streaming=streaming
        )
        
        # Create LangChain model instance
        self.llm = self.model_checker.get_langchain_model(
            provider=provider,
            model_id=model_id,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            streaming=streaming
        )
        
        self.provider = provider
        self.model_id = model_id
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        logger.info("llm_provider_initialized", provider=provider, model_id=model_id)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True
    )
    async def generate_response(
        self,
        system_prompt: str,
        user_message: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Generate a response from the LLM.
        
        Uses retry logic with exponential backoff for reliability.
        
        Args:
            system_prompt: System prompt defining the assistant's behavior
            user_message: User's input message
            temperature: Optional temperature override
            max_tokens: Optional max_tokens override
            
        Returns:
            Generated response text
            
        Raises:
            RuntimeError: If LLM is not initialized
            Exception: If all retry attempts fail
        """
        if self.llm is None:
            raise RuntimeError("LLM provider not initialized. Call initialize_provider() first.")
        
        logger.info(
            "generating_response",
            provider=self.provider,
            model_id=self.model_id,
            system_prompt_length=len(system_prompt),
            user_message_length=len(user_message)
        )
        
        # Prepare messages
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message)
        ]
        
        try:
            # Temporarily override parameters if specified
            if temperature is not None or max_tokens is not None:
                temp_llm = self._create_temp_llm(temperature, max_tokens)
                response = await temp_llm.agenerate([messages])
            else:
                response = await self.llm.agenerate([messages])
            
            result = response.generations[0][0].text
            
            logger.info(
                "response_generated",
                response_length=len(result),
                provider=self.provider
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "llm_generation_error",
                error=str(e),
                provider=self.provider,
                model_id=self.model_id
            )
            raise
    
    async def stream_response(
        self,
        system_prompt: str,
        user_message: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response from the LLM.
        
        Yields chunks of text as they are generated, useful for real-time
        user interfaces.
        
        Args:
            system_prompt: System prompt defining the assistant's behavior
            user_message: User's input message
            temperature: Optional temperature override
            max_tokens: Optional max_tokens override
            
        Yields:
            Text chunks as they are generated
            
        Raises:
            RuntimeError: If LLM is not initialized
            Exception: If generation fails
        """
        if self.llm is None:
            raise RuntimeError("LLM provider not initialized. Call initialize_provider() first.")
        
        logger.info(
            "streaming_response",
            provider=self.provider,
            model_id=self.model_id
        )
        
        # Prepare messages
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message)
        ]
        
        try:
            # Create streaming LLM if not already enabled
            streaming_llm = self._create_temp_llm(temperature, max_tokens, streaming=True)
            
            # Stream the response
            async for chunk in streaming_llm.astream(messages):
                if hasattr(chunk, 'content'):
                    content = chunk.content
                    # Handle different content types
                    if isinstance(content, str):
                        yield content
                    elif isinstance(content, list):
                        yield str(content)
                    else:
                        yield str(chunk)
                else:
                    yield str(chunk)
                    
        except Exception as e:
            logger.error(
                "llm_streaming_error",
                error=str(e),
                provider=self.provider,
                model_id=self.model_id
            )
            raise
    
    def count_tokens(self, text: str) -> int:
        """
        Count the number of tokens in a text string.
        
        Uses LangChain's token counter for the active model.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Number of tokens
            
        Raises:
            RuntimeError: If LLM is not initialized
        """
        if self.llm is None:
            raise RuntimeError("LLM provider not initialized. Call initialize_provider() first.")
        
        try:
            # Use LangChain's get_num_tokens method
            token_count = self.llm.get_num_tokens(text)
            
            logger.debug(
                "tokens_counted",
                text_length=len(text),
                token_count=token_count,
                provider=self.provider
            )
            
            return token_count
            
        except Exception as e:
            # Fallback: rough estimate (1 token ≈ 4 characters)
            estimated_tokens = len(text) // 4
            
            logger.warning(
                "token_count_fallback",
                error=str(e),
                estimated_tokens=estimated_tokens
            )
            
            return estimated_tokens
    
    def _create_temp_llm(
        self,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        streaming: Optional[bool] = None
    ):
        """
        Create a temporary LLM instance with overridden parameters.
        
        Args:
            temperature: Temperature override
            max_tokens: Max tokens override
            streaming: Streaming override
            
        Returns:
            LangChain chat model instance
        """
        if self.provider is None or self.model_id is None:
            raise RuntimeError("LLM provider not initialized")
        
        # Get API key from config
        api_key = self.config.get_token(self.provider)
        if not api_key:
            raise RuntimeError(f"No API key configured for provider: {self.provider}")
        
        # Use overrides or current values
        temp = temperature if temperature is not None else self.temperature
        tokens = max_tokens if max_tokens is not None else self.max_tokens
        stream = streaming if streaming is not None else False
        
        return self.model_checker.get_langchain_model(
            provider=self.provider,
            model_id=self.model_id,
            api_key=api_key,
            temperature=temp,
            max_tokens=tokens,
            streaming=stream
        )
    
    def get_config_info(self) -> dict:
        """
        Get current LLM configuration information.
        
        Returns:
            Dictionary with provider, model, and parameter details
        """
        return {
            "provider": self.provider,
            "model_id": self.model_id,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "initialized": self.llm is not None
        }


# Dependency injection helper
def get_llm_service() -> LLMService:
    """
    Dependency injection helper for FastAPI routes.
    
    Returns:
        LLMService instance
    """
    from services.config_service import ConfigService
    from services.model_checker import ModelChecker
    
    config_service = ConfigService()
    model_checker = ModelChecker(config_service)
    
    return LLMService(
        config_service=config_service,
        model_checker=model_checker
    )
