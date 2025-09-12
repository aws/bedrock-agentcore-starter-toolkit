# Getting Started with AgentCore Memory

Amazon Bedrock AgentCore Memory lets you create and manage memory resources that store conversation context for your AI agents. This section guides you through installing dependencies and implementing both short-term and long-term memory features.

## Install Dependencies

To get started with Amazon Bedrock AgentCore Memory, make a folder for this quick start, create a virtual environment, and install the dependencies.

```bash
mkdir agentcore-memory-quickstart
cd agentcore-memory-quickstart
python3 -m venv .venv
source venv/bin/activate
pip install bedrock-agentcore
```

## Create Memory

### Create Memory for Short-term Memory

Adding short-term memory is a quick, one-time setup process. Short-term memory maintains context without persisting historical data. This is useful for tracking current conversation flow, such as customer support interactions. Note that for short-term memory, you don't need to add a memory strategy which is used to extract memories for long-term storage.

```python
from bedrock_agentcore.memory import MemoryClient

client = MemoryClient(region_name="us-west-2")

memory = client.create_memory(
    name="CustomerSupportAgentMemory",
    description="Memory for customer support conversations",
)

# The memory_id will be used in following operations
print(f"Memory ID: {memory.get('id')}")
print(f"Memory: {memory}")
```

### List Existing Memory Resources

If you already have existing memory resources created in Amazon Bedrock AgentCore Memory, you can list them to find their identifiers:

```python
for memory in client.list_memories():
    print(f"Memory Arn: {memory.get('arn')}")
    print(f"Memory ID: {memory.get('id')}")
    print("--------------------------------------------------------------------")
```

## Maintain User Context Using Short-term Memory

### Create Events in Short-term Memory

The create_event action stores agent interactions into short-term memory instantly. You can save conversations either one turn at a time or in batches, depending on your application needs. Each saved interaction can include user messages, assistant responses, and tool actions. The process is synchronous, ensuring no conversation data is lost.

```python
client.create_event(
    memory_id=memory.get("id"), # This is the id from create_memory or list_memories
    actor_id="User84",  # This is the identifier of the actor, could be an agent or end-user.
    session_id="OrderSupportSession1", #Unique id for a particular request/conversation.
    messages=[
        ("Hi, I'm having trouble with my order #12345", "USER"),
        ("I'm sorry to hear that. Let me look up your order.", "ASSISTANT"),
        ("lookup_order(order_id='12345')", "TOOL"),
        ("I see your order was shipped 3 days ago. What specific issue are you experiencing?", "ASSISTANT"),
        ("Actually, before that - I also want to change my email address", "USER"),
        (
            "Of course! I can help with both. Let's start with updating your email. What's your new email?",
            "ASSISTANT",
        ),
        ("newemail@example.com", "USER"),
        ("update_customer_email(old='old@example.com', new='newemail@example.com')", "TOOL"),
        ("Email updated successfully! Now, about your order issue?", "ASSISTANT"),
        ("The package arrived damaged", "USER"),
    ],
)
```

### Load Conversations from Short-term Memory

The list_events method loads conversations from short-term memory using the memory_id, actor_id and session_id. The process is synchronous and returns the conversation data:

```python
conversations = client.list_events(
    memory_id=memory.get("id"),
    actor_id="User84",
    session_id="OrderSupportSession1",
    max_results=5,
)
```

## Long-term Memory

### Create Memory with Long-term Memory

With long-term memory, you can extract and store information from conversations for future use. When you add long-term memory, you can use one of the following strategies:

- **User Preferences (UserPreferenceMemoryStrategy)**: Stores and learns recurring patterns in user behavior, interaction styles, and choices. This enables the agent to automatically adapt its responses to match user preferences across multiple sessions.

- **Semantic Facts (SemanticMemoryStrategy)**: Maintains knowledge of facts and domain-specific information, technical concepts, and their relationships. This allows the agent to provide informed responses based on previously established context and understanding.

- **Session Summaries (SummaryMemoryStrategy)**: Creates condensed representations of interaction content and outcomes. These summaries provide quick reference points for past activities and help optimize context window usage for future interactions.

