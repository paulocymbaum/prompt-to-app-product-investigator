"""
Custom exception classes for the Product Investigator Chatbot.

This module defines application-specific exceptions with user-friendly messages
and appropriate HTTP status codes for API responses.
"""

from typing import Any, Dict, Optional
from fastapi import status


class AppException(Exception):
    """Base exception for all application errors."""
    
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        self.user_message = user_message or message
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for JSON response."""
        return {
            "error": self.__class__.__name__,
            "message": self.user_message,
            "details": self.details
        }


class ConfigurationError(AppException):
    """Raised when there's a configuration issue."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
            user_message="Configuration error. Please check your settings."
        )


class APITokenError(AppException):
    """Raised when API token is invalid or missing."""
    
    def __init__(self, provider: str, details: Optional[Dict[str, Any]] = None):
        message = f"Invalid or missing API token for {provider}"
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details or {"provider": provider},
            user_message=f"Please configure a valid API token for {provider} in Settings."
        )


class ModelNotFoundError(AppException):
    """Raised when a requested model doesn't exist."""
    
    def __init__(self, model_id: str, provider: str):
        message = f"Model {model_id} not found for provider {provider}"
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            details={"model_id": model_id, "provider": provider},
            user_message=f"The model '{model_id}' is not available. Please select a different model."
        )


class SessionNotFoundError(AppException):
    """Raised when a session doesn't exist."""
    
    def __init__(self, session_id: str):
        message = f"Session {session_id} not found"
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            details={"session_id": session_id},
            user_message="Session not found. It may have expired or been deleted."
        )


class ConversationError(AppException):
    """Raised when there's an error in conversation processing."""
    
    def __init__(self, message: str, session_id: Optional[str] = None):
        details = {"session_id": session_id} if session_id else {}
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
            user_message="Unable to process your message. Please try again."
        )


class LLMServiceError(AppException):
    """Raised when LLM service fails."""
    
    def __init__(self, provider: str, error_details: str):
        message = f"LLM service error from {provider}: {error_details}"
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details={"provider": provider, "error": error_details},
            user_message=f"The AI service ({provider}) is temporarily unavailable. Please try again in a moment."
        )


class RAGServiceError(AppException):
    """Raised when RAG/vector store operations fail."""
    
    def __init__(self, operation: str, error_details: str):
        message = f"RAG service error during {operation}: {error_details}"
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={"operation": operation, "error": error_details},
            user_message="Error accessing conversation history. Your data is safe, please try again."
        )


class StorageError(AppException):
    """Raised when storage operations fail."""
    
    def __init__(self, operation: str, filepath: Optional[str] = None, error_details: Optional[str] = None):
        message = f"Storage error during {operation}"
        if filepath:
            message += f" on {filepath}"
        if error_details:
            message += f": {error_details}"
        
        details = {"operation": operation}
        if filepath:
            details["filepath"] = filepath
        if error_details:
            details["error"] = error_details
        
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
            user_message="Error saving or loading data. Please try again."
        )


class PromptGenerationError(AppException):
    """Raised when prompt generation fails."""
    
    def __init__(self, session_id: str, error_details: str):
        message = f"Prompt generation failed for session {session_id}: {error_details}"
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={"session_id": session_id, "error": error_details},
            user_message="Unable to generate prompt. Please ensure the investigation is complete."
        )


class GraphGenerationError(AppException):
    """Raised when graph generation fails."""
    
    def __init__(self, session_id: str, error_details: str):
        message = f"Graph generation failed for session {session_id}: {error_details}"
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={"session_id": session_id, "error": error_details},
            user_message="Unable to generate visualization. Your conversation data is intact."
        )


class ExportError(AppException):
    """Raised when export operations fail."""
    
    def __init__(self, format_type: str, session_id: str, error_details: str):
        message = f"Export to {format_type} failed for session {session_id}: {error_details}"
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={"format": format_type, "session_id": session_id, "error": error_details},
            user_message=f"Unable to export as {format_type.upper()}. Please try a different format."
        )


class RateLimitError(AppException):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, provider: str, retry_after: Optional[int] = None):
        message = f"Rate limit exceeded for {provider}"
        details = {"provider": provider}
        if retry_after:
            details["retry_after_seconds"] = retry_after
        
        user_msg = f"Too many requests to {provider}. "
        if retry_after:
            user_msg += f"Please wait {retry_after} seconds before trying again."
        else:
            user_msg += "Please wait a moment before trying again."
        
        super().__init__(
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=details,
            user_message=user_msg
        )


class ValidationError(AppException):
    """Raised when input validation fails."""
    
    def __init__(self, field: str, issue: str):
        message = f"Validation error for {field}: {issue}"
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details={"field": field, "issue": issue},
            user_message=f"Invalid {field}: {issue}"
        )


class InvestigationNotCompleteError(AppException):
    """Raised when attempting operations that require a complete investigation."""
    
    def __init__(self, session_id: str, missing_categories: Optional[list] = None):
        message = f"Investigation not complete for session {session_id}"
        details = {"session_id": session_id}
        if missing_categories:
            details["missing_categories"] = missing_categories
        
        user_msg = "The investigation is not yet complete. "
        if missing_categories:
            user_msg += f"Please answer questions about: {', '.join(missing_categories)}."
        else:
            user_msg += "Please answer more questions before generating the prompt."
        
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
            user_message=user_msg
        )


class TokenLimitExceededError(AppException):
    """Raised when token limit is exceeded."""
    
    def __init__(self, current_tokens: int, max_tokens: int):
        message = f"Token limit exceeded: {current_tokens} > {max_tokens}"
        super().__init__(
            message=message,
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            details={"current_tokens": current_tokens, "max_tokens": max_tokens},
            user_message=f"Your message is too long ({current_tokens} tokens). Maximum is {max_tokens} tokens."
        )
