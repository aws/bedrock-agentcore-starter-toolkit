# AgentCore Browser Quickstart

AgentCore Browser enables your agents to interact with web pages through a managed Chrome browser. The agent can navigate websites, search for information, extract content, and interact with web elements in a secure, managed environment.

## Prerequisites

Before you start, ensure you have:

* **AWS Account** with credentials configured. See instructions below.
* **Python 3.10+** installed
* **Boto3** installed
* **IAM Execution Role** with the required permissions (see below)
* **Model access**: Anthropic Claude Sonnet 4.0 enabled in the Amazon Bedrock console. For information about using a different model with the Strands Agents see the Model Providers section in the Strands Agents SDK documentation.

### Credentials configuration (if not already configured)

Confirm your AWS credentials are configured:

```bash
aws sts get-caller-identity
```

If this command fails, configure your credentials. See [Configuration and credential file settings](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html) in the AWS CLI documentation.

### Attach Required Permissions

Your IAM user or role needs permissions to use Browser. Attach this policy to your IAM identity:

```json
{
    "Version":"2012-10-17",
    "Statement": [
        {
            "Sid": "BedrockAgentCoreBrowserFullAccess",
            "Effect": "Allow",
            "Action": [
                "bedrock-agentcore:CreateBrowser",
                "bedrock-agentcore:ListBrowsers",
                "bedrock-agentcore:GetBrowser",
                "bedrock-agentcore:DeleteBrowser",
                "bedrock-agentcore:StartBrowserSession",
                "bedrock-agentcore:ListBrowserSessions",
                "bedrock-agentcore:GetBrowserSession",
                "bedrock-agentcore:StopBrowserSession",
                "bedrock-agentcore:UpdateBrowserStream",
                "bedrock-agentcore:ConnectBrowserAutomationStream",
                "bedrock-agentcore:ConnectBrowserLiveViewStream"
            ],
            "Resource": "arn:aws:bedrock-agentcore:<region>:<account_id>:browser/*"
        },
        {
            "Sid": "BedrockModelAccess",
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream"
            ],
            "Resource": [
                "*"
            ]
        }
    ]
}
```

**To attach this policy**:

1. Navigate to the IAM Console
2. Find your user or role (the one returned by `aws sts get-caller-identity`)
3. Click "Add permissions" → "Create inline policy"
4. Switch to JSON view and paste the policy above
5. Name it `AgentCoreBrowserAccess` and save

>Note: If you're deploying agents to AgentCore Runtime (not covered in this guide), you'll also need to create an IAM execution role with a service trust policy. See the AgentCore Runtime QuickStart Guide for those requirements.

## Using **AgentCore** Browser via AWS Strands

### Step 1: Install Dependencies

Create a project folder and install the required packages:

```bash
mkdir agentcore-browser-quickstart
cd agentcore-browser-quickstart
python3 -m venv .venv
source .venv/bin/activate
```

On Windows, use: `.venv\Scripts\activate`

Install the required packages:

```bash
pip install bedrock-agentcore strands-agents strands-agents-tools playwright nest-asyncio
```

These packages provide:

* `bedrock-agentcore`: The SDK for AgentCore tools including Browser
* `strands-agents`: The Strands agent framework
* `strands-agents-tools`: The tools that the Strands agent framework offers including Browser tool
* `playwright`: Python library for browser automation. Strands uses playwright for browser automation
* `nest-asyncio`: Allows running asyncio event loops within existing event loops

### Step 2: Create Your Agent with Browser

Create a file named `browser_agent.py` and add the following code:

```python
from strands import Agent
from strands_tools.browser import AgentCoreBrowser

# Initialize the Browser tool
browser_tool = AgentCoreBrowser(region="us-west-2")

# Create an agent with the Browser tool
agent = Agent(tools=[browser_tool.browser])

# Test the agent with a web search prompt
prompt = "what are the services offered by Bedrock AgentCore? Use the documentaiton link if needed: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/what-is-bedrock-agentcore.html"
print(f"\\nPrompt: {prompt}\\n")

response = agent(prompt)
print("\\nAgent Response:")
print(response.message["content"][0]["text"])
```

This code:

* Initializes the Browser tool for the `us-west-2` region
* Creates an agent that can use the browser to interact with websites
* Sends a prompt asking the agent to search AgentCore documentation and answer question
* Prints the agent's response with the response

