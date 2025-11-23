"""
Model Checker Service for fetching and validating LLM models.

This service handles:
- LangChain-based model listing for Groq and OpenAI
- Model list retrieval and caching
- Error handling for invalid tokens
- Retry logic with exponential backoff
- Dynamic model discovery

SOLID Principles:
- Single Responsibility: Manages only model checking
- Open/Closed: Extensible for new providers via LangChain
- Dependency Inversion: Depends on ConfigService abstraction
"""

import httpx
import os
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import structlog
from services.config_service import ConfigService
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI

logger = structlog.get_logger()


class ModelChecker:
    """
    Service for fetching and caching available LLM models from providers.
    
    Implements retry logic and caching to optimize API calls and handle
    transient failures gracefully.
    """
    
    def __init__(self, config_service: ConfigService):
        """
        Initialize the model checker service.
        
        Args:
            config_service: Configuration service for retrieving API tokens
        """
        self.config = config_service
        self.cache: Dict[str, Dict] = {}
        self.cache_ttl = 300  # 5 minutes in seconds
        
        logger.info("model_checker_initialized")
    
    def _is_cache_valid(self, provider: str) -> bool:
        """
        Check if cached models are still valid.
        
        Args:
            provider: Provider name
            
        Returns:
            True if cache is valid, False otherwise
        """
        if provider not in self.cache:
            return False
        
        cache_entry = self.cache[provider]
        expiry_time = cache_entry.get("expiry")
        
        if not expiry_time:
            return False
        
        is_valid = datetime.utcnow() < expiry_time
        
        if not is_valid:
            logger.info("cache_expired", provider=provider)
        
        return is_valid
    
    def get_cached_models(self, provider: str) -> Optional[List[dict]]:
        """
        Get cached models if available and valid.
        
        Args:
            provider: Provider name ('groq' or 'openai')
            
        Returns:
            List of cached models or None if cache is invalid
        """
        if self._is_cache_valid(provider):
            logger.info("cache_hit", provider=provider)
            return self.cache[provider]["models"]
        
        logger.info("cache_miss", provider=provider)
        return None
    
    def _cache_models(self, provider: str, models: List[dict]) -> None:
        """
        Cache models with expiry time.
        
        Args:
            provider: Provider name
            models: List of models to cache
        """
        expiry_time = datetime.utcnow() + timedelta(seconds=self.cache_ttl)
        
        self.cache[provider] = {
            "models": models,
            "expiry": expiry_time,
            "cached_at": datetime.utcnow()
        }
        
        logger.info("models_cached", provider=provider, count=len(models))
    
    def invalidate_cache(self, provider: Optional[str] = None) -> None:
        """
        Invalidate cache for a provider or all providers.
        
        Args:
            provider: Provider name or None to invalidate all
        """
        if provider:
            if provider in self.cache:
                del self.cache[provider]
                logger.info("cache_invalidated", provider=provider)
        else:
            self.cache.clear()
            logger.info("cache_invalidated_all")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError, Exception)),
        reraise=True
    )
    async def fetch_groq_models(self, api_key: str) -> List[dict]:
        """
        Fetch available models from Groq using direct API (LangChain doesn't expose model listing).
        
        Args:
            api_key: Groq API key
            
        Returns:
            List of model dictionaries with enhanced metadata
            
        Raises:
            httpx.HTTPStatusError: If API returns error status
            httpx.TimeoutException: If request times out
            httpx.NetworkError: If network error occurs
        """
        logger.info("fetching_groq_models")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.groq.com/openai/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=30.0
                )
                response.raise_for_status()
                
                data = response.json()
                models = data.get("data", [])
                
                # Enhance models with additional metadata for LangChain compatibility
                enhanced_models = []
                for model in models:
                    enhanced_model = {
                        "id": model.get("id"),
                        "name": model.get("id"),  # Use ID as name
                        "provider": "groq",
                        "object": model.get("object", "model"),
                        "created": model.get("created"),
                        "owned_by": model.get("owned_by", "groq"),
                        "context_window": self._get_groq_context_window(model.get("id")),
                        "supports_streaming": True,
                        "langchain_class": "ChatGroq"
                    }
                    enhanced_models.append(enhanced_model)
                
                logger.info("groq_models_fetched", count=len(enhanced_models))
                return enhanced_models
                
        except httpx.HTTPStatusError as e:
            logger.error(
                "groq_api_error",
                status_code=e.response.status_code,
                detail=e.response.text[:200]
            )
            raise
        except httpx.TimeoutException as e:
            logger.error("groq_api_timeout", error=str(e))
            raise
        except httpx.NetworkError as e:
            logger.error("groq_network_error", error=str(e))
            raise
        except Exception as e:
            logger.error("groq_unexpected_error", error=str(e), error_type=type(e).__name__)
            raise
    
    def _get_groq_context_window(self, model_id: str) -> int:
        """
        Get context window size for Groq models.
        
        Args:
            model_id: Model identifier
            
        Returns:
            Context window size in tokens
        """
        # Known Groq model context windows
        context_windows = {
            "llama2-70b-4096": 4096,
            "mixtral-8x7b-32768": 32768,
            "gemma-7b-it": 8192,
            "llama3-8b-8192": 8192,
            "llama3-70b-8192": 8192,
            "llama-3.3-70b-versatile": 32768,
            "llama-3.1-8b-instant": 128000,
            "meta-llama/llama-4-scout-17b-16e-instruct": 32768,
        }
        return context_windows.get(model_id, 4096)  # Default to 4096
    
    def _get_openai_context_window(self, model_id: str) -> int:
        """
        Get context window size for OpenAI models.
        
        Args:
            model_id: Model identifier
            
        Returns:
            Context window size in tokens
        """
        # Known OpenAI model context windows
        context_windows = {
            "gpt-4": 8192,
            "gpt-4-32k": 32768,
            "gpt-4-turbo": 128000,
            "gpt-4-turbo-preview": 128000,
            "gpt-3.5-turbo": 4096,
            "gpt-3.5-turbo-16k": 16384,
        }
        
        # Handle model variants
        for key, value in context_windows.items():
            if model_id.startswith(key):
                return value
        
        return 4096  # Default
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError, Exception)),
        reraise=True
    )
    async def fetch_openai_models(self, api_key: str) -> List[dict]:
        """
        Fetch available models from OpenAI API with retry logic.
        
        Args:
            api_key: OpenAI API key
            
        Returns:
            List of model dictionaries with enhanced metadata for LangChain
            
        Raises:
            httpx.HTTPStatusError: If API returns error status
            httpx.TimeoutException: If request times out
            httpx.NetworkError: If network error occurs
        """
        logger.info("fetching_openai_models")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=30.0
                )
                response.raise_for_status()
                
                data = response.json()
                models = data.get("data", [])
                
                # Filter to chat models and enhance with metadata
                chat_models = []
                for model in models:
                    model_id = model.get("id", "")
                    # Filter to relevant chat/completion models
                    if any(x in model_id for x in ["gpt-4", "gpt-3.5-turbo", "gpt-4-turbo"]):
                        enhanced_model = {
                            "id": model_id,
                            "name": model_id,
                            "provider": "openai",
                            "object": model.get("object", "model"),
                            "created": model.get("created"),
                            "owned_by": model.get("owned_by", "openai"),
                            "context_window": self._get_openai_context_window(model_id),
                            "supports_streaming": True,
                            "supports_functions": "gpt-4" in model_id or "gpt-3.5-turbo" in model_id,
                            "langchain_class": "ChatOpenAI"
                        }
                        chat_models.append(enhanced_model)
                
                logger.info("openai_models_fetched", count=len(chat_models))
                return chat_models
                
        except httpx.HTTPStatusError as e:
            logger.error(
                "openai_api_error",
                status_code=e.response.status_code,
                detail=e.response.text[:200]
            )
            raise
        except httpx.TimeoutException as e:
            logger.error("openai_api_timeout", error=str(e))
            raise
        except httpx.NetworkError as e:
            logger.error("openai_network_error", error=str(e))
            raise
        except Exception as e:
            logger.error("openai_unexpected_error", error=str(e), error_type=type(e).__name__)
            raise
    
    async def fetch_models(self, provider: str, api_key: Optional[str] = None) -> List[dict]:
        """
        Fetch models for a provider with caching.
        
        Args:
            provider: Provider name ('groq' or 'openai')
            api_key: Optional API key (if not provided, fetched from config)
            
        Returns:
            List of model dictionaries
            
        Raises:
            ValueError: If provider is not supported
            Exception: If API call fails after retries
        """
        # Check cache first
        cached_models = self.get_cached_models(provider)
        if cached_models is not None:
            return cached_models
        
        # Get API key if not provided
        if not api_key:
            api_key = self.config.get_token(provider)
            
        if not api_key:
            logger.error("no_api_key", provider=provider)
            raise ValueError(f"No API key configured for {provider}")
        
        # Fetch models based on provider
        if provider == "groq":
            models = await self.fetch_groq_models(api_key)
        elif provider == "openai":
            models = await self.fetch_openai_models(api_key)
        else:
            logger.error("unsupported_provider", provider=provider)
            raise ValueError(f"Unsupported provider: {provider}")
        
        # Cache the results
        self._cache_models(provider, models)
        
        return models
    
    async def validate_model_selection(
        self,
        provider: str,
        model_id: str,
        available_models: Optional[List[dict]] = None
    ) -> bool:
        """
        Validate that a model ID exists in the available models.
        
        Args:
            provider: Provider name
            model_id: Model ID to validate
            available_models: Optional list of available models (uses cache/fetch if not provided)
            
        Returns:
            True if model is valid, False otherwise
        """
        if available_models is None:
            # Try to get from cache first
            available_models = self.get_cached_models(provider)
            
            # If not in cache, fetch fresh models
            if not available_models:
                try:
                    logger.info("cache_miss_validating_model", provider=provider)
                    available_models = await self.fetch_models(provider)
                except Exception as e:
                    logger.error("failed_fetch_validation", provider=provider, error=str(e))
                    return False
            
        if not available_models:
            logger.warning("no_models_for_validation", provider=provider)
            return False
        
        # Extract model IDs from available models
        model_ids = [model.get("id") for model in available_models if model.get("id")]
        
        is_valid = model_id in model_ids
        
        if is_valid:
            logger.info("model_validated", provider=provider, model_id=model_id)
        else:
            logger.warning("invalid_model", provider=provider, model_id=model_id)
        
        return is_valid
    
    def get_langchain_model(self, provider: str, model_id: str, api_key: str, **kwargs):
        """
        Get a LangChain chat model instance for the specified provider and model.
        
        LangChain models will use environment variables for API keys, so we temporarily
        set them in the environment.
        
        Args:
            provider: Provider name ('groq' or 'openai')
            model_id: Model identifier
            api_key: API key for authentication
            **kwargs: Additional arguments to pass to the model (temperature, max_tokens, etc.)
            
        Returns:
            LangChain chat model instance
            
        Raises:
            ValueError: If provider is not supported
        """
        logger.info("creating_langchain_model", provider=provider, model_id=model_id)
        
        if provider == "groq":
            # Set env variable for Groq
            os.environ["GROQ_API_KEY"] = api_key
            return ChatGroq(
                model=model_id,
                temperature=kwargs.get("temperature", 0.7),
                max_tokens=kwargs.get("max_tokens", 2000),
                streaming=kwargs.get("streaming", False),
                request_timeout=kwargs.get("timeout", 60.0)
            )
        elif provider == "openai":
            # Set env variable for OpenAI
            os.environ["OPENAI_API_KEY"] = api_key
            return ChatOpenAI(
                model=model_id,
                temperature=kwargs.get("temperature", 0.7),
                max_tokens=kwargs.get("max_tokens", 2000),
                streaming=kwargs.get("streaming", False),
                request_timeout=kwargs.get("timeout", 60.0)
            )
        else:
            raise ValueError(f"Unsupported provider: {provider}")
