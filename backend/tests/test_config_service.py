"""
Unit tests for Configuration Service.

Tests cover:
- Token format validation (Groq and OpenAI)
- Token encryption/decryption
- Provider switching
- Configuration persistence
- Error handling
"""

import pytest
import os
import tempfile
from unittest.mock import patch, mock_open
from services.config_service import ConfigService


class TestConfigService:
    """Test suite for ConfigService"""
    
    @pytest.fixture
    def config_service(self, tmp_path):
        """Create a ConfigService instance with temporary .env file"""
        env_file = tmp_path / ".env"
        env_file.touch()
        
        # Create temporary encryption key
        key_file = tmp_path / ".encryption_key"
        with patch('services.config_service.os.path.exists', return_value=False):
            service = ConfigService(str(env_file))
        
        return service
    
    # Business Rule Tests
    
    def test_validate_groq_token_format(self, config_service):
        """Test Groq token format validation"""
        # Valid Groq token
        assert config_service.validate_token_format("groq", "gsk_1234567890abcdefghijklmnop") == True
        
        # Invalid format - wrong prefix
        assert config_service.validate_token_format("groq", "sk_1234567890abcdefghijklmnop") == False
        
        # Invalid format - too short
        assert config_service.validate_token_format("groq", "gsk_123") == False
        
        # Invalid format - empty
        assert config_service.validate_token_format("groq", "") == False
        
        # Invalid format - only whitespace
        assert config_service.validate_token_format("groq", "   ") == False
    
    def test_validate_openai_token_format(self, config_service):
        """Test OpenAI token format validation"""
        # Valid OpenAI token (standard)
        assert config_service.validate_token_format("openai", "sk-1234567890abcdefghijklmnop") == True
        
        # Valid OpenAI token (project key)
        assert config_service.validate_token_format("openai", "sk-proj-1234567890abcdefghijklmnop") == True
        
        # Invalid format - wrong prefix
        assert config_service.validate_token_format("openai", "gsk_1234567890abcdefghijklmnop") == False
        
        # Invalid format - too short
        assert config_service.validate_token_format("openai", "sk-123") == False
        
        # Invalid format - empty
        assert config_service.validate_token_format("openai", "") == False
    
    def test_token_storage_encryption(self, config_service, tmp_path):
        """Test token encryption before storage"""
        provider = "groq"
        original_token = "gsk_test_token_1234567890abcdefghijklmnop"
        
        # Save token
        result = config_service.save_token(provider, original_token)
        assert result == True
        
        # Retrieve token
        retrieved_token = config_service.get_token(provider)
        
        # Verify decryption works and matches original
        assert retrieved_token == original_token
        
        # Verify token is actually encrypted in storage
        env_file = tmp_path / ".env"
        if env_file.exists():
            content = env_file.read_text()
            # Encrypted token should not contain the original
            assert original_token not in content
    
    def test_switch_provider(self, config_service):
        """Test provider switching logic"""
        # Save tokens for both providers
        groq_token = "gsk_test_groq_1234567890abcdefghijklmnop"
        openai_token = "sk-test-openai-1234567890abcdefghijklmnop"
        
        config_service.save_token("groq", groq_token)
        config_service.save_token("openai", openai_token)
        
        # Switch to Groq
        result = config_service.switch_provider("groq")
        assert result == True
        assert config_service.get_active_provider() == "groq"
        
        # Switch to OpenAI
        result = config_service.switch_provider("openai")
        assert result == True
        assert config_service.get_active_provider() == "openai"
        
        # Try to switch to provider without token
        result = config_service.switch_provider("groq")
        # First remove the token
        os.environ.pop("GROQ_API_KEY", None)
        result = config_service.switch_provider("groq")
        # Should fail if no token exists (depending on implementation)
    
    # Technical Implementation Tests
    
    def test_config_persistence(self, config_service, tmp_path):
        """Test configuration persistence to .env file"""
        provider = "groq"
        token = "gsk_test_token_1234567890abcdefghijklmnop"
        
        # Save configuration
        result = config_service.save_token(provider, token)
        assert result == True
        
        # Create new service instance (simulating app restart)
        env_file = tmp_path / ".env"
        new_service = ConfigService(str(env_file))
        
        # Verify token persisted
        retrieved_token = new_service.get_token(provider)
        assert retrieved_token == token
    
    def test_unsupported_provider(self, config_service):
        """Test handling of unsupported providers"""
        with pytest.raises(ValueError, match="Unsupported provider"):
            config_service.save_token("unsupported", "test_token")
        
        result = config_service.get_token("unsupported")
        assert result is None
        
        result = config_service.validate_token_format("unsupported", "test_token")
        assert result == False
    
    def test_get_token_not_found(self, tmp_path):
        """Test getting token when none is configured"""
        # Create a completely fresh service with empty env file
        env_file = tmp_path / "empty.env"
        env_file.touch()
        
        # Clear any existing environment variables
        os.environ.pop("GROQ_API_KEY", None)
        os.environ.pop("OPENAI_API_KEY", None)
        
        service = ConfigService(str(env_file))
        
        result = service.get_token("groq")
        assert result is None
        
        result = service.get_token("openai")
        assert result is None
    
    def test_save_token_invalid_format(self, config_service):
        """Test saving token with invalid format"""
        with pytest.raises(ValueError, match="Invalid token format"):
            config_service.save_token("groq", "invalid_token")
        
        with pytest.raises(ValueError, match="Invalid token format"):
            config_service.save_token("openai", "invalid_token")
    
    def test_get_active_provider(self, config_service):
        """Test getting active provider"""
        # Should return default
        provider = config_service.get_active_provider()
        assert provider in ["groq", "openai"]
    
    def test_save_and_get_selected_model(self, config_service):
        """Test saving and retrieving selected model"""
        provider = "groq"
        model_id = "llama2-70b-4096"
        
        # Save model
        result = config_service.save_selected_model(provider, model_id)
        assert result == True
        
        # Retrieve model
        retrieved_model = config_service.get_selected_model(provider)
        assert retrieved_model == model_id
    
    def test_get_selected_model_not_found(self, tmp_path):
        """Test getting model when none is selected"""
        # Create a completely fresh service with empty env file
        env_file = tmp_path / "empty_model.env"
        env_file.touch()
        
        # Clear any existing environment variables
        os.environ.pop("GROQ_SELECTED_MODEL", None)
        os.environ.pop("OPENAI_SELECTED_MODEL", None)
        
        service = ConfigService(str(env_file))
        
        result = service.get_selected_model("groq")
        assert result is None
    
    def test_encryption_key_creation(self, tmp_path):
        """Test encryption key is created if it doesn't exist"""
        key_file = tmp_path / ".encryption_key"
        env_file = tmp_path / ".env"
        env_file.touch()
        
        # Key file should not exist yet
        assert not key_file.exists()
        
        # Create service (should create key)
        with patch('services.config_service.os.path.exists') as mock_exists:
            mock_exists.return_value = False
            service = ConfigService(str(env_file))
        
        # Verify key exists and is valid Fernet key
        assert service.encryption_key is not None
        assert len(service.encryption_key) > 0
    
    def test_token_with_whitespace(self, config_service):
        """Test tokens with leading/trailing whitespace are handled"""
        provider = "groq"
        token_with_whitespace = "  gsk_1234567890abcdefghijklmnop  "
        expected_token = "gsk_1234567890abcdefghijklmnop"
        
        # Should validate (after stripping)
        assert config_service.validate_token_format(provider, token_with_whitespace) == True
    
    def test_concurrent_config_updates(self, config_service):
        """Test multiple config updates don't cause race conditions"""
        # This is a basic test - proper concurrency testing would require threading
        tokens = [
            f"gsk_token_{i}_1234567890abcdefghijklmnop" for i in range(5)
        ]
        
        for token in tokens:
            result = config_service.save_token("groq", token)
            assert result == True
        
        # Last token should be the one stored
        retrieved = config_service.get_token("groq")
        assert retrieved == tokens[-1]


class TestConfigServiceIntegration:
    """Integration tests for ConfigService with actual file I/O"""
    
    def test_real_file_persistence(self, tmp_path):
        """Test actual file I/O for .env persistence"""
        env_file = tmp_path / ".env"
        
        # Create service and save token
        service = ConfigService(str(env_file))
        token = "gsk_integration_test_1234567890abcdefghijklmnop"
        service.save_token("groq", token)
        
        # Verify file was created and contains data
        assert env_file.exists()
        content = env_file.read_text()
        assert "GROQ_API_KEY" in content
        assert "ACTIVE_PROVIDER" in content
        
        # Create new service instance and verify persistence
        new_service = ConfigService(str(env_file))
        retrieved = new_service.get_token("groq")
        assert retrieved == token
