#!/usr/bin/env python3
"""Interactive agent testing"""

from agent_example import agent_invocation

def interactive_test():
    """Interactive testing loop"""
    print("🤖 Agent Test - Type 'quit' to exit")
    
    while True:
        user_input = input("\nYour prompt: ")
        
        if user_input.lower() in ['quit', 'exit', 'q']:
            print("Goodbye!")
            break
            
        try:
            payload = {"prompt": user_input}
            response = agent_invocation(payload)
            print(f"\n🤖 Agent: {response}")
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    interactive_test()