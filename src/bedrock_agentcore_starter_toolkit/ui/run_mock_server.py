#!/usr/bin/env python3
"""Run the UI backend server in mock mode for testing.

This allows you to test the UI without needing a real agent configuration.

Usage:
    cd ui
    uv run python run_mock_server.py
"""

import os
import sys

# Set mock mode environment variable
os.environ["AGENTCORE_MOCK_MODE"] = "true"

if __name__ == "__main__":
    print("🎭 Starting AgentCore UI in MOCK MODE")
    print("=" * 60)
    print("This mode simulates agent responses for testing the UI.")
    print("No real agent configuration is required.")
    print("=" * 60)
    print()
    print("Server will start at: http://localhost:8001")
    print("Press Ctrl+C to stop")
    print()

    try:
        import uvicorn

        # Run uvicorn from the ui directory
        uvicorn.run(
            "backend.main:app",
            host="127.0.0.1",
            port=8001,
            reload=True,
            log_level="info",
        )
    except ImportError:
        print("Error: uvicorn not found. Please install dependencies:")
        print("  pip install -r backend/requirements.txt")
        print()
        print("Or run with uv:")
        print("  uv run python run_mock_server.py")
        sys.exit(1)
