"""
LLM provider-related data models.

This module defines Pydantic models for:
- Provider: LLM provider configuration
- Model: LLM model information
- Prompt: Generated prompt data
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime
import uuid


class Provider(BaseModel):
    """LLM provider configuration."""
    name: str  # "groq" or "openai"
    api_key: str
    base_url: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "name": "groq",
                "api_key": "gsk_xxx",
                "base_url": "https://api.groq.com/openai/v1"
            }
        }


class Model(BaseModel):
    """LLM model information."""
    id: str
    name: str
    provider: str
    context_window: int
    capabilities: List[str] = Field(default_factory=list)
    cost_per_token: Optional[float] = None
    metadata: Dict = Field(default_factory=dict)

    class Config:
        json_schema_extra = {
            "example": {
                "id": "llama2-70b-4096",
                "name": "LLaMA2-70b-chat",
                "provider": "groq",
                "context_window": 4096,
                "capabilities": ["chat", "completion"],
                "cost_per_token": 0.0001,
                "metadata": {}
            }
        }


class Prompt(BaseModel):
    """Generated prompt data."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    content: str
    version: int = 1
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict = Field(default_factory=dict)

    class Config:
        json_schema_extra = {
            "example": {
                "id": "prompt-123",
                "session_id": "session-456",
                "content": "You are an expert developer...",
                "version": 1,
                "generated_at": "2024-01-01T12:00:00Z",
                "metadata": {"word_count": 500}
            }
        }