### Step 3: Run the Agent

Execute the script:

```bash
python browser_agent.py
```

**Expected Output**: You should see the agent's response containing details about the first MacBook search result on Amazon, such as the product name, price, and key specifications. The agent navigates the website, performs the search, and extracts the requested information.

If you encounter errors, verify:

* Your IAM role/user has the correct permissions
* You have model access enabled in the Amazon Bedrock console
* Your AWS credentials are properly configured

### Step 4: View the Browser Session Live

While your browser script is running, you can view the session in real-time through the AWS Console:

1. Open the [AgentCore Browser Console](https://us-west-2.console.aws.amazon.com/bedrock-agentcore/builtInTools)
2. Navigate to **Built-in tools** in the left navigation
3. Select the Browser tool (for example, `AgentCore Browser Tool`, or your custom browser)
4. In the **Browser sessions** section, find your active session with status **Ready**
5. In the **Live view / recording** column, click the provided "View live session" URL
6. The live view opens in a new browser window, displaying the real-time browser session

The live view interface provides:

* Real-time video stream of the browser session
* Interactive controls to take over or release control from automation
* Ability to terminate the session

## Session Recording and Replay

Session recording captures all browser interactions and allows you to replay sessions for debugging, analysis, and monitoring. This feature requires a custom browser tool with recording enabled.

### Prerequisites for Session Recording

To enable session recording, you need:

1. **An Amazon S3 bucket** to store recording data
2. **An IAM execution role** with permissions to write to your S3 bucket
3. **A custom browser tool** configured with recording enabled

### Step 1: Configure IAM Role for Recording

**Step 1.1: Create the IAM Policy**

Create an IAM execution role with the following permissions. This role allows AgentCore Browser to write recording data to S3 and log activity to CloudWatch.

1. Navigate to the [IAM Console](https://console.aws.amazon.com/iam/)
2. Go to **Policies → Create Policy**
3. Click **JSON** and paste the below while replacing `your-recording-bucket` with your S3 bucket name:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "BrowserPermissions",
            "Effect": "Allow",
            "Action": [
                "bedrock-agentcore:ConnectBrowserAutomationStream",
                "bedrock-agentcore:ListBrowsers",
                "bedrock-agentcore:GetBrowserSession",
                "bedrock-agentcore:ListBrowserSessions",
                "bedrock-agentcore:CreateBrowser",
                "bedrock-agentcore:StartBrowserSession",
                "bedrock-agentcore:StopBrowserSession",
                "bedrock-agentcore:ConnectBrowserLiveViewStream",
                "bedrock-agentcore:UpdateBrowserStream",
                "bedrock-agentcore:DeleteBrowser",
                "bedrock-agentcore:GetBrowser"
            ],
            "Resource": "*"
        },
        {
            "Sid": "S3Permissions",
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "s3:ListBucket",
                "s3:ListMultipartUploadParts",
                "s3:AbortMultipartUpload"
            ],
            "Resource": [
                "arn:aws:s3:::your-recording-bucket",
                "arn:aws:s3:::your-recording-bucket/*"
            ]
        },
        {
            "Sid": "CloudWatchLogsPermissions",
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents",
                "logs:DescribeLogStreams"
            ],
            "Resource": "*"
        }
    ]
}
```

This policy includes:

* **Browser Permissions**: Allows the role to manage browser sessions and streams
* **S3 Permissions**: Allows writing and reading recording data, including multipart uploads for large recordings
* **CloudWatch Logs Permissions**: Allows logging browser activity for debugging and monitoring

4. Click **Next**
5. Name the policy `AgentCoreBrowserRecordingPolicy`
6. Click **Create policy**

**Step 1.2: Create the Role using the IAM Policy with Trust Policy**

1. Navigate to the [IAM Console](https://console.aws.amazon.com/iam/)
2. Click **Roles** → **Create role**
3. Click **Custom trust policy**
4. Paste the following trust policy (replace `123456789012` with your account ID and adjust region if needed):

```json
{
    "Version":"2012-10-17",
    "Statement": [{
        "Sid": "BedrockAgentCoreBrowser",
        "Effect": "Allow",
        "Principal": {
            "Service": "bedrock-agentcore.amazonaws.com"
        },
        "Action": "sts:AssumeRole",
        "Condition": {
            "StringEquals": {
                "aws:SourceAccount": "123456789012"
            },
            "ArnLike": {
                "aws:SourceArn": "arn:aws:bedrock-agentcore:us-west-2:123456789012:*"
            }
        }
    }]
}
```

5. Click **Next**
6. Select the policy `AgentCoreBrowserRecordingPolicy` and click **Next**
7. Name the role `AgentCoreBrowserRecordingRole`
8. Click **Create role**
9. Click on the newly created role and copy the **ARN** (for example, `arn:aws:iam::123456789012:role/AgentCoreBrowserRecordingRole`)

You'll use this role ARN when creating a browser with recording enabled in the next step. Make sure to replace `123456789012` with your AWS account ID and adjust the region in `aws:SourceArn` if using a region other than `us-west-2`.

### Step 2: Create a Browser Tool with Recording

Create a file named `create_browser_with_recording.py` and add the following code:

```python
import boto3
import uuid

