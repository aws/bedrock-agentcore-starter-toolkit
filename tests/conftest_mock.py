"""
Mock conftest.py for CI testing without bedrock_agentcore.
Copy this to tests/conftest.py for CI, or update the existing one.
"""

import os
import sys
from unittest.mock import Mock

# Check if we're in mock mode
if os.environ.get("BEDROCK_AGENTCORE_MOCK_MODE") == "true":
    # Create mock bedrock_agentcore module
    sys.modules["bedrock_agentcore"] = Mock()
    sys.modules["bedrock_agentcore"].BedrockAgentCoreApp = Mock

    # Create mock boto3
    sys.modules["boto3"] = Mock()
    sys.modules["botocore"] = Mock()

# Rest of your conftest content goes here...
