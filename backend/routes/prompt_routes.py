"""
Prompt API Routes for prompt generation and management.

This module provides REST API endpoints for:
- Generating comprehensive development prompts from session data
- Regenerating prompts with modifications
- Downloading prompts in multiple formats
- Prompt caching for performance optimization
- Version tracking for regenerations

SOLID Principles:
- Single Responsibility: Handles only prompt-related API endpoints
- Open/Closed: Extensible for new prompt operations
- Dependency Inversion: Depends on PromptGenerator abstraction
"""

from fastapi import APIRouter, HTTPException, status, Depends, Response
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List
import structlog
import tempfile
import os
from datetime import datetime

from services.prompt_generator import PromptGenerator
from storage.conversation_storage import ConversationStorage

logger = structlog.get_logger()

# Create router
router = APIRouter(prefix="/api/prompt", tags=["prompts"])


# In-memory cache for prompts
# Key: session_id, Value: {"prompt": str, "version": int, "cached_at": datetime}
_prompt_cache = {}


# Dependency injection functions

def get_conversation_storage() -> ConversationStorage:
    """Get ConversationStorage instance."""
    data_dir = os.getenv("DATA_DIR", "./data")
    conversations_dir = os.path.join(data_dir, "conversations")
    return ConversationStorage(base_dir=conversations_dir)


def get_prompt_generator(
    storage: ConversationStorage = Depends(get_conversation_storage)
) -> PromptGenerator:
    """Get PromptGenerator instance with storage dependency."""
    return PromptGenerator(storage=storage)


# Pydantic Models

class GeneratePromptResponse(BaseModel):
    """Response model for generate prompt endpoint."""
    prompt: str = Field(..., description="Generated development prompt")
    cached: bool = Field(..., description="Whether prompt was retrieved from cache")
    token_count: int = Field(..., description="Estimated token count")
    session_id: str = Field(..., description="Session identifier")
    version: int = Field(default=1, description="Prompt version number")
    
    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "# Product Development Prompt\n\n...",
                "cached": False,
                "token_count": 6500,
                "session_id": "abc-123",
                "version": 1
            }
        }


class RegeneratePromptRequest(BaseModel):
    """Request model for regenerating prompt with modifications."""
    session_id: str = Field(..., description="Session identifier")
    focus_areas: Optional[List[str]] = Field(
        None,
        description="Specific areas to emphasize (e.g., 'security', 'performance')"
    )
    additional_requirements: Optional[str] = Field(
        None,
        description="Additional requirements to append to prompt"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "abc-123",
                "focus_areas": ["security", "scalability"],
                "additional_requirements": "Must support mobile-first design"
            }
        }


class RegeneratePromptResponse(BaseModel):
    """Response model for regenerate prompt endpoint."""
    prompt: str = Field(..., description="Regenerated development prompt")
    version: int = Field(..., description="New prompt version number")
    session_id: str = Field(..., description="Session identifier")
    token_count: int = Field(..., description="Estimated token count")
    modifications_applied: bool = Field(..., description="Whether modifications were applied")
    
    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "# Product Development Prompt\n\n...",
                "version": 2,
                "session_id": "abc-123",
                "token_count": 7200,
                "modifications_applied": True
            }
        }


# API Endpoints

