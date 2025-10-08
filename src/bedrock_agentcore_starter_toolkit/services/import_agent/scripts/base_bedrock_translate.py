"""Base class for Bedrock Agent translation services.

This module provides a base class with common functionality for translating
AWS Bedrock Agent configurations into different frameworks.

Contains all the common logic between Langchain and Strands translations.
"""

import io
import json
import os
import time
import uuid
import zipfile
from typing import Dict, Tuple

import autopep8
import boto3
from bedrock_agentcore.memory import MemoryClient
from openapi_schema_to_json_schema import to_json_schema

from ....operations.gateway import GatewayClient
from ..utils import (
    clean_gateway_or_target_name,
    clean_variable_name,
    generate_pydantic_models,
    get_base_dir,
    get_template_fixtures,
    prune_tool_name,
    safe_substitute_placeholders,
    unindent_by_one,
)


class BaseBedrockTranslator:
    """Base class for Bedrock Agent translation services."""

    def __init__(self, agent_config, debug: bool, output_dir: str, enabled_primitives: dict):
        """Initialize the base translator with common configuration.

        Args:
            agent_config: The agent configuration dictionary
            debug: Whether to enable debug mode
            output_dir: The directory to output generated files
            enabled_primitives: Dictionary of enabled primitives for the agent
        """
        self.agent_info = agent_config["agent"]
        self.debug = debug
        self.output_dir = output_dir
        self.user_id = uuid.uuid4().hex[:8]
        self.cleaned_agent_name = self.agent_info["agentName"].replace(" ", "_").replace("-", "_").lower()[:30]

        # agent metadata
        self.model_id = self.agent_info.get("foundationModel", "")
        self.agent_region = self.agent_info["agentArn"].split(":")[3]
        self.instruction = self.agent_info.get("instruction", "")
        self.enabled_prompts = []
        self.idle_timeout = self.agent_info.get("idleSessionTTLInSeconds", 600)

        # memory
        self.memory_config = self.agent_info.get("memoryConfiguration", {})
        self.memory_enabled = bool(self.memory_config)
        self.memory_enabled_types = self.memory_config.get("enabledMemoryTypes", [])

        # kbs
        self.knowledge_bases = agent_config.get("knowledge_bases", [])
        self.single_kb = len(self.knowledge_bases) == 1
        self.kb_generation_prompt_enabled = False
        self.single_kb_optimization_enabled = False

        # multi agent collaboration
        self.multi_agent_enabled = (
            self.agent_info.get("agentCollaboration", "DISABLED") != "DISABLED" and agent_config["collaborators"]
        )
        self.supervision_type = self.agent_info.get("agentCollaboration", "SUPERVISOR")
        self.collaborators = agent_config.get("collaborators", [])
        self.collaborator_map = {
            collaborator.get("collaboratorName", ""): collaborator for collaborator in self.collaborators
        }
        self.collaborator_descriptions = [
            f"{{'agentName': '{collaborator['agent'].get('agentName', '')}', 'collaboratorName (for invocation)': 'invoke_{collaborator.get('collaboratorName', '')}', 'collaboratorInstruction': '{collaborator.get('collaborationInstruction', '')}}}"
            for collaborator in self.collaborators
        ]
        self.is_collaborator = "collaboratorName" in agent_config
        self.is_accepting_relays = agent_config.get("relayConversationHistory", "DISABLED") == "TO_COLLABORATOR"
        self.collaboration_instruction = agent_config.get("collaborationInstruction", "")
        self.collaborator_name = agent_config.get("collaboratorName", "")

        # action groups and tools
        self.action_groups = [
            group
            for group in agent_config.get("action_groups", [])
            if group.get("actionGroupState", "DISABLED") == "ENABLED"
        ]
        self.custom_ags = [group for group in self.action_groups if "parentActionSignature" not in group]
        self.tools = []
        self.mcp_tools = []
        self.action_group_tools = []

        # user input and code interpreter
        self.code_interpreter_enabled = any(
            group["actionGroupName"] == "codeinterpreteraction" and group["actionGroupState"] == "ENABLED"
            for group in self.action_groups
        )
        self.user_input_enabled = any(
            group["actionGroupName"] == "userinputaction" and group["actionGroupState"] == "ENABLED"
            for group in self.action_groups
        )

        # orchestration steps
        self.prompt_configs = self.agent_info.get("promptOverrideConfiguration", {}).get("promptConfigurations", [])

        # guardrails
        self.guardrail_config = {}
        if "guardrailConfiguration" in self.agent_info:
            guardrail_id = self.agent_info["guardrailConfiguration"].get("guardrailId", "")
            guardrail_version = self.agent_info["guardrailConfiguration"].get("version", "")
            if guardrail_id:
                self.guardrail_config = {"guardrailIdentifier": guardrail_id, "guardrailVersion": guardrail_version}

        # AgentCore
        self.enabled_primitives = enabled_primitives
        self.gateway_enabled = enabled_primitives.get("gateway", False) and self.custom_ags
        self.gateway_cognito_result = {}  # Initialize before create_gateway() call
        self.created_gateway = self.create_gateway() if self.gateway_enabled else {}

        self.agentcore_memory_enabled = enabled_primitives.get("memory", False) and self.memory_enabled
        self.observability_enabled = enabled_primitives.get("observability", False)
        self.code1p = enabled_primitives.get("code_interpreter", False) and self.code_interpreter_enabled

        # Initialize imports
        self.imports_code = """    # ---------- NOTE: This file is auto-generated by the Bedrock AgentCore Starter Toolkit. ----------
    # Use this agent definition as a starting point for your custom agent implementation.
    # Review the generated code, evaluate agent behavior, and make necessary changes before deploying.
    # Extend the agent with additional tools, memory, and other features as required.
    # -------------------------------------------------------------------------------------------------

    import json, sys, os, re, io, uuid, asyncio
    from typing import Union, Optional, Annotated, Dict, List, Any, Literal
    from inputimeout import inputimeout, TimeoutOccurred # pylint: disable=import-error # type: ignore
    from pydantic import BaseModel, Field
    import boto3
    from dotenv import load_dotenv

    from bedrock_agentcore.runtime.context import RequestContext
    from bedrock_agentcore import BedrockAgentCoreApp

    load_dotenv()
        """

        # If this agent is not a collaborator, create a BedrockAgentCore entrypoint
        if not self.is_collaborator:
            self.imports_code += """
    app = BedrockAgentCoreApp()
    """

        # Initialize code sections
        self.prompts_code = ""
        self.models_code = ""
        self.tools_code = ""
        self.memory_code = ""
        self.kb_code = ""
        self.collaboration_code = ""
        self.agent_setup_code = ""
        self.usage_code = ""

    def _clean_fixtures_and_prompt(self, base_template, fixtures) -> Tuple[str, Dict]:
        """Clean up the base template and fixtures by removing unused keys.

        Args:
            base_template: The template string to clean
            fixtures: Dictionary of fixtures to clean

        Returns:
            Tuple containing the cleaned template and fixtures
        """
        removed_keys = []

        # Remove KBs
        if not self.knowledge_bases:
            for key in list(fixtures.keys()):
                if "knowledge_base" in key:
                    removed_keys.append(key)

        # Remove Memory
        if not self.memory_enabled_types:
            for key in list(fixtures.keys()):
                if key.startswith("$memory"):
                    removed_keys.append(key)

        # Remove User Input
        if not self.user_input_enabled:
            removed_keys.append("$ask_user_missing_information$")
            removed_keys.append("$respond_to_user_guideline$")

        if not self.action_groups:
            removed_keys.append("$prompt_session_attributes$")

        if not self.code_interpreter_enabled:
            removed_keys.append("$code_interpreter_guideline$")
            removed_keys.append("$code_interpreter_files$")

        for key in removed_keys:
            if key in fixtures:
                del fixtures[key]
            base_template = base_template.replace(key, "")

        return base_template, fixtures

    def generate_prompt(self, config: Dict):
        """Generate prompt code based on the configuration."""
        prompt_type = config.get("promptType", "")
        self.enabled_prompts.append(prompt_type)

        if prompt_type == "ORCHESTRATION":
            orchestration_fixtures = get_template_fixtures("orchestrationBasePrompts", "REACT_MULTI_ACTION")
            orchestration_base_template: str = config["basePromptTemplate"]["system"]

            orchestration_base_template, orchestration_fixtures = self._clean_fixtures_and_prompt(
                orchestration_base_template, orchestration_fixtures
            )

            injected_orchestration_prompt = safe_substitute_placeholders(
                orchestration_base_template, orchestration_fixtures
            )
            injected_orchestration_prompt = safe_substitute_placeholders(
                injected_orchestration_prompt, {"instruction": self.instruction}
            )
            injected_orchestration_prompt = safe_substitute_placeholders(
                injected_orchestration_prompt, {"$agent_collaborators$ ": ",".join(self.collaborator_descriptions)}
            )

            # This tool does not apply
            injected_orchestration_prompt = injected_orchestration_prompt.replace(
                "using the AgentCommunication__sendMessage tool", ""
            )

            self.prompts_code += f"""
    ORCHESTRATION_TEMPLATE=\"""\n{injected_orchestration_prompt}\""" """

        elif prompt_type == "MEMORY_SUMMARIZATION":
            self.prompts_code += f"""
    MEMORY_TEMPLATE=\"""\n
    {config["basePromptTemplate"]["messages"][0]["content"]}
    \"""
"""
        elif prompt_type == "PRE_PROCESSING":
            self.prompts_code += f"""
    PRE_PROCESSING_TEMPLATE=\"""\n
    {config["basePromptTemplate"]["system"]}
    \"""
"""
        elif prompt_type == "POST_PROCESSING":
            self.prompts_code += f"""
    POST_PROCESSING_TEMPLATE=\"""\n
    {config["basePromptTemplate"]["messages"][0]["content"][0]["text"]}
    \"""
"""
        elif prompt_type == "KNOWLEDGE_BASE_RESPONSE_GENERATION" and self.knowledge_bases:
            self.kb_generation_prompt_enabled = True

            self.prompts_code += f"""
    KB_GENERATION_TEMPLATE=\"""\n
    {config["basePromptTemplate"]}
    \"""
"""
        elif prompt_type == "ROUTING_CLASSIFIER" and self.supervision_type == "SUPERVISOR_ROUTER":
            routing_fixtures = get_template_fixtures("routingClassifierBasePrompt", "")
            routing_template: str = config.get("basePromptTemplate", "")

            injected_routing_template = safe_substitute_placeholders(routing_template, routing_fixtures)
            injected_routing_template = safe_substitute_placeholders(
                injected_routing_template, {"$reachable_agents$": ",".join(self.collaborator_descriptions)}
            )
            injected_routing_template = safe_substitute_placeholders(
                injected_routing_template, {"$tools_for_routing$": str(self.action_group_tools + self.tools)}
            )
            injected_routing_template = safe_substitute_placeholders(
                injected_routing_template, {"$knowledge_bases_for_routing$": str(self.knowledge_bases)}
            )

            self.prompts_code += f"""
    ROUTING_TEMPLATE=\"""\n
    {injected_routing_template}\"""
    """

    def generate_memory_configuration(self, memory_saver: str) -> str:
        """Generate memory configuration for LangChain agent."""
        # Short Term Memory
        output = f"""
    checkpointer_STM = {memory_saver}()
    """

        if self.agentcore_memory_enabled:
            self.imports_code += "\nfrom bedrock_agentcore.memory import MemoryClient\n"

            memory_client = MemoryClient(region_name=self.agent_region)

            print("  Creating AgentCore Memory (This will take a few minutes)...")
            memory = memory_client.create_memory_and_wait(
                name=f"{self.cleaned_agent_name}_memory_{uuid.uuid4().hex[:3].lower()}",
                strategies=[
                    {
                        "summaryMemoryStrategy": {
                            "name": "SessionSummarizer",
                            "namespaces": ["/summaries/{actorId}/{sessionId}"],
                        }
                    }
                ],
            )

            memory_id = memory["id"]

            output += f"""
    memory_client = MemoryClient(region_name='{self.agent_region}')
    memory_id = "{memory_id}"
        """

        elif self.memory_enabled:
            memory_manager_path = os.path.join(self.output_dir, "LTM_memory_manager.py")
            max_sessions = (
                self.agent_info["memoryConfiguration"]
                .get("sessionSummaryConfiguration", {})
                .get("maxRecentSessions", 20)
            )
            max_days = self.agent_info["memoryConfiguration"].get("storageDays", 30)

            with (
                open(memory_manager_path, "a", encoding="utf-8") as target,
                open(
                    os.path.join(get_base_dir(__file__), "assets", "memory_manager_template.py"),
                    "r",
                    encoding="utf-8",
                ) as template,
            ):
                target.truncate(0)
                for line in template:
                    target.write(line)

                self.imports_code += """
    from .LTM_memory_manager import LongTermMemoryManager"""

                output += f"""
    memory_manager =  LongTermMemoryManager(llm_MEMORY_SUMMARIZATION, max_sessions = {max_sessions}, summarization_prompt = MEMORY_TEMPLATE, max_days = {max_days}, platform = {'"langchain"' if memory_saver == "InMemorySaver" else '"strands"'}, storage_path = "{self.output_dir}/session_summaries_{self.agent_info["agentName"]}.json")
"""

        return output

    def generate_action_groups_code(self, platform: str) -> str:
        """Generate code for action groups and tools."""
        if not self.action_groups:
            return ""

        tool_code = ""
        tool_instances = []

        # OpenAPI and Function Action Groups
        if self.gateway_enabled:
            self.create_gateway_proxy_and_targets()

            self.imports_code += "\nfrom bedrock_agentcore_starter_toolkit.operations.gateway import GatewayClient\n"
            tool_code += f"""
    gateway_client = GatewayClient(region_name="{self.agent_region}")
    client_info = {{
        "client_id": os.environ.get("cognito_client_id", ""),
        "client_secret": os.environ.get("cognito_client_secret", ""),
        "user_pool_id": os.environ.get("cognito_user_pool_id", ""),
        "token_endpoint": os.environ.get("cognito_token_endpoint", ""),
        "scope": os.environ.get("cognito_scope", ""),
        "domain_prefix": os.environ.get("cognito_domain_prefix", ""),
    }}

    access_token = gateway_client.get_access_token_for_cognito(client_info)
            """

            if platform == "langchain":
                self.imports_code += "\nfrom langchain_mcp_adapters.client import MultiServerMCPClient\n"
                tool_code += f"""
    mcp_url = '{self.created_gateway.get("gatewayUrl", "")}'
    headers = {{
        "Content-Type": "application/json",
        "Authorization": f"Bearer {{access_token}}",
    }}

    mcp_client = MultiServerMCPClient({{
        "agent": {{
            "transport": "streamable_http",
            "url": mcp_url,
            "headers": headers,
        }}
    }})

    mcp_tools = asyncio.run(mcp_client.get_tools())
"""
            else:
                self.imports_code += """
    from mcp.client.streamable_http import streamablehttp_client
    from strands.tools.mcp.mcp_client import MCPClient
    from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
"""
                tool_code += f"""
    mcp_url = '{self.created_gateway.get("gatewayUrl", "")}'
    headers = {{
        "Content-Type": "application/json",
        "Authorization": f"Bearer {{access_token}}",
    }}

    streamable_http_mcp_client = MCPClient(lambda: streamablehttp_client(mcp_url, headers=headers))

    # To avoid erroring out on tool discovery
    try:
        def init_mcp():
            streamable_http_mcp_client.start()
            return streamable_http_mcp_client.list_tools_sync()

        with ThreadPoolExecutor() as executor:
            future = executor.submit(init_mcp)
            mcp_tools = future.result(timeout=10)

    except (FutureTimeoutError, Exception):
        mcp_tools = []
"""

        remaining_action_groups = (
            self.custom_ags
            if not self.gateway_enabled
            else [ag for ag in self.custom_ags if "lambda" not in ag.get("actionGroupExecutor", {})]
        )

        for action_group in remaining_action_groups:
            additional_tool_instances = []
            additional_code = ""

            if action_group.get("apiSchema", False):
                additional_tool_instances, additional_code = self.generate_openapi_ag_code(action_group, platform)

            elif action_group.get("functionSchema", False):
                additional_tool_instances, additional_code = self.generate_structured_ag_code(action_group, platform)

            tool_code += additional_code
            tool_instances.extend(additional_tool_instances)

        # User Input Action Group
        if self.user_input_enabled:
            tool_code += """
    # User Input Tool
    @tool
    def user_input_tool(user_targeted_question: str):
        \"\"\"You can ask a human for guidance when you think you got stuck or you are not sure what to do next.
        The input should be a question for the human. If you do not have the parameters to invoke a function,
        then use this tool to ask the user for them.\"\"\"
        return input(user_targeted_question)
"""
            tool_instances.append("user_input_tool")

        # Code Interpreter Action Group
        if self.code_interpreter_enabled:
            tool_code += self.generate_code_interpreter(platform)
            tool_instances.append("code_tool")

        # Collect Action Group Tools
        tool_code += f"""
    action_group_tools = [{", ".join(tool_instances)}]\n"""
        self.action_group_tools = tool_instances

        return tool_code

    def generate_openapi_ag_code(self, ag: Dict, platform: str) -> Tuple[list, str]:
        """Generate code for OpenAPI Action Groups."""
        tool_code = ""
        tool_instances = []

        executor_is_lambda = bool(ag["actionGroupExecutor"].get("lambda", False))
        action_group_name = ag.get("actionGroupName", "")
        action_group_desc = ag.get("description", "").replace('"', '\\"')

        if executor_is_lambda:
            lambda_arn = ag.get("actionGroupExecutor", {}).get("lambda", "")
            lambda_region = lambda_arn.split(":")[3] if lambda_arn else "us-west-2"

        openapi_schema = ag.get("apiSchema", {}).get("payload", {})

        for func_name, func_spec in openapi_schema.get("paths", {}).items():
            # Function metadata
            clean_func_name = clean_variable_name(func_name)

            for method, method_spec in func_spec.items():
                # Naming
                tool_name = prune_tool_name(f"{action_group_name}_{clean_func_name}_{method}")
                param_model_name = f"{tool_name}_Params"
                input_model_name = f"{tool_name}_Input"
                request_model_name = ""

                # Data
                params = method_spec.get("parameters", [])
                request_body = method_spec.get("requestBody", {})
                content = request_body.get("content", {})
                content_models = []

                if params:
                    nested_schema, param_model_name = generate_pydantic_models(params, f"{tool_name}_Params")
                    tool_code += nested_schema

                if request_body:
                    for content_type, content_schema in content.items():
                        content_type_safe = clean_variable_name(content_type)
                        model_name = f"{tool_name}_{content_type_safe}"

                        nested_schema, model_name = generate_pydantic_models(content_schema, model_name, content_type)
                        tool_code += nested_schema
                        content_models.append(model_name)

                # Create a union model if there are multiple content models
                if len(content_models) > 1:
                    request_model_name = f"{tool_name}_Request_Body"
                    tool_code += f"""

    {request_model_name} = Union[{", ".join(content_models)}]"""
                elif len(content_models) == 1:
                    request_model_name = next(iter(content_models))

                # un-nest if only one type of input is provided
                if params and content_models:
                    params_model_code = f"{param_model_name} |" if params else ""
                    request_model_code = (
                        f'request_body: {request_model_name} | None = Field(None, description = "Request body (ie. for a POST method) for this API Call")'
                        if content_models
                        else ""
                    )
                    tool_code += f"""
    class {input_model_name}(BaseModel):
        parameters: {params_model_code} None = Field(None, description = \"Parameters (ie. for a GET method) for this API Call\")
        {request_model_code}
    """
                elif params:
                    input_model_name = param_model_name
                elif content_models:
                    input_model_name = request_model_name
                else:
                    input_model_name = "None"

                func_desc = method_spec.get("description", method_spec.get("summary", "No Description Provided."))
                func_desc += f"\\nThis tool is part of the group of tools called {action_group_name}{f' (description: {action_group_desc})' if action_group_desc else ''}."

                schema_code_strands = (
                    f"inputSchema={input_model_name}.model_json_schema()" if input_model_name != "None" else ""
                )
                schema_code_langchain = f"args_schema={input_model_name}" if input_model_name != "None" else ""
                tool_code += f"@tool({schema_code_strands if platform == 'strands' else schema_code_langchain})\n"

                if executor_is_lambda:
                    tool_code += f"""

    def {tool_name}({f"input_data: {input_model_name}" if input_model_name != "None" else ""}) -> str:
        \"\"\"{func_desc}\"\"\"
        lambda_client = boto3.client('lambda', region_name="{lambda_region}")
    """
                    nested_code = """
        request_body_dump = model_dump.get("request_body", model_dump)
        content_type = request_body_dump.get("content_type_annotation", "*") if request_body_dump else None

        request_body = {"content": {content_type: {"properties": []}}}
        for param_name, param_value in request_body_dump.items():
            if param_name != "content_type_annotation":
                request_body["content"][content_type]["properties"].append({
                    "name": param_name,
                    "value": param_value
                })
        """

                    param_code = (
                        f"""model_dump = input_data.model_dump(exclude_unset = True)
        model_dump = model_dump.get("parameters", model_dump)

        for param_name, param_value in model_dump.items():
            parameters.append({{
                "name": param_name,
                "value": param_value
            }})
        {nested_code if content_models else ""}"""
                        if input_model_name != "None"
                        else ""
                    )

                    content_model_code = """
            if request_body:
                payload["requestBody"] = request_body
                """

                    tool_code += f"""

        parameters = []

        {param_code}

        try:
            payload = {{
                "messageVersion": "1.0",
                "agent": {{
                    "name": "{self.agent_info.get("agentName", "")}",
                    "id": "{self.agent_info.get("agentId", "")}",
                    "alias": "{self.agent_info.get("alias", "")}",
                    "version": "{self.agent_info.get("version", "")}"
                }},
                "sessionId": "",
                "sessionAttributes": {{}},
                "promptSessionAttributes": {{}},
                "actionGroup": "{action_group_name}",
                "apiPath": "{func_name}",
                "inputText": last_input,
                "httpMethod": "{method.upper()}",
                "parameters": {"parameters" if param_model_name else "{}"}
            }}

            {content_model_code if content_models else ""}

            response = lambda_client.invoke(
                FunctionName="{lambda_arn}",
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )

            response_payload = json.loads(response['Payload'].read().decode('utf-8'))

            return str(response_payload)

        except Exception as e:
            return f"Error executing {clean_func_name}/{method}: {{str(e)}}"
"""
                else:
                    tool_code += f"""
    def {tool_name}(input_data) -> str:
        \"\"\"{func_desc}\"\"\"
        return input(f"Return of control: {tool_name} was called with the input {{input_data}}, enter desired output:")
        """
                tool_instances.append(tool_name)

        return tool_instances, tool_code

    def generate_structured_ag_code(self, ag: Dict, platform: str) -> Tuple[list, str]:
        """Generate code for Structured Function Action Groups."""
        tool_code = ""
        tool_instances = []

        executor_is_lambda = bool(ag["actionGroupExecutor"].get("lambda", False))
        action_group_name = ag.get("actionGroupName", "")
        action_group_desc = ag.get("description", "").replace('"', '\\"')

        if executor_is_lambda:
            lambda_arn = ag.get("actionGroupExecutor", {}).get("lambda", "")
            lambda_region = lambda_arn.split(":")[3] if lambda_arn else "us-west-2"

        function_schema = ag.get("functionSchema", {}).get("functions", [])

        for func in function_schema:
            # Function metadata
            func_name = func.get("name", "")
            clean_func_name = clean_variable_name(func_name)
            func_desc = func.get("description", "").replace('"', '\\"')
            func_desc += f"\\nThis tool is part of the group of tools called {action_group_name}" + (
                f" (description: {action_group_desc})" if action_group_desc else ""
            )

            # Naming
            tool_name = prune_tool_name(f"{action_group_name}_{clean_func_name}")
            model_name = f"{action_group_name}_{clean_func_name}_Input"

            # Parameter Signature Generation
            params = func.get("parameters", {})
            param_list = []

            tool_code += f"""
    class {model_name}(BaseModel):"""

            if params:
                for param_name, param_info in params.items():
                    param_type = param_info.get("type", "string")
                    param_desc = param_info.get("description", "").replace('"', '\\"')
                    required = param_info.get("required", False)

                    # Map JSON Schema types to Python types
                    type_mapping = {
                        "string": "str",
                        "number": "float",
                        "integer": "int",
                        "boolean": "bool",
                        "array": "list",
                        "object": "dict",
                    }
                    py_type = type_mapping.get(param_type, "str")
                    param_list.append(f"{param_name}: {py_type} = None")

                    if required:
                        tool_code += f"""
        {param_name}: {py_type} = Field(..., description="{param_desc}")"""
                    else:
                        tool_code += f"""
        {param_name}: {py_type} = Field(None, description="{param_desc}")"""
            else:
                tool_code += """
        pass"""

            param_signature = ", ".join(param_list)
            params_input = ", ".join(
                [
                    f"{{'name': '{param_name}', 'type': '{param_info.get('type', 'string')}', 'value': {param_name}}}"
                    for param_name, param_info in params.items()
                ]
            )

            schema_code_strands = f"inputSchema={model_name}.model_json_schema()" if params else ""
            schema_code_langchain = f"args_schema={model_name}" if params else ""
            tool_code += f"""
    @tool({schema_code_strands if platform == "strands" else schema_code_langchain})
    """

            # Tool Function Code Generation
            if executor_is_lambda:
                tool_code += f"""
    def {tool_name}({param_signature}) -> str:
        \"\"\"{func_desc}\"\"\"
        lambda_client = boto3.client('lambda', region_name="{lambda_region}")

        # Prepare parameters
        parameters = [{params_input}]"""

                # Lambda invocation code
                tool_code += f"""

        # Invoke Lambda function
        try:
            payload = {{
                "actionGroup": "{action_group_name}",
                "function": "{func_name}",
                "inputText": last_input,
                "parameters": parameters,
                "agent": {{
                    "name": "{self.agent_info.get("agentName", "")}",
                    "id": "{self.agent_info.get("agentId", "")}",
                    "alias": "{self.agent_info.get("alias", "")}",
                    "version": "{self.agent_info.get("version", "")}"
                }},
                "sessionId": "",
                "sessionAttributes": {{}},
                "promptSessionAttributes": {{}},
                "messageVersion": "1.0"
            }}

            response = lambda_client.invoke(
                FunctionName="{lambda_arn}",
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )

            response_payload = json.loads(response['Payload'].read().decode('utf-8'))

            return str(response_payload)

        except Exception as e:
            return f"Error executing {func_name}: {{str(e)}}"
    """

            else:
                tool_code += f"""
    def {tool_name}({param_signature}) -> str:
        \"\"\"{func_desc}\"\"\"
        return input(f"Return of control: {action_group_name}_{func_name} was called with the input {{{", ".join(params.keys())}}}, enter desired output:")
        """

            tool_instances.append(tool_name)

        return tool_instances, tool_code

    def generate_example_usage(self) -> str:
        """Generate example usage code for the agent."""
        memory_code = (
            "LongTermMemoryManager.end_all_sessions()"
            if self.memory_enabled and not self.agentcore_memory_enabled
            else ""
        )
        run_code = "else: app.run()" if not self.is_collaborator else ""
        return f"""

    def cli():
        global user_id
        user_id = "{uuid.uuid4().hex[:8].lower()}" # change user_id if necessary
        session_id = uuid.uuid4().hex[:8].lower()
        try:
            while True:
                try:
                    query = inputimeout("\\nEnter your question (or 'exit' to quit): ", timeout={self.idle_timeout})

                    if query.lower() == "exit":
                        break

                    result = endpoint({{"message": query}}, RequestContext(session_id=session_id)).get('result', {{}})
                    if not result:
                        print("  Error:" + str(result.get('error', {{}})))
                        continue

                    print(f"\\nResponse: {{result.get('response', 'No response provided')}}")

                    if result["sources"]:
                        print(f"  Sources: {{', '.join(set(result.get('sources', [])))}}")

                    if result["tools_used"]:
                        tools_used.update(result.get('tools_used', []))
                        print(f"\\n  Tools Used: {{', '.join(tools_used)}}")

                    tools_used.clear()
                except KeyboardInterrupt:
                    print("\\n\\nExiting...")
                    break
                except TimeoutOccurred:
                    print("\\n\\nNo input received in the last {0} seconds. Exiting...")
                    break
        except Exception as e:
            print("\\n\\nError: {{}}".format(e))
        finally:
            {memory_code}
            print("Session ended.")

    if __name__ == "__main__":
        if len(sys.argv) > 1 and sys.argv[1] == "--cli":
            cli() # Run the CLI interface
        {run_code}
        """

    def generate_code_interpreter(self, platform: str):
        """Generate code for third-party code interpreter used in the agent."""
        if not self.code1p:
            self.imports_code += """
    from interpreter import interpreter"""

            return f"""

    # Code Interpreter Tool
    interpreter.llm.model = "bedrock/{self.model_id}"
    interpreter.llm.supports_functions = True
    interpreter.computer.emit_images = True
    interpreter.llm.supports_vision = True
    interpreter.auto_run = True
    interpreter.messages = []
    interpreter.anonymized_telemetry = False
    interpreter.system_message += "USER NOTES: DO NOT give further clarification or remarks on the code, or ask the user any questions. DO NOT write long running code that awaits user input. Remember that you can write to files using cat. Remember to keep track of your current working directory. Output the code you wrote so that the parent agent calling you can use it as part of a larger answer. \\n" + interpreter.system_message

    @tool
    def code_tool(original_question: str) -> str:
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
        return interpreter.chat(original_question, display=False)
"""
        else:
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
            coding_agent = create_react_agent(model=llm_ORCHESTRATION, prompt=coding_prompt, tools=coding_tools)
            coding_agent_input = {"messages": [{"role": "user", "content": original_question}]}

            return coding_agent.invoke(coding_agent_input)["messages"][-1].content
            """
            else:
                code_1p += """
            coding_agent = Agent(
                model=llm_ORCHESTRATION,
                system_prompt=coding_prompt,
                tools=coding_tools,
                )

            return str(coding_agent(original_question))
            """

            return code_1p

    def _get_url_regex_pattern(self) -> str:
        """Get the URL regex pattern for source extraction."""
        return r"(?:https?://|www\.)(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(?:/[^/\s]*)*"

    def generate_entrypoint_code(self, platform: str) -> str:
        """Generate entrypoint code for the agent."""
        entrypoint_code = ""

        if not self.is_collaborator:
            entrypoint_code += """
    @app.entrypoint
    """

        agentcore_memory_entrypoint_code = (
            """
            event = memory_client.create_event(
                memory_id=memory_id,
                actor_id=user_id,
                session_id=session_id,
                messages=formatted_messages
            )
        """
            if self.agentcore_memory_enabled
            else ""
        )

        tools_used_update_code = (
            "tools_used.update(list(agent_result.metrics.tool_metrics.keys()))"
            if platform == "strands"
            else "tools_used.update([msg.name for msg in agent_result if isinstance(msg, ToolMessage)])"
        )
        response_content_code = "str(agent_result)" if platform == "strands" else "agent_result[-1].content"
        url_pattern = self._get_url_regex_pattern()

        entrypoint_code += f"""
    def endpoint(payload, context):
        try:
            {"global user_id" if self.agentcore_memory_enabled else ""}
            {'user_id = user_id or payload.get("userId", uuid.uuid4().hex[:8])' if self.agentcore_memory_enabled else ""}
            session_id = context.session_id or payload.get("sessionId", uuid.uuid4().hex[:8])

            tools_used.clear()
            agent_query = payload.get("message", "")
            if not agent_query:
                return {{'error': "No query provided, please provide a 'message' field in the payload."}}

            agent_result = invoke_agent(agent_query)

            {tools_used_update_code}
            response_content = {response_content_code}

            # Gathering sources from the response
            sources = []
            urls = re.findall({repr(url_pattern)}, response_content)
            source_tags = re.findall(r"<source>(.*?)</source>", response_content)
            sources.extend(urls)
            sources.extend(source_tags)
            sources = list(set(sources))

            formatted_messages = [(agent_query, "USER"), (response_content if response_content else "No Response.", "ASSISTANT")]

            {agentcore_memory_entrypoint_code}

            return {{'result': {{'response': response_content, 'sources': sources, 'tools_used': list(tools_used), 'sessionId': session_id, 'messages': formatted_messages}}}}
        except Exception as e:
            return {{'error': str(e)}}
    """
        return entrypoint_code

    def translate(self, output_path: str, code_sections: list, platform: str):
        """Translate Bedrock agent config to LangChain code."""
        code = "\n".join(code_sections)
        code = unindent_by_one(code)

        code = autopep8.fix_code(code, options={"aggressive": 1, "max_line_length": 120})

        with open(output_path, "a+", encoding="utf-8") as f:
            f.truncate(0)
            f.write(code)

        environment_variables = {}
        if self.gateway_cognito_result:
            client_info = self.gateway_cognito_result.get("client_info", {})
            environment_variables.update(
                {
                    "cognito_client_id": client_info.get("client_id", ""),
                    "cognito_client_secret": client_info.get("client_secret", ""),
                    "cognito_user_pool_id": client_info.get("user_pool_id", ""),
                    "cognito_token_endpoint": client_info.get("token_endpoint", ""),
                    "cognito_scope": client_info.get("scope", ""),
                    "cognito_domain_prefix": client_info.get("domain_prefix", ""),
                }
            )

        # Write a .env file with the environment variables
        env_file_path = os.path.join(self.output_dir, ".env")
        with open(env_file_path, "w", encoding="utf-8") as env_file:
            for key, value in environment_variables.items():
                env_file.write(f"{key}={value}\n")

        # Copy over requirements.txt
        requirements_path = os.path.join(get_base_dir(__file__), "assets", f"requirements_{platform}.j2")
        if os.path.exists(requirements_path):
            with (
                open(requirements_path, "r", encoding="utf-8") as src_file,
                open(os.path.join(self.output_dir, "requirements.txt"), "w", encoding="utf-8") as dest_file,
            ):
                dest_file.truncate(0)
                dest_file.write(src_file.read())

        return environment_variables

    # --------------------------------
    # START: AgentCore Gateway Functions
    # --------------------------------

    def create_gateway(self):
        """Create the gateway and proxy for the agent."""
        print("  Creating Gateway for Agent...")
        gateway_client = GatewayClient(region_name=self.agent_region)
        gateway_name = f"{self.cleaned_agent_name.replace('_', '-')}-gateway-{uuid.uuid4().hex[:5].lower()}"

        self.gateway_cognito_result = gateway_client.create_oauth_authorizer_with_cognito(gateway_name=gateway_name)

        gateway = gateway_client.create_mcp_gateway(
            name=gateway_name,
            enable_semantic_search=True,
            authorizer_config=self.gateway_cognito_result["authorizer_config"],
        )
        return gateway

    def create_gateway_proxy_and_targets(self):
        """Create gateway proxy for the agent."""
        action_groups = self.custom_ags
        function_name = f"gateway_proxy_{uuid.uuid4().hex[:8].lower()}"
        account_id = boto3.client("sts").get_caller_identity().get("Account")
        lambda_arn = f"arn:aws:lambda:{self.agent_region}:{account_id}:function:{function_name}"

        # Aggregate info from the action_groups
        tool_mappings = {}

        for ag in action_groups:
            time.sleep(10)  # Sleep to avoid throttling issues with the Gateway API

            if "lambda" not in ag.get("actionGroupExecutor", {}):
                continue

            action_group_name = ag.get("actionGroupName", "AG")
            clean_action_group_name = clean_gateway_or_target_name(action_group_name)
            action_group_desc = ag.get("description", "").replace('"', '\\"')
            end_lambda_arn = ag.get("actionGroupExecutor", {}).get("lambda", "")
            tools = []

            if ag.get("apiSchema", False):
                openapi_schema = ag.get("apiSchema", {}).get("payload", {})

                for func_name, func_spec in openapi_schema.get("paths", {}).items():
                    clean_func_name = clean_variable_name(func_name)
                    for method, method_spec in func_spec.items():
                        tool_name_unpruned = f"{action_group_name}_{clean_func_name}_{method}"
                        tool_name = prune_tool_name(
                            tool_name_unpruned, length=(54 - len(clean_action_group_name))
                        )  # to ensure the tool is below 64 characters

                        tool_mappings[f"{clean_action_group_name}___{tool_name}"] = {
                            "actionGroup": action_group_name,
                            "apiPath": func_name,
                            "httpMethod": method.upper(),
                            "type": "openapi",
                            "lambdaArn": end_lambda_arn,
                            "lambdaRegion": end_lambda_arn.split(":")[3] if end_lambda_arn else "us-west-2",
                        }

                        func_desc = method_spec.get(
                            "description", method_spec.get("summary", "No Description Provided.")
                        )
                        func_desc += f"\\nThis tool is part of the group of tools called {action_group_name}{f' (description: {action_group_desc})' if action_group_desc else ''}."

                        # Convert AG OpenAPI Schema to JSON Schema

                        # Gateway does not support oneOf yet, so we need to flatten the schema
                        GATEWAY_ONEOF_NOT_SUPPORTED = True
                        parameters = method_spec.get("parameters", [])

                        request_body_required = method_spec.get("requestBody", {}).get("required", False)
                        request_body = method_spec.get("requestBody", {}).get("content", {})

                        requirements = []
                        if parameters:
                            requirements.append("parameters")
                        if request_body_required:
                            requirements.append("requestBody")

                        content_schemas = []
                        for content_type, content_schema in request_body.items():
                            content_schema = content_schema.get("schema", {})
                            converted = to_json_schema(content_schema)
                            converted.get("properties", {}).update(
                                {
                                    "contentType": {"description": f"MUST BE SET TO {content_type}", "type": "string"}
                                }  # NOTE: GATEWAY DOES NOT SUPPORT ENUM OR CONST YET
                            )
                            converted.get("required", []).append("contentType")
                            del converted["$schema"]
                            content_schemas.append(converted)

                        param_properties = {}
                        required_params = []
                        for parameter in parameters:
                            param_name = parameter.get("name", "")
                            param_desc = parameter.get("description", "").replace('"', '\\"')
                            param_required = parameter.get("required", False)
                            if "schema" in parameter:
                                param_type = parameter.get("schema", {}).get("type", "string")

                                param_properties[param_name] = {
                                    "type": param_type,
                                    "description": param_desc,
                                }
                            else:
                                param_content = parameter.get("content", {})
                                content_schemas = []
                                for content_type, content_schema in param_content.items():
                                    content_schema = content_schema.get("schema", {})
                                    converted = to_json_schema(content_schema)
                                    converted.get("properties", {}).update(
                                        {
                                            "contentType": {
                                                "description": f"MUST BE SET TO {content_type}",
                                                "type": "string",
                                            }
                                        }  # NOTE: GATEWAY DOES NOT SUPPORT ENUM OR CONST YET
                                    )
                                    converted.get("required", []).append("contentType")
                                    del converted["$schema"]
                                    content_schemas.append(converted)

                                param_properties[param_name] = (
                                    content_schemas[0]
                                    if len(content_schemas) == 1
                                    or (GATEWAY_ONEOF_NOT_SUPPORTED and len(content_schemas) > 1)
                                    else {
                                        "type": "object",
                                        "description": param_desc,
                                        "oneOf": content_schemas,  # NOTE: GATEWAY DOES NOT SUPPORT ONEOF YET
                                    }
                                )

                            if param_required:
                                required_params.append(param_name)

                        input_schema = {
                            "type": "object",
                            "properties": {},
                            "required": requirements,
                        }

                        if parameters:
                            input_schema["properties"]["parameters"] = {
                                "type": "object",
                                "properties": param_properties,
                                "required": required_params,
                            }
                        if content_schemas:
                            input_schema["properties"]["requestBody"] = (
                                content_schemas[0]
                                if len(content_schemas) == 1
                                or (GATEWAY_ONEOF_NOT_SUPPORTED and len(content_schemas) > 1)
                                else {
                                    "type": "object",
                                    "oneOf": content_schemas,
                                }  # NOTE: GATEWAY DOES NOT SUPPORT ONEOF YET
                            )

                        tools.append({"name": tool_name, "description": func_desc, "inputSchema": input_schema})

            elif ag.get("functionSchema", False):
                function_schema = ag.get("functionSchema", {}).get("functions", [])

                for func in function_schema:
                    func_name = func.get("name", "")
                    clean_func_name = clean_variable_name(func_name)
                    tool_name = prune_tool_name(f"{action_group_name}_{clean_func_name}")

                    tool_mappings[f"{clean_action_group_name}___{tool_name}"] = {
                        "actionGroup": action_group_name,
                        "function": func_name,
                        "type": "structured",
                        "lambdaArn": end_lambda_arn,
                        "lambdaRegion": end_lambda_arn.split(":")[3] if end_lambda_arn else "us-west-2",
                    }

                    func_desc = func.get("description", "No Description Provided.")
                    func_desc += f"\\nThis tool is part of the group of tools called {action_group_name}{f' (description: {action_group_desc})' if action_group_desc else ''}."

                    func_parameters = func.get("parameters", {})

                    # Convert AG Function Schema to JSON Schema
                    new_properties = {}
                    required_params = []
                    for param_name, param_info in func_parameters.items():
                        param_type = param_info.get("type", "string")
                        param_desc = param_info.get("description", "").replace('"', '\\"')
                        param_required = param_info.get("required", False)

                        new_properties[param_name] = {
                            "type": param_type,
                            "description": param_desc,
                        }

                        if param_required:
                            required_params.append(param_name)

                    tools.append(
                        {
                            "name": tool_name,
                            "description": func_desc,
                            "inputSchema": {
                                "type": "object",
                                "properties": new_properties,
                                "required": required_params,
                            },
                        }
                    )

            if tools:
                self.create_gateway_lambda_target(tools, lambda_arn, clean_action_group_name)

        agent_metadata = {
            "name": self.agent_info.get("agentName", ""),
            "id": self.agent_info.get("agentId", ""),
            "alias": self.agent_info.get("alias", ""),
            "version": self.agent_info.get("version", ""),
        }

        lambda_code = f"""
