# Semantic Search Memory Example

This example demonstrates the complete workflow for creating a memory resource with semantic strategy, writing events, and retrieving memory records.

```python
# Semantic Search Memory Example

from bedrock_agentcore_starter_toolkit.operations.memory.manager import MemoryManager
from bedrock_agentcore.memory.session import MemorySessionManager
from bedrock_agentcore.memory.constants import ConversationalMessage, MessageRole
from bedrock_agentcore_starter_toolkit.operations.memory.models.strategies import SemanticStrategy
import time

memory_manager = MemoryManager(region_name="us-west-2")

print("Creating memory resource...")

memory = memory_manager.get_or_create_memory(
    name="CustomerSupportSemantic",
    description="Customer support memory store",
    strategies=[
        SemanticStrategy(
            name="semanticLongTermMemory",
            namespaces=['/strategies/{memoryStrategyId}/actors/{actorId}'],
        )
    ]
)

print(f"Memory ID: {memory.get('id')}")

# Create a session to store memory events
session_manager = MemorySessionManager(
    memory_id=memory.get("id"),
    region_name="us-west-2")

# Write memory events (conversation turns)
session_manager.add_turns(
    actor_id="User1",
    session_id="OrderSupportSession1",
    messages=[
        ConversationalMessage(
            "Hi, how can I help you today?",
            MessageRole.ASSISTANT)],
)

session_manager.add_turns(
    actor_id="User1",
    session_id="OrderSupportSession1",
    messages=[
        ConversationalMessage(
            "Hi, I am a new customer. I just made an order, but it hasn't arrived. The Order number is #35476",
            MessageRole.USER)],
)

session_manager.add_turns(
    actor_id="User1",
    session_id="OrderSupportSession1",
    messages=[
        ConversationalMessage(
            "I'm sorry to hear that. Let me look up your order.",
            MessageRole.ASSISTANT)],
)

# List all events in the session
events = session_manager.list_events(
    actor_id="User1",
    session_id="OrderSupportSession1",
)

for event in events:
    print(f"Event: {event}")
    print("--------------------------------------------------------------------")

print("Waiting 2 minutes for semantic processing...")
time.sleep(120)

# List all memory records
memory_records = session_manager.list_long_term_memory_records(
    namespace_prefix="/"
)

for record in memory_records:
    print(f"Memory record: {record}")
    print("--------------------------------------------------------------------")

# Perform a semantic search
memory_records = session_manager.search_long_term_memories(
    query="can you summarize the support issue",
    namespace_prefix="/",
    top_k=3
)

for record in memory_records:
    print(f"retrieved memory: {record}")
    print("--------------------------------------------------------------------")

```
