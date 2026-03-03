"""Test script to verify Anthropic API and available models."""

import os
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

api_key = os.getenv("ANTHROPIC_API_KEY")

if not api_key:
    print("❌ ANTHROPIC_API_KEY not found in .env file")
    print("Please add your API key to .env file")
    exit(1)

print(f"✓ API key found: {api_key[:20]}...")

# Test different model names
models_to_test = [
    "claude-3-5-sonnet-20241022",
    "claude-3-5-sonnet-20240620",
    "claude-3-opus-20240229",
    "claude-3-sonnet-20240229",
    "claude-3-haiku-20240307",
]

client = Anthropic(api_key=api_key)

print("\nTesting models...\n")

for model in models_to_test:
    try:
        response = client.messages.create(
            model=model,
            max_tokens=10,
            messages=[{"role": "user", "content": "Hi"}]
        )
        print(f"✓ {model} - WORKS")
        print(f"  Response: {response.content[0].text}")
        break  # Stop after first working model
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg or "not_found" in error_msg:
            print(f"✗ {model} - NOT FOUND")
        elif "401" in error_msg or "authentication" in error_msg.lower():
            print(f"✗ {model} - AUTH ERROR (check API key)")
        else:
            print(f"✗ {model} - ERROR: {error_msg[:100]}")

print("\n" + "="*50)
print("Recommendation: Use the first model that works above")
print("Update config.yaml with that model name")