To create a memory resource with long-term memory, use the create_memory_and_wait method with a strategy. When you add a memory strategy for the first time to a memory resource (either on create or update), it may take 2-3 minutes for it to become ACTIVE:

```python
memory = client.create_memory_and_wait(
    name="MyAgentMemory",
    strategies=[{
        "summaryMemoryStrategy": {
            # Name of the extraction model/strategy
            "name": "SessionSummarizer",
            # Organize facts by session ID for easy retrieval
            # Example: "summaries/User84/session123" contains summary of session123
            "namespaces": ["/summaries/{actorId}/{sessionId}"]
        }
    }]
)
```

If you are already using short-term memory, you can upgrade to use long-term memory by adding a strategy to the existing memory resource:

```python
summary_strategy = client.add_summary_strategy(
    memory_id = memory.get("id"),
    name="SessionSummarizer",
    description="Summarizes conversation sessions",
    namespaces=["/summaries/{actorId}/{sessionId}"] #Namespace allow you to organize all extracted information. This template will extract information for each sessionId belonging to an actor in separate namespace
)
```

!!! note
    Long-term memory records will only be extracted from events that are stored after the newly added strategies become ACTIVE. Conversations stored before a strategy is added will not appear in long-term memory.

### Save Conversations and View Extracted Memories

The following example demonstrates how to save a conversation and retrieve its automatically extracted memories. After saving the conversation, we wait for 1 minute to allow the long-term memory strategies to process and extract meaningful information before retrieving it.

```python
import time

event = client.create_event(
    memory_id=memory.get("id"), # This is the id from create_memory or list_memories
    actor_id="User84",  # This is the identifier of the actor, could be an agent or end-user.
    session_id="OrderSupportSession1",
    messages=[
        ("Hi, I'm having trouble with my order #12345", "USER"),
        ("I'm sorry to hear that. Let me look up your order.", "ASSISTANT"),
        ("lookup_order(order_id='12345')", "TOOL"),
        ("I see your order was shipped 3 days ago. What specific issue are you experiencing?", "ASSISTANT"),
        ("Actually, before that - I also want to change my email address", "USER"),
        (
            "Of course! I can help with both. Let's start with updating your email. What's your new email?",
            "ASSISTANT",
        ),
        ("newemail@example.com", "USER"),
        ("update_customer_email(old='old@example.com', new='newemail@example.com')", "TOOL"),
        ("Email updated successfully! Now, about your order issue?", "ASSISTANT"),
        ("The package arrived damaged", "USER"),
    ],
)

# Wait for meaningful memories to be extracted from the conversation.
time.sleep(60)

# We will query for the summary of the issue using the namespace set in summary strategy above
memories = client.retrieve_memories(
    memory_id=memory.get("id"),
    namespace=f"/summaries/User84/OrderSupportSession1",
    query="can you summarize the support issue"
)
```

## Use Long-term Memory in an Agent

### Install Dependencies

```bash
pip install strands
```

### Add Memory to an Agent

```python
from strands import tool, Agent
from strands_tools.agent_core_memory import AgentCoreMemoryToolProvider
import time
from bedrock_agentcore.memory import MemoryClient

client = MemoryClient(region_name="us-west-2")
memory = client.create_memory_and_wait(
    name="MyAgentMemory",
    strategies=[{
        "userPreferenceMemoryStrategy": {
            "name": "UserPreference",
            "namespaces": ["/users/{actorId}"]
        }
    }]
)

strands_provider = AgentCoreMemoryToolProvider(
    memory_id=memory.get("id"),
    actor_id="CaliforniaPerson",
    session_id="TalkingAboutFood",
    namespace="/users/CaliforniaPerson",
    region="us-west-2"
)
agent = Agent(tools=strands_provider.tools)

agent("Im vegetarian and I prefer restaurants with a quiet atmosphere.")
agent("Im in the mood for Italian cuisine.")
agent("Id prefer something mid-range and located downtown.")
agent("I live in Irvine.")

time.sleep(60)

# This will use the long-term memory tool
agent("I dont remember what I was in a mood for, do you remember?")
```

