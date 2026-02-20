# HalluciGuard - AI Hallucination Detection Middleware
# Copyright (C) 2026 HalluciGuard Contributors

import os
from halluciGuard import Guard, GuardConfig

def test_openai_connection_path():
    print("Testing OpenAI connection path...")
    try:
        from openai import OpenAI
        client = OpenAI(api_key="sk-dummy-key")
        guard = Guard(provider="openai", client=client)
        print("✅ OpenAI SDK initialized.")
        try:
            guard.chat(model="gpt-4o", messages=[{"role": "user", "content": "test"}])
        except Exception as e:
            if "Authentication" in str(e) or "401" in str(e) or "Invalid API key" in str(e):
                print(f"✅ OpenAI API connection path verified (Auth Error as expected): {str(e)[:50]}...")
            else:
                print(f"❌ OpenAI API connection path failed: {e}")
    except ImportError:
        print("❌ OpenAI SDK not installed.")

def test_anthropic_connection_path():
    print("\nTesting Anthropic connection path...")
    try:
        import anthropic
        client = anthropic.Anthropic(api_key="ant-dummy-key")
        guard = Guard(provider="anthropic", client=client)
        print("✅ Anthropic SDK initialized.")
        try:
            guard.chat(model="claude-sonnet-4-6", messages=[{"role": "user", "content": "test"}])
        except Exception as e:
            if "Authentication" in str(e) or "401" in str(e) or "invalid x-api-key" in str(e):
                print(f"✅ Anthropic API connection path verified (Auth Error as expected): {str(e)[:50]}...")
            else:
                print(f"❌ Anthropic API connection path failed: {e}")
    except ImportError:
        print("❌ Anthropic SDK not installed.")

def test_google_connection_path():
    print("\nTesting Google Gemini connection path...")
    try:
        from google import genai
        guard = Guard(provider="google", api_key="dummy-gemini-key")
        print("✅ Google Gemini SDK configured.")
        try:
            guard.chat(model="gemini-3.1-pro", messages=[{"role": "user", "content": "test"}])
        except Exception as e:
            if "INVALID_ARGUMENT" in str(e) or "401" in str(e) or "400" in str(e) or "API key" in str(e):
                print(f"✅ Google API connection path verified (Auth/API Error as expected): {str(e)[:50]}...")
            else:
                print(f"❌ Google API connection path failed: {e}")
    except ImportError:
        print("❌ Google Gemini SDK not installed.")

if __name__ == "__main__":
    test_openai_connection_path()
    test_anthropic_connection_path()
    test_google_connection_path()