import boto3
import json

agent_metadata = {agent_metadata}
tool_mappings = {tool_mappings}

def get_json_type(value):
    if isinstance(value, str):
        return "string"
    elif isinstance(value, bool):
        return "boolean"
    elif isinstance(value, int):
        return "integer"
    elif isinstance(value, float):
        return "number"
    elif isinstance(value, list):
        return "array"
    elif isinstance(value, dict):
        return "object"
    elif value is None:
        return "null"
    else:
        return "unknown"

def transform_object(event_obj):
    result = []
    for key, value in event_obj.items():
        json_type = get_json_type(value)
        if json_type == "array":
            value = [transform_object(item) if isinstance(item, dict) else item for item in value]
        elif json_type == "object":
            value = transform_object(value)

        result.append({{
            "name": key,
            "value": value,
            "type": json_type
        }})
    return result

def lambda_handler(event, context):
    tool_name = context.client_context.custom.get('bedrockAgentCoreToolName', '')
    session_id = context.client_context.custom.get('bedrockAgentCoreSessionId', '')

    tool_info = tool_mappings.get(tool_name, {{}})
    if not tool_info:
        return {{'statusCode': 400, 'body': f"Tool {{tool_name}} not found"}}

    action_group = tool_info.get('actionGroup', '')
    end_lambda_arn = tool_info.get('lambdaArn', '')
    lambda_region = tool_info.get('lambdaRegion', 'us-west-2')

    lambda_client = boto3.client("lambda", region_name=lambda_region)

    payload = {{
        "messageVersion": "1.0",
        "agent": agent_metadata,
        "actionGroup": action_group,
        "sessionId": session_id,
        "sessionAttributes": {{}},
        "promptSessionAttributes": {{}},
        "inputText": ''
    }}

    if tool_info.get('type') == 'openapi':
        request_body_properties = transform_object(event.get('requestBody', {{}}))
        parameters_properties = transform_object(event.get('parameters', {{}}))
        content_type = event.get('requestBody', {{}}).get('contentType', 'application/json')

        payload.update({{
            "apiPath": tool_info.get('apiPath', ''),
            "httpMethod": tool_info.get('httpMethod', 'GET'),
            "parameters": parameters_properties,
            "requestBody": {{
                "content": {{
                    content_type: {{
                        "properties": request_body_properties,
                    }}
                }}
            }},
        }})
    elif tool_info.get('type') == 'structured':
        payload.update({{
            "function": tool_info.get('function', ''),
            "parameters": transform_object(event)
        }})

    try:
        response = lambda_client.invoke(
            FunctionName=end_lambda_arn,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )

        response_payload = json.loads(response['Payload'].read().decode('utf-8'))

        return {{'statusCode': 200, 'body': json.dumps(response_payload)}}

    except Exception as e:
        return {{'statusCode': 500, 'body': f'Error invoking Lambda: {{str(e)}}'}}
    """

        self.create_lambda(lambda_code, function_name)

    def _update_gateway_role_with_lambda_permission(self, function_name):
        """Update the gateway role with lambda invoke permission."""
        if not self.created_gateway or not self.created_gateway.get("roleArn"):
            return

        iam = boto3.client("iam")
        account_id = boto3.client("sts").get_caller_identity().get("Account")

        # Extract role name from ARN
        gateway_role_arn = self.created_gateway["roleArn"]
        gateway_role_name = gateway_role_arn.split("/")[-1]

        # Create the lambda invoke policy for the gateway role
        gateway_lambda_invoke_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "AmazonBedrockAgentCoreGatewayLambdaProd",
                    "Effect": "Allow",
                    "Action": ["lambda:InvokeFunction"],
                    "Resource": [f"arn:aws:lambda:*:{account_id}:function:*:*"],
                    "Condition": {"StringEquals": {"aws:ResourceAccount": account_id}},
                }
            ],
        }

        # Create and attach the policy to the gateway role
        policy_name = "GatewayLambdaInvokePolicy"
        try:
            policy_response = iam.create_policy(
                PolicyName=policy_name,
                PolicyDocument=json.dumps(gateway_lambda_invoke_policy),
                Description=f"Policy to allow gateway role to invoke Lambda function {function_name}",
            )
            policy_arn = policy_response["Policy"]["Arn"]
            print(f"  Created policy {policy_name} with ARN {policy_arn}")
        except iam.exceptions.EntityAlreadyExistsException:
            # Policy already exists, get its ARN
            policy_arn = f"arn:aws:iam::{account_id}:policy/{policy_name}"
            print(f"  Policy {policy_name} already exists")

        # Attach the policy to the gateway role
        try:
            iam.attach_role_policy(
                RoleName=gateway_role_name,
                PolicyArn=policy_arn,
            )
            print(f"  Attached lambda invoke policy to gateway role {gateway_role_name}")
        except iam.exceptions.EntityAlreadyExistsException:
            print(f"  Policy already attached to gateway role {gateway_role_name}")
        except Exception as e:
            print(f"  Warning: Could not attach lambda invoke policy to gateway role {gateway_role_name}: {str(e)}")

    def create_lambda(self, code, function_name):
        """Create a Lambda function for the agent proxy."""
        lambda_client = boto3.client("lambda", region_name=self.agent_region)
        iam = boto3.client("iam")

        role_name = "AgentCoreTestLambdaRole"

        lambda_trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "lambda.amazonaws.com"},
                    "Action": "sts:AssumeRole",
                }
            ],
        }

        # Lambda invoke policy for the proxy to call other Lambda functions
        lambda_invoke_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {"Effect": "Allow", "Action": ["lambda:InvokeFunction"], "Resource": "arn:aws:lambda:*:*:function:*"}
            ],
        }

        # Create zip file
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr("lambda_function.py", code)
        zip_buffer.seek(0)

        # Create Lambda execution role
        try:
            role_response = iam.create_role(
                RoleName=role_name, AssumeRolePolicyDocument=json.dumps(lambda_trust_policy)
            )

            # Attach basic execution role for CloudWatch logs
            iam.attach_role_policy(
                RoleName=role_name,
                PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
            )

            # Create and attach custom policy for Lambda invocation
            try:
                policy_response = iam.create_policy(
                    PolicyName="AgentCoreLambdaInvokePolicy",
                    PolicyDocument=json.dumps(lambda_invoke_policy),
                    Description="Policy to allow Lambda proxy to invoke other Lambda functions",
                )
                lambda_invoke_policy_arn = policy_response["Policy"]["Arn"]
            except iam.exceptions.EntityAlreadyExistsException:
                # Policy already exists, get its ARN
                account_id = boto3.client("sts").get_caller_identity().get("Account")
                lambda_invoke_policy_arn = f"arn:aws:iam::{account_id}:policy/AgentCoreLambdaInvokePolicy"

            iam.attach_role_policy(
                RoleName=role_name,
                PolicyArn=lambda_invoke_policy_arn,
            )

            role_arn = role_response["Role"]["Arn"]

            # Wait a bit for role to propagate
            time.sleep(10)
            print(f"  Created Lambda role {role_name} with ARN {role_arn}")

        except iam.exceptions.EntityAlreadyExistsException:
            role = iam.get_role(RoleName=role_name)
            role_arn = role["Role"]["Arn"]

            # Ensure the existing role has the Lambda invoke policy attached
            try:
                account_id = boto3.client("sts").get_caller_identity().get("Account")
                lambda_invoke_policy_arn = f"arn:aws:iam::{account_id}:policy/AgentCoreLambdaInvokePolicy"
                iam.attach_role_policy(
                    RoleName=role_name,
                    PolicyArn=lambda_invoke_policy_arn,
                )
            except iam.exceptions.EntityAlreadyExistsException:
                # Policy is already attached, which is fine
                pass
            except Exception:
                # If the policy doesn't exist, create it
                try:
                    policy_response = iam.create_policy(
                        PolicyName="AgentCoreLambdaInvokePolicy",
                        PolicyDocument=json.dumps(lambda_invoke_policy),
                        Description="Policy to allow Lambda proxy to invoke other Lambda functions",
                    )
                    lambda_invoke_policy_arn = policy_response["Policy"]["Arn"]
                    iam.attach_role_policy(
                        RoleName=role_name,
                        PolicyArn=lambda_invoke_policy_arn,
                    )
                except Exception:
                    # If we still can't attach the policy, log a warning but continue
                    print(f"Warning: Could not attach Lambda invoke policy to role {role_name}")

        # Create Lambda function
        try:
            response = lambda_client.create_function(
                FunctionName=function_name,
                Runtime="python3.10",
                Role=role_arn,
                Handler="lambda_function.lambda_handler",
                Code={"ZipFile": zip_buffer.read()},
                Description="Proxy Lambda for AgentCore Gateway",
            )

            lambda_arn = response["FunctionArn"]

            lambda_client.add_permission(
                FunctionName=function_name,
                StatementId="AllowAgentCoreInvoke",
                Action="lambda:InvokeFunction",
                Principal=self.created_gateway["roleArn"],
            )

            print(f"  Created Gateway Proxy Lambda function {function_name} with ARN {lambda_arn}")

        except lambda_client.exceptions.ResourceConflictException:
            response = lambda_client.get_function(FunctionName=function_name)
            lambda_arn = response["Configuration"]["FunctionArn"]

        # Update gateway role with lambda invoke permission
        self._update_gateway_role_with_lambda_permission(function_name)

        return lambda_arn

    def create_gateway_lambda_target(self, tools, lambda_arn, target_name):
        """Create a Lambda target for the gateway."""
        target = GatewayClient(region_name=self.agent_region).create_mcp_gateway_target(
            gateway=self.created_gateway,
            target_type="lambda",
            target_payload={"lambdaArn": lambda_arn, "toolSchema": {"inlinePayload": tools}},
            name=target_name,
        )
        return target

    # --------------------------------
    # END: AgentCore Gateway Functions
    # --------------------------------


# ruff: noqa: E501
