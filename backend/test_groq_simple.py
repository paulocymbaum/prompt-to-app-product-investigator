#!/usr/bin/env python3
"""
Simple standalone integration test for Groq API
This test doesn't require the full app infrastructure.
"""

import os
import sys
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv

# Try multiple locations for .env
env_paths = [
    Path(__file__).parent.parent / '.env',  # project root
    Path(__file__).parent / '.env',  # backend dir
    Path('.env'),  # current dir
]

for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path)
        print(f"📁 Loaded .env from: {env_path}")
        break

def test_groq_connection():
    """Test basic Groq API connection"""
    from groq import Groq
    
    api_key = os.getenv("GROQ_API_KEY")
    
    if not api_key:
        print("❌ GROQ_API_KEY not found in environment")
        return False
    
    print(f"✅ GROQ_API_KEY found (starts with: {api_key[:8]}...)")
    
    try:
        client = Groq(api_key=api_key)
        
        # Test a simple completion
        print("\n🔄 Testing Groq API with simple prompt...")
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": "What is 2+2? Answer with just the number.",
                }
            ],
            model="llama-3.3-70b-versatile",
            max_tokens=10,
        )
        
        response = chat_completion.choices[0].message.content
        print(f"✅ Groq API Response: {response}")
        
        # Check if response contains "4"
        if "4" in response:
            print("✅ Response is correct!")
            return True
        else:
            print(f"⚠️  Unexpected response: {response}")
            return True  # Still a success - API works
            
    except Exception as e:
        print(f"❌ Groq API Error: {e}")
        return False

def test_groq_models_list():
    """Test fetching available models from Groq"""
    from groq import Groq
    
    api_key = os.getenv("GROQ_API_KEY")
    
    if not api_key:
        print("❌ GROQ_API_KEY not found")
        return False
    
    try:
        client = Groq(api_key=api_key)
        
        print("\n🔄 Fetching available Groq models...")
        models = client.models.list()
        
        model_count = len(models.data)
        print(f"✅ Found {model_count} available models:")
        
        for model in models.data[:5]:  # Show first 5
            print(f"   - {model.id}")
        
        if model_count > 5:
            print(f"   ... and {model_count - 5} more")
        
        return True
        
    except Exception as e:
        print(f"❌ Error fetching models: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 Groq API Integration Test")
    print("=" * 60)
    
    results = []
    
    # Test 1: Basic connection
    print("\n📋 Test 1: Basic API Connection")
    print("-" * 60)
    results.append(("Basic Connection", test_groq_connection()))
    
    # Test 2: Models list
    print("\n📋 Test 2: Fetch Models List")
    print("-" * 60)
    results.append(("Models List", test_groq_models_list()))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Results Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed")
        sys.exit(1)
