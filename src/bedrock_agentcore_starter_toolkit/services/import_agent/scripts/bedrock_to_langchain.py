# pylint: disable=consider-using-f-string, line-too-long
# ruff: noqa: E501
"""Bedrock Agent to LangChain Translator.

This script translates AWS Bedrock Agent configurations into equivalent LangChain code.
"""

import os
import textwrap

from ..utils import clean_variable_name, generate_pydantic_models, prune_tool_name
from .base_bedrock_translate import BaseBedrockTranslator


class BedrockLangchainTranslation(BaseBedrockTranslator):
    """Class to translate Bedrock Agent configurations to LangChain code."""

    def __init__(self, agent_config, debug: bool, output_dir: str, enabled_primitives: dict):
        """Initialize the BedrockLangchainTranslation class."""
        super().__init__(agent_config, debug, output_dir, enabled_primitives)

        self.imports_code += self.generate_imports()
        self.tools_code = self.generate_action_groups_code()
        self.memory_code = self.generate_memory_configuration(memory_saver="InMemorySaver")
        self.collaboration_code = self.generate_collaboration_code()
        self.kb_code = self.generate_knowledge_base_code()
        self.models_code = self.generate_model_configurations()
        self.agent_setup_code = self.generate_agent_setup()
        self.usage_code = self.generate_example_usage()

        # If this agent is not a collaborator, create a BedrockAgentCore entrypoint
        if not self.is_collaborator:
            self.imports_code += """
    from bedrock_agentcore import BedrockAgentCoreApp

    app = BedrockAgentCoreApp()
    """

        if self.observability_enabled:
            self.imports_code += """
    from opentelemetry.instrumentation.langchain import LangchainInstrumentor

    LangchainInstrumentor().instrument()
"""

        # Format prompts code
        self.prompts_code = textwrap.fill(
            self.prompts_code, width=150, break_long_words=False, replace_whitespace=False
        )

        self.code_sections = [
            self.imports_code,
            self.models_code,
            self.prompts_code,
            self.collaboration_code,
            self.tools_code,
            self.memory_code,
            self.kb_code,
            self.agent_setup_code,
            self.usage_code,
        ]

    def generate_imports(self) -> str:
        """Generate import statements for LangChain components."""
        return """
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))

    from langchain_aws import ChatBedrockConverse
    from langchain_aws.retrievers import AmazonKnowledgeBasesRetriever

    from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
    from langchain_core.globals import set_verbose, set_debug

    from langchain.tools import tool

    from langgraph.prebuilt import create_react_agent, InjectedState
    from langgraph.checkpoint.memory import InMemorySaver
    """

    def generate_model_configurations(self) -> str:
        """Generate LangChain model configurations from Bedrock agent config."""
        model_configs = []

        for i, config in enumerate(self.prompt_configs):
            prompt_type = config.get("promptType", f"CUSTOM_{i}")
            inference_config = config.get("inferenceConfiguration", {})

            # Skip KB Generation if no knowledge bases are defined
            if prompt_type == "KNOWLEDGE_BASE_RESPONSE_GENERATION" and not self.knowledge_bases:
                continue

            # Build model configuration string
            model_config = f"""
    llm_{prompt_type} = ChatBedrockConverse(
        model_id="{self.model_id}",
        region_name="{self.agent_region}",
        provider="{self.agent_info["model"]["providerName"].lower()}",
        temperature={inference_config.get("temperature", 0)},
        max_tokens={inference_config.get("maximumLength", 2048)},
        stop_sequences={repr(inference_config.get("stopSequences", []))},
        top_p={inference_config.get("topP", 1.0)}
            """

            # Add guardrails if available
            if self.guardrail_config and prompt_type != "MEMORY_SUMMARIZATION":
                model_config += """,
        guardrails={}""".format(self.guardrail_config)

            model_config += "\n)"
            model_configs.append(model_config)

            # Generate the associated system prompt for this model
            self.generate_prompt(config)

        return "\n".join(model_configs)

    def generate_knowledge_base_code(self) -> str:
        """Generate code for knowledge base retrievers."""
        if not self.knowledge_bases:
            return ""

        kb_code = ""

        for kb in self.knowledge_bases:
            kb_name = kb.get("name", "")
            kb_description = kb.get("description", "")
            kb_id = kb.get("knowledgeBaseId", "")
            kb_region_name = kb.get("knowledgeBaseArn", "").split(":")[3]

            kb_code += f"""retriever_{kb_name} = AmazonKnowledgeBasesRetriever(
        knowledge_base_id="{kb_id}",
        retrieval_config={{"vectorSearchConfiguration": {{"numberOfResults": 5}}}},
        region_name="{kb_region_name}"
    )

    retriever_tool_{kb_name} = retriever_{kb_name}.as_tool(name="kb_{kb_name}", description="{kb_description}")
    """
            self.tools.append(f"retriever_tool_{kb_name}")

        return kb_code

    def generate_collaboration_code(self) -> str:
        """Generate code for multi-agent collaboration."""
        if not self.multi_agent_enabled or not self.collaborators:
            return ""

        collaborator_code = ""

        # Create the collaborators
        for i, collaborator in enumerate(self.collaborators):
            collaborator_name = collaborator.get("collaboratorName", "")
            collaborator_file_name = f"langchain_collaborator_{collaborator_name}"
            collaborator_path = os.path.join(self.output_dir, f"{collaborator_file_name}.py")

            # Recursively translate the collaborator agent to LangChain
            BedrockLangchainTranslation(
                collaborator, debug=self.debug, output_dir=self.output_dir, enabled_primitives=self.enabled_primitives
            ).translate_bedrock_to_langchain(collaborator_path)

            self.imports_code += (
                f"\nfrom {collaborator_file_name} import invoke_agent as invoke_{collaborator_name}_collaborator"
            )

            # conversation relay
            relay_conversation_history = collaborator.get("relayConversationHistory", "DISABLED") == "TO_COLLABORATOR"

            # Create tool to invoke the collaborator
            collaborator_code += """
    @tool
    def invoke_{0}(query: str, state: Annotated[dict, InjectedState]) -> str:
        \"\"\"Invoke the collaborator agent/specialist with the following description: {1}\"\"\"
        {2}
        invoke_agent_response = invoke_{0}_collaborator(query{3})
        tools_used.update([msg.name for msg in invoke_agent_response if isinstance(msg, ToolMessage)])
        return invoke_agent_response
        """.format(
                collaborator_name,
                self.collaborator_descriptions[i],
                "relay_history = state.get('messages', [])[:-1]" if relay_conversation_history else "",
                ", relay_history" if relay_conversation_history else "",
            )

            # Add the tool to the list of tools
            self.tools.append(f"invoke_{collaborator_name}")

        return collaborator_code

    def generate_action_groups_code(self) -> str:
        """Generate structured tools for action groups."""
        if not self.action_groups:
            return ""

        self.imports_code += """
    from langchain.tools import StructuredTool
    from pydantic import BaseModel, Field
    """

        tool_code = ""
        tool_instances = []

        for ag in self.action_groups:
            tool_instances_to_add = []
            code_to_add = ""

            # Route to the correct function for AG tool generation
            if ag.get("apiSchema", False):
                tool_instances_to_add, code_to_add = self.generate_openapi_action_groups_code(ag)
            if ag.get("functionSchema", False):
                tool_instances_to_add, code_to_add = self.generate_structured_action_groups_code(ag)

            tool_code += code_to_add
            tool_instances.extend(tool_instances_to_add)

        # Apply most up to date single KB optimization logic
        # Need there to be no AG tools and only one KB for this to apply
        self.single_kb_optimization_enabled = (
            self.single_kb and self.kb_generation_prompt_enabled and not tool_instances
        )

        if self.user_input_enabled:
            self.imports_code += """
    from langchain_community.tools import HumanInputRun"""
            tool_code += """
    user_input_tool = HumanInputRun(input_func=input)
    user_input_tool.description += \". If you do not have the parameters to invoke a function, then use this tool to ask the user for them.\""""
            tool_instances.append("user_input_tool")

        if self.code_interpreter_enabled:
            tool_code += self.generate_code_interpreter(platform="langchain")
            tool_instances.append("code_tool")

        tool_code += f"""
    action_group_tools = [{", ".join(tool_instances)}]
"""
        self.action_group_tools = tool_instances

        return tool_code

    def generate_structured_action_groups_code(self, ag):
        """Generate tool code for functionSchema action groups."""
        executor_is_lambda = bool(ag["actionGroupExecutor"].get("lambda", False))
        action_group_name = ag.get("actionGroupName", "")
        action_group_desc = ag.get("description", "").replace('"', '\\"')

        tool_code = ""
        tool_instances = []

        if executor_is_lambda:
            lambda_arn = ag.get("actionGroupExecutor", {}).get("lambda", "")
            lambda_region = lambda_arn.split(":")[3] if lambda_arn else "us-west-2"

        function_schema = ag.get("functionSchema", {}).get("functions", [])

        for func in function_schema:
            func_name = func.get("name", "")
            clean_func_name = clean_variable_name(func_name)
            func_desc = func.get("description", "").replace('"', '\\"')
            func_desc += f"\\nThis tool is part of the group of tools called {action_group_name}" + (
                f" (description: {action_group_desc})" if action_group_desc else ""
            )
            params = func.get("parameters", {})
            param_list = []
            tool_name = f"{action_group_name}_{clean_func_name}"

            tool_name = prune_tool_name(tool_name)

            # Create a Pydantic model for the function inputs
            model_name = f"{action_group_name}_{clean_func_name}_Input"

            tool_code += f"""
    class {model_name}(BaseModel):"""

            params_input = ", ".join(
                [
                    f"{{'name': '{param_name}', 'type': '{param_info.get('type', 'string')}', 'value': {param_name}}}"
                    for param_name, param_info in params.items()
                ]
            )

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

            param_sig = ", ".join(param_list)

            # Create function implementation
            if executor_is_lambda:
                tool_code += f"""

    def {tool_name}({param_sig}) -> str:
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

    def {tool_name}({param_sig}) -> str:
        \"\"\"{func_desc}\"\"\"
        return input(f"Return of control: {action_group_name}_{func_name} was called with the input {{{", ".join(params.keys())}}}, enter desired output:")
        """

            # Create StructuredTool
            tool_code += f"""
    {tool_name}_tool = StructuredTool.from_function(
        func={tool_name},
        name="{tool_name}",
        description="{func_desc}",
        args_schema={model_name}
    )
    """
            tool_instances.append(f"{tool_name}_tool")

        return tool_instances, tool_code

    def generate_openapi_action_groups_code(self, ag) -> str:
        """Generate tool code for openAPI schema action groups."""
        executor_is_lambda = bool(ag["actionGroupExecutor"].get("lambda", False))
        action_group_name = ag.get("actionGroupName", "")
        action_group_desc = ag.get("description", "").replace('"', '\\"')

        tool_code = """
    """
        tool_instances = []

        if executor_is_lambda:
            lambda_arn = ag.get("actionGroupExecutor", {}).get("lambda", "")
            lambda_region = lambda_arn.split(":")[3] if lambda_arn else "us-west-2"

        openapi_schema = ag.get("apiSchema", {}).get("payload", {})

        for func_name, func_spec in openapi_schema["paths"].items():
            clean_func_name = clean_variable_name(func_name)
            for method, method_spec in func_spec.items():
                tool_name = f"{action_group_name}_{clean_func_name}_{method}"

                tool_name = prune_tool_name(tool_name)

                params = method_spec.get("parameters", [])
                request_body = method_spec.get("requestBody", {})
                content = request_body.get("content", {})

                param_model_name = f"{tool_name}_Params"
                input_model_name = f"{tool_name}_Input"
                request_model_name = ""
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
                    tool_code += """
    class {0}(BaseModel):
        parameters: {1} None = Field(None, description = \"Parameters (ie. for a GET method) for this API Call\")
        {2}
    """.format(
                        input_model_name,
                        f"{param_model_name} |" if params else "",
                        (
                            f'request_body: {request_model_name} | None = Field(None, description = "Request body (ie. for a POST method) for this API Call")'
                            if content_models
                            else ""
                        ),
                    )
                elif params:
                    input_model_name = param_model_name
                elif content_models:
                    input_model_name = request_model_name
                else:
                    input_model_name = "None"

                func_desc = method_spec.get("description", method_spec.get("summary", "No Description Provided."))
                func_desc += f"\\nThis tool is part of the group of tools called {action_group_name}{f' (description: {action_group_desc})' if action_group_desc else ''}."

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
                if content_type:
                    payload["contentType"] = content_type"""

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

                tool_code += f"""
    {tool_name}_tool = StructuredTool.from_function(
        func={tool_name},
        name="{tool_name}",
        description="{func_desc}"
    )
    """
                tool_instances.append(f"{tool_name}_tool")

        return tool_instances, tool_code

    def generate_agent_setup(self) -> str:
        """Generate agent setup code."""
        agent_code = f"tools = [{','.join(self.tools)}]\ntools_used = set()"

        if self.action_groups and self.tools_code:
            agent_code += """\ntools += action_group_tools"""

        memory_retrieve_code = (
            ""
            if not self.memory_enabled
            else (
                "memory_synopsis = memory_manager.get_memory_synopsis()"
                if not self.agentcore_memory_enabled
                else """
            memories = memory_client.retrieve_memories(memory_id=memory_id, namespace=f'/summaries/{user_id}', query=query, actor_id=user_id, top_k=20)
            memory_synopsis = "\\n".join([m.get("content", {}).get("text", "") for m in memories])