region = "us-west-2"
bucket = "your-recording-bucket" # Replace with your S3 bucket name

# Initialize the Bedrock AgentCore CONTROL plane client
client = boto3.client(
    "bedrock-agentcore-control",
    region_name=region
    )

# Create a custom browser with recording enabled
response = client.create_browser(
    name="MyRecordingBrowser",
    description="Browser with session recording enabled",
    networkConfiguration={
        "networkMode": "PUBLIC"
    },
    executionRoleArn="arn:aws:iam::123456789012:role/AgentCoreBrowserRecordingRole",
    clientToken=str(uuid.uuid4()),
    recording={
        "enabled": True,
        "s3Location": {
            "bucket": bucket,
            "prefix": "browser-recordings"
        }
    }
)
browser_identifier = response.get("browserId") or response.get("browserIdentifier")
print(f"Created browser with recording: {browser_identifier}")
print(f"Recordings will be stored at: s3://{bucket}/browser-recordings/")
```

Replace the following values:

* `123456789012`: Your AWS account ID
* `AgentCoreBrowserRecordingRole`: Name of your IAM execution role
* `your-recording-bucket`: Name of your S3 bucket for recordings. If you need to create a new bucket, follow [this](https://docs.aws.amazon.com/code-library/latest/ug/python_3_s3_code_examples.html#basics) documentation
* region: Your region if needed

This code:

* Creates a custom browser tool with recording enabled
* Configures the S3 location for storing recording data
* Associates an execution role that has permissions to write to S3
* Returns a browser identifier for use in subsequent sessions

**Run the script**:

```bash
python create_browser_with_recording.py
```

**Expected Output**: You should see the browser identifier and the S3 location where recordings will be stored.

### Step 3: Use the Recording-Enabled Browser

Create a file named `browser_with_recording.py`, add the following code, and replace `your-browser-identifier` with the identifier from Step 2. This is an AWS Strands based example but you can do the same with Playwright, or any other library.

```python
import time
from strands import Agent
from strands_tools.browser import AgentCoreBrowser

# Reuse the existing browser created with recording; ensure identifier is used
browser_identifier = "your-browser-identifier"
region = "us-west-2"
browser_tool = AgentCoreBrowser(region=region, identifier=browser_identifier)

try:
    browser_tool.identifier = browser_identifier
except Exception:
    pass
