# Usage of Import Agent CLI

This document explains how to use the `import_agent` command.

The workflow can be started with `agentcore create import`. Additionally, the following flags can be provided.

## Available Flags

| Flag | Description | Type | Default |
|------|-------------|------|---------|
| `--region` | AWS Region to use when fetching Bedrock Agents | string | None |
| `--agent-id` | ID of the Bedrock Agent to import | string | None |
| `--agent-alias-id` | ID of the Agent Alias to use | string | None |
| `--target-platform` | Target platform (langchain + langgraph or strands) | string | None |
| `--verbose` | Enable verbose mode | boolean | False |
| `--disable-memory` | Disable AgentCore Memory primitive | boolean | False |
| `--disable-code-interpreter` | Disable AgentCore Code Interpreter primitive | boolean | False |
| `--disable-observability` | Disable AgentCore Observability primitive | boolean | False |
| `--deploy-runtime` | Deploy to AgentCore Runtime | boolean | False |
| `--run-option` | How to run the agent (locally, runtime, none) | string | None |
| `--output-dir` | Output directory for generated code | string | "./output/" |

## Behavior

- If required flags like `--agent-id`, `--agent-alias-id`, or `--target-platform` are not provided, the command will fall back to interactive prompts.
- Boolean flags like `--verbose`, `--debug`, `--disable-memory`, etc. don't require values; their presence sets them to `True`.
- If neither `--verbose` nor `--debug` flags are provided, the command will prompt the user to enable verbose mode.
- `--verbose` will enable verbose mode. Use `--verbose` for standard verbose output for the generated agent.
- Memory, Code Interpreter, and Observability primitives are enabled by default. Use `--disable-memory`, `--disable-code-interpreter`, or `--disable-observability` to disable them.
- If the `--deploy-runtime` flag is not provided, the command will prompt the user whether to deploy the agent to AgentCore Runtime.
- If the `--run-option` flag is not provided, the command will prompt the user to select how to run the agent.
- The `--run-option` can be one of:
  - `locally`: Run the agent locally
  - `runtime`: Run on AgentCore Runtime (requires `--deploy-runtime`)
  - `none`: Don't run the agent
