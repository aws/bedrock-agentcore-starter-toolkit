# Getting Started with Browser Sandbox

The Amazon Bedrock AgentCore Browser Sandbox provides a secure environment for interacting with web applications. This guide will help you get started with implementing browser automation in your agent applications.

## Prerequisites

Before using the browser sandbox, ensure you have:

- An AWS account with appropriate permissions
- Python 3.10+ installed

## Install the SDK

```bash
pip install bedrock-agentcore
```

## Create a Browser Session

The bedrock-agentcore SDK provides a convenient way to create browser sessions using the managed browser `aws.browser.v1`:

```python
from bedrock_agentcore.tools.browser_client import browser_session

# Create a browser session using the context manager
with browser_session("us-west-2") as client:
    # The session_id is automatically generated
    print(f"Session ID: {client.session_id}")

# The session is automatically closed when exiting the context manager
```

If you need more control over the session lifecycle, you can also use the client without a context manager:

```python
from bedrock_agentcore.tools.browser_client import BrowserClient

# Create a browser client
client = BrowserClient(region_name="us-west-2")

# Start a browser session
client.start()
print(f"Session ID: {client.session_id}")

try:
    # Generate WebSocket URL and headers
    url, headers = client.generate_ws_headers()

    # Perform browser operations...

finally:
    # Always close the session when done
    client.stop()
```

## Interact with Web Applications

Use the `browser-use` library to interact with web applications:

```python
from bedrock_agentcore.tools.browser_client import browser_session
from browser_use import BrowserUse
import time

# Create a browser session
with browser_session("us-west-2") as client:
    # Generate WebSocket URL and headers
    websocket_url, headers = client.generate_ws_headers()

    # Connect to the browser using the WebSocket URL
    browser = BrowserUse(websocket_url=websocket_url, headers=headers)
    browser.connect()

    try:
        # Navigate to a website
        print("Navigating to AWS website...")
        browser.goto("https://aws.amazon.com")

        # Wait for page to load
        time.sleep(2)

        # Take a screenshot
        screenshot = browser.screenshot()

        # Save screenshot to file (optional)
        with open("screenshot.png", "wb") as f:
            f.write(screenshot)

        # Click on a link
        browser.click("Products")

        # Wait for page to load
        time.sleep(2)

        # Type in a search box
        browser.type("input[name='searchField']", "Lambda")

        # Press Enter
        browser.press("Enter")

        # Wait for search results
        time.sleep(3)

        # Extract text from the page
        page_text = browser.text()
        print("Page text:", page_text[:200] + "...")  # Print first 200 characters

    finally:
        # Always disconnect when done
        browser.disconnect()
```

## Browser Agent Integration

Here's a complete example of how to integrate the browser sandbox with an agent to perform browser actions through natural language:

```python
import asyncio
import time
from bedrock_agentcore.tools.browser_client import browser_session
from browser_use import Agent
from langchain_aws import ChatBedrockConverse
from browser_use.browser import BrowserProfile
from browser_use.browser.session import BrowserSession


async def demo():
    # Create ChatBedrockConverse once
    bedrock_chat = ChatBedrockConverse(
        model="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
        region_name="us-west-2"
    )

    with browser_session('us-west-2') as client:
        time.sleep(20)
        ws_url, headers = client.generate_ws_headers()
        # Create browser profile with headers
        browser_profile = BrowserProfile(
            headers=headers,
            timeout=600000,  # 600 seconds timeout
        )

        # Create a browser session with CDP URL and keep_alive=True for persistence
        session = BrowserSession(
            cdp_url=ws_url,
            browser_profile=browser_profile,
        )
        await session.start()

        # Use BrowserUse with the existing browser session
        agent = Agent(
            task="Goto amazon.com and search for coffee makers, take a screenshot and store it in the current directory",
            llm=bedrock_chat,  # Specify your LLM
            browser_session=session
        )
        result = await agent.run()
        print(result)

if __name__ == "__main__":
    asyncio.run(demo())
```

This example demonstrates:

1. Creating a browser session using the `browser_session` context manager
2. Generating WebSocket URL and headers for browser interaction
3. Processing natural language commands
4. Handling various browser actions like navigation, clicking, typing, and taking screenshots
5. Proper cleanup of resources when done

You can extend this example to integrate with your own agent framework, adding more sophisticated command parsing and error handling as needed.

## Best Practices

To get the most out of the browser sandbox:

1. **Use context managers**: The `browser_session` context manager ensures proper cleanup
2. **Handle errors gracefully**: Always include proper error handling and cleanup
3. **Implement timeouts**: Add appropriate waits for page loading and element interactions
4. **Secure credentials**: Never hardcode sensitive information in your browser automation code
5. **Disconnect properly**: Always disconnect from the browser when done
