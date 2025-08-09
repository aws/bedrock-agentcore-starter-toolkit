import uuid

from .base_agent_create import BaseAgentCreator
from .utils import clean_variable_name


class StrandsCreate(BaseAgentCreator):
    def __init__(self, config, output_dir):
        super().__init__(config, output_dir)

        self.tool_class_results = self.create_tool_classes()

        self.tools_1p_code = "\n".join(
            [
                self.generate_code_interpreter_code("strands"),
                self.generate_browser_code("strands"),
                self.generate_human_input_code(),
            ]
        )

        self.imports_code += self.generate_imports()
        self.models_code = self.generate_models_code()
        self.prompts_code = self.generate_prompts_code()
        self.kb_code = self.generate_knowledge_base_code()
        self.tool_client_code = self.generate_tool_client_code()
        self.memory_code = self.generate_memory_configuration(memory_saver="SlidingWindowConversationManager")
        self.agent_setup_code = self.generate_agent_setup()
        self.usage_code = self.generate_agent_usage_code()

        self.code_sections = [
            self.imports_code,
            self.models_code,
            self.prompts_code,
            self.kb_code,
            self.tool_client_code,
            self.tools_1p_code,
            self.memory_code,
            self.agent_setup_code,
            self.usage_code,
        ]

    def generate_imports(self) -> str:
        """Generate import statements for Strands components."""
        return """
    from strands import Agent, tool
    from strands.agent.conversation_manager import SlidingWindowConversationManager
    from strands.types.content import Message
    """

    def generate_models_code(self):
        """Generate code for the LLM."""
        match self.provider_model:
            case "bedrock":
                self.imports_code += "from strands.models import BedrockModel\n"
                guardrail_code = (
                    f",guardrail_id='{self.guardrail_id}', guardrail_version='{self.guardrail_version}'"
                    if self.guardrail_id
                    else ""
                )
                return f"""
    llm = BedrockModel(
        model_id="{self.foundation_model}",
        temperature={self.temperature}{guardrail_code}
    )
                """
            case "openai":
                self.imports_code += "from strands.models.openai import OpenAIModel\n"
                return f"""
    llm = OpenAIModel(
        model_id="{self.foundation_model}",
        params={{"temperature": {self.temperature}}},
        client_args={{"api_key": os.environ.get("MODEL_API_KEY")}}
    )
                """
            case "anthropic":
                self.imports_code += "from strands.models.anthropic import AnthropicModel\n"
                return f"""
    llm = AnthropicModel(
        model_id="{self.foundation_model}",
        params={{"temperature": {self.temperature}}},
        client_args={{"api_key": os.environ.get("MODEL_API_KEY")}}
    )
                """
            case "litellm":
                self.imports_code += "from strands.models.litellm import LiteLLMModel\n"
                return f"""
    llm = LiteLLMModel(
        model_id="{self.foundation_model}",
        params={{"temperature": {self.temperature}}},
        client_args={{"api_key": os.environ.get("MODEL_API_KEY")}}
    )
                """

    def generate_knowledge_base_code(self) -> str:
        """Generate code for knowledge base retrievers."""
        if not self.knowledge_bases:
            return ""

        kb_code = ""

        for kb in self.knowledge_bases:
            kb_name = kb.get("name", "").replace(" ", "_")
            kb_description = kb.get("description", "")
            kb_id = kb.get("knowledgeBaseId", "")
            kb_region_name = kb.get("knowledgeBaseArn", "").split(":")[3]

            kb_code += f"""
    @tool
    def retrieve_{kb_name}(query: str):
        \"""This is a knowledge base with the following description: {kb_description}. Invoke it with a query to get relevant results.\"""
        client = boto3.client("bedrock-agent-runtime", region_name="{kb_region_name}")
        return client.retrieve(
            retrievalQuery={{"text": query}},
            knowledgeBaseId="{kb_id}",
            retrievalConfiguration={{
                "vectorSearchConfiguration": {{"numberOfResults": 10}},
            }},
        ).get('retrievalResults', [])
    """
            self.tools.append(f"retrieve_{kb_name}")

        return kb_code

    def generate_tool_client_code(self) -> str:
        """Generate code for tool clients."""
        if not self.tool_class_results:
            return ""

        tool_client_code = "mcp_tools = []\n"

        if self.tool_class_results["gateways"]:
            self.imports_code += "\nfrom bedrock_agentcore_starter_toolkit.operations.gateway import GatewayClient\n"
            self.imports_code += """
    from mcp.client.streamable_http import streamablehttp_client
    from strands.tools.mcp.mcp_client import MCPClient
    from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
"""

            tool_client_code += f"gateway_client = GatewayClient(region_name='{self.region}')\n"

            tool_client_code += """
    def init_mcp(client):
        client.start()
        return client.list_tools_sync()
"""

            for gateway in self.tool_class_results["gateways"]:
                client_info = gateway.get("client_info", {})
                access_token_uuid = uuid.uuid4().hex[:5]
                client_name = clean_variable_name(gateway.get("name", "")) + "_client"
                tool_client_code += f"""
    access_token_{access_token_uuid} = gateway_client.get_access_token_for_cognito({client_info})

    {client_name} = MCPClient(lambda: streamablehttp_client(
        url='{gateway.get("gatewayUrl", "")}',
        headers={{
            "Content-Type": "application/json",
            "Authorization": f"Bearer {{access_token_{access_token_uuid}}}",
        }}
    ))

    try:
        with ThreadPoolExecutor() as executor:
            future = executor.submit(init_mcp({client_name}))
            mcp_tools += future.result(timeout=10)

    except (FutureTimeoutError, Exception):
        pass
    """

        elif self.tool_class_results["mcp_servers"]:
            self.imports_code += """
    from mcp.client.streamable_http import streamablehttp_client
    from strands.tools.mcp.mcp_client import MCPClient
    from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
"""
            for server_url in self.tool_class_results["mcp_servers"]:
                tool_client_code += f"""
    mcp_client = MCPClient(lambda: streamablehttp_client(
        mcp_url='{server_url}',
        headers={{"Content-Type": "application/json"}}
    ))
    try:
        def get_mcp_tools():
            mcp_client.start()
            return mcp_client.list_tools_sync()

        with ThreadPoolExecutor() as executor:
            future = executor.submit(get_mcp_tools)
            mcp_tools += future.result(timeout=10)
    except (FutureTimeoutError, Exception):
        pass
        """

        return tool_client_code

    def generate_agent_setup(self):
        """Generate the agent setup code."""
        agent_code = f"tools = [{','.join(self.tools)}]\n"

        if self.tool_classes and len(self.tool_classes) > 0:
            agent_code += "tools += mcp_tools\n"

        agent_code += """
    agent = Agent(
                model=llm,
                system_prompt=SYSTEM_PROMPT,
                tools=tools,
                conversation_manager=checkpointer_STM
            )
    """

        return agent_code

    def create_strands(self, name):
        return self.create(name, self.code_sections)


# ruff: noqa
