"""
Pytest configuration and fixtures.

This module provides common fixtures for testing:
- Test client
- Mock LLM responses
- Sample data

Note: WeasyPrint requires system libraries (libgobject, pango) which may not
be available on all development machines. We mock it globally for tests.
"""

import pytest
from unittest.mock import MagicMock
import sys
import os
from dotenv import load_dotenv

# Mock weasyprint before any imports to avoid system library dependencies
# This must happen before importing app (which imports export_routes → export_service → weasyprint)
sys.modules['weasyprint'] = MagicMock()

from fastapi.testclient import TestClient
from app import app

# Load test environment variables
load_dotenv(".env.test")


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def mock_groq_api_key():
    """Mock Groq API key."""
    return "gsk_test_key_12345"


@pytest.fixture
def mock_openai_api_key():
    """Mock OpenAI API key."""
    return "sk-test-key-12345"


@pytest.fixture
def sample_session_id():
    """Sample session ID."""
    return "test-session-123"


@pytest.fixture
def sample_message():
    """Sample message data."""
    return {
        "session_id": "test-session-123",
        "message": "I want to build a task management app for teams"
    }


@pytest.fixture
def sample_question():
    """Sample question data."""
    return {
        "id": "q-123",
        "category": "functionality",
        "text": "What is the main purpose of your product?",
        "context": [],
        "is_followup": False
    }


@pytest.fixture
def sample_conversation_history():
    """Sample conversation history."""
    return [
        {
            "role": "assistant",
            "content": "What is the main purpose of your product?"
        },
        {
            "role": "user",
            "content": "A task management app for teams"
        },
        {
            "role": "assistant",
            "content": "Who are your target users?"
        },
        {
            "role": "user",
            "content": "Small to medium-sized development teams"
        }
    ]
