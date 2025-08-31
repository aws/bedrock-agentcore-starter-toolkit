from random import randint

from bedrock_agentcore import BedrockAgentCoreApp
from bedrock_agentcore.memory import MemoryClient

app = BedrockAgentCoreApp()
client = MemoryClient(region_name="us-west-2")


@app.entrypoint
def entrypoint(_payload):
    print("Receiving payload:", _payload)
    memory_id = create_memory()

    return {"memory_id": memory_id}


def create_memory():
    name = "CustomerSupportAgentMemory" + str(randint(1, 10000))
    description = "Memory for customer support conversations"

    memory = client.create_memory(
        name=name,
        description=description,
    )

    print(f"Memory ID: {memory.get('id')}")
    print(f"Memory: {memory}")

    return memory.get("id")


app.run()