@router.get("/generate/{session_id}", response_model=GeneratePromptResponse, status_code=status.HTTP_200_OK)
async def generate_prompt(
    session_id: str,
    force_regenerate: bool = False,
    generator: PromptGenerator = Depends(get_prompt_generator)
) -> GeneratePromptResponse:
    """
    Generate comprehensive development prompt from session data.
    
    Analyzes all conversation answers and generates a best-practice development
    prompt emphasizing SOLID principles, DRY, and architecture patterns.
    Results are cached for performance.
    
    Args:
        session_id: Session identifier
        force_regenerate: If True, bypass cache and regenerate (default: False)
        generator: PromptGenerator dependency
        
    Returns:
        Generated prompt with metadata
        
    Raises:
        404: Session not found
        400: Investigation incomplete
        500: Generation failed
        
    Example:
        GET /api/prompt/generate/abc-123
        
        Response:
        {
            "prompt": "# Product Development Prompt...",
            "cached": false,
            "token_count": 6500,
            "session_id": "abc-123",
            "version": 1
        }
    """
    logger.info(
        "api_generate_prompt",
        session_id=session_id,
        force_regenerate=force_regenerate
    )
    
    try:
        # Check cache first (unless force regenerate)
        if not force_regenerate and session_id in _prompt_cache:
            cached_data = _prompt_cache[session_id]
            logger.info(
                "prompt_cache_hit",
                session_id=session_id,
                version=cached_data.get("version", 1)
            )
            
            return GeneratePromptResponse(
                prompt=cached_data["prompt"],
                cached=True,
                token_count=len(cached_data["prompt"]) // 4,  # Rough estimate
                session_id=session_id,
                version=cached_data.get("version", 1)
            )
        
        # Generate new prompt
        prompt = await generator.generate_prompt(session_id)
        
        # Estimate token count (1 token ≈ 4 chars)
        token_count = len(prompt) // 4
        
        # Cache the result
        _prompt_cache[session_id] = {
            "prompt": prompt,
            "version": 1,
            "cached_at": datetime.utcnow()
        }
        
        logger.info(
            "prompt_generated_via_api",
            session_id=session_id,
            token_count=token_count,
            prompt_length=len(prompt)
        )
        
        return GeneratePromptResponse(
            prompt=prompt,
            cached=False,
            token_count=token_count,
            session_id=session_id,
            version=1
        )
        
    except FileNotFoundError as e:
        logger.warning("session_not_found_for_prompt", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}"
        )
    except ValueError as e:
        logger.warning("prompt_generation_validation_error", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Prompt generation failed: {str(e)}"
        )
    except Exception as e:
        logger.error(
            "generate_prompt_error",
            session_id=session_id,
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate prompt: {str(e)}"
        )


@router.post("/regenerate", response_model=RegeneratePromptResponse, status_code=status.HTTP_200_OK)
async def regenerate_prompt(
    request: RegeneratePromptRequest,
    generator: PromptGenerator = Depends(get_prompt_generator)
) -> RegeneratePromptResponse:
    """
    Regenerate prompt with modifications or additional focus areas.
    
    Clears the cache and generates a new version of the prompt, optionally
    applying user-specified modifications or focus areas.
    
    Args:
        request: Regeneration request with optional modifications
        generator: PromptGenerator dependency
        
    Returns:
        Regenerated prompt with new version number
        
    Raises:
        404: Session not found
        400: Invalid modifications
        500: Regeneration failed
        
    Example:
        POST /api/prompt/regenerate
        {
            "session_id": "abc-123",
            "focus_areas": ["security"],
            "additional_requirements": "Must support OAuth 2.0"
        }
        
        Response:
        {
            "prompt": "# Product Development Prompt...",
            "version": 2,
            "session_id": "abc-123",
            "token_count": 7200,
            "modifications_applied": true
        }
    """
    logger.info(
        "api_regenerate_prompt",
        session_id=request.session_id,
        has_focus_areas=bool(request.focus_areas),
        has_additional_reqs=bool(request.additional_requirements)
    )
    
    try:
        # Get current version from cache
        current_version = 1
        if request.session_id in _prompt_cache:
            current_version = _prompt_cache[request.session_id].get("version", 1)
            # Clear cache for regeneration
            del _prompt_cache[request.session_id]
            logger.info("prompt_cache_cleared", session_id=request.session_id)
        
        # Generate new prompt
        prompt = await generator.generate_prompt(request.session_id)
        
        # Apply modifications if specified
        modifications_applied = False
        
        if request.focus_areas:
            # Add focus areas to prompt
            focus_section = "\n\n## Additional Focus Areas\n\n"
            focus_section += "Please pay special attention to:\n\n"
            for area in request.focus_areas:
                focus_section += f"- **{area.title()}**: Implement comprehensive {area} measures\n"
            prompt += focus_section
            modifications_applied = True
            logger.info(
                "focus_areas_applied",
                session_id=request.session_id,
                focus_areas=request.focus_areas
            )
        
        if request.additional_requirements:
            # Add additional requirements
            additional_section = "\n\n## Additional Requirements\n\n"
            additional_section += request.additional_requirements
            prompt += additional_section
            modifications_applied = True
            logger.info(
                "additional_requirements_applied",
                session_id=request.session_id,
                requirements_length=len(request.additional_requirements)
            )
        
        # Increment version
        new_version = current_version + 1
        
        # Cache the new version
        _prompt_cache[request.session_id] = {
            "prompt": prompt,
            "version": new_version,
            "cached_at": datetime.utcnow()
        }
        
        # Estimate token count
        token_count = len(prompt) // 4
        
        logger.info(
            "prompt_regenerated_via_api",
            session_id=request.session_id,
            version=new_version,
            token_count=token_count,
            modifications_applied=modifications_applied
        )
        
        return RegeneratePromptResponse(
            prompt=prompt,
            version=new_version,
            session_id=request.session_id,
            token_count=token_count,
            modifications_applied=modifications_applied
        )
        
    except FileNotFoundError as e:
        logger.warning("session_not_found_for_regenerate", session_id=request.session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {request.session_id}"
        )
    except ValueError as e:
        logger.warning("prompt_regeneration_validation_error", session_id=request.session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Prompt regeneration failed: {str(e)}"
        )
    except Exception as e:
        logger.error(
            "regenerate_prompt_error",
            session_id=request.session_id,
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to regenerate prompt: {str(e)}"
        )


