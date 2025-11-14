# Observability & Evaluation Quick Start

Get insights into your agent's behavior and evaluate its performance using the CLI.

## Overview

The toolkit provides three simple commands:
- **`agentcore obs`** - View traces and understand what your agent is doing
- **`agentcore eval`** - Evaluate your agent's performance with built-in evaluators

## Prerequisites

1. **Configure your agent** with a `.bedrock_agentcore.yaml` file
2. **Run your agent** to generate traces

## Quick Start: 3-Step Workflow

### 1. Test Your Agent

```bash
# Invoke your agent with a prompt
agentcore invoke '{"prompt": "What is my favorite color?"}'
```

This stores the session ID in your config for easy access.

### 2. View Agent Traces

```bash
# List all traces in your session
agentcore obs list

# Show detailed trace visualization
agentcore obs show
```

### 3. Evaluate Performance

```bash
# Evaluate with default evaluator (Helpfulness)
agentcore eval run

# Use multiple evaluators
agentcore eval run -e Builtin.Helpfulness -e Builtin.GoalSuccessRate
```
