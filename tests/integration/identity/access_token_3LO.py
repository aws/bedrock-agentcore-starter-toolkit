import asyncio

from bedrock_agentcore.identity.auth import requires_access_token
from bedrock_agentcore.runtime import BedrockAgentCoreApp


class StreamingQueue:
    def __init__(self):
        self.finished = False
        self.queue = asyncio.Queue()

    async def put(self, item):
        await self.queue.put(item)

    async def finish(self):
        self.finished = True
        await self.queue.put(None)

    async def stream(self):
        while True:
            item = await self.queue.get()
            if item is None and self.finished:
                break
            yield item


app = BedrockAgentCoreApp()
queue = StreamingQueue()


async def agent_task():
    try:
        await queue.put("Begin agent execution")
        await need_token_3LO_async(access_token="")
        await queue.put("End agent execution")
    finally:
        await queue.finish()


@app.entrypoint
async def agent_invocation(payload):
    asyncio.create_task(agent_task())
    return queue.stream()


async def on_auth_url(url: str):
    print(f"Authorization url: {url}")
    await queue.put(f"Authorization url: {url}")


@requires_access_token(
    provider_name="Google4",  # replace with your own credential provider name
    scopes=["https://www.googleapis.com/auth/userinfo.email"],
    auth_flow="USER_FEDERATION",
    on_auth_url=on_auth_url,
    force_authentication=True,
)
async def need_token_3LO_async(*, access_token: str):
    await queue.put(f"received token for async func: {access_token}")


app.run()