agent = Agent(tools=[browser_tool.browser])
prompt = (
    "1) Open https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/what-is-bedrock-agentcore.html; "
    "in the left navigation open 'Use Amazon Bedrock AgentCore built-in tools to interact with your applications', then 'AgentCore Browser: interact with web applications'; scroll down and up briefly. "
    "2) Go to https://pypi.org, search 'bedrock-agentcore', open the project page, then click 'Release history'. "
    "3) Go to https://github.com/awslabs/amazon-bedrock-agentcore-samples/tree/main, open 01-tutorials -> 05-AgentCore-tools -> 02-Agent-Core-browser-tool -> 01-browser-with-NovaAct, "
    "then open 'live_view_with_nova_act.py' (or 'basic_browser_with_nova_act.py') and scroll. Keep all actions in the active tab; be resilient to layout changes. Summarize visited pages."
)
print(f"\nPrompt: {prompt}\n")
response = agent(prompt)
print("\nAgent Response:")
print(response.message["content"][0]["text"])
```

This code:

* Starts a browser session with your recording-enabled browser
* Performs several browser actions (navigate, fill form, click)
* All interactions are automatically recorded
* Stops the session, which triggers the final upload of recording data to S3

**Run the script**:

```bash
python browser_with_recording.py
```

**Expected Output**: You should see confirmation messages for each action, and a final message indicating the recording has been saved to S3.

**Note**: Session recording captures DOM mutations and reconstructs them during playback. The browser may make cross-origin HTTP requests to fetch external assets during replay.

### Step 4: Replay and Inspect Recorded Sessions in the AWS Console

Once a browser session completes, the recording data is uploaded to your S3 bucket in chunks. Access recordings through the AWS Console:

**To access session replay in the console**:

1. Navigate to the [AgentCore Browser Console](https://us-west-2.console.aws.amazon.com/bedrock-agentcore/builtInTools?region=us-west-2) and click **Browser use tools**
2. Select your custom browser tool from the list (for example, `MyRecordingBrowser`)
3. In the **Browser sessions** section, find a completed session with status **Terminated** (If there is no browser session with terminated status, manually terminate the session by clicking on the **Terminate** button)
4. Click on the **View Recording** of the session ID that you are interested in to open the session details
5. The session replay page displays with the title showing your browser name and session ID

**Session Analysis Features**:

The console provides multiple tabs for comprehensive session analysis:

* **Video Player**: Interactive playback with timeline scrubber for navigation
* **Pages Navigation**: Panel showing all visited pages with time ranges
* **User Actions**: All user interactions with timestamps, methods, and details
* **Page DOM**: DOM structure and HTML content for each page
* **Console Logs**: Browser console output, errors, and log messages
* **CDP Events**: Chrome DevTools Protocol events with parameters and results
* **Network Events**: HTTP requests, responses, status codes, and timing

**Navigate Recordings**:

* Click on pages in the Pages panel to jump to specific moments
* Click on user actions to see where they occurred in the timeline
* Use the video timeline scrubber for precise navigation
* Choose **View recording** links in action tables to jump to specific interactions

### Step 5: Access Recordings Programmatically

You can also access recording data directly from S3:

```python
import boto3

s3_client = boto3.client('s3', region_name='us-west-2')

# List recordings in your bucket
bucket_name = "your-recording-bucket"
prefix = "browser-recordings/"

response = s3_client.list_objects_v2(
    Bucket=bucket_name,
    Prefix=prefix
)

print(f"Recordings in s3://{bucket_name}/{prefix}:\\n")
for obj in response.get('Contents', []):
    print(f"  {obj['Key']}")
    print(f"    Size: {obj['Size']} bytes")
    print(f"    Last Modified: {obj['LastModified']}")
    print()
```

Recording data is stored in your S3 bucket with the following structure:

```
s3://your-recording-bucket/browser-recordings/
  └── session-id/
      ├── batch_1.ndjson.gz
      ├── batch_2.ndjson.gz
      └── batch_3.ndjson.gz
```

Each session creates a folder with the session ID, and recording data is uploaded in chunks as the session progresses.

## Using AgentCore Browser with Other Browse Libraries and Models

### AgentCore Browser with Amazon Nova Act

Amazon Nova Act is a new AI model trained to perform actions within a web browser, currently in research preview. In this section, you will learn how to use Nova Act SDK to send natural language instructions to AgentCore Browser and perform actions. Please follow the Prerequisites if you've not already done so to get setup. Additionally, there are some more dependencies to install.

#### Step 1: Install Dependencies

Create a project folder (if you have not already):

```bash
mkdir agentcore-browser-quickstart
cd agentcore-browser-quickstart
python3 -m venv .venv
source .venv/bin/activate
```

On Windows, use: `.venv\Scripts\activate`

Install the required packages:

```bash
pip install bedrock-agentcore nova-act rich boto3
```

These packages provide:

* `bedrock-agentcore`: The SDK for AgentCore tools including Browser
* `nova-act`: The SDK for Nova Act which includes the model and orchestrator for browser automation
* `rich`: Library for rich text and beautiful formatting in the terminal
* `boto3`: AWS SDK for Python (Boto3) to create, configure, and manage AWS services

#### Step 2: Get Nova Act API Key

Navigate to [Nova Act](https://nova.amazon.com/act) page and generate an API key using your [amazon.com](http://amazon.com/) credentials. (Note this currently works only for US based [amazon.com](http://amazon.com/) accounts)

Create a file named `nova_act_browser_agent.py` and add the following code:

```python
from bedrock_agentcore.tools.browser_client import browser_session
from nova_act import NovaAct
from rich.console import Console
import argparse
import json
import boto3

