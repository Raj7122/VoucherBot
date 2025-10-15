#!/usr/bin/env python3

import gradio as gr
import requests
import time

# Gradio testing utilities
def test_gradio_app():
    """Test the Gradio app functionality using Gradio's testing API."""

    print("🚀 Starting Gradio App Tests...")

    # Test 1: Basic App Accessibility
    try:
        response = requests.get("http://localhost:7860")
        if response.status_code == 200:
            print("✅ Test 1 PASSED: Gradio app is accessible")
        else:
            print(f"❌ Test 1 FAILED: App not accessible (status: {response.status_code})")
            return
    except Exception as e:
        print(f"❌ Test 1 FAILED: Could not connect to app - {str(e)}")
        return

    # Test 2: Initialize Gradio Client for Testing
    try:
        from gradio_client import Client
        client = Client("http://localhost:7860/")
        print("✅ Test 2 PASSED: Gradio client initialized")
    except Exception as e:
        print(f"❌ Test 2 FAILED: Could not initialize Gradio client - {str(e)}")
        return

    # Test 3: Basic Chatbot Response (English)
    try:
        result = client.predict(
            "Hello, I need help finding housing with Section 8 voucher",
            [],  # history
            {"preferences": {"language": "en"}},  # current_state (app_state)
            False,  # strict_mode
            api_name="/handle_chat_message"
        )
        print("✅ Test 3 PASSED: Basic chatbot response received")
        print(f"   Response: {result[0][:100]}...")
    except Exception as e:
        print(f"❌ Test 3 FAILED: Basic chatbot test failed - {str(e)}")

    # Test 4: Housing Search (Simulated)
    try:
        result = client.predict(
            "Search for 2 bedroom apartments in Brooklyn under $2000",
            [],
            {"preferences": {"language": "en"}},
            False,
            api_name="/handle_chat_message"
        )
        print("✅ Test 4 PASSED: Housing search query processed")
        print(f"   Response: {result[0][:100]}...")
    except Exception as e:
        print(f"❌ Test 4 FAILED: Housing search test failed - {str(e)}")

    # Test 5: Violation Checking
    try:
        result = client.predict(
            "Check building violations for 123 Main St, Brooklyn",
            [],
            {"preferences": {"language": "en"}},
            False,
            api_name="/handle_chat_message"
        )
        print("✅ Test 5 PASSED: Violation checking query processed")
        print(f"   Response: {result[0][:100]}...")
    except Exception as e:
        print(f"❌ Test 5 FAILED: Violation checking test failed - {str(e)}")

    # Test 6: Multilingual Support (Spanish)
    try:
        result = client.predict(
            "Hola, necesito ayuda con vivienda",
            [],
            {"preferences": {"language": "es"}},
            False,
            api_name="/handle_chat_message"
        )
        print("✅ Test 6 PASSED: Spanish language support")
        print(f"   Response: {result[0][:100]}...")
    except Exception as e:
        print(f"❌ Test 6 FAILED: Spanish support test failed - {str(e)}")

    # Test 7: Email Generation
    try:
        result = client.predict(
            "Draft an email to a landlord about my Section 8 voucher",
            [],
            {"preferences": {"language": "en"}},
            False,
            api_name="/handle_chat_message"
        )
        print("✅ Test 7 PASSED: Email generation query processed")
        print(f"   Response: {result[0][:100]}...")
    except Exception as e:
        print(f"❌ Test 7 FAILED: Email generation test failed - {str(e)}")

    print("🏁 Gradio App Testing Complete!")

if __name__ == "__main__":
    test_gradio_app()
