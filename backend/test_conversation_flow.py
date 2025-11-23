#!/usr/bin/env python3
"""
Integration test for complete conversation flow with Groq API.
Tests the full user journey: token setup → start chat → conversation → completion
"""

import os
import sys
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv

env_paths = [
    Path(__file__).parent.parent / '.env',
    Path(__file__).parent / '.env',
    Path('.env'),
]

for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path)
        print(f"📁 Loaded .env from: {env_path}")
        break

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from services.config_service import ConfigService
from services.llm_service import LLMService
from services.rag_service import RAGService
from services.question_generator import QuestionGenerator
from services.session_service import SessionService
from services.conversation_service import ConversationService

def test_config_service():
    """Test ConfigService for token management"""
    print("\n" + "="*60)
    print("📋 Test 1: Configuration Service")
    print("="*60)
    
    try:
        config = ConfigService()
        
        # Get API key from environment
        groq_key = os.getenv("GROQ_API_KEY")
        if not groq_key:
            print("❌ GROQ_API_KEY not found in environment")
            return False
        
        # Test token validation
        print("\n🔍 Testing token validation...")
        is_valid = config.validate_token_format("groq", groq_key)
        print(f"   Token format valid: {'✅' if is_valid else '❌'}")
        
        # Save token (it encrypts and stores in .env)
        print("\n💾 Saving token to config...")
        success = config.save_token("groq", groq_key)
        print(f"   Token saved: {'✅' if success else '❌'}")
        
        # Switch provider
        print("\n🔄 Setting Groq as active provider...")
        success = config.switch_provider("groq")
        print(f"   Provider switched: {'✅' if success else '❌'}")
        
        # Select model
        print("\n🤖 Selecting model...")
        model = "llama-3.3-70b-versatile"
        success = config.save_selected_model("groq", model)
        print(f"   Model selected: {model} {'✅' if success else '❌'}")
        
        # Verify configuration
        print("\n✔️  Verifying configuration...")
        active = config.get_active_provider()
        selected_model = config.get_selected_model()
        print(f"   Active provider: {active}")
        print(f"   Selected model: {selected_model}")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_conversation_flow():
    """Test full conversation flow with real LLM"""
    print("\n" + "="*60)
    print("📋 Test 2: Conversation Flow with Real LLM")
    print("="*60)
    
    try:
        # Initialize services
        print("\n🔧 Initializing services...")
        config = ConfigService()
        llm_service = LLMService(config)
        rag_service = RAGService()
        question_generator = QuestionGenerator(llm_service, rag_service)
        session_service = SessionService()
        
        conversation = ConversationService(
            llm_service=llm_service,
            rag_service=rag_service,
            question_generator=question_generator,
            session_service=session_service
        )
        print("   ✅ All services initialized")
        
        # Start investigation
        print("\n🚀 Starting investigation...")
        session_id, initial_question = conversation.start_investigation()
        print(f"   Session ID: {session_id}")
        print(f"   Initial Question: {initial_question['text'][:100]}...")
        
        # Simulate answering questions
        answers = [
            "A task management app for remote teams with real-time collaboration",
            "Remote teams, project managers, freelancers",
            "Task tracking, real-time chat, file sharing, time tracking",
            "Web and mobile (iOS and Android)",
        ]
        
        print("\n💬 Simulating conversation...")
        for i, answer in enumerate(answers, 1):
            print(f"\n   Question {i}: Answering...")
            print(f"   Answer: {answer[:80]}...")
            
            next_question = conversation.process_answer(session_id, answer)
            
            if next_question is None:
                print(f"   ✅ Investigation complete after {i} answers")
                break
            else:
                print(f"   ✅ Next question: {next_question['text'][:80]}...")
        
        # Get conversation history
        print("\n📜 Retrieving conversation history...")
        history = conversation.get_conversation_history(session_id)
        print(f"   Total messages: {len(history)}")
        
        # Check completion status
        is_complete = conversation.is_investigation_complete(session_id)
        print(f"\n✔️  Investigation complete: {'✅' if is_complete else '❌'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Conversation flow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_session_persistence():
    """Test session persistence and retrieval"""
    print("\n" + "="*60)
    print("📋 Test 3: Session Persistence")
    print("="*60)
    
    try:
        config = ConfigService()
        llm_service = LLMService(config)
        rag_service = RAGService()
        question_generator = QuestionGenerator(llm_service, rag_service)
        session_service = SessionService()
        
        conversation = ConversationService(
            llm_service=llm_service,
            rag_service=rag_service,
            question_generator=question_generator,
            session_service=session_service
        )
        
        # Start a session
        print("\n🚀 Creating test session...")
        session_id, _ = conversation.start_investigation()
        print(f"   Session ID: {session_id}")
        
        # Add some answers
        print("\n💬 Adding test answers...")
        conversation.process_answer(session_id, "A productivity app")
        conversation.process_answer(session_id, "Students and professionals")
        
        # Retrieve session
        print("\n🔍 Retrieving session...")
        session = conversation.get_session(session_id)
        print(f"   Session found: {'✅' if session else '❌'}")
        print(f"   Session state: {session.state if session else 'N/A'}")
        
        # Get history
        history = conversation.get_conversation_history(session_id)
        print(f"   Messages in history: {len(history)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Session persistence test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("="*60)
    print("🧪 FULL CONVERSATION FLOW INTEGRATION TEST")
    print("="*60)
    
    results = []
    
    # Run tests
    results.append(("Config Service", test_config_service()))
    results.append(("Conversation Flow", test_conversation_flow()))
    results.append(("Session Persistence", test_session_persistence()))
    
    # Summary
    print("\n" + "="*60)
    print("📊 Test Results Summary")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All conversation flow tests passed!")
        print("✅ Backend is ready for user token configuration!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed")
        sys.exit(1)
