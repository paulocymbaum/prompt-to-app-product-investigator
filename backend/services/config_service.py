"""
Configuration Service for managing API tokens and provider settings.

This service handles:
- API token encryption/decryption
- Provider selection (Groq/OpenAI)
- Token format validation
- Persistent storage in .env file

SOLID Principles:
- Single Responsibility: Manages only configuration
- Open/Closed: Extensible for new providers
- Dependency Inversion: Uses abstract encryption interface
"""

from cryptography.fernet import Fernet
import os
import re
from typing import Optional
from dotenv import load_dotenv, set_key, find_dotenv
import structlog

logger = structlog.get_logger()


class ConfigService:
    """
    Service for managing API configuration including token storage and provider selection.
    
    Implements secure token storage with encryption and provides validation
    for different provider token formats.
    """
    
    def __init__(self, env_file: str = ".env"):
        """
        Initialize the configuration service.
        
        Args:
            env_file: Path to the .env file for persistent storage
        """
        self.env_file = env_file
        self.encryption_key = self._get_or_create_key()
        self.cipher = Fernet(self.encryption_key)
        
        # Load dotenv with override to ensure we use the specified file
        load_dotenv(self.env_file, override=True)
        
        logger.info("config_service_initialized", env_file=env_file)
    
    def _get_or_create_key(self) -> bytes:
        """
        Get existing encryption key or create a new one.
        
        Returns:
            Encryption key as bytes
        """
        key_file = ".encryption_key"
        
        if os.path.exists(key_file):
            with open(key_file, "rb") as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, "wb") as f:
                f.write(key)
            logger.info("encryption_key_created")
            return key
    
    def save_token(self, provider: str, token: str) -> bool:
        """
        Encrypt and save API token to .env file.
        
        Args:
            provider: Provider name ('groq' or 'openai')
            token: API token to encrypt and save
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            ValueError: If provider is not supported
        """
        if provider not in ["groq", "openai"]:
            logger.error("unsupported_provider", provider=provider)
            raise ValueError(f"Unsupported provider: {provider}")
        
        if not self.validate_token_format(provider, token):
            logger.error("invalid_token_format", provider=provider)
            raise ValueError(f"Invalid token format for {provider}")
        
        try:
            # Encrypt the token
            encrypted_token = self.cipher.encrypt(token.encode()).decode()
            
            # Determine environment variable name
            env_var = f"{provider.upper()}_API_KEY"
            
            # Use the configured env_file
            env_path = self.env_file
            
            # Ensure the file exists
            if not os.path.exists(env_path):
                open(env_path, 'a').close()
            
            # Save to .env file
            set_key(env_path, env_var, encrypted_token)
            
            # Also update active provider
            set_key(env_path, "ACTIVE_PROVIDER", provider)
            
            # Reload environment to pick up changes
            load_dotenv(env_path, override=True)
            
            logger.info("token_saved", provider=provider, env_var=env_var)
            return True
            
        except Exception as e:
            logger.error("token_save_failed", provider=provider, error=str(e))
            return False
    
    def get_token(self, provider: str) -> Optional[str]:
        """
        Decrypt and return API token from environment.
        
        Args:
            provider: Provider name ('groq' or 'openai')
            
        Returns:
            Decrypted token string or None if not found
        """
        if provider not in ["groq", "openai"]:
            logger.error("unsupported_provider", provider=provider)
            return None
        
        try:
            env_var = f"{provider.upper()}_API_KEY"
            encrypted_token = os.getenv(env_var)
            
            if not encrypted_token:
                logger.warning("token_not_found", provider=provider)
                return None
            
            # Try to decrypt (if it's encrypted)
            try:
                decrypted_token = self.cipher.decrypt(encrypted_token.encode()).decode()
                logger.info("token_retrieved", provider=provider)
                return decrypted_token
            except Exception:
                # Token might not be encrypted (for backwards compatibility)
                logger.info("token_retrieved_unencrypted", provider=provider)
                return encrypted_token
                
        except Exception as e:
            logger.error("token_retrieval_failed", provider=provider, error=str(e))
            return None
    
    def validate_token_format(self, provider: str, token: str) -> bool:
        """
        Validate token format for the specified provider.
        
        Args:
            provider: Provider name ('groq' or 'openai')
            token: Token to validate
            
        Returns:
            True if token format is valid, False otherwise
        """
        if not token or not token.strip():
            logger.warning("empty_token_validation", provider=provider)
            return False
        
        token = token.strip()
        
        if provider == "groq":
            # Groq tokens typically start with 'gsk_'
            if token.startswith("gsk_") and len(token) > 20:
                return True
            logger.warning("invalid_groq_token_format", token_prefix=token[:4])
            return False
            
        elif provider == "openai":
            # OpenAI tokens start with 'sk-' (or 'sk-proj-' for project keys)
            if (token.startswith("sk-") or token.startswith("sk-proj-")) and len(token) > 20:
                return True
            logger.warning("invalid_openai_token_format", token_prefix=token[:7])
            return False
        
        logger.error("unsupported_provider_validation", provider=provider)
        return False
    
    def switch_provider(self, new_provider: str) -> bool:
        """
        Switch the active LLM provider.
        
        Args:
            new_provider: New provider name ('groq' or 'openai')
            
        Returns:
            True if successful, False otherwise
        """
        if new_provider not in ["groq", "openai"]:
            logger.error("invalid_provider_switch", provider=new_provider)
            return False
        
        try:
            # Check if token exists for the new provider
            token = self.get_token(new_provider)
            if not token:
                logger.error("provider_switch_no_token", provider=new_provider)
                return False
            
            # Update active provider
            env_path = self.env_file
            
            # Ensure the file exists
            if not os.path.exists(env_path):
                open(env_path, 'a').close()
            
            set_key(env_path, "ACTIVE_PROVIDER", new_provider)
            
            # Reload environment to pick up changes
            load_dotenv(env_path, override=True)
            
            logger.info("provider_switched", new_provider=new_provider)
            return True
            
        except Exception as e:
            logger.error("provider_switch_failed", provider=new_provider, error=str(e))
            return False
    
    def get_active_provider(self) -> Optional[str]:
        """
        Get the currently active provider.
        
        Returns:
            Active provider name or None
        """
        provider = os.getenv("ACTIVE_PROVIDER", os.getenv("DEFAULT_PROVIDER", "groq"))
        logger.info("active_provider_retrieved", provider=provider)
        return provider
    
    def get_selected_model(self, provider: Optional[str] = None) -> Optional[str]:
        """
        Get the selected model for a provider.
        
        Args:
            provider: Provider name, or None to use active provider
            
        Returns:
            Model ID or None
        """
        if not provider:
            provider = self.get_active_provider()
        
        env_var = f"{provider.upper()}_SELECTED_MODEL"
        model = os.getenv(env_var)
        
        if model:
            logger.info("selected_model_retrieved", provider=provider, model=model)
        else:
            logger.warning("no_model_selected", provider=provider)
        
        return model
    
    def save_selected_model(self, provider: str, model_id: str) -> bool:
        """
        Save the selected model for a provider.
        
        Args:
            provider: Provider name ('groq' or 'openai')
            model_id: Model identifier
            
        Returns:
            True if successful, False otherwise
        """
        if provider not in ["groq", "openai"]:
            logger.error("invalid_provider_model_save", provider=provider)
            return False
        
        try:
            env_var = f"{provider.upper()}_SELECTED_MODEL"
            env_path = self.env_file
            
            # Ensure the file exists
            if not os.path.exists(env_path):
                open(env_path, 'a').close()
            
            set_key(env_path, env_var, model_id)
            
            # Reload environment to pick up changes
            load_dotenv(env_path, override=True)
            
            logger.info("model_saved", provider=provider, model_id=model_id)
            return True
            
        except Exception as e:
            logger.error("model_save_failed", provider=provider, error=str(e))
            return False