@router.get("/download/{session_id}")
async def download_prompt(
    session_id: str,
    format: str = "md",
    generator: PromptGenerator = Depends(get_prompt_generator)
):
    """
    Download generated prompt in specified format (txt or md).
    
    Returns the prompt as a downloadable file with appropriate content type
    and filename.
    
    Args:
        session_id: Session identifier
        format: File format - 'txt' or 'md' (default: 'md')
        generator: PromptGenerator dependency
        
    Returns:
        File download response
        
    Raises:
        400: Invalid format
        404: Session not found
        500: Download failed
        
    Example:
        GET /api/prompt/download/abc-123?format=md
        
        Downloads file: product_prompt_abc-123_2024-01-01.md
    """
    logger.info(
        "api_download_prompt",
        session_id=session_id,
        format=format
    )
    
    # Validate format
    if format not in ["txt", "md"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Format must be 'txt' or 'md'"
        )
    
    try:
        # Get or generate prompt
        if session_id in _prompt_cache:
            prompt = _prompt_cache[session_id]["prompt"]
            logger.info("download_using_cached_prompt", session_id=session_id)
        else:
            prompt = await generator.generate_prompt(session_id)
            # Cache for future use
            _prompt_cache[session_id] = {
                "prompt": prompt,
                "version": 1,
                "cached_at": datetime.utcnow()
            }
            logger.info("download_generated_new_prompt", session_id=session_id)
        
        # Create timestamp for filename
        timestamp = datetime.utcnow().strftime("%Y-%m-%d")
        filename = f"product_prompt_{session_id}_{timestamp}.{format}"
        
        # Set appropriate content type
        media_type = "text/plain" if format == "txt" else "text/markdown"
        
        logger.info(
            "prompt_downloaded_via_api",
            session_id=session_id,
            format=format,
            filename=filename,
            content_length=len(prompt)
        )
        
        # Return as streaming response to avoid creating temp files
        return StreamingResponse(
            iter([prompt]),
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": media_type
            }
        )
        
    except FileNotFoundError as e:
        logger.warning("session_not_found_for_download", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}"
        )
    except ValueError as e:
        logger.warning("prompt_download_validation_error", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Prompt download failed: {str(e)}"
        )
    except Exception as e:
        logger.error(
            "download_prompt_error",
            session_id=session_id,
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download prompt: {str(e)}"
        )


@router.delete("/cache/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def clear_cache(session_id: str):
    """
    Clear cached prompt for a specific session.
    
    Removes the prompt from cache, forcing regeneration on next request.
    Useful for testing or when conversation data has been updated.
    
    Args:
        session_id: Session identifier
        
    Returns:
        204 No Content on success
        
    Example:
        DELETE /api/prompt/cache/abc-123
    """
    logger.info("api_clear_prompt_cache", session_id=session_id)
    
    if session_id in _prompt_cache:
        del _prompt_cache[session_id]
        logger.info("prompt_cache_cleared_via_api", session_id=session_id)
    else:
        logger.info("prompt_cache_not_found", session_id=session_id)
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/cache", status_code=status.HTTP_204_NO_CONTENT)
async def clear_all_cache():
    """
    Clear all cached prompts.
    
    Removes all prompts from cache. Useful for memory management or testing.
    
    Returns:
        204 No Content on success
        
    Example:
        DELETE /api/prompt/cache
    """
    logger.info("api_clear_all_prompt_cache", cache_size=len(_prompt_cache))
    
    cache_size = len(_prompt_cache)
    _prompt_cache.clear()
    
    logger.info("all_prompt_cache_cleared_via_api", cleared_count=cache_size)
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)


__all__ = ['router']