## Custom Strategies

You can customize existing strategies by specifying your own prompt. This allows you to specify the exact information you want to extract. In the example below, we will create a custom prompt to extract a user's preference about their airline needs.

### Create an IAM Role for the Service

Start by ensuring you have an IAM role with the managed policy `AmazonBedrockAgentCoreMemoryBedrockModelInferenceExecutionRolePolicy`, or create a policy with the following permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream"
            ],
            "Resource": [
                "arn:aws:bedrock:*::foundation-model/*",
                "arn:aws:bedrock:*:*:inference-profile/*"
            ],
            "Condition": {
                "StringEquals": {
                    "aws:ResourceAccount": "${aws:PrincipalAccount}"
                }
            }
        }
    ]
}
```

This role is assumed by the Service to call the model in your AWS account. Use the trust policy below when creating the role or when using the managed policy:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "",
            "Effect": "Allow",
            "Principal": {
                "Service": [
                    "bedrock-agentcore.amazonaws.com"
                ]
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
```

### Create a Long-term Memory with a Custom Strategy

```python
from bedrock_agentcore.memory import MemoryClient

client = MemoryClient(region_name="us-west-2")

# Our custom prompt ensures that we're able to extract a customer's travel preferences.
CUSTOM_PROMPT = """\
You are tasked with analyzing conversations to extract the user's preferences. You'll be analyzing two sets of data:

<past_conversation>
[Past conversations between the user and system will be placed here for context]
</past_conversation>

<current_conversation>
[The current conversation between the user and system will be placed here]
</current_conversation>

Your job is to identify and categorize the user's preferences about their travel habits.
- Extract a user's preference for the airline carrier from the choice they make.
- Extract a user's preference for the seat type on the airline from the choice they make. It can aisle, middle or window
"""

# Replace the value with the role arn created above.
MEMORY_EXECUTION_ROLE_ARN = "arn:aws:iam::123456789012:role/MyRole"

memory = client.create_memory_and_wait(
    name="AirlineMemoryAgent",
    strategies=[{
        "customMemoryStrategy": {
            "name": "UserPreference",
            "namespaces": ["/users/{actorId}"],
            "configuration" : {
                "userPreferenceOverride" : {
                    "extraction" : {
                        "modelId" : "anthropic.claude-3-5-sonnet-20241022-v2:0",
                        "appendToPrompt": CUSTOM_PROMPT
                    }
                }
            }
        }
    }],
    memory_execution_role_arn=MEMORY_EXECUTION_ROLE_ARN
)
```

### Create Events to Upload User Conversations

```python
event = client.create_event(
    memory_id=memory.get("id"), # This is the id from create_memory or list_memories
    actor_id="User84",  # This is the identifier of the actor, could be an agent or end-user.
    session_id="AirlineBookingSession1",
    messages=[
        ("Hi, I would like to book a flight from Seattle to New York for this Sunday", "USER"),
        ("Certainly, let me try to find the best flights for you", "ASSISTANT"),
        ("flight_search(start='Seattle', end='New York', date='2025-07-30')", "TOOL"),
        ("I have a two options available. 1/ Delta Airlines DL456 at 10:30 AM 2/ American Airline AA345 at 4PM. ", "ASSISTANT"),
        ("Delta airline", "USER"),
        ("Sure. I will get you a seat on Delta flight DL456. Do you have a preference for a seat type","ASSISTANT",),
        ("Yes. Window please", "USER"),
        ("I have booked you on flight DL456 at 10:30 AM on 07/30/2025. Your seat number is 26A. You will more details in your email", "ASSISTANT"),
    ],
)
```

### Search for User's Preferences

```python
memories = client.retrieve_memories(
    memory_id=memory.get("id"),
    namespace=f"/users/User84",
    query="What are the user's preferences for airline type ?"
)

memories = client.retrieve_memories(
    memory_id=memory.get("id"),
    namespace=f"/users/User84",
    query="What are the user's preferences for seat type ?"
)
```
