# AgentCore UI User Guide

Welcome to the AgentCore UI! This guide will help you get started with using the web interface to interact with your AgentCore agents and inspect memory resources.

## Table of Contents

- [Getting Started](#getting-started)
- [Using the Chat Interface](#using-the-chat-interface)
- [Memory Inspection](#memory-inspection)
- [Authentication Options](#authentication-options)
- [Configuration Panel](#configuration-panel)
- [Session Management](#session-management)
- [Troubleshooting](#troubleshooting)

## Getting Started

### Launching the UI

To launch the AgentCore UI, use the `launch` command with the `--ui` flag:

**For local development (agent running in Docker container):**

```bash
agentcore launch --local --ui
```

**For remote agents (deployed to AWS):**

```bash
agentcore launch --ui
```

The UI will automatically open in your default browser at `http://localhost:8001`.

### Prerequisites

- **Local Mode**: Docker must be running with your agent container at `http://127.0.0.1:8000`
- **Remote Mode**:
  - Valid AWS credentials configured (via AWS CLI, environment variables, or IAM role)
  - A `project_config.yaml` file in your current directory with agent configuration
  - Agent deployed to AWS via AgentCore Runtime

## Using the Chat Interface

The chat interface is the main view for interacting with your agent. It provides a familiar messaging experience similar to popular chat applications.

### Sending Messages

1. Type your message in the text input field at the bottom of the screen
2. Press **Enter** or click the **Send** button to submit your message
3. Your message will appear on the right side of the chat
4. Wait for the agent's response, which will appear on the left side

### Message Features

- **Markdown Support**: Agent responses support markdown formatting including:
  - **Bold** and _italic_ text
  - Code blocks with syntax highlighting
  - Lists and bullet points
  - Links and images
- **Timestamps**: Each message displays a timestamp showing when it was sent

- **Auto-scroll**: The chat automatically scrolls to show the latest message

- **Loading Indicator**: A typing indicator appears while the agent is processing your request

### Example Conversation

```
You: What is Amazon Bedrock AgentCore?

Agent: Amazon Bedrock AgentCore is a suite of services that enables you to
deploy and operate AI agents securely at scale. It includes:

- **Runtime**: Serverless runtime for deploying agents
- **Memory**: Context-aware memory management
- **Gateway**: MCP server for tool integration
- And more...
```

## Memory Inspection

The Memory view allows you to inspect the memory resources configured for your agent. This is useful for understanding what information your agent is storing and how it's organized.

### Accessing Memory View

Click the **Memory** tab in the navigation bar to switch to the memory inspection view.

### Memory Overview

The memory overview card displays:

- **Memory ID**: Unique identifier for the memory resource
- **Name**: Human-readable name of the memory
- **Status**: Current status (ACTIVE, CREATING, FAILED, etc.)
- **Event Expiry**: Number of days before memory events expire
- **Memory Type**:
  - **Short-term**: Only maintains conversation context
  - **Short-term and Long-term**: Includes persistent memory across sessions

### Memory Strategies

Below the overview, you'll see a list of configured memory strategies. Each strategy card shows:

- **Strategy Name**: Descriptive name of the strategy
- **Type**: Strategy type (Semantic, Summary, User Preference, or Custom)
- **Status**: Current status with color-coded indicator
  - 🟢 Green: Active
  - 🟡 Yellow: Creating
  - 🔴 Red: Failed
- **Description**: Optional description of what the strategy does
- **Namespaces**: Logical partitions for organizing memory content

### Strategy Types

**Semantic Strategy**

- Stores and retrieves information based on semantic similarity
- Useful for finding related information across conversations
- Enables long-term memory capabilities

**Summary Strategy**

- Automatically summarizes conversation history
- Reduces token usage while maintaining context
- Typically used for short-term memory

**User Preference Strategy**

- Learns and stores user preferences over time
- Enables personalized agent responses
- Persists across sessions

**Custom Strategy**

- User-defined extraction and consolidation logic
- Flexible configuration for specific use cases

### Refreshing Memory Data

Click the **Refresh** button to fetch the latest memory information from AWS.

## Authentication Options

The AgentCore UI supports different authentication methods depending on your deployment mode.

### Local Mode (No Authentication)

When running in local mode (`--local` flag), no authentication is required. The UI connects directly to your local agent container.

**Configuration:**

- Mode: Local
- Auth Method: None
- Endpoint: http://127.0.0.1:8000

### Remote Mode with IAM Authentication

IAM authentication uses your AWS credentials from the local environment.

**Configuration:**

- Mode: Remote
- Auth Method: IAM
- Credentials: Fetched from AWS CLI, environment variables, or IAM role

**How it works:**

1. The backend server uses boto3's default credential chain
2. Credentials are automatically discovered from:
   - Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
   - AWS CLI configuration (`~/.aws/credentials`)
   - IAM role (if running on EC2, ECS, or Lambda)
3. No manual credential entry required

**Optional User ID:**

- You can optionally provide a User ID for identity context
- This is useful for testing different user personas
- Leave empty to use default credentials

### Remote Mode with OAuth Authentication

OAuth authentication uses bearer tokens for secure agent invocation.

**Configuration:**

- Mode: Remote
- Auth Method: OAuth
- Bearer Token: Entered directly in the UI

**How it works:**

1. When the agent uses OAuth authentication, a token input field appears below the configuration panel
2. Obtain a bearer token from your OAuth provider
3. Enter the token in the provided input field
4. The token is securely included in all agent invocation requests
5. Messages cannot be sent until a valid token is provided

**Token Input Features:**

- **Show/Hide Toggle**: Click the eye icon to show or hide the token text
- **Character Count**: Displays the number of characters in your token
- **Validation**: The send button is disabled until a token is entered
- **Session Persistence**: The token is stored in memory for the current browser session

**Security Notes:**

- Tokens are only stored in browser memory (not localStorage)
- Tokens are cleared when you close the browser tab
- Never share your bearer token with others
- Tokens are sent securely to the backend via the request body

## Configuration Panel

The configuration panel displays current connection settings and agent information. It's located at the top of the chat view.

### Information Displayed

- **Connection Mode**: Local or Remote
- **Agent Name**: Name of the agent from configuration
- **Agent ARN**: Amazon Resource Name (remote mode only)
- **Region**: AWS region (remote mode only)
- **Session ID**: Current conversation session identifier
- **Auth Method**: Authentication method being used

### Configuration Source

- **Local Mode**: Configuration is minimal (just connection endpoint)
- **Remote Mode**: Configuration is loaded from `project_config.yaml` in your current directory

### Example Configuration Panel

```
Mode: Remote
Agent: my-weather-agent
ARN: arn:aws:bedrock-agentcore:us-east-1:123456789012:agent/abc123
Region: us-east-1
Session: sess_20240115_143025_abc123
Auth: IAM
```

## Session Management

Sessions maintain conversation context across multiple interactions with your agent. Each session has a unique identifier.

### Current Session

The current session ID is displayed in the configuration panel. All messages in the current conversation use this session ID.

### Starting a New Conversation

To start a fresh conversation with no prior context:

1. Click the **New Conversation** button (usually in the top-right corner)
2. A new session ID will be generated
3. The chat history will be cleared
4. Your next message will start a new conversation context

### Session Persistence

- Session IDs are stored in browser sessionStorage
- Sessions persist across page refreshes
- Sessions are cleared when you close the browser tab
- Starting a new conversation generates a new session ID

### Why Sessions Matter

Sessions are crucial for:

- **Context Continuity**: Agent remembers previous messages in the conversation
- **Memory Association**: Memory events are linked to specific sessions
- **Debugging**: Session IDs help trace conversations in logs
- **Testing**: Different sessions allow testing various conversation flows

## Troubleshooting

### UI Won't Load

**Problem**: Browser shows "Cannot connect" or blank page

**Solutions**:

1. Check that the backend server is running (should start automatically with `--ui` flag)
2. Verify the URL is `http://localhost:8001`
3. Check browser console for errors (F12 → Console tab)
4. Try refreshing the page (Ctrl+R or Cmd+R)

### Agent Not Responding

**Problem**: Messages send but no response appears

**Solutions**:

**For Local Mode:**

1. Verify Docker is running: `docker ps`
2. Check agent container is running at port 8000
3. Test agent directly: `curl http://127.0.0.1:8000/health`
4. Review agent container logs: `docker logs <container-id>`

**For Remote Mode:**

1. Verify AWS credentials: `aws sts get-caller-identity`
2. Check agent is deployed: `agentcore status`
3. Verify agent ARN in `project_config.yaml` is correct
4. Check AWS region matches your agent's region
5. Review backend logs in the terminal where you ran `launch --ui`

### Configuration Not Found

**Problem**: UI shows "No configuration file found"

**Solutions**:

1. Create a `project_config.yaml` file in your current directory
2. Ensure the file contains valid agent configuration
3. Restart the UI: Stop the server (Ctrl+C) and run `agentcore launch --ui` again

**Example minimal configuration:**

```yaml
agents:
  - name: my-agent
    aws:
      region: us-east-1
    bedrock_agentcore:
      agent_arn: arn:aws:bedrock-agentcore:us-east-1:123456789012:agent/abc123
```

### Memory Not Loading

**Problem**: Memory view shows "Memory not configured" or error

**Solutions**:

1. Verify memory is configured in `project_config.yaml`:
   ```yaml
   agents:
     - name: my-agent
       memory:
         memory_id: mem_abc123
   ```
2. Check AWS credentials have permission to access Bedrock AgentCore Memory
3. Verify the memory ID exists: Use AWS Console or CLI to confirm
4. Ensure the region in configuration matches where memory was created

### Authentication Errors

**Problem**: "Authentication failed" or "Access denied" errors

**Solutions**:

**For IAM:**

1. Verify AWS credentials: `aws sts get-caller-identity`
2. Check IAM permissions include:
   - `bedrock-agentcore:InvokeAgent`
   - `bedrock-agentcore:GetMemory` (if using memory)
3. Ensure credentials are not expired
4. Try refreshing credentials: `aws sso login` (if using SSO)

**For OAuth:**

1. Verify bearer token is valid and not expired
2. Check token has required scopes
3. Confirm OAuth configuration in `project_config.yaml` is correct

### CORS Errors

**Problem**: Browser console shows CORS policy errors

**Solutions**:

1. This usually indicates the frontend is running on a different port than expected
2. If running frontend dev server separately, set `VITE_API_BASE_URL` in `.env`:
   ```
   VITE_API_BASE_URL=http://localhost:8001
   ```
3. Restart the frontend dev server
4. For production, ensure frontend is built and served by the backend

### Slow Response Times

**Problem**: Agent takes a long time to respond

**Possible Causes**:

- **Cold Start**: First invocation after deployment may take 10-30 seconds
- **Complex Processing**: Agent is performing intensive operations
- **Network Latency**: Connection to AWS services
- **Memory Retrieval**: Fetching large amounts of memory data

**Tips**:

- Wait patiently for the first response (cold start)
- Subsequent responses should be faster
- Check agent logs for performance bottlenecks
- Consider optimizing agent code or memory strategies

## Tips and Best Practices

### Effective Agent Interaction

1. **Be Specific**: Provide clear, detailed prompts for better responses
2. **Use Context**: Reference previous messages in the conversation
3. **Test Incrementally**: Start with simple queries before complex ones
4. **Review Memory**: Check memory view to understand what the agent remembers

### Session Management

1. **Start Fresh**: Use "New Conversation" when testing different scenarios
2. **Keep Context**: Maintain the same session for related queries
3. **Document Sessions**: Note session IDs for important conversations

### Memory Inspection

1. **Regular Checks**: Periodically review memory strategies to ensure they're active
2. **Understand Types**: Know which strategies provide short-term vs long-term memory
3. **Monitor Status**: Watch for failed strategies and investigate issues

### Development Workflow

1. **Local First**: Test changes locally before deploying to AWS
2. **Use Mock Mode**: Test UI without a real agent (see `MOCK_MODE.md`)
3. **Check Logs**: Review backend logs for detailed error information
4. **Iterate Quickly**: Use local mode for rapid development cycles

## Additional Resources

- **Main Documentation**: [AgentCore Documentation](https://docs.aws.amazon.com/bedrock-agentcore/)
- **UI README**: [UI Technical Documentation](README.md)
- **Mock Mode**: [Testing Without an Agent](MOCK_MODE.md)
- **API Reference**: See backend API endpoint documentation in `backend/main.py`
- **GitHub**: [AgentCore Starter Toolkit](https://github.com/aws/bedrock-agentcore-starter-toolkit)

## Getting Help

If you encounter issues not covered in this guide:

1. Check the [GitHub Issues](https://github.com/aws/bedrock-agentcore-starter-toolkit/issues)
2. Review backend logs in your terminal
3. Check browser console for frontend errors (F12 → Console)
4. Join the [Discord community](https://discord.gg/bedrockagentcore-preview)
5. Consult the [AWS Documentation](https://docs.aws.amazon.com/bedrock-agentcore/)

---

**Happy agent building!** 🚀
