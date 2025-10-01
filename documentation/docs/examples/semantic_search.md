# Semantic Search Memory Example

This example demonstrates the complete workflow for creating a memory resource with semantic strategy, writing events, and retrieving memory records.

```python
import time
from bedrock_agentcore.memory import MemoryManager
from bedrock_agentcore.models.strategies.semantic import SemanticStrategy
from bedrock_agentcore.session import MemorySessionManager
from bedrock_agentcore.constants import ConversationalMessage, MessageRole

memory_manager = MemoryManager(region_name="us-west-2")

print("Creating memory resource...")

memory = memory_manager.get_or_create_memory(
    name="CustomerSupportSemantic5",
    description="Customer support memory store",
    strategies=[
        SemanticStrategy(
            name="semanticLongTermMemory",
        )
    ]
)

print(f"Memory ID: {memory.get('id')}")

# View all memories
memories = memory_manager.list_memories()
for memory in memories:
    print(f"Memory: {memory}")

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

print("Waiting 30 seconds for semantic processing...")
time.sleep(30)

# List all memory records
memory_records = session_manager.list_memory_records(
    memoryId=memory.get("id"),
    namespace="/"
)

for record in memory_records.get("memoryRecordSummaries", []):
    print(f"Memory record: {record}")
    print("--------------------------------------------------------------------")

# Perform a semantic search
memory_records = session_manager.retrieve_memory_records(
    memoryId=memory.get("id"),
    namespace="/",
    searchCriteria={
        "searchQuery": "can you summarize the support issue",
        "topK": 3})

for record in memory_records.get("memoryRecordSummaries", []):
    print(f"retrieved memory: {record}")
    print("--------------------------------------------------------------------")
```
