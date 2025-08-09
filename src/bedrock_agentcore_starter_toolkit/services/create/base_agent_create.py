import os
import uuid

import autopep8
import boto3
from bedrock_agentcore.memory import MemoryClient

from bedrock_agentcore_starter_toolkit.operations.gateway import GatewayClient

from .utils import clean_variable_name, get_base_dir, unindent_by_one


class BaseAgentCreator:
    """Base class for creating agents with a specific platform."""

    def __init__(self, config, output_dir):
        """Initialize the base agent creator with configuration and output directory."""
        self.config = config
        self.output_dir = output_dir
        self.tool_class_results = {}

        # Deployment information
        self.platform = config.get("platform", "strands")
        self.debug_enabled = config.get("agent", {}).get("debug_enabled", False)
        self.region = config.get("region", "us-west-2")

        # Agent Metadata
        self.agent_name = config.get("agent", {}).get("name", "default_agent")
        self.cleaned_agent_name = clean_variable_name(self.agent_name)
        self.instruction = config.get("agent", {}).get("instruction", "Default instruction for the agent.")
        self.gateway_cognito_result = {}

        # Model Information
        self.foundation_model = config.get("agent", {}).get("foundationModel", "anthropic.claude-opus-4-20250514-v1:0")
        self.provider_model = config.get("agent", {}).get("providerModel", "bedrock")
        self.temperature = 0.3
        self.guardrail_id = (
            config.get("agent", {}).get("modelConfig", {}).get("guardrailConfiguration", {}).get("guardrailId", None)
        )
        self.guardrail_version = (
            config.get("agent", {}).get("modelConfig", {}).get("guardrailConfiguration", {}).get("version", None)
        )

        # Knowledge Bases
        self.knowledge_bases = config.get("knowledge_bases", [])

        # AgentCore Memory
        self.memory = config.get("memory", {})
        self.memory_enabled = self.memory.get("enabled", False)
        self.memory_strategies = self.memory.get("strategies", [])
        self.memory_max_days = self.memory.get("max_days", 30)

        # AgentCore 1P Tools
        self.code_interpreter_enabled = config.get("tools_1p", {}).get("code_interpreter", False)
        self.browser_enabled = config.get("tools_1p", {}).get("browser", False)
        self.human_input_enabled = config.get("tools_1p", {}).get("human_input", False)

        # AgentCore Tool Classes
        self.tool_classes = config.get("tool_classes", [])

        # AgentCore Observability
        self.observability_enabled = config.get("observability_enabled", False)

        # Agent Data
        self.tools = []

        # Code sections to be generated
        self.imports_code = """
    import os
    import sys
    import boto3
    import uuid
    from typing import Union, Optional, Annotated, Dict, List, Any, Literal
    from dotenv import load_dotenv

    from bedrock_agentcore.runtime.context import RequestContext
    from bedrock_agentcore import BedrockAgentCoreApp

    load_dotenv()

    app = BedrockAgentCoreApp()
        """

        self.code_sections = []

    # ----------------------
    # Imports and Common Code
    # ----------------------

    def generate_agent_usage_code(self):
        """Generate code for agent usage."""
        agentcore_memory_entrypoint_code = (
            """
            event = memory_client.create_event(
                memory_id=memory_id,
                actor_id=user_id,
                session_id=session_id,
                messages=formatted_messages
            )
        """
            if self.memory_enabled
            else ""
        )

        entrypoint_code = f"""
    @app.entrypoint
    def endpoint(payload, context):
        \"\"\"Entrypoint for AgentCore Runtime.\"\"\"
        try:
            {'user_id = user_id or payload.get("userId", uuid.uuid4().hex[:8])' if self.memory_enabled else ""}
            session_id = context.session_id or payload.get("sessionId", uuid.uuid4().hex[:8])

                agent_query = payload.get("message", "")
            if not agent_query:
                return {{'error': "No query provided, please provide a 'message' field in the payload."}}

            agent_result = agent(agent_query)
            response_content = str(agent_result)
            formatted_messages = [(agent_query, "USER"), (response_content if response_content else "No Response.", "ASSISTANT")]

            {agentcore_memory_entrypoint_code}

            return {{
                "response": agent_result,
                "messages": formatted_messages,
                "sessionId": session_id
            }}
        except Exception as e:
            return {{
                "error": f"An error occurred: {{str(e)}}",
                "sessionId": session_id
            }}
        """

        cli_code = f"""

    def cli():
        \"\"\"CLI for Local Development.\"\"\"
        {'user_id = "{uuid.uuid4().hex[:8].lower()}" # change user_id if necessary' if self.memory_enabled else ""}
        session_id = uuid.uuid4().hex[:8].lower()
        try:
            while True:
                try:
                    query = input("\\n\\nEnter your question (or 'exit' to quit): ")

                    if query.lower() == "exit":
                        break

                    endpoint({{"message": query{', "userId": user_id' if self.memory_enabled else ""}}}, RequestContext(session_id=session_id)).get('result', {{}})

                except KeyboardInterrupt:
                    print("\\n\\nExiting...")
                    break
        except Exception as e:
            print(f"\\n\\nError: {{e}}")
        finally:
            print("Session ended.")

    if __name__ == "__main__":
        if len(sys.argv) > 1 and sys.argv[1] == "--cli":
            cli() # Run the CLI interface
        else: app.run() # Run the Starlette app
        """

        return entrypoint_code + "\n\n" + cli_code

    def generate_prompts_code(self):
        """Generate code for agent prompts."""
        return f"""
    SYSTEM_PROMPT = \"\"\"

    ## Instructions
    {self.instruction}

    ## Guidelines
    - Always respond in a helpful and informative manner.
    - If you don't know the answer, say "I don't know" instead of making up an answer.
    - If the question is ambiguous, ask for clarification.
    - Use the tools available to you to answer the question.
    \"\"\"
    """

    # ----------------------
    # 1P Tool Code Generation
    # ----------------------

    def generate_human_input_code(self):
        """Generate code for the human input tool."""
        if not self.human_input_enabled:
            return ""

        self.tools.append("human_input_tool")

        return """
    @tool
    def human_input_tool(query: str):
        \"""
        INPUT: The original question asked by the user.
        OUTPUT: The response from the human input tool.
        CAPABILITIES: Asking the user for input, clarifying questions, and gathering additional information from the user.
        TOOL DESCRIPTION: This tool is capable of asking the user for input, clarifying questions,
        and gathering additional information from the user. It can be used to clarify ambiguous questions,
        gather more context, or ask for specific details that the agent needs to provide a better response.
        \"""
        return input(query)
        """

    def generate_code_interpreter_code(self, platform):
        """Generate code for the code interpreter tool."""
        if not self.code_interpreter_enabled:
            return ""

        self.imports_code += """
    from bedrock_agentcore.tools import code_interpreter_client"""

        code_1p = """
    # Code Interpreter Tool
    @tool
    def code_tool(original_question: str):
        \"""
        INPUT: The original question asked by the user.
        OUTPUT: The output of the code interpreter.
        CAPABILITIES: writing custom code for difficult calculations or questions, executing system-level code to control the user's computer and accomplish tasks, and develop code for the user.

        TOOL DESCRIPTION: This tool is capable of almost any code-enabled task. DO NOT pass code to this tool. Instead, call on it to write and execute any code safely.
        Pass any and all coding tasks to this tool in the form of the original question you got from the user. It can handle tasks that involve writing, running,
        testing, and troubleshooting code. Use it for system calls, generating and running code, and more.

        EXAMPLES: Opening an application and performing tasks programatically, solving or calculating difficult questions via code, etc.

        IMPORTANT: Before responding to the user that you cannot accomplish a task, think whether this tool can be used.
        IMPORTANT: Do not tell the code interpreter to do long running tasks such as waiting for user input or running indefinitely.\"""

        with code_interpreter_client.code_session(region="us-west-2") as session:
            print(f"Session started with ID: {session.session_id}")
            print(f"Code Interpreter Identifier: {session.identifier}")

            def get_result(response):
                if "stream" in response:
                    event_stream = response["stream"]

                    try:
                        for event in event_stream:
                            if "result" in event:
                                result = event["result"]

                                if result.get("isError", False):
                                    return {"error": True, "message": result.get("content", "Unknown error")}
                                else:
                                    return {"success": True, "content": result.get("content", {})}

                        return {"error": True, "message": "No result found in event stream"}

                    except Exception as e:
                        return {"error": True, "message": f"Failed to process event stream: {str(e)}"}

            @tool
            def execute_code(code: str, language: str):
                \"""
                Execute code in the code interpreter sandbox.
                Args:
                    code (str): The code to execute in the sandbox. This should be a complete code snippet that can run
                     independently. If you created a file, pass the file content as a string.
                    language (str): The programming language of the code (e.g., "python", "javascript").
                Returns:
                    dict: The response from the code interpreter service, including execution results or error messages.
                Example:
                    code = "print('Hello, World!')"
                    language = "python"
                \"""

                response = session.invoke(method="executeCode", params={"code": code, "language": language})
                return get_result(response)

            @tool
            def list_files(path: str) -> List[str]:
                \"""
                List files in the code interpreter sandbox.
                Args:
                    path (str): The directory path to list files from in the sandbox.
                Returns:
                    dict: The response from the code interpreter service, including file paths or error messages.
                Example:
                    path = "/home/user/sandbox"
                \"""

                if not path:
                    path = "/"

                response = session.invoke(method="listFiles", params={"path": path})
                return get_result(response)

            @tool
            def read_files(file_paths: List[str]):
                \"""
                Read files from the code interpreter sandbox.
                Args:
                    file_paths (List[str]): List of file paths to read from the sandbox.
                Returns:
                    dict: The response from the code interpreter service, including file contents or error messages.
                Example:
                    file_paths = ["example.txt", "script.py"]
                \"""
                response = session.invoke(method="readFiles", params={"paths": file_paths})
                return get_result(response)

            @tool
            def write_files(files_to_create: List[Dict[str, str]]):
                \"""
                Write files to the code interpreter sandbox.
                Args:
                    files_to_create (List[Dict[str, str]]): List of dictionaries with 'path' and 'text' keys,
                    where 'path' is the file path and 'text' is the content to write.
                Returns:
                    dict: The response from the code interpreter service, including success status and error messages.
                Example:
                    files_to_create = [{"path": "example.txt", "text": "Hello, World!"},
                    {"path": "script.py", "text": "print('Hello from script!')"}]
                \"""

                response = session.invoke(method="writeFiles", params={"content": files_to_create})
                return get_result(response)

            @tool
            def remove_files(file_paths: List[str]):
                \"""
                Removes files from the code interpreter sandbox.
                Args:
                    file_paths (List[str]): List of file paths to remove from the sandbox.
                Returns:
                    dict: The response from the code interpreter service, including file contents or error messages.
                Example:
                    file_paths = ["example.txt", "script.py"]
                \"""
                response = session.invoke(method="removeFiles", params={"paths": file_paths})
                return get_result(response)

            coding_tools = [
                execute_code,
                list_files,
                read_files,
                write_files,
                remove_files,
            ]

            coding_prompt = \"""
            You are a code interpreter tool that can execute code in various programming languages.
            You'll be given a query that describes a coding task or question.
            You will write and execute code to answer the query.
            You can handle tasks that involve writing, running, testing, and troubleshooting code.
            You can handle errors and return results, making you useful for tasks that require code execution.
            You can run Python scripts, execute Java code, and more.

            IMPORTANT: Ensure that the code is safe to execute and does not contain malicious content.
            IMPORTANT: Do not run indefinitely or wait for user input.
            IMPORTANT: After executing code and receiving results, you MUST provide a clear response that
                       includes the answer to the user's question.
            IMPORTANT: Always respond with the actual result or answer, not just "I executed the code" or
                       "The result is displayed above".
            IMPORTANT: If code execution produces output, include that output in your response to the user.
            \"""
    """

        if platform == "langchain":
            code_1p += """
        coding_agent = create_react_agent(model=llm, prompt=coding_prompt, tools=coding_tools)
        coding_agent_input = {"messages": [{"role": "user", "content": original_question}]}

        return coding_agent.invoke(coding_agent_input)["messages"][-1].content
        """

        else:
            code_1p += """
        coding_agent = Agent(
            model=llm,
            system_prompt=coding_prompt,
            tools=coding_tools,
            )

        return str(coding_agent(original_question))
        """

        self.tools.append("code_tool")

        return code_1p

    def generate_browser_code(self, platform):
        """Generate code for the browser tool."""
        if not self.browser_enabled:
            return ""

        self.imports_code += """
    from bedrock_agentcore.tools.browser_client import BrowserClient
    from browser_use import Agent, BrowserSession
    """

        self.tools.append("browser_tool")

        browser_1p = f"""
    @tool
    def browser_tool(query: str):
        \"""
        INPUT: The original question asked by the user.
        OUTPUT: The response from the browser tool.
        CAPABILITIES: Searching the web, retrieving information from websites, and answering questions based on web content.
        \"""

        with BrowserClient(region={self.region}) as client:
            ws_url, headers = client.generate_ws_headers()

            session = BrowserSession(wss_url=ws_url, extra_http_headers=headers)

            agent = Agent(
                task=query,
                llm=llm,
                browser_session=session,
            )

            history = agent.run()

            return history.final_result()
"""

        return browser_1p

    # ----------------------
    # Memory Management
    # ----------------------

    def generate_memory_configuration(self, memory_saver: str) -> str:
        """Generate memory configuration for LangChain agent."""
        # Short Term Memory
        output = f"""
    checkpointer_STM = {memory_saver}()
    """

        if self.memory_enabled:
            self.imports_code += "\nfrom bedrock_agentcore.memory import MemoryClient\n"

            strategies = []
            for strategy in self.memory_strategies:
                if strategy == "summarization":
                    strategies.append(
                        {
                            "summaryMemoryStrategy": {
                                "name": "SessionSummarizer",
                                "namespaces": ["/summarization/{actorId}/{sessionId}"],
                            }
                        }
                    )
                elif strategy == "user_preferences":
                    strategies.append(
                        {
                            "userPreferenceMemoryStrategy": {
                                "name": "UserPreference",
                                "namespaces": ["/user_preferences/{actorId}"],
                            }
                        }
                    )
                elif strategy == "semantic":
                    strategies.append(
                        {
                            "semanticMemoryStrategy": {
                                "name": "FactExtractor",
                                "namespaces": ["semantic/{sessionId}"],
                            }
                        }
                    )

            memory_client = MemoryClient(region_name=self.region)

            print("  Creating AgentCore Memory (This will take a few minutes)...")
            memory = memory_client.create_memory_and_wait(
                name=f"memory_{uuid.uuid4().hex[:3].lower()}",
                strategies=strategies,
            )

            memory_id = memory["id"]

            output += f"""
    memory_client = MemoryClient(region_name='{self.region}')
    memory_id = "{memory_id}"
        """

            for strategy in self.memory_strategies:
                namespace = ""
                if strategy == "semantic":
                    namespace = "semantic"
                elif strategy == "user_preferences":
                    namespace = "/user_preferences/{user_id}"
                elif strategy == "summarization":
                    namespace = "/summarization/{user_id}"

                output += f"""
    @tool
    def {strategy}_memory_tool(query: str):
        memories = memory_client.retrieve_memories(
            memory_id=memory_id,
            namespace="{namespace}",
            query=query,
            top_k=5
        )
        memory_synopsis = "\\n".join([m.get("content", {{}}).get("text", "") for m in memories])
        return memory_synopsis
    """

                self.tools.append(f"{strategy}_memory_tool")

        return output

    # ----------------------
    # AgentCore Gateway + Custom MCP
    # ----------------------

    def create_tool_classes(self):
        """Create the gateway and proxy for the agent."""
        if self.tool_classes:
            print("  Creating Tool Classes for Agent...")

        gateway_client = GatewayClient(region_name=self.region)
        agentcore_client = boto3.client("bedrock-agentcore-control")

        tool_class_results = {
            "gateways": [],
            "mcp_servers": [],
        }

        for tool_class in self.tool_classes:
            if tool_class["type"] == "new_gateway":
                gateway_name = f"{self.cleaned_agent_name.replace('_', '-')}-gateway-{uuid.uuid4().hex[:5].lower()}"

                cognito_result = gateway_client.create_oauth_authorizer_with_cognito(gateway_name=gateway_name)

                gateway = gateway_client.create_mcp_gateway(
                    name=gateway_name,
                    enable_semantic_search=True,
                    authorizer_config=self.gateway_cognito_result["authorizer_config"],
                )

                gateway.update(cognito_result)

                for target in tool_class.get("targets", []):
                    if target["target_type"] == "lambda":
                        payload = {
                            "lambdaArn": target["lambda_arn"],
                            "toolSchema": target["tool_schema"],
                        }
                        credentials = {}

                    else:
                        payload = target["spec"]
                        credentials = target["credentials"]

                    gateway_client.create_mcp_gateway_target(
                        gateway=gateway,
                        name=f"target-{uuid.uuid4().hex[:5].lower()}",
                        target_type=target["target_type"],
                        target_payload=payload,
                        credentials=credentials,
                    )

                tool_class_results["gateways"].append(gateway)

            elif tool_class["type"] == "existing_gateway":
                gateway = agentcore_client.get_gateway(gatewayIdentifier=tool_class["gateway_id"])

                gateway_scopes = [
                    {
                        "ScopeName": "invoke",  # Just 'invoke', will be formatted as resource_server_id/invoke
                        "ScopeDescription": "Scope for invoking the agentcore gateway",
                    }
                ]
                scope_names = [f"{gateway['name']}/{scope['ScopeName']}" for scope in gateway_scopes]

                authorizer_config = gateway.get("authorizerConfiguration", {})
                discovery_url = authorizer_config.get("customJWTAuthorizer", {}).get("discoveryUrl", "")
                user_pool_id = discovery_url.split("/")[-3]
                # Extract region from discovery URL (e.g., us-west-2 from cognito-idp.us-west-2.amazonaws.com)
                cognito_region = discovery_url.split("cognito-idp.")[1].split(".amazonaws.com")[0]
                cognito_client = boto3.client("cognito-idp", region_name=cognito_region)
                user_pool_client_response = cognito_client.create_user_pool_client(
                    UserPoolId=user_pool_id,
                    ClientName=f"agentcore-client-{GatewayClient.generate_random_id()}",
                    GenerateSecret=True,
                    AllowedOAuthFlows=["client_credentials"],
                    AllowedOAuthScopes=scope_names,  # Using the formatted scope names
                    AllowedOAuthFlowsUserPoolClient=True,
                    SupportedIdentityProviders=["COGNITO"],
                )

                domain_prefix = f"agentcore-{GatewayClient.generate_random_id()}"
                client_id = user_pool_client_response["UserPoolClient"]["ClientId"]
                client_secret = user_pool_client_response["UserPoolClient"]["ClientSecret"]

                gateway.update(
                    {
                        "client_info": {
                            "client_id": client_id,
                            "client_secret": client_secret,
                            "user_pool_id": user_pool_id,
                            "token_endpoint": f"https://{domain_prefix}.auth.{self.region}.amazoncognito.com/oauth2/token",
                            "scope": scope_names[0],
                            "domain_prefix": domain_prefix,
                        }
                    }
                )

                tool_class_results["gateways"].append(gateway)

            elif tool_class["type"] == "custom_mcp":
                tool_class_results["mcp_servers"].append(tool_class["mcp_server_url"])

        return tool_class_results

    # ----------------------
    # Agent Creation
    # ----------------------

    def create(self, name: str, code_sections):
        """Create the agent code and write it to the output directory."""
        output_path = os.path.join(self.output_dir, name)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        code = "\n".join(code_sections)
        code = unindent_by_one(code)
        code = autopep8.fix_code(code, options={"aggressive": 1, "max_line_length": 120})

        with open(output_path, "a+", encoding="utf-8") as f:
            f.truncate(0)
            f.write(code)

        environment_variables = {}
        for gateway in self.tool_class_results.get("gateways", []):
            if "client_info" in gateway:
                client_info = gateway["client_info"]
                environment_variables.update(
                    {
                        f"{gateway['name']}_COGNITO_CLIENT_ID": client_info.get("client_id", ""),
                        f"{gateway['name']}_COGNITO_CLIENT_SECRET": client_info.get("client_secret", ""),
                        f"{gateway['name']}_COGNITO_USER_POOL_ID": client_info.get("user_pool_id", ""),
                        f"{gateway['name']}_COGNITO_TOKEN_ENDPOINT": client_info.get("token_endpoint", ""),
                        f"{gateway['name']}_COGNITO_SCOPE": client_info.get("scope", ""),
                        f"{gateway['name']}_COGNITO_DOMAIN_PREFIX": client_info.get("domain_prefix", ""),
                    }
                )

        # Write a .env file with the environment variables
        env_file_path = os.path.join(self.output_dir, ".env")
        with open(env_file_path, "w", encoding="utf-8") as env_file:
            for key, value in environment_variables.items():
                env_file.write(f"\n{key}={value}")

        # Copy over requirements.txt
        requirements_path = os.path.join(get_base_dir(__file__), "assets", f"requirements_{self.platform}.j2")
        if os.path.exists(requirements_path):
            with (
                open(requirements_path, "r", encoding="utf-8") as src_file,
                open(os.path.join(self.output_dir, "requirements.txt"), "w", encoding="utf-8") as dest_file,
            ):
                dest_file.truncate(0)
                dest_file.write(src_file.read())

        return environment_variables


# ruff: noqa
