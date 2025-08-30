#!/usr/bin/env python3
"""
Test script to verify the Unicode fix for _handle_aws_response function.
This script can be run independently to test the fix.
"""

import json
import sys
import os

# Add the src directory to the path so we can import the module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from bedrock_agentcore_starter_toolkit.services.runtime import _handle_aws_response


def test_unicode_fix():
    """Test the Unicode fix with various multibyte characters."""
    
    print("Testing Unicode fix for _handle_aws_response...")
    
    # Test cases with different languages
    test_cases = [
        ("Chinese", "你好世界"),
        ("Japanese", "こんにちは"),
        ("Korean", "안녕하세요"),
        ("Arabic", "مرحبا بالعالم"),
        ("Russian", "Привет мир"),
        ("Emoji", "Hello 👋 World 🌍"),
        ("Mixed", "Hello 你好 こんにちは 안녕하세요 🌍")
    ]
    
    all_passed = True
    
    for language, text in test_cases:
        print(f"\nTesting {language}: {text}")
        
        # Test 1: Plain text as bytes
        text_bytes = text.encode('utf-8')
        response = {
            "contentType": "application/json",
            "response": [text_bytes]
        }
        
        result = _handle_aws_response(response)
        
        if result["response"][0] == text:
            print(f"  ✅ Plain text: PASSED")
        else:
            print(f"  ❌ Plain text: FAILED - Expected '{text}', got '{result['response'][0]}'")
            all_passed = False
        
        # Test 2: JSON with Unicode as bytes
        json_data = {"message": text, "status": "success"}
        json_bytes = json.dumps(json_data, ensure_ascii=False).encode('utf-8')
        response = {
            "contentType": "application/json", 
            "response": [json_bytes]
        }
        
        result = _handle_aws_response(response)
        
        if result["response"][0] == json_data:
            print(f"  ✅ JSON: PASSED")
        else:
            print(f"  ❌ JSON: FAILED - Expected {json_data}, got {result['response'][0]}")
            all_passed = False
    
    # Test backward compatibility
    print(f"\nTesting backward compatibility...")
    
    response = {
        "contentType": "application/json",
        "response": [
            "regular string",
            {"existing": "dict"},
            ["existing", "list"]
        ]
    }
    
    result = _handle_aws_response(response)
    expected = ["regular string", {"existing": "dict"}, ["existing", "list"]]
    
    if result["response"] == expected:
        print(f"  ✅ Backward compatibility: PASSED")
    else:
        print(f"  ❌ Backward compatibility: FAILED")
        all_passed = False
    
    # Test mixed types
    print(f"\nTesting mixed event types...")
    
    chinese_bytes = "你好".encode('utf-8')
    json_bytes = '{"key": "值"}'.encode('utf-8')
    
    response = {
        "contentType": "application/json",
        "response": [chinese_bytes, json_bytes, "string", {"dict": "value"}]
    }
    
    result = _handle_aws_response(response)
    expected = ["你好", {"key": "值"}, "string", {"dict": "value"}]
    
    if result["response"] == expected:
        print(f"  ✅ Mixed types: PASSED")
    else:
        print(f"  ❌ Mixed types: FAILED")
        print(f"    Expected: {expected}")
        print(f"    Got: {result['response']}")
        all_passed = False
    
    print(f"\n{'='*50}")
    if all_passed:
        print("🎉 All tests PASSED! Unicode fix is working correctly.")
        return 0
    else:
        print("❌ Some tests FAILED. Please check the implementation.")
        return 1


if __name__ == "__main__":
    exit_code = test_unicode_fix()
    sys.exit(exit_code)