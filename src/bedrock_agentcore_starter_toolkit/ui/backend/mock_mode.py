"""Mock mode for testing the UI without a real agent."""

import random
import time
from datetime import datetime, timezone
from typing import Optional

# Mock responses for testing
MOCK_RESPONSES = [
    "Hello! I'm a mock agent. I can help you test the UI without needing a real agent configuration.",
    "This is a simulated response. In production, I would be powered by Amazon Bedrock AgentCore.",
    "I'm processing your request... Here's a mock response with some "
    "**markdown** formatting!\n\n- Point 1\n- Point 2\n- Point 3",
    "Let me help you with that. This is a longer response to test how the UI "
    "handles multi-line content.\n\nI can include:\n1. Numbered lists\n"
    "2. **Bold text**\n3. *Italic text*\n\nAnd even code blocks:\n"
    "```python\ndef hello():\n    print('Hello, World!')\n```",
    "Great question! In mock mode, I generate random responses to help you test the UI functionality.",
    "🎉 The UI is working perfectly! This mock agent helps you develop and test without needing AWS credentials.",
]


class MockAgentService:
    """Mock service that simulates agent behavior."""

    def __init__(self):
        """Initialize the mock agent service."""
        self.session_id = self._generate_session_id()

    @staticmethod
    def _generate_session_id() -> str:
        """Generate a mock session ID."""
        return f"mock-session-{int(time.time())}-{random.randint(1000, 9999)}"  # nosec B311

    def get_config(self) -> dict:
        """Return mock configuration."""
        return {
            "mode": "local",
            "agent_name": "Mock Agent (Test Mode)",
            "agent_arn": "arn:aws:bedrock:us-east-1:123456789012:agent/mock-agent-id",
            "region": "us-east-1",
            "session_id": self.session_id,
            "auth_method": "none",
            "memory_id": "mock-memory-123",
        }

    def invoke(self, message: str, session_id: Optional[str] = None) -> dict:
        """Simulate agent invocation with a mock response."""
        # Use provided session_id or generate new one
        if session_id:
            self.session_id = session_id

        # Simulate processing delay
        time.sleep(random.uniform(0.5, 1.5))  # nosec B311

        # Select a random response
        response_text = random.choice(MOCK_RESPONSES)  # nosec B311

        # Sometimes add the user's message context
        if random.random() > 0.5:  # nosec B311
            response_text = f"You asked: '{message}'\n\n{response_text}"

        return {
            "response": response_text,
            "session_id": self.session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def create_new_session(self) -> dict:
        """Create a new mock session."""
        self.session_id = self._generate_session_id()
        return {"session_id": self.session_id}

    def get_memory(self) -> Optional[dict]:
        """Return mock memory information."""
        return {
            "memory_id": "mock-memory-123",
            "name": "Mock Memory Resource",
            "status": "ENABLED",
            "event_expiry_days": 30,
            "memory_type": "short-term",
            "strategies": [
                {
                    "strategy_id": "mock-strategy-1",
                    "name": "Session Summary",
                    "type": "SESSION_SUMMARY",
                    "status": "ENABLED",
                    "description": "Summarizes conversation sessions",
                }
            ],
        }
