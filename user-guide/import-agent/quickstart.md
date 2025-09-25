# Import Agent Quick Start

Get started with importing your Bedrock Agent to AgentCore in just a few minutes.

## Prerequisites

- AWS credentials configured with access to Bedrock Agents
- Use `ada` or `aws configure` to ensure that your credentials are available for the utility to assume.
- Bedrock AgentCore Starter Toolkit installed
- An existing Amazon Bedrock Agent

## Basic Usage

### Interactive Mode (Recommended)

The simplest way to get started is with interactive mode:

```
agentcore import-agent
```

The utility will guide you through:

1. **Agent Selection**: Choose your Bedrock Agent and alias
1. **Target Platform**: Select LangChain/LangGraph or Strands
1. **AgentCore Primitives**: Configure Memory, Code Interpreter, Observability
1. **Deployment Options**: Deploy to AgentCore Runtime or run locally

### Command Line Mode

For automation or when you know your parameters:

```
agentcore import-agent \
  --region us-east-1 \
  --agent-id ABCD1234 \
  --agent-alias-id TSTALIASID \
  --target-platform strands \
  --output-dir ./my-agent \
  --deploy-runtime \
  --run-option runtime
```

## Step-by-Step Walkthrough

### 1. Launch the Import Utility

```
agentcore import-agent
```

### 2. Configure AWS Region

```
? Select AWS Region: us-east-1
```

### 3. Select Your Agent

The utility will list your available Bedrock Agents in the selected region:

```
? Select Bedrock Agent:
  > my-customer-service-agent (ID: ABCD1234)
    my-research-agent (ID: EFGH5678)
    my-code-assistant (ID: IJKL9012)
```

### 4. Choose Agent Alias

```
? Select Agent Alias:
  > TSTALIASID (Test)
    PRODALIASID (Production)
```

### 5. Select Target Platform

```
? Choose target platform:
  > strands (1.0.x)
    langchain (0.3.x) + langgraph (0.5.x)
```

### 7. Deployment Options

```
? Deploy to AgentCore Runtime? [y/N]: Y
? How would you like to run the agent?
  > Run on AgentCore Runtime
    Install dependencies and run locally
    Don't run now
```

## Generated Output

After completion, you'll find:

```
./output/
├── strands_agent.py          # Your converted agent
├── requirements.txt          # Dependencies
├── .agentcore-config.yaml   # Deployment configuration
└── README.md                # Generated documentation
```

## Testing Your Agent

### Local Testing

```
cd ./output
python -m pip install -r requirements.txt
python strands_agent.py
```

### AgentCore Runtime Testing

If deployed to runtime:

```
cd ./output
agentcore invoke "Hello, test message"
```

## Common Options

### Enable Debug Mode

Get detailed logging in the output agent:

```
agentcore import-agent --debug
```

### Disable Specific Primitives

Skip certain AgentCore features:

```
agentcore import-agent \
  --disable-memory \
  --disable-code-interpreter
```

### Custom Output Directory

Specify where to generate files:

```
agentcore import-agent --output-dir ./my-custom-agent
```

## Next Steps

- **Review Generated Code**: Examine the converted agent implementation
- **Test Functionality**: Verify your agent works as expected
- **Customize Integration**: Add custom AgentCore primitive configurations
- **Production Deployment**: Deploy to AgentCore Runtime for production usage

For detailed configuration options, see the [Configuration Reference](configuration.html).