console = Console()

from boto3.session import Session

boto_session = Session()
region = boto_session.region_name
print("using region", region)

def browser_with_nova_act(prompt, starting_page, nova_act_key, region="us-west-2"):
    result = None
    with browser_session(region) as client:
        ws_url, headers = client.generate_ws_headers()
        try:
            with NovaAct(
                cdp_endpoint_url=ws_url,
                cdp_headers=headers,
                nova_act_api_key=nova_act_key,
                starting_page=starting_page,
            ) as nova_act:
                result = nova_act.act(prompt)
        except Exception as e:
            console.print(f"NovaAct error: {e}")
        finally:
            return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", required=True, help="Browser Search instruction")
    parser.add_argument("--starting-page", required=True, help="Starting URL")
    parser.add_argument("--nova-act-key", required=True, help="Nova Act API key")
    parser.add_argument("--region", default="us-west-2", help="AWS region")
    args = parser.parse_args()

    result = browser_with_nova_act(
        args.prompt, args.starting_page, args.nova_act_key, args.region
    )
    console.print(f"\n[cyan] Response[/cyan] {result.response}")
    console.print(f"\n[bold green]Nova Act Result:[/bold green] {result}")
```

This code:

* Initializes the Browser tool for the `us-west-2` region
* Creates a Nova Act agent that can use the browser to interact with websites
* Accepts a prompt, starting page and executes the actions on the browser
* Prints the agent's response with the response

#### Step 3: Run the Agent

Execute the script (Replace with your Nova Act API key in the command):

```bash
python nova_act_browser_agent.py --prompt "What are the common usecases of Bedrock AgentCore?" --starting-page "https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/what-is-bedrock-agentcore.html" --nova-act-key "your-nova-act-API-key"
```

**Expected Output**: You should see the agent's response containing details of the common usecases of Amazon Bedrock AgentCore. The agent navigates the website, performs the search, and extracts the requested information.

If you encounter errors, verify:

* Your IAM role/user has the correct permissions
* Your Nova Act API key is correct
* Your AWS credentials are properly configured

#### Step 4: View the Browser Session Live

While your browser script is running, you can view the session in real-time through the AWS Console:

1. Open the [AgentCore Browser Console](https://us-west-2.console.aws.amazon.com/bedrock-agentcore/builtInTools)
2. Navigate to **Built-in tools** in the left navigation
3. Select the Browser tool (for example, `AgentCore Browser Tool`, or your custom browser)
4. In the **Browser sessions** section, find your active session with status **Ready**
5. In the **Live view / recording** column, click the provided "View live session" URL
6. The live view opens in a new browser window, displaying the real-time browser session

The live view interface provides:

* Real-time video stream of the browser session
* Interactive controls to take over or release control from automation
* Ability to terminate the session

### AgentCore Browser with Playwright

#### Step 1: Install Dependencies

You can use Browser directly without an agent framework or an LLM. This is useful when you want programmatic control over browser automation. AgentCore provides two ways to interact with Browser: using Playwright with the SDK client or with libraries like browser-use.

**SDK Client with Playwright**: The `bedrock_agentcore` SDK provides integration with Playwright for browser automation. Use this approach for rich browser interactions with familiar Playwright APIs.

Create a project folder (if you didn't create one before) and install the required packages:

```bash
mkdir agentcore-browser-quickstart
cd agentcore-browser-quickstart
python3 -m venv .venv
source .venv/bin/activate
```

On Windows, use: `.venv\Scripts\activate`

Install the required packages:

```bash
pip install bedrock-agentcore playwright boto3 nest-asyncio
```

These packages provide:

* `bedrock-agentcore`: The SDK for AgentCore tools including Browser
* `playwright`: Python library for browser automation
* `boto3`: AWS SDK for Python (Boto3) to create, configure, and manage AWS services
* `nest-asyncio`: Allows running asyncio event loops within existing event loops

#### Step 2: Control Browser with Playwright

Create a file named `direct_browser_playwright.py` and add the following code:

```python
from playwright.async_api import async_playwright, Playwright, BrowserType
from bedrock_agentcore.tools.browser_client import browser_session
import asyncio

