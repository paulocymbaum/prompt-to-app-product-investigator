"""
Configuration API Routes for LLM Provider Management.

This module provides FastAPI endpoints for:
- API token management (save/retrieve)
- Model listing from providers
- Model selection
- Provider switching

SOLID Principles:
- Single Responsibility: Handles only configuration-related HTTP endpoints
- Open/Closed: Extensible for new configuration features
- Dependency Inversion: Depends on ConfigService and ModelChecker abstractions
"""

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict
import structlog
from services.config_service import ConfigService
from services.model_checker import ModelChecker

logger = structlog.get_logger()

# Initialize router
router = APIRouter(
    prefix="/api/config",
    tags=["configuration"]
)

# Pydantic models for request/response validation

class TokenRequest(BaseModel):
    """Request model for saving API tokens"""
    provider: str = Field(..., description="Provider name (groq or openai)")
    token: str = Field(..., description="API token", min_length=10)
    
    @validator('provider')
    def validate_provider(cls, v):
        if v not in ['groq', 'openai']:
            raise ValueError('Provider must be either "groq" or "openai"')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "provider": "groq",
                "token": "gsk_1234567890abcdef"
            }
        }


class TokenResponse(BaseModel):
    """Response model for token operations"""
    status: str
    provider: str
    message: str


class ModelInfo(BaseModel):
    """Model information"""
    id: str
    name: str
    provider: str
    context_window: int
    supports_streaming: bool
    langchain_class: str
    owned_by: Optional[str] = None
    created: Optional[int] = None


class ModelsResponse(BaseModel):
    """Response model for model listing"""
    provider: str
    models: List[ModelInfo]
    cached: bool


class ModelSelectRequest(BaseModel):
    """Request model for selecting a model"""
    provider: str = Field(..., description="Provider name")
    model_id: str = Field(..., description="Model identifier")
    
    @validator('provider')
    def validate_provider(cls, v):
        if v not in ['groq', 'openai']:
            raise ValueError('Provider must be either "groq" or "openai"')
        return v


class ModelSelectResponse(BaseModel):
    """Response model for model selection"""
    status: str
    provider: str
    model_id: str
    message: str


class ProviderStatus(BaseModel):
    """Provider-specific status"""
    token_exists: bool
    selected_model: Optional[str] = None


class ConfigStatusResponse(BaseModel):
    """Response model for configuration status"""
    active_provider: Optional[str]
    has_groq_token: bool
    has_openai_token: bool
    selected_model: Optional[str]
    providers: Dict[str, ProviderStatus]


# Dependency injection
def get_config_service() -> ConfigService:
    """Dependency for ConfigService"""
    return ConfigService()


def get_model_checker(config: ConfigService = Depends(get_config_service)) -> ModelChecker:
    """Dependency for ModelChecker"""
    return ModelChecker(config)


# API Endpoints

@router.post(
    "/token",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Save API Token",
    description="Save and validate an API token for a specific provider"
)
async def save_token(
    request: TokenRequest,
    config: ConfigService = Depends(get_config_service)
) -> TokenResponse:
    """
    Save an API token for the specified provider.
    
    Validates token format before saving:
    - Groq tokens must start with 'gsk_'
    - OpenAI tokens must start with 'sk-' or 'sk-proj-'
    
    Raises:
        HTTPException 400: Invalid token format
        HTTPException 500: Failed to save token
    """
    logger.info("save_token_request", provider=request.provider)
    
    # Validate token format
    if not config.validate_token_format(request.provider, request.token):
        logger.warning(
            "invalid_token_format",
            provider=request.provider,
            token_prefix=request.token[:10] if len(request.token) >= 10 else request.token
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid token format for {request.provider}. "
                   f"{'Expected format: gsk_*' if request.provider == 'groq' else 'Expected format: sk-* or sk-proj-*'}"
        )
    
    try:
        # Save token
        config.save_token(request.provider, request.token)
        
        logger.info("token_saved_successfully", provider=request.provider)
        
        return TokenResponse(
            status="success",
            provider=request.provider,
            message=f"Token saved successfully for {request.provider}"
        )
        
    except Exception as e:
        logger.error("save_token_failed", provider=request.provider, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save token: {str(e)}"
        )


