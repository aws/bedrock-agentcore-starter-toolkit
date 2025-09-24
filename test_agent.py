#!/usr/bin/env python3
"""Simple test script for the agent"""

from agent_example import agent_invocation

def test_prompts():
    """Test various prompts with the agent"""
    
    test_cases = [
        {"prompt": "Hello, how are you?"},
        {"prompt": "What's the weather like?"},
        {"prompt": "Explain quantum computing in simple terms"},
        {"prompt": "Write a Python function to calculate fibonacci numbers"}
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- Test {i} ---")
        print(f"Input: {test_case}")
        
        try:
            result = agent_invocation(test_case)
            print(f"Output: {result}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    test_prompts()