"""
            )
        )

        # Create agent based on available components
        agent_code += """
    config = {{"configurable": {{"thread_id": "1"}}}}
    set_verbose({})
    set_debug({})

    _agent = None
    first_turn = True
    last_input = ""
    user_id = ""
    {}

    # agent update loop
    def get_agent(query: str):

        global _agent, user_id, memory_id

        {}
            {}
            system_prompt = ORCHESTRATION_TEMPLATE
            {}
            _agent = create_react_agent(
                model=llm_ORCHESTRATION,
                prompt=system_prompt,
                tools=tools,
                checkpointer=checkpointer_STM,
                debug={}
            )

        return _agent
""".format(
            self.debug,
            self.debug,
            'last_agent = ""' if self.multi_agent_enabled and self.supervision_type == "SUPERVISOR_ROUTER" else "",
            (
                "if _agent is None or memory_manager.has_memory_changed():"
                if self.memory_enabled and not self.agentcore_memory_enabled
                else "if _agent is None:"
            ),
            memory_retrieve_code,
            (
                "system_prompt = system_prompt.replace('$memory_synopsis$', memory_synopsis)"
                if self.memory_enabled
                else ""
            ),
            self.debug,
        )

        # Generate routing code if needed
        routing_code = self.generate_routing_code()

        # Set up relay parameter definition based on whether we're accepting relays
        relay_param_def = ", relayed_messages = []" if self.is_accepting_relays else ""

        # Add relay handling code if needed
        relay_code = (
            """if relayed_messages:
            agent.update_state(config, {"messages": relayed_messages})"""
            if self.is_accepting_relays
            else ""
        )

        # Set up preprocessing code if enabled
        preprocess_code = ""
        if "PRE_PROCESSING" in self.enabled_prompts:
            preprocess_code = """
        pre_process_output = llm_PRE_PROCESSING.invoke([SystemMessage(PRE_PROCESSING_TEMPLATE), HumanMessage(question)])
        question += "\\n<PRE_PROCESSING>{}</PRE_PROCESSING>".format(pre_process_output.content)
