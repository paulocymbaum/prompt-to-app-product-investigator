"""Simplified tests for Configuration API Routes focusing on key functionality"""

import pytest
from fastapi.testclient import TestClient
from app import app
from services.config_service import ConfigService
from routes.config_routes import get_config_service

client = TestClient(app)

class TestConfigRoutesSimple:
    """Simplified test suite for configuration API routes"""
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Cleanup after each test"""
        yield
        app.dependency_overrides.clear()
    
    @pytest.fixture
    def config_service(self, tmp_path):
        """Create ConfigService and override dependency"""
        env_file = tmp_path / ".env"
        env_file.touch()
        service = ConfigService(str(env_file))
        app.dependency_overrides[get_config_service] = lambda: service
        return service
    
    def test_save_groq_token(self, config_service):
        """Test saving Groq token"""
        response = client.post(
            "/api/config/token",
            json={"provider": "groq", "token": "gsk_" + "a" * 40}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "success"
    
    def test_save_openai_token(self, config_service):
        """Test saving OpenAI token"""
        response = client.post(
            "/api/config/token",
            json={"provider": "openai", "token": "sk-" + "b" * 45}
        )
        assert response.status_code == 200
    
    def test_invalid_token_format(self, config_service):
        """Test invalid token format"""
        response = client.post(
            "/api/config/token",
            json={"provider": "groq", "token": "invalid"}
        )
        # Either 400 (invalid format) or 422 (validation error) is acceptable
        assert response.status_code in [400, 422]
    
    def test_get_status(self, config_service):
        """Test getting configuration status"""
        response = client.get("/api/config/status")
        assert response.status_code == 200
        data = response.json()
        assert "has_groq_token" in data
        assert "has_openai_token" in data
    
    def test_delete_token(self, config_service):
        """Test deleting a token"""
        # First save a token
        client.post("/api/config/token", json={"provider": "groq", "token": "gsk_" + "a" * 40})
        # Then delete it
        response = client.delete("/api/config/token/groq")
        assert response.status_code == 204
    
    def test_invalid_provider(self, config_service):
        """Test with invalid provider"""
        response = client.post(
            "/api/config/token",
            json={"provider": "invalid", "token": "test"}
        )
        assert response.status_code == 422
