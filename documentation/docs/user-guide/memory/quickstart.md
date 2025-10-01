# Getting Started with AgentCore Memory

Amazon Bedrock AgentCore Memory lets you create and manage memory resources that store conversation context for your AI agents. This section guides you through installing dependencies and implementing both short-term and long-term memory features. 

The steps are as follows

1. Create a memory resource containing a semantic strategy
2. Write events (conversation history) to the memory resource.
3. Retrieve memory records from long term memory
4. Integrate with an agent

## Prerequisites

### Before starting, make sure you have:

* **AWS Account** with credentials configured (`aws configure`)
* **Python 3.10+** installed


To get started with Amazon Bedrock AgentCore Memory, make a folder for this quick start, create a virtual environment, and install the dependencies. The below command can be run directly in the terminal.

```bash
mkdir agentcore-memory-quickstart
cd agentcore-memory-quickstart
python -m venv .venv
source .venv/bin/activate
pip install bedrock-agentcore
```


**Note: The AgentCore Starter Toolkit is intended to help developers get started quickly. The Boto3 Python library provides the most comprehensive set of operations for AgentCore Memory. You can find the Boto3 documentation here.**


## Step One: Create a Memory Resource

A memory resource is needed to start storing information for your agent. By default, memory events (which we refer to as short-term memory) can be written to a memory resource. In order for insights to be extracted and placed into long term memory records, the resource requires a 'memory strategy' - a configuration that defines how conversational data should be processed, and what information to extract (such as facts, preferences, or summaries).

We are going to create a memory resource with a semantic strategy so that both short term and long term memory can be utilized. This will take 1-2 minutes. Memory resources can also be created in the AWS console.

```python
from bedrock_agentcore.memory import MemoryManager
from bedrock_agentcore.session import MemorySessionManager
from bedrock_agentcore.constants import StrategyType
from bedrock_agentcore.models.strategies.semantic import SemanticStrategy

memory_manager = MemoryManager(region_name="us-west-2")

print("Creating memory resource...")

memory = memory_manager.get_or_create_memory(
    name="CustomerSupportSemantic",
    description="Customer suppoer memory store",
    strategies=[
        SemanticStrategy(
            name="semanticLongTermMemory",
        )
    ]
)

print(f"Memory ID: {memory.get('id')}")
```


You can call list_memories to see that the memory resource has been created with:

```python
memories = memory_manager.list_memories()
```



## Step Two: Write events to memory

Writing events to memory has multiple purposes. First, event contents (most commonly conversation history) are stored as short term memory. Second, relevant insights are pulled from events and written into memory records as a part of long term memory.

The memory resource id, actor id, and session id are required to create an event. We are going to create three events, simulating messages between an end user and a chat bot.
 

```python
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
```


You can get events for a specific actor after they’ve been written.


```python
# List all events in the session
events = session_manager.list_events(
    actor_id="User1",
    session_id="OrderSupportSession1"
)
```


In this case, we can see the last three events for the actor and session.

## Step Three: Retrieve records from long term memory

After the events were written to the memory resource, they were analyzed and useful information was sent to long term memory. Since the memory contains a semantic long term memory strategy, the system extracts and stores factual information.

You can list all memory records with:

```python
# List all memory records
memory_records = session_manager.list_memory_records(
    memoryId=memory.get("id"),
    namespace="/"
)
```

Or ask for the most relevant information as part of a semantic search:

```python
# Perform a semantic search
memory_records = session_manager.retrieve_memory_records(
    memoryId=memory.get("id"),
    namespace="/",
    searchCriteria={
        "searchQuery": "can you summarize the support issue",
        "topK": 3})
```


Important information about the user is likely stored is long term memory. Agents can use long term memory rather than a full conversation history to make sure that LLMs are not overloaded with context.

The full example source file showing steps 1 - 3 is available [here](../../examples/semantic_search.md).

## Step Four: Putting it all together

Now that the concepts are clear, let’s incorporate this in an agent. The following example shows a conversational AI agent built using the Strands SDK that automatically extracts and remembers user preferences from conversations. 

Install dependencies for the strands SDK.

```bash
pip install strands
pip install flask
```