"""
            if self.debug:
                preprocess_code += '        print("PREPROCESSING_OUTPUT: {pre_process_output}")'

        # Memory recording code
        memory_add_user = (
            """
        memory_manager.add_message({'role': 'user', 'content': question})"""
            if self.memory_enabled and not self.agentcore_memory_enabled
            else ""
        )

        memory_add_assistant = (
            """
        memory_manager.add_message({'role': 'assistant', 'content': str(response)})"""
            if self.memory_enabled and not self.agentcore_memory_enabled
            else ""
        )

        # KB optimization code if enabled
        kb_code = ""
        if self.single_kb_optimization_enabled:
            kb_name = self.knowledge_bases[0]["name"]
            kb_code = f"""
        if first_turn:
            search_results = retriever_{kb_name}.invoke(question)
            response = llm_KNOWLEDGE_BASE_RESPONSE_GENERATION.invoke([SystemMessage(KB_GENERATION_TEMPLATE.replace("$search_results$, search_results)), HumanMessage(question))])
            first_turn = False
"""

        # Post-processing code
        post_process_code = (
            """
        post_process_prompt = POST_PROCESSING_TEMPLATE.replace("$question$", question).replace("$latest_response$", response["messages"][-1].content).replace("$responses$", str(response["messages"]))
        post_process_output = llm_POST_PROCESSING.invoke([HumanMessage(post_process_prompt)])
        return [AIMessage(post_process_output.content)]"""
            if "POST_PROCESSING" in self.enabled_prompts
            else "return response['messages']"
        )

        # Combine it all into the invoke_agent function
        agent_code += f"""
    def invoke_agent(question: str{relay_param_def}):
        {"global last_agent" if self.supervision_type == "SUPERVISOR_ROUTER" else ""}
        {"global first_turn" if self.single_kb_optimization_enabled else ""}
        global last_input, memory_id
        last_input = question
        agent = get_agent(question)
        {relay_code}
        {routing_code}
        {preprocess_code}
        {memory_add_user}

        response = agent.invoke({{"messages": [{{"role": "user", "content": question}}]}}, config)
        {memory_add_assistant}
        {kb_code}
        {post_process_code}
        """

        agentcore_memory_code = (
            """
            event = memory_client.create_event(
                memory_id=memory_id,
                actor_id=user_id,
                session_id=session_id,
                messages=formatted_messages
            )
        """
            if self.agentcore_memory_enabled and self.memory_enabled
            else ""
        )

        if not self.is_collaborator:
            agent_code += """
    @app.entrypoint
    """

        agent_code += (
            """
    def endpoint(payload, context):
        try:
            global user_id, tools_used

            user_id = payload.get("userId", uuid.uuid4().hex[:8])
            session_id = context.session_id or payload.get("sessionId", uuid.uuid4().hex[:8])

            tools_used.clear()
            agent_query = payload.get("prompt", "")
            if not agent_query:
                return {'error': "No query provided, please provide a 'prompt' field in the payload."}

            agent_result = invoke_agent(agent_query)
            print(f"Agent Result: {{agent_result}}")

            def format_message(msg):
                try:
                    text = msg.content if hasattr(msg, "content") else msg.text()

                    if not text or text.strip() == "":
                        return ("No response provided.", "UNKNOWN")
                    if isinstance(msg, HumanMessage):
                        return (text, "USER")
                    elif isinstance(msg, AIMessage):
                        return (text, "ASSISTANT")
                    elif isinstance(msg, ToolMessage):
                        return (text, "TOOL")
                    else:
                        return (text, "UNKNOWN")
                except Exception:
                    return ("No response provided.", "UNKNOWN")

            formatted_messages = [format_message(msg) for msg in agent_result]

            tools_used.update([msg.name for msg in agent_result if isinstance(msg, ToolMessage)])
            sources = []
            response_content = agent_result[-1].content

            urls = re.findall(r'(?:https?://|www\.)(?:[a-zA-Z0-9\-]+\.)+[a-zA-Z]{2,}(?:/[^/\s]*)*', response_content)
            source_tags = re.findall(r"<source>(.*?)</source>", response_content)

            if urls: sources.extend(urls)
            if source_tags: sources.extend(source_tags)

            sources = list(set(sources))

            %s

            return {'result': {'response': response_content, 'sources': sources, 'tools_used': list(tools_used), 'sessionId': session_id, 'messages': formatted_messages}}
        except Exception as e:
            return {'error': str(e)}
        """
            % agentcore_memory_code
        )

        return agent_code

    def generate_routing_code(self):
        """Generate routing code for supervisor router."""
        if not self.multi_agent_enabled or self.supervision_type != "SUPERVISOR_ROUTER":
            return ""

        code = """
        conversation = agent.checkpointer.get(config)
        if not conversation:
            conversation = {}
        messages = str(conversation.get("channel_values", {}).get("messages", []))

        routing_template = ROUTING_TEMPLATE
        routing_template = routing_template.replace("$last_user_request$", question).replace("$conversation$", messages).replace("$last_most_specialized_agent$", last_agent)
        routing_choice = llm_ROUTING_CLASSIFIER.invoke([SystemMessage(routing_template), HumanMessage(question)]).content

        choice = str(re.findall(r'<a.*?>(.*?)</a>', routing_choice)[0])"""

        if self.debug:
            code += """
        print("Routing to agent: {}. Last used agent was {}.".format(choice, last_agent))"""

        code += """
        if choice == "undecidable":
            pass"""

        for agent in self.collaborators:
            agent_name = agent.get("collaboratorName", "")
            relay_param = (
                ", messages"
                if self.collaborator_map.get(agent_name, {}).get("relayConversationHistory", "DISABLED")
                == "TO_COLLABORATOR"
                else ""
            )
            code += f"""
        elif choice == "{agent_name}":
            last_agent = "{agent_name}"
            return invoke_{agent_name}_collaborator(question{relay_param})"""

        code += """
        elif choice == "keep_previous_agent":
            return eval(f"invoke_{last_agent}_collaborator")(question, messages)"""

        return code

    def translate_bedrock_to_langchain(self, output_path: str):
        """Translate Bedrock agent config to LangChain code."""
        self.translate(output_path, self.code_sections)
