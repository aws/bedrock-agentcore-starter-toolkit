# Getting Started with Browser

The Amazon Bedrock AgentCore Browser provides a secure, managed environment for web browsing and automation. This guide will help you implement powerful browser capabilities in your agent applications.

## Prerequisites

Before using the browser tool, ensure you have:

- An AWS account with appropriate permissions
- Python 3.10+ installed

## Install the SDK

```
pip install bedrock-agentcore
```

## Create a Browser Session

The bedrock-agentcore SDK provides a convenient way to create browser sessions:

```
from bedrock_agentcore.tools.browser_client import browser_session

# Create a browser session using the context manager
with browser_session("us-west-2") as client:
    # The session_id is automatically generated
    print(f"Session ID: {client.session_id}")

    # Generate WebSocket URL and headers for connecting automation frameworks
    websocket_url, headers = client.generate_ws_headers()

    # Use these to connect your preferred browser automation tool
    # (See examples below)

# The session is automatically closed when exiting the context manager
```

For more control over the session lifecycle:

```
from bedrock_agentcore.tools.browser_client import BrowserClient

# Create a browser client
client = BrowserClient(region="us-west-2")

# Start a browser session
client.start()
print(f"Session ID: {client.session_id}")

try:
    # Generate WebSocket URL and headers
    url, headers = client.generate_ws_headers()

    # Perform browser operations with your preferred automation tool

finally:
    # Always close the session when done
    client.stop()
```

## Integration Examples

### Example 1: Browser Automation with Nova Act

##### Install dependencies

```
pip install nova-act
```

You can build a browser agent using Nova Act to automate web interactions:

```
import time
from bedrock_agentcore.tools.browser_client import browser_session
from nova_act import NovaAct
from rich.console import Console

NOVA_ACT_API_KEY = "YOUR_NOVA_ACT_API_KEY"

console = Console()

def main():
    try:
        # Step 1: Create browser session
        with browser_session("us-west-2") as client:
            print("\r   ✅ Browser ready!                    ")
            ws_url, headers = client.generate_ws_headers()

            # Step 2: Use Nova Act to interact with the browser
            with NovaAct(
                    cdp_endpoint_url=ws_url,
                    cdp_headers=headers,
                    preview={"playwright_actuation": True},
                    nova_act_api_key=NOVA_ACT_API_KEY,
                    starting_page="https://www.amazon.com",
                ) as nova_act:
                    result = nova_act.act("Search for coffee maker and get the details of the lowest priced one on the first page")
                    console.print(f"\n[bold green]Nova Act Result:[/bold green] {result}")

    except KeyboardInterrupt:
        console.print("\n\n[yellow]Shutting down...[/yellow]")
        if 'client' in locals():
            client.stop()
            print("✅ Browser session terminated")
    except Exception as e:
        print(f"\n[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
```

### Example 2: Using Playwright for Browser Control

##### Install dependencies

```
pip install playwright
```

You can use the Playwright automation framework with the Browser Tool:

```
import time
import base64
from datetime import datetime
from playwright.sync_api import sync_playwright, Playwright, BrowserType
from bedrock_agentcore.tools.browser_client import browser_session

def capture_cdp_screenshot(context, page, filename_prefix="screenshot", image_format="jpeg"):
    """Capture a screenshot using the CDP API and save to file."""
    cdp_client = context.new_cdp_session(page)
    screenshot_data = cdp_client.send("Page.captureScreenshot", {
        "format": image_format,
        "quality": 80,
        "captureBeyondViewport": True
    })

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{filename_prefix}_{timestamp}.{image_format}"
    image_bytes = base64.b64decode(screenshot_data['data'])

    with open(filename, "wb") as f:
        f.write(image_bytes)

    print(f"✅ Screenshot saved: {filename}")
    return filename


def main(playwright: Playwright):
    with browser_session("us-west-2") as client:
        print("📡 Browser session started... waiting for readiness")

        ws_url, headers = client.generate_ws_headers()
        chromium: BrowserType = playwright.chromium
        browser = chromium.connect_over_cdp(ws_url, headers=headers)

        try:
            context = browser.contexts[0] if browser.contexts else browser.new_context()
            page = context.pages[0] if context.pages else context.new_page()

            # Step 1: Navigate to Amazon
            print("🌐 Navigating to Amazon...")
            page.goto("https://www.amazon.com", wait_until="domcontentloaded")
            time.sleep(2)
            capture_cdp_screenshot(context, page, "amazon_home")

            # Step 2: Search for "coffee maker"
            print("🔎 Searching for 'coffee maker'...")
            page.fill("input#twotabsearchtextbox", "coffee maker")
            page.keyboard.press("Enter")
            page.wait_for_selector(".s-result-item", timeout=10000)
            time.sleep(2)
            capture_cdp_screenshot(context, page, "coffee_maker_results")

        finally:
            print("🔒 Closing browser session...")
            if not page.is_closed():
                page.close()
            browser.close()


if __name__ == "__main__":
    with sync_playwright() as p:
        main(p)
```

## Browser Tool Architecture

The AWS Browser Tool provides:

- **Fully managed browser environment** running in the AWS cloud
- **WebSocket-based CDP interface** for browser control
- **Integration with popular automation frameworks** like Playwright, Puppeteer, and NovaAct
- **Security and isolation** between browser sessions

## Best Practices

To get the most out of the browser tool:

1. **Use context managers** for proper resource cleanup
1. **Handle exceptions properly** to ensure browser sessions are closed
1. **Consider performance** when making multiple browser requests
1. **Secure sensitive data** - never hardcode credentials in browser automation code
1. **Use appropriate timeouts** for network and page load operations
1. **Add error recovery** for common browser automation challenges