@router.get(
    "/models",
    response_model=ModelsResponse,
    summary="List Available Models",
    description="Fetch list of available models from the specified provider"
)
async def get_models(
    provider: str,
    force_refresh: bool = False,
    config: ConfigService = Depends(get_config_service),
    checker: ModelChecker = Depends(get_model_checker)
) -> ModelsResponse:
    """
    Retrieve available models for the specified provider.
    
    Uses cached models if available (5-minute TTL), unless force_refresh is True.
    
    Args:
        provider: Provider name (groq or openai)
        force_refresh: If True, bypass cache and fetch fresh data
        
    Raises:
        HTTPException 400: Invalid provider
        HTTPException 401: No token configured
        HTTPException 500: Failed to fetch models
    """
    logger.info("get_models_request", provider=provider, force_refresh=force_refresh)
    
    # Validate provider
    if provider not in ['groq', 'openai']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Provider must be either "groq" or "openai"'
        )
    
    # Check if token is configured
    token = config.get_token(provider)
    if not token:
        logger.warning("no_token_configured", provider=provider)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"No API token configured for {provider}. Please save a token first."
        )
    
    try:
        # Invalidate cache if force refresh
        if force_refresh:
            checker.invalidate_cache(provider)
        
        # Check cache first
        cached_models = checker.get_cached_models(provider)
        if cached_models is not None:
            logger.info("returning_cached_models", provider=provider, count=len(cached_models))
            return ModelsResponse(
                provider=provider,
                models=[ModelInfo(**model) for model in cached_models],
                cached=True
            )
        
        # Fetch models from API
        models = await checker.fetch_models(provider)
        
        logger.info("models_fetched_successfully", provider=provider, count=len(models))
        
        return ModelsResponse(
            provider=provider,
            models=[ModelInfo(**model) for model in models],
            cached=False
        )
        
    except Exception as e:
        logger.error("fetch_models_failed", provider=provider, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch models: {str(e)}"
        )


@router.post(
    "/model/select",
    response_model=ModelSelectResponse,
    summary="Select Model",
    description="Select a specific model for the provider"
)
async def select_model(
    request: ModelSelectRequest,
    config: ConfigService = Depends(get_config_service),
    checker: ModelChecker = Depends(get_model_checker)
) -> ModelSelectResponse:
    """
    Select and save a model for the specified provider.
    
    Validates that the model exists in the provider's available models.
    
    Raises:
        HTTPException 400: Invalid model ID or provider
        HTTPException 401: No token configured
        HTTPException 500: Failed to save selection
    """
    logger.info(
        "select_model_request",
        provider=request.provider,
        model_id=request.model_id
    )
    
    # Check if token is configured
    token = config.get_token(request.provider)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"No API token configured for {request.provider}"
        )
    
    try:
        # Validate model exists
        is_valid = checker.validate_model_selection(request.provider, request.model_id)
        
        if not is_valid:
            logger.warning(
                "invalid_model_selection",
                provider=request.provider,
                model_id=request.model_id
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Model '{request.model_id}' not found for provider '{request.provider}'"
            )
        
        # Save model selection
        config.save_selected_model(request.provider, request.model_id)
        
        # Switch to this provider
        config.switch_provider(request.provider)
        
        logger.info(
            "model_selected_successfully",
            provider=request.provider,
            model_id=request.model_id
        )
        
        return ModelSelectResponse(
            status="success",
            provider=request.provider,
            model_id=request.model_id,
            message=f"Model '{request.model_id}' selected for {request.provider}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("select_model_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to select model: {str(e)}"
        )


@router.get(
    "/status",
    response_model=ConfigStatusResponse,
    summary="Get Configuration Status",
    description="Get current configuration status including active provider and tokens"
)
async def get_config_status(
    config: ConfigService = Depends(get_config_service)
) -> ConfigStatusResponse:
    """
    Retrieve current configuration status.
    
    Returns information about which tokens are configured and active provider.
    """
    logger.info("get_config_status_request")
    
    try:
        active_provider = config.get_active_provider()
        selected_model = config.get_selected_model(active_provider) if active_provider else None
        
        # Build provider-specific status
        providers_status = {
            "groq": ProviderStatus(
                token_exists=bool(config.get_token("groq")),
                selected_model=config.get_selected_model("groq")
            ),
            "openai": ProviderStatus(
                token_exists=bool(config.get_token("openai")),
                selected_model=config.get_selected_model("openai")
            )
        }
        
        return ConfigStatusResponse(
            active_provider=active_provider,
            has_groq_token=bool(config.get_token("groq")),
            has_openai_token=bool(config.get_token("openai")),
            selected_model=selected_model,
            providers=providers_status
        )
        
    except Exception as e:
        logger.error("get_config_status_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get configuration status: {str(e)}"
        )


@router.delete(
    "/token/{provider}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete API Token",
    description="Remove API token for the specified provider"
)
async def delete_token(
    provider: str,
    config: ConfigService = Depends(get_config_service)
):
    """
    Delete the API token for the specified provider.
    
    Raises:
        HTTPException 400: Invalid provider
        HTTPException 500: Failed to delete token
    """
    logger.info("delete_token_request", provider=provider)
    
    if provider not in ['groq', 'openai']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Provider must be either "groq" or "openai"'
        )
    
    try:
        # Delete token by directly removing from env (bypass validation)
        import os
        from dotenv import set_key, unset_key
        env_var = f"{provider.upper()}_API_KEY"
        env_file = config.env_file
        
        # Remove from environment
        if os.path.exists(env_file):
            unset_key(env_file, env_var)
        
        logger.info("token_deleted_successfully", provider=provider)
        return None
        
    except Exception as e:
        logger.error("delete_token_failed", provider=provider, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete token: {str(e)}"
        )
