# MemoryManager Comprehensive Guide

A high-level client for managing AWS Bedrock AgentCore Memory resources with full lifecycle management, strategy support, and advanced features.

## Table of Contents

1. [Overview](#overview)
2. [Installation & Setup](#installation--setup)
3. [Quick Start](#quick-start)
4. [Strategy Types Guide](#strategy-types-guide)
5. [Advanced Usage](#advanced-usage)
6. [Error Handling](#error-handling)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

## Overview

The `MemoryManager` class provides a comprehensive interface for managing AWS Bedrock AgentCore Memory resources. It handles all **Bedrock-agentcore-control operations** for creating, configuring, and managing memory resources that enable AI agents to retain and recall information across conversations and sessions. AgentCore Memory transforms stateless AI interactions into intelligent, context-aware experiences by automatically storing, organizing, and retrieving relevant information, allowing your agents to build relationships, remember preferences, and provide increasingly personalized responses over time.

### Key Features

- **Full Lifecycle Management**: Create, read, update, delete memories with automatic status polling
- **Strategy Management**: Add, modify, delete memory strategies of various types
- **Type Safety**: Support for strongly-typed strategy objects with validation
- **Backward Compatibility**: Works with existing dictionary-based strategy configurations
- **Advanced Polling**: Automatic waiting for resource state transitions
- **Error Handling**: Comprehensive error handling with detailed logging

### Supported Strategy Types

- **Semantic Memory Strategy**: Extract semantic information from conversations
- **Summary Memory Strategy**: Create summaries of conversation content
- **User Preference Strategy**: Store and manage user preferences
- **Custom Semantic Strategy**: Custom extraction and consolidation with specific prompts
- **Custom Summary Strategy**: Custom consolidation with specific prompts
- **Custom User Preference Strategy**: Custom extraction and consolidation with specific prompts

## Installation & Setup

```python
from bedrock_agentcore_starter_toolkit.operations.memory.manager import MemoryManager
from bedrock_agentcore_starter_toolkit.operations.memory.models import (
    SemanticStrategy, SummaryStrategy, UserPreferenceStrategy,
    CustomSemanticStrategy, ExtractionConfig, ConsolidationConfig
)

# Initialize with default region
manager = MemoryManager()

# Initialize with specific region
manager = MemoryManager(region_name="us-east-1")

# Initialize with custom boto3 session
import boto3
session = boto3.Session(profile_name="my-profile")
manager = MemoryManager(boto3_session=session)

# Initialize with both (must match)
manager = MemoryManager(region_name="us-east-1", boto3_session=session)

# Initialize with custom boto client configuration
from botocore.config import Config as BotocoreConfig

# Custom retry and timeout configuration
custom_config = BotocoreConfig(
    retries={'max_attempts': 5, 'mode': 'adaptive'},
    read_timeout=60,
    connect_timeout=30,
    max_pool_connections=50
)
manager = MemoryManager(region_name="us-east-1", boto_client_config=custom_config)

# Custom configuration with existing user agent (will be preserved and extended)
custom_config_with_agent = BotocoreConfig(
    user_agent_extra="my-application/1.0",
    retries={'max_attempts': 3}
)
manager = MemoryManager(region_name="us-east-1", boto_client_config=custom_config_with_agent)

# Combine all initialization options
manager = MemoryManager(
    region_name="us-east-1",
    boto3_session=session,
    boto_client_config=custom_config
)
```

## Quick Start

### Basic Memory Creation

```python
# Create a simple memory with semantic strategy
from bedrock_agentcore_starter_toolkit.operations.memory.models import SemanticStrategy

manager = MemoryManager(region_name="us-east-1")

# Using typed strategy (recommended)
semantic_strategy = SemanticStrategy(
    name="ConversationSemantics",
    description="Extract semantic information from conversations",
    namespaces=["semantics/{actorId}/{sessionId}"]
)

memory = manager.create_memory_and_wait(
    name="MyMemory",
    strategies=[semantic_strategy],
    description="My first memory resource"
)

print(f"Created memory: {memory.id}")
```

### Get or Create Pattern

```python
# Get existing memory or create if it doesn't exist
memory = manager.get_or_create_memory(
    name="PersistentMemory",
    strategies=[semantic_strategy],
    description="Always available memory"
)
```

### List and Manage Memories

```python
# List all memories
memories = manager.list_memories()
for memory_summary in memories:
    print(f"Memory: {memory_summary.id} - {memory_summary.name} ({memory_summary.status})")

# Get specific memory details
memory = manager.get_memory("mem-123")
print(f"Memory status: {memory.status}")

# Delete memory
manager.delete_memory_and_wait("mem-123")
```

### Create Memory and wait

```python
from bedrock_agentcore_starter_toolkit.operations.memory.models import (
    SemanticStrategy, CustomSemanticStrategy, ExtractionConfig, ConsolidationConfig
)

# Create with typed strategies
semantic = SemanticStrategy(name="MySemanticStrategy")
custom = CustomSemanticStrategy(
    name="MyCustomStrategy",
    extraction_config=ExtractionConfig(
        append_to_prompt="Extract insights",
        model_id="anthropic.claude-3-sonnet-20240229-v1:0"
    ),
    consolidation_config=ConsolidationConfig(
        append_to_prompt="Consolidate insights",
        model_id="anthropic.claude-3-haiku-20240307-v1:0"
    )
)

memory = manager.create_memory_and_wait(
    name="TypedMemory",
    strategies=[semantic, custom],
    description="Memory with typed strategies",
    event_expiry_days=120,
    memory_execution_role_arn="arn:aws:iam::123456789012:role/MemoryRole"
)
```

#### Get Memory

```python
memory = manager.get_memory("mem-123")
print(f"Memory: {memory.name} - Status: {memory.status}")
print(f"Description: {memory.description}")
```

#### List Memories

```python
# List all memories
memories = manager.list_memories()
for memory in memories:
    print(f"ID: {memory.id}")
    print(f"Name: {memory.name}")
    print(f"Status: {memory.status}")

# List with limit
recent_memories = manager.list_memories(max_results=10)
```

#### Delete Memory
```python
# Delete and wait for completion
response = manager.delete_memory_and_wait("mem-123")
print("Memory successfully deleted")
```

---

### Status and Information Methods

#### Get Memory Status

```python
status = manager.get_memory_status("mem-123")
print(f"Memory status: {status}")

# Check if memory is ready
if status == "ACTIVE":
    print("Memory is ready for use")
```

#### Get Memory Strategies

```python
strategies = manager.get_memory_strategies("mem-123")
for strategy in strategies:
    print(f"Strategy: {strategy.name} ({strategy.type})")
    print(f"ID: {strategy.strategyId}")
    print(f"Status: {strategy.get('status', 'N/A')}")
```

---

### Strategy Management Methods

```python
from bedrock_agentcore_starter_toolkit.operations.memory.models import SummaryStrategy

# Add typed strategy
summary = SummaryStrategy(
    name="ConversationSummary",
    description="Summarize conversations",
    namespaces=["summaries/{actorId}/{sessionId}"]
)

memory = manager.add_strategy_and_wait(
    memory_id="mem-123",
    strategy=summary
)

# Add custom strategy with configurations
custom = CustomSemanticStrategy(
    name="CustomStrategy",
    extraction_config=ExtractionConfig(
        append_to_prompt="Extract key insights",
        model_id="anthropic.claude-3-sonnet-20240229-v1:0"
    ),
    consolidation_config=ConsolidationConfig(
        append_to_prompt="Consolidate insights",
        model_id="anthropic.claude-3-haiku-20240307-v1:0"
    )
)

memory = manager.add_strategy_and_wait(
    memory_id="mem-123",
    strategy=custom
)
```

#### Update Memory Strategies

```python
# Add multiple strategies
new_strategies = [
    SemanticStrategy(name="NewSemantic"),
    SummaryStrategy(name="NewSummary")
]

memory = manager.update_memory_strategies_and_wait(
    memory_id="mem-123",
    add_strategies=new_strategies
)

# Modify existing strategy
modify_configs = [{
    "strategyId": "strat-456",
    "description": "Updated description",
    "namespaces": ["updated/{actorId}"]
}]

memory = manager.update_memory_strategies_and_wait(
    memory_id="mem-123",
    modify_strategies=modify_configs
)

# Delete strategies
memory = manager.update_memory_strategies_and_wait(
    memory_id="mem-123",
    delete_strategy_ids=["strat-789", "strat-101"]
)

# Combined operations
memory = manager.update_memory_strategies_and_wait(
    memory_id="mem-123",
    add_strategies=[SemanticStrategy(name="NewStrategy")],
    modify_strategies=[{"strategyId": "strat-456", "description": "Updated"}],
    delete_strategy_ids=["strat-old"]
)
```

#### Modify Strategy

```python
# Update strategy description and namespaces
memory = manager.modify_strategy(
    memory_id="mem-123",
    strategy_id="strat-456",
    description="Updated strategy description",
    namespaces=["custom/{actorId}/{sessionId}"]
)

# Update strategy configuration
memory = manager.modify_strategy(
    memory_id="mem-123",
    strategy_id="strat-456",
    configuration={
        "extraction": {
            "appendToPrompt": "New extraction prompt",
            "modelId": "anthropic.claude-3-sonnet-20240229-v1:0"
        }
    }
)
```

#### Delete strategy

```python
memory = manager.delete_strategy(
    memory_id="mem-123",
    strategy_id="strat-456"
)
```

---

### Convenience Strategy Methods

```python
memory = manager.add_semantic_strategy_and_wait(
    memory_id="mem-123",
    name="ConversationSemantics",
    description="Extract semantic information",
    namespaces=["semantics/{actorId}/{sessionId}"]
)
```

```python
memory = manager.add_summary_strategy_and_wait(
    memory_id="mem-123",
    name="ConversationSummary",
    description="Summarize conversations",
    namespaces=["summaries/{actorId}/{sessionId}"]
)
```

```python
memory = manager.add_user_preference_strategy_and_wait(
    memory_id="mem-123",
    name="UserPreferences",
    description="Store user preferences",
    namespaces=["preferences/{actorId}"]
)
```

```python
extraction_config = {
    "prompt": "Extract key business insights from the conversation",
    "modelId": "anthropic.claude-3-sonnet-20240229-v1:0"
}

consolidation_config = {
    "prompt": "Consolidate business insights into actionable summaries",
    "modelId": "anthropic.claude-3-haiku-20240307-v1:0"
}

memory = manager.add_custom_semantic_strategy_and_wait(
    memory_id="mem-123",
    name="BusinessInsights",
    extraction_config=extraction_config,
    consolidation_config=consolidation_config,
    description="Extract and consolidate business insights"
)
```

## Strategy Types Guide

```python
from bedrock_agentcore_starter_toolkit.operations.memory.models import SemanticStrategy

# Basic semantic strategy
semantic = SemanticStrategy(
    name="ConversationSemantics",
    description="Extract semantic information from conversations"
)

# With custom namespaces
semantic = SemanticStrategy(
    name="ConversationSemantics",
    description="Extract semantic information from conversations",
    namespaces=["semantics/{actorId}/{sessionId}"]
)

# Add to memory
memory = manager.add_strategy_and_wait(memory_id="mem-123", strategy=semantic)
```

### Summary Strategy

```python
from bedrock_agentcore_starter_toolkit.operations.memory.models import SummaryStrategy

# Basic summary strategy
summary = SummaryStrategy(
    name="ConversationSummary",
    description="Summarize conversation content"
)

# With custom namespaces
summary = SummaryStrategy(
    name="ConversationSummary",
    description="Summarize conversation content",
    namespaces=["summaries/{actorId}/{sessionId}"]
)

# Add to memory
memory = manager.add_strategy_and_wait(memory_id="mem-123", strategy=summary)
```

### User Preference Strategy

```python
from bedrock_agentcore_starter_toolkit.operations.memory.models import UserPreferenceStrategy

# User preference strategy
user_pref = UserPreferenceStrategy(
    name="UserPreferences",
    description="Store user preferences and settings",
    namespaces=["preferences/{actorId}"]  # Note: typically per-actor, not per-session
)

# Add to memory
memory = manager.add_strategy_and_wait(memory_id="mem-123", strategy=user_pref)
```

### Custom Semantic Strategy

```python
from bedrock_agentcore_starter_toolkit.operations.memory.models import (
    CustomSemanticStrategy, ExtractionConfig, ConsolidationConfig
)

# Create configuration objects
extraction_config = ExtractionConfig(
    append_to_prompt="Extract key business insights and action items from the conversation",
    model_id="anthropic.claude-3-sonnet-20240229-v1:0"
)

consolidation_config = ConsolidationConfig(
    append_to_prompt="Consolidate business insights into actionable summaries with priorities",
    model_id="anthropic.claude-3-haiku-20240307-v1:0"
)

# Create custom strategy
custom = CustomSemanticStrategy(
    name="BusinessInsights",
    description="Extract and consolidate business insights",
    extraction_config=extraction_config,
    consolidation_config=consolidation_config,
    namespaces=["business/{actorId}/{sessionId}"]
)

# Add to memory
memory = manager.add_strategy_and_wait(memory_id="mem-123", strategy=custom)
```

### Dictionary Strategies

For backward compatibility, dictionary-based strategies are still supported:

```python
# Dictionary semantic strategy
semantic = {
    "semanticMemoryStrategy": {
        "name": "SemanticStrategy",
        "description": "dictionary-based strategy",
        "namespaces": ["business/{actorId}/{sessionId}"]
    }
}

# Dictionary summary strategy
summary = {
    "summaryMemoryStrategy": {
        "name": "SummaryStrategy",
        "description": "summary strategy"
    }
}

# Mix typed and Dictionary strategies
mixed_strategies = [
    SemanticStrategy(name="TypedStrategy"),
    semantic, summary
]

memory = manager.create_memory_and_wait(
    name="MixedMemory",
    strategies=mixed_strategies
)
```

## Advanced Usage

### Namespace Patterns

Namespaces support template variables for dynamic organization:

```python
# Available template variables
namespaces = [
    "global/shared",                   # Static namespace
    "actor/{actorId}",                 # Per-actor namespace
    "session/{actorId}/{sessionId}",   # Per-session namespace
    "strategy/{strategyId}",           # Per-strategy namespace
    "custom/{actorId}/{sessionId}"     # Custom pattern
]

strategy = SemanticStrategy(
    name="FlexibleStrategy",
    namespaces=namespaces
)
```

### Batch Strategy Operations

```python
# Add multiple strategies at once
strategies_to_add = [
    SemanticStrategy(name="Semantic1"),
    SummaryStrategy(name="Summary1"),
    UserPreferenceStrategy(name="UserPref1")
]

# Modify multiple strategies
strategies_to_modify = [
    {"strategyId": "strat-1", "description": "Updated description 1"},
    {"strategyId": "strat-2", "description": "Updated description 2"}
]

# Delete multiple strategies
strategy_ids_to_delete = ["strat-3", "strat-4"]

# Execute all operations in one call
memory = manager.update_memory_strategies_and_wait(
    memory_id="mem-123",
    add_strategies=strategies_to_add,
    modify_strategies=strategies_to_modify,
    delete_strategy_ids=strategy_ids_to_delete
)
```

### Custom Polling Configuration

```python
# Create memory with custom polling
memory = manager.create_memory_and_wait(
    name="SlowMemory",
    strategies=[SemanticStrategy(name="Strategy1")],
    max_wait=600,      # Wait up to 10 minutes
    poll_interval=30   # Check every 30 seconds
)

# Add strategy with custom polling
memory = manager.add_strategy_and_wait(
    memory_id="mem-123",
    strategy=SummaryStrategy(name="SlowStrategy"),
    max_wait=900,      # Wait up to 15 minutes
    poll_interval=60   # Check every minute
)
```

### Memory Configuration Options

```python
# Full memory configuration
memory = manager.create_memory_and_wait(
    name="FullyConfiguredMemory",
    strategies=[SemanticStrategy(name="Strategy1")],
    description="A fully configured memory resource",
    event_expiry_days=180,  # Keep events for 6 months
    memory_execution_role_arn="arn:aws:iam::123456789012:role/MemoryExecutionRole",
    encryption_key_arn="arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012"
)
```

### Custom Boto Client Configuration

The `boto_client_config` parameter allows you to customize the underlying boto3 client behavior for advanced use cases:

```python
from botocore.config import Config as BotocoreConfig

# Production configuration with enhanced reliability
production_config = BotocoreConfig(
    retries={
        'max_attempts': 10,
        'mode': 'adaptive'  # Adaptive retry mode for better handling of throttling
    },
    read_timeout=120,       # 2 minutes for read operations
    connect_timeout=60,     # 1 minute for connection establishment
    max_pool_connections=50 # Higher connection pool for concurrent operations
)

manager = MemoryManager(
    region_name="us-east-1",
    boto_client_config=production_config
)

# Development configuration with faster timeouts
dev_config = BotocoreConfig(
    retries={'max_attempts': 3},
    read_timeout=30,
    connect_timeout=10
)

dev_manager = MemoryManager(
    region_name="us-east-1",
    boto_client_config=dev_config
)

# Custom user agent for tracking
tracking_config = BotocoreConfig(
    user_agent_extra="MyApp/2.1.0 Environment/Production",
    retries={'max_attempts': 5}
)

# The final user agent will be: "MyApp/2.1.0 Environment/Production bedrock-agentcore-starter-toolkit"
tracking_manager = MemoryManager(
    region_name="us-east-1",
    boto_client_config=tracking_config
)

# Regional failover configuration
regional_config = BotocoreConfig(
    retries={
        'max_attempts': 8,
        'mode': 'adaptive'
    },
    read_timeout=90,
)

regional_manager = MemoryManager(
    region_name="us-west-2",
    boto_client_config=regional_config
)
```

### Working with Memory Objects

```python
# Memory objects provide dict-like access
memory = manager.get_memory("mem-123")

# Access properties
print(f"ID: {memory.id}")
print(f"Name: {memory.name}")
print(f"Status: {memory.status}")
print(f"Description: {memory.description}")

# Dict-style access
print(f"ID: {memory['id']}")
print(f"Name: {memory['name']}")

# Safe access with defaults
creation_time = memory.get('creationTime', 'Unknown')
```

## Error Handling

### Common Error Patterns

```python
from botocore.exceptions import ClientError

try:
    memory = manager.create_memory_and_wait(
        name="TestMemory",
        strategies=[SemanticStrategy(name="TestStrategy")]
    )
except ClientError as e:
    error_code = e.response['Error']['Code']
    error_message = e.response['Error']['Message']

    if error_code == 'ValidationException':
        print(f"Invalid parameters: {error_message}")
    elif error_code == 'ResourceNotFoundException':
        print(f"Resource not found: {error_message}")
    elif error_code == 'AccessDeniedException':
        print(f"Access denied: {error_message}")
    else:
        print(f"AWS error ({error_code}): {error_message}")

except TimeoutError as e:
    print(f"Operation timed out: {e}")

except RuntimeError as e:
    print(f"Memory operation failed: {e}")

except Exception as e:
    print(f"Unexpected error: {e}")
```

### Handling Memory State Transitions

```python
# Check memory status before operations
def safe_add_strategy(manager, memory_id, strategy):
    """Safely add a strategy, handling state transitions."""
    try:
        status = manager.get_memory_status(memory_id)
        if status != "ACTIVE":
            print(f"Memory is {status}, waiting for ACTIVE state...")
            # Could implement custom waiting logic here

        return manager.add_strategy_and_wait(memory_id, strategy)

    except ClientError as e:
        if e.response['Error']['Code'] == 'ConflictException':
            print("Memory is being modified, retrying...")
            # Could implement retry logic here
        raise
```

### Strategy Validation

```python
# Validate strategy configuration before adding
def validate_and_add_strategy(manager, memory_id, strategy):
    """Validate strategy before adding to memory."""
    if isinstance(strategy, BaseStrategy):
        # Pydantic validation happens automatically
        try:
            strategy_dict = strategy.to_dict()
        except ValidationError as e:
            print(f"Strategy validation failed: {e}")
            return None

    return manager.add_strategy_and_wait(memory_id, strategy)
```

## Best Practices

### 1. Use Typed Strategies

```python
# ✅ Recommended: Use typed strategies
semantic = SemanticStrategy(
    name="ConversationSemantics",
    description="Extract semantic information"
)

# ❌ Avoid: Dictionary strategies (unless migrating)
semantic_dict = {
    "semanticMemoryStrategy": {
        "name": "ConversationSemantics",
        "description": "Extract semantic information"
    }
}
```

### 2. Always Use Wait Methods

```python
# ✅ Recommended: Use wait methods for reliability
memory = manager.create_memory_and_wait(name="MyMemory", strategies=[strategy])
memory = manager.add_strategy_and_wait(memory_id, new_strategy)

# ❌ Avoid: Non-wait methods (unless you handle state management)
memory = manager._create_memory(name="MyMemory", strategies=[strategy])  # Private method
memory = manager.add_strategy(memory_id, new_strategy)  # May leave memory in CREATING state
```

### 3. Use Descriptive Names and Namespaces

```python
# ✅ Recommended: Clear, descriptive names
semantic = SemanticStrategy(
    name="CustomerSupportSemantics",
    description="Extract semantic information from customer support conversations",
    namespaces=["support/semantics/{actorId}/{sessionId}"]
)

# ❌ Avoid: Generic names
semantic = SemanticStrategy(name="Strategy1")
```

### 4. Handle Errors Gracefully

```python
# ✅ Recommended: Comprehensive error handling
def create_memory_safely(manager, name, strategies):
    """Create memory with proper error handling."""
    try:
        return manager.create_memory_and_wait(name=name, strategies=strategies)
    except TimeoutError:
        print(f"Memory creation timed out for {name}")
        # Could check status and decide whether to wait longer
        return None
    except ClientError as e:
        print(f"Failed to create memory {name}: {e}")
        return None
```

### 5. Use Get-or-Create Pattern

```python
# ✅ Recommended: Use get_or_create for idempotent operations
memory = manager.get_or_create_memory(
    name="PersistentMemory",
    strategies=[SemanticStrategy(name="DefaultStrategy")]
)

# This is safe to call multiple times
```

### 6. Organize Strategies by Purpose

```python
# ✅ Recommended: Group related strategies
conversation_strategies = [
    SemanticStrategy(
        name="ConversationSemantics",
        namespaces=["conversation/semantics/{actorId}/{sessionId}"]
    ),
    SummaryStrategy(
        name="ConversationSummary",
        namespaces=["conversation/summaries/{actorId}/{sessionId}"]
    )
]

user_strategies = [
    UserPreferenceStrategy(
        name="UserPreferences",
        namespaces=["user/preferences/{actorId}"]
    )
]

# Create separate memories or combine them
memory = manager.create_memory_and_wait(
    name="ConversationMemory",
    strategies=conversation_strategies + user_strategies
)
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Memory Stuck in CREATING State

**Problem**: Memory remains in CREATING state and never becomes ACTIVE.

**Possible Causes:**
- Invalid strategy configuration
- Insufficient IAM permissions
- Resource limits exceeded

**Solutions:**
```python
# Check memory status and failure reason
try:
    memory = manager.get_memory("mem-123")
    if memory.status == "FAILED":
        failure_reason = memory.get("failureReason", "Unknown")
        print(f"Memory creation failed: {failure_reason}")
except ClientError as e:
    print(f"Error retrieving memory: {e}")

# Use longer timeout for complex configurations
memory = manager.create_memory_and_wait(
    name="ComplexMemory",
    strategies=complex_strategies,
    max_wait=600,  # 10 minutes instead of default 5
    poll_interval=30  # Check every 30 seconds
)
```

#### 2. Strategy Addition Fails

**Problem**: Adding strategies to existing memory fails.

**Possible Causes:**
- Memory not in ACTIVE state
- Invalid strategy configuration
- Conflicting strategy names

**Solutions:**
```python
# Always check memory status first
status = manager.get_memory_status("mem-123")
if status != "ACTIVE":
    print(f"Memory is {status}, cannot add strategies")
    return

# Use wait methods to handle state transitions
try:
    memory = manager.add_strategy_and_wait(
        memory_id="mem-123",
        strategy=new_strategy,
        max_wait=300
    )
except TimeoutError:
    print("Strategy addition timed out")
except RuntimeError as e:
    print(f"Strategy addition failed: {e}")
```

#### 3. Permission Errors

**Problem**: Access denied errors when managing memories.

**Required IAM Permissions:**
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock-agentcore-control:CreateMemory",
                "bedrock-agentcore-control:GetMemory",
                "bedrock-agentcore-control:ListMemories",
                "bedrock-agentcore-control:UpdateMemory",
                "bedrock-agentcore-control:DeleteMemory"
            ],
            "Resource": "*"
        }
    ]
}
```

#### 4. Region Configuration Issues

**Problem**: Resources not found or region mismatch errors.

**Solutions:**
```python
# Ensure consistent region configuration
import boto3

# Option 1: Explicit region
manager = MemoryManager(region_name="us-east-1")

# Option 2: Use session with region
session = boto3.Session(region_name="us-east-1")
manager = MemoryManager(boto3_session=session)

# Option 3: Check current region
session = boto3.Session()
print(f"Current region: {session.region_name}")
manager = MemoryManager(boto3_session=session)
```

#### 5. Strategy Configuration Validation Errors

**Problem**: Pydantic validation errors when creating typed strategies.

**Solutions:**
```python
from pydantic import ValidationError

try:
    strategy = CustomSemanticStrategy(
        name="TestStrategy",
        extraction_config=ExtractionConfig(
            append_to_prompt="Extract insights",
            model_id="invalid-model-id"  # This might cause validation error
        ),
        consolidation_config=ConsolidationConfig(
            append_to_prompt="Consolidate insights",
            model_id="anthropic.claude-3-haiku-20240307-v1:0"
        )
    )
except ValidationError as e:
    print(f"Strategy validation failed: {e}")
    # Fix the configuration and try again
```

### Debugging Tips

#### Enable Debug Logging

```python
import logging

# Enable debug logging for MemoryManager
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('bedrock_agentcore_starter_toolkit.operations.memory.manager')
logger.setLevel(logging.DEBUG)

# Now all MemoryManager operations will show debug information
manager = MemoryManager(region_name="us-east-1")
```

#### Check Resource States

```python
def debug_memory_state(manager, memory_id):
    """Debug helper to check memory and strategy states."""
    try:
        memory = manager.get_memory(memory_id)
        print(f"Memory Status: {memory.status}")

        strategies = manager.get_memory_strategies(memory_id)
        print(f"Number of strategies: {len(strategies)}")

        for strategy in strategies:
            print(f"  Strategy: {strategy.name}")
            print(f"    ID: {strategy.strategyId}")
            print(f"    Type: {strategy.get('type', 'N/A')}")
            print(f"    Status: {strategy.get('status', 'N/A')}")

    except Exception as e:
        print(f"Error debugging memory {memory_id}: {e}")

# Usage
debug_memory_state(manager, "mem-123")
```

#### Validate Strategy Configurations

```python
def validate_strategy_config(strategy):
    """Validate strategy configuration before use."""
    if isinstance(strategy, BaseStrategy):
        try:
            # This will trigger Pydantic validation
            strategy_dict = strategy.to_dict()
            print(f"Strategy {strategy.name} is valid")
            return True
        except Exception as e:
            print(f"Strategy {strategy.name} validation failed: {e}")
            return False
    else:
        print("Dictionary strategy - manual validation needed")
        return True

# Usage
for strategy in strategies:
    validate_strategy_config(strategy)
```

### Performance Considerations

#### Batch Operations

```python
# ✅ Efficient: Batch multiple strategy operations
memory = manager.update_memory_strategies_and_wait(
    memory_id="mem-123",
    add_strategies=[strategy1, strategy2, strategy3],
    modify_strategies=[modify_config1, modify_config2],
    delete_strategy_ids=["old-strat-1", "old-strat-2"]
)

# ❌ Inefficient: Multiple individual operations
manager.add_strategy_and_wait(memory_id, strategy1)
manager.add_strategy_and_wait(memory_id, strategy2)
manager.add_strategy_and_wait(memory_id, strategy3)
```

#### Polling Configuration

```python
# For production environments, consider longer intervals
memory = manager.create_memory_and_wait(
    name="ProductionMemory",
    strategies=strategies,
    max_wait=900,      # 10 minutes to wait longer
    poll_interval=60   # Check every minute to reduce API calls
)

# For development, use shorter intervals for faster feedback
memory = manager.create_memory_and_wait(
    name="DevMemory",
    strategies=strategies,
    max_wait=300,      # 5 minutes
    poll_interval=10   # Check every 10 seconds
)
```

### Memory Limits and Quotas

Be aware of AWS service limits: Check [AWS Bedrock AgentCore documentation](https://docs.aws.amazon.com/bedrock-agentcore/) for limits

### Getting Help

If you encounter issues not covered in this guide:

1. **Check AWS CloudWatch Logs**: Look for detailed error messages
2. **Review IAM Permissions**: Ensure all required permissions are granted
3. **Validate Configurations**: Use the debugging helpers provided above
4. **Check AWS Service Health**: Verify no ongoing service issues
5. **Consult AWS Documentation**: For the latest API changes and limits

---

This comprehensive guide covers all aspects of using the MemoryManager effectively. The documentation includes detailed method references, practical examples, error handling patterns, best practices, and troubleshooting guidance to help you successfully implement memory management in your applications.
