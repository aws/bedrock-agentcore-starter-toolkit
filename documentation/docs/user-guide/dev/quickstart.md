# QuickStart: Local Development with `agentcore dev`

This guide shows how to use the Amazon Bedrock AgentCore development server to rapidly iterate on your agent locally with hot reloading.

`agentcore dev` starts a local uvicorn server that watches your code for changes and automatically reloads when you save files. This enables a fast development loop without needing to redeploy to AWS after every change.

---

## What is `agentcore dev`?

The development server provides:

- **Hot Reloading** - Automatically detects code changes and restarts the server
- **Local Testing** - Test your agent locally before deploying to Bedrock AgentCore
- **Environment Configuration** - Inject environment variables for testing different configurations

The dev server runs your agent using the [Bedrock AgentCore SDK](https://github.com/aws/bedrock-agentcore-sdk-python/blob/main/src/bedrock_agentcore/runtime/app.py) ASGI application, just like it runs in production on AgentCore Runtime.

---

## Prerequisites

- Python **3.10+**
- **uv** installed
- An AgentCore project created by running `agentcore create`:
  - A `.bedrock_agentcore.yaml` configuration file, OR
  - A `src/main.py` entrypoint file
- **AWS credentials** configured (only if using Bedrock as model provider)
- Project dependencies installed

---

## Step 1: Navigate to Your Project

Start from the root of your AgentCore project. If you don't have a project yet, create one with [`agentcore create`](../create/quickstart.md).

```bash
cd my-agent-project
```

---

## Step 2: Start the Development Server

Run the dev server from your project directory:

```bash
agentcore dev
```

You should see output like:

```
Starting development server with hot reloading
Agent: my_agent
Module: src.main:app
Server will be available at: http://localhost:8080/invocations
Test your agent with: agentcore invoke --dev "Hello" in a new terminal window
This terminal window will be used to run the dev server
Press Ctrl+C to stop the server

INFO:     Will watch for changes in these directories: ['/path/to/project']
INFO:     Uvicorn running on http://0.0.0.0:8080 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using WatchFiles
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

The server is now running and watching for file changes!

---

## Step 3: Test Your Agent

Open a **new terminal window** and invoke your agent:

```bash
agentcore invoke --dev "What can you do?"
```

You should see the agent's response streamed to your terminal.

---

## Step 4: Make Changes and See Them Live

1. Open `src/main.py` in your editor
2. Modify the agent's system prompt or add a new tool
3. Save the file
4. Watch the dev server output - you'll see:

    ```
    INFO:     Detected changes in 'src/main.py'
    INFO:     Reloading...
    INFO:     Application shutdown complete.
    INFO:     Application startup complete.
    ```

5. Invoke your agent again to see the changes immediately:

```bash
agentcore invoke --dev "Test my changes"
```
---

## Step 5: Stop the Development Server

In the terminal running the dev server, press:

```
Ctrl+C
```

You'll see:

```
Shutting down development server...
Development server stopped
```

---

## Advanced Usage

### Custom Port

If port 8080 is already in use, specify a different port:

```bash
agentcore dev --port 9000
```

Then invoke with:

```bash
agentcore invoke --dev --port 9000 "Hello"
```

**Automatic Port Selection**: If the requested port is unavailable, the dev server will automatically find the next available port and use it. The port in use will be displayed when the dev server is running.

---

### Environment Variables

Override environment variables for testing different configurations:

```bash
agentcore dev --env AWS_REGION=us-west-2 --env DEBUG=true
```

### Example: Test with Different Memory

```bash
agentcore dev --env BEDROCK_AGENTCORE_MEMORY_ID=test-memory-123
```

---

## Automatic Environment Variable Injection

If your `.bedrock_agentcore.yaml` includes memory or AWS configuration, these environment variables are automatically injected:

- `BEDROCK_AGENTCORE_MEMORY_ID` - From `memory.memory_id` in config
- `AWS_REGION` - From `aws.region` in config
- `LOCAL_DEV=1` - Always set to indicate local development mode

This matches the environment your agent will have in production.

---

## Troubleshooting

### No Agent Project Found

```
No agent project found in current directory.

Expected either:
  " .bedrock_agentcore.yaml configuration file, or
  " src/main.py entrypoint file

Run 'agentcore dev' from your agent project directory.
```

**Solution**: Navigate to your project root or create a project with `agentcore create`.

---

### Port Already in Use

If you see:

```
Port 8080 is already in use
Using port 8081 instead
Test your agent with: agentcore invoke --dev --port 8081 "Hello" in a new terminal window
```

The dev server automatically found an available port. Use the displayed port number when invoking.

---

### AWS Credentials Required

```
Local dev with Bedrock as the model provider requires AWS creds
```

**Solution**: Configure AWS credentials if using Bedrock models:

```bash
aws configure
```

Or set environment variables:

```bash
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_REGION=us-east-1
```

**Note**: AWS credentials are only required if using Bedrock as your model provider. API key-based providers (OpenAI, Anthropic, etc.) don't need AWS credentials.

---

### Invalid Environment Variable Format

```
Invalid environment variable format: INVALID_FORMAT. Use KEY=VALUE format.
```

**Solution**: Ensure `--env` flags use the `KEY=VALUE` format:

```bash
#  Correct
agentcore dev --env API_KEY=secret123

#  Incorrect
agentcore dev --env API_KEY secret123
```

---

## Best Practices

### 1. Use `.env.local` for Secrets

Store API keys and secrets in `.env.local` (gitignored by default):

```bash
# .env.local
ANTHROPIC_API_KEY=sk-ant-xxxxx
OPENAI_API_KEY=sk-xxxxx
```

The dev server automatically loads values from `.env.local` when running locally.

---

### 2. Test Different Configurations

Use `--env` to quickly test different configurations:

```bash
# Test in different region
agentcore dev --env AWS_REGION=eu-west-1

# Test with verbose logging
agentcore dev --env LOG_LEVEL=DEBUG

# Test without memory
agentcore dev --env BEDROCK_AGENTCORE_MEMORY_ID=""
```

---

### 3. Keep Dev Server Running

Leave the dev server running in one terminal while you work in your editor. The hot reload will handle restarts automatically.

---

### 4. Use Multiple Terminal Windows

- **Terminal 1**: Run `agentcore dev`
- **Terminal 2**: Run `agentcore invoke --dev "test queries"`
- **Terminal 3**: Edit code, run tests, view logs

---

## Next Steps

- **Deploy your agent**: Use [`agentcore launch`](../runtime/quickstart.md) for simple deployments
- **Add more tools**: Integrate MCP tools or custom functions
- **Configure memory**: Set up [AgentCore Memory](../memory/quickstart.md) for stateful agents
- **Review logs**: Monitor uvicorn output for errors or performance issues

---