Create a new file called `preference_saver.py` and add the following code.

```python
from bedrock_agentcore.memory import MemoryManager
from bedrock_agentcore.session import MemorySessionManager
from bedrock_agentcore.constants import StrategyType, ConversationalMessage, MessageRole
from strands import Agent
from flask import Flask, request, jsonify
import uuid

# Initialize memory storage for the agent
# This creates a persistent memory that can store user preferences and conversation history
memory_manager = MemoryManager(region_name="us-west-2")
memory = memory_manager.create_memory_and_wait(
    name=f"PreferenceSaverMemory",
    strategies=[
        {
            # User preference strategy stores personalized information about each user
            StrategyType.USER_PREFERENCE.value: {
                "name": "UserPreference",
                "namespaces": ["/users/{actorId}"],  # Separate memory space per user
            }
        }
    ],
)
memory_id = memory["id"]
print(f"✅ Memory created: {memory_id}")

# Session manager handles conversation turns and memory retrieval
session_manager = MemorySessionManager(memory_id=memory_id, region_name="us-west-2")

# Initialize the conversational AI agent
agent = Agent()

# Create Flask web server to handle HTTP requests
app = Flask(__name__)

@app.route('/invoke', methods=['POST'])
def invoke():
    """
    Main endpoint for processing user messages.
    Retrieves relevant memories, generates a response, and saves the conversation.
    """
    payload = request.get_json()
    message = payload.get("message", "Hello!")
    user_id = payload.get("user_id", "user1")
    session_id = f"session_{user_id}"

    # Retrieve relevant memories for context
    # This searches the user's memory for information related to their current message
    try:
        memories = session_manager.retrieve_memory_records(
            memoryId=memory_id,
            namespace=f"/users/{user_id}",
            searchCriteria={"searchQuery": message, "topK": 3}
        )
        # Extract content from memory records to provide context
        context = "\n".join([m.get("content", "") for m in memories.get("memoryRecordSummaries", [])])
        if context:
            # Prepend relevant memories to the current message for better responses
            message = f"Previous: {context}\n\n{message}"
    except:
        # Continue without memory context if retrieval fails
        pass

    # Generate response using the AI agent
    response = agent(message)

    # Save the conversation turn to memory for future reference
    # This stores both the user's message and the agent's response
    try:
        session_manager.add_turns(
            actor_id=user_id,
            session_id=session_id,
            messages=[
                ConversationalMessage(payload.get('message'), MessageRole.USER),
                ConversationalMessage(response.message, MessageRole.ASSISTANT)
            ]
        )
    except:
        # Continue even if memory saving fails
        pass

    return jsonify({"response": response.message})

if __name__ == "__main__":
    print("🚀 Starting memory-enhanced conversational agent server on port 8080...")
    print("Send POST requests to http://localhost:8080/invoke with JSON: {'message': 'your message', 'user_id': 'user123'}")
    app.run(host='0.0.0.0', port=8080, debug=True)
```

Execute the agent code with:

```bash
python `preference_saver.py`
```

and wait for the “Memory created” message. In another terminal, invoke the agent using the following commands:

#### Invocation 1:
```bash
curl -X POST http://localhost:8080/invoke -H "Content-Type: application/json" -d '{"message": "My name is Alice and I like pepperoni on pizza", "user_id": "alice"}'
```

The preference is extracted asynchronously and can take up to a minute to be extracted. Please give it a minute before the next invocation.

#### Invocation 2:

```bash
curl -X POST http://localhost:8080/invoke -H "Content-Type: application/json" -d '{"message": "What topping do I like on pizza?", "user_id": "alice"}'
```


The agent stores each conversation turn as a memory event, allowing the UserPreferenceMemoryStrategy to automatically extract and consolidate personal preferences over time. Before responding to new messages, it queries the
memory store to retrieve relevant context, then saves the new user-bot exchange as another memory event.

The end result is a context-aware agent!

## What’s Next?

Consider the following as you continue your AgentCore journey

* Add another strategy to your memory resource
* Enable observability for more visibility into how memory is working
* Look at the vast collection of samples to familiarize yourself with other use cases.