async def run(playwright: Playwright):
    # Create and maintain a browser session
    with browser_session('us-west-2') as client:
        # Get WebSocket URL and authentication headers
        ws_url, headers = client.generate_ws_headers()

        # Connect to the remote browser
        chromium: BrowserType = playwright.chromium
        browser = await chromium.connect_over_cdp(
            ws_url,
            headers=headers
        )

        # Get the browser context and page
        context = browser.contexts[0]
        page = context.pages[0]

        try:
            # Navigate to a website
            await page.goto("https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/what-is-bedrock-agentcore.html")

            # Print the page title
            title = await page.title()
            print(f"Page title: {title}")

            # Keep the session alive for 2 minutes to allow viewing
            print("\\nBrowser session is active. Check the AWS Console for live view.")
            await asyncio.sleep(120)

        finally:
            # Clean up resources
            await page.close()
            await browser.close()

async def main():
    async with async_playwright() as playwright:
        await run(playwright)

# Run the async function
if __name__ == "__main__":
    asyncio.run(main())
```

This code:

* Creates a managed browser session using AgentCore Browser
* Connects to the remote Chrome browser using Playwright's Chrome DevTools Protocol (CDP)
* Navigates to [Agentcore documentation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/what-is-bedrock-agentcore.html) and prints the page title
* Keeps the session alive for 2 minutes, allowing you to view it in the AWS Console
* Properly closes the browser and cleans up resources

**Run the script**:

```bash
python direct_browser_playwright.py
```

**Expected Output**: You should see the page title printed (for example, `Page title: What is Amazon Bedrock AgentCore? - Amazon Bedrock AgentCore`). The script keeps the browser session active for 2 minutes before closing.

## Common Issues & Solutions

<details>
<summary>Permission denied errors</summary>

**Symptom**: Errors mentioning access denied or insufficient permissions.

**Solution**:

* Verify your IAM user or role has the required Browser permissions
* Check your AWS credentials: `aws sts get-caller-identity`
* For recording: Verify the execution role has S3 write permissions
* For recording: Confirm the trust policy allows `bedrock-agentcore.amazonaws.com` to assume the role
</details>

<details>
<summary>Model access denied</summary>

**Symptom**: Errors about model access or authorization when running agents.

**Solution**:

* Navigate to the Amazon Bedrock console
* Go to **Model access** in the left navigation
* Enable **Anthropic Claude Sonnet 4**
* Verify you're in the correct region (match the region in your code)
</details>

<details>
<summary>Browser session timeout</summary>

**Symptom**: Browser sessions end unexpectedly or timeout errors occur.

**Solution**:

* Check the `sessionTimeoutSeconds` parameter when starting sessions
* Default timeout is 900 seconds (15 minutes)
* Increase timeout for longer sessions: `sessionTimeoutSeconds=1800`
* Sessions automatically stop after the timeout period
</details>

<details>
<summary>Recording not appearing in S3</summary>

**Symptom**: No recording files in your S3 bucket after session completes.

**Solution**:

* Verify the execution role has correct S3 permissions
* Confirm the S3 bucket name and prefix are correct
* Check the execution role trust policy includes bedrock-agentcore service
* Review CloudWatch Logs for S3 upload errors
* Ensure the session ran for at least a few seconds (very short sessions may not generate recordings)
</details>

<details>
<summary>Playwright connection errors</summary>

**Symptom**: Cannot connect to browser with Playwright or WebSocket errors.

**Solution**:

* Verify you installed playwright: `pip install playwright`
* Confirm the browser session started successfully before connecting
* Check that the session is still active (not timed out)
* Verify your network allows WebSocket connections
</details>

## Find Your Resources

After using AgentCore Browser, view your resources in the AWS Console:

| Resource | Location |
| --- | --- |
| Live View | Browser Console → Tool Name → Click View live session |
| Session Recordings | Browser Console → Tool Name → Click View recording |
| Browser Logs | CloudWatch → Log groups → `/aws/bedrock-agentcore/browser/` |
| Recording Files | S3 → Your bucket → `browser-recordings/` prefix |
| Custom Browsers | AgentCore Console → Built-in tools → Your custom browser |
| IAM Roles | IAM → Roles → Search for your execution role |
