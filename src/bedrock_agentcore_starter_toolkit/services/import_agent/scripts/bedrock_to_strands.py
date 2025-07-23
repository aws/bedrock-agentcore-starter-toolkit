# pylint: disable=consider-using-f-string, line-too-long
# ruff: noqa: E501
"""Bedrock Agent to Strands Translator.

This script translates AWS Bedrock Agent configurations into equivalent Strands code.
"""

import os
import textwrap

from ..utils import clean_variable_name, generate_pydantic_models, prune_tool_name
from .base_bedrock_translate import BaseBedrockTranslator


class BedrockStrandsTranslation(BaseBedrockTranslator):
    """Class to translate Bedrock Agent configurations to Strands code."""

    def __init__(self, agent_config, debug: bool, output_dir: str, enabled_primitives: dict):
        """Initialize the BedrockStrandsTranslation class."""
        super().__init__(agent_config, debug, output_dir, enabled_primitives)

        self.imports_code += self.generate_imports()
        self.tools_code = self.generate_action_groups_code()
        self.memory_code = self.generate_memory_configuration(memory_saver="SlidingWindowConversationManager")
        self.collaboration_code = self.generate_collaboration_code()
        self.kb_code = self.generate_knowledge_base_code()
        self.models_code = self.generate_model_configurations()
        self.agent_setup_code = self.generate_agent_setup()
        self.usage_code = self.generate_example_usage()

        # if not a collaborator, create a BedrockAgentCore entrypoint
        if not self.is_collaborator:
            self.imports_code += """
    from bedrock_agentcore import BedrockAgentCoreApp

    app = BedrockAgentCoreApp()"""

        # make prompts more readable
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
        """Generate import statements for Strands components."""
        return """
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))

    from strands import Agent, tool
    from strands.agent.conversation_manager import SlidingWindowConversationManager
    from strands.models import BedrockModel
    from strands.types.content import Message
    """

    def generate_model_configurations(self) -> str:
        """Generate Strands model configurations from Bedrock agent config."""
        model_configs = []

        for i, config in enumerate(self.prompt_configs):
            prompt_type = config.get("promptType", "CUSTOM_{}".format(i))
            if prompt_type == "KNOWLEDGE_BASE_RESPONSE_GENERATION" and not self.knowledge_bases:
                continue
            inference_config = config.get("inferenceConfiguration", {})

            # Build model config string using string formatting
            model_config = f"""
    llm_{prompt_type} = BedrockModel(
        model_id="{self.model_id}",
        region_name="{self.agent_region}",
        temperature={inference_config.get("temperature", 0)},
        max_tokens={inference_config.get("maximumLength", 2048)},
        stop_sequences={repr(inference_config.get("stopSequences", []))},
        top_p={inference_config.get("topP", 1.0)},
        top_k={inference_config.get("topK", 250)}"""

            # Add guardrails if available
            if self.guardrail_config and prompt_type != "MEMORY_SUMMARIZATION":
                model_config += f""",
        guardrail_id="{self.guardrail_config["guardrailIdentifier"]}",
        guardrail_version="{self.guardrail_config["guardrailVersion"]}\""""

            model_config += "\n)"
            model_configs.append(model_config)

            self.generate_prompt(config)

        return "\n".join(model_configs)

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

    def generate_collaboration_code(self) -> str:
        """Generate code for multi-agent collaboration."""
        if not self.multi_agent_enabled or not self.collaborators:
            return ""

        collaborator_code = ""

        # create the collaborators
        for i, collaborator in enumerate(self.collaborators):
            collaborator_file_name = f"strands_collaborator_{collaborator.get('collaboratorName', '')}"
            collaborator_path = os.path.join(self.output_dir, f"{collaborator_file_name}.py")
            BedrockStrandsTranslation(
                collaborator, debug=self.debug, output_dir=self.output_dir, enabled_primitives=self.enabled_primitives
            ).translate_bedrock_to_strands(collaborator_path)

            self.imports_code += f"\nfrom {collaborator_file_name} import invoke_agent as invoke_{collaborator.get('collaboratorName', '')}_collaborator"

            # conversation relay
            relay_conversation_history = collaborator.get("relayConversationHistory", "DISABLED") == "TO_COLLABORATOR"

            # create the collaboration code
            collaborator_code += f"""
    @tool
    def invoke_{collaborator.get("collaboratorName", "")}(query: str) -> str:
        \"""Invoke the collaborator agent/specialist with the following description: {self.collaborator_descriptions[i]}\"""
        {"relay_history = get_agent().messages[:-2]" if relay_conversation_history else ""}
        invoke_agent_response = invoke_{collaborator.get("collaboratorName", "")}_collaborator(query{", relay_history" if relay_conversation_history else ""})
        return invoke_agent_response
        """

            self.tools.append("invoke_" + collaborator.get("collaboratorName", ""))

        return collaborator_code

    def generate_action_groups_code(self) -> str:
        """Generate structured tools for action groups."""
        if not self.action_groups:
            return ""

        tool_code = ""
        tool_instances = []

        for ag in self.action_groups:
            tool_instances_to_add = []
            code_to_add = ""
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

        if self.code_interpreter_enabled:
            tool_code += self.generate_code_interpreter(platform="strands")
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
            spec_code = ""
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

            spec_code += f"""
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
                        spec_code += f"""
        {param_name}: {py_type} = Field(..., description="{param_desc}")"""
                    else:
                        spec_code += f"""
        {param_name}: {py_type} = Field(None, description="{param_desc}")"""
            else:
                spec_code += """
        pass"""

            param_sig = ", ".join(param_list)

            func_desc += "EXPECTED INPUT (as Pydantic base model):\n" + spec_code.replace('"""', '\\"\\"\\"')

            tool_code += "@tool()\n"

            # Create function implementation
            if executor_is_lambda:
                tool_code += f"""
    def {tool_name}({param_sig}) -> str:
        \"\"\"{func_desc}\"\"\"
        lambda_client = boto3.client('lambda', region_name="{lambda_region}")
        global last_input

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

            tool_instances.append(tool_name)

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

                tool_code += f"@tool({f'inputSchema={input_model_name}.model_json_schema()' if input_model_name != 'None' else ''})\n"

                if executor_is_lambda:
                    tool_code += f"""

    def {tool_name}({f"input_data: {input_model_name}" if input_model_name != "None" else ""}) -> str:
        \"\"\"{func_desc}\"\"\"
        lambda_client = boto3.client('lambda', region_name="{lambda_region}")
        global last_input
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
                tool_instances.append(tool_name)

        return tool_instances, tool_code

    def generate_agent_setup(self) -> str:
        """Generate agent setup code."""
        agent_code = f"tools = [{','.join(self.tools)}]\ntools_used = set()"

        if self.debug or self.observability_enabled:
            self.imports_code += "\nfrom strands.telemetry.tracer import get_tracer"
            agent_code += '\nos.environ["STRANDS_OTEL_ENABLE_CONSOLE_EXPORT"] = "true"'
        else:
            agent_code += '\nos.environ["STRANDS_OTEL_ENABLE_CONSOLE_EXPORT"] = "false"'

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

    def make_msg(role, text):
        return {{
            "role": role,
            "content": [{{"text": text}}]
        }}

    def inference(model, messages, system_prompt=""):
        if system_prompt: response = model.converse(messages=messages, system_prompt=system_prompt)
        else: response = model.converse(messages=messages)

        text = ""
        for chunk in response:
            if not "contentBlockDelta" in chunk:
                continue
            text += chunk["contentBlockDelta"].get("delta", {{}}).get("text", "")

        return text

    _agent = None
    first_turn = True
    last_input = ""
    user_id = ""
    {}

    # agent update loop
    def get_agent():
        global _agent
        {}
            {}
            system_prompt = ORCHESTRATION_TEMPLATE
            {}
            _agent = Agent(
                model=llm_ORCHESTRATION,
                system_prompt=system_prompt,
                tools=tools,
                conversation_manager=checkpointer_STM
            )
        return _agent
    """.format(
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
        )

        # Generate routing code if needed
        routing_code = self.generate_routing_code()

        # Set up relay parameter definition based on whether we're accepting relays
        relay_param_def = ", relayed_messages = []" if self.is_accepting_relays else ""

        # Add relay handling code if needed
        relay_code = (
            """if relayed_messages:
            agent.messages = relayed_messages"""
            if self.is_accepting_relays
            else ""
        )

        # Set up preprocessing code if enabled
        preprocess_code = ""
        if "PRE_PROCESSING" in self.enabled_prompts:
            preprocess_code = """
        pre_process_output = inference(llm_PRE_PROCESSING, [make_msg("user", question)], system_prompt=PRE_PROCESSING_TEMPLATE)
        question += "\\n<PRE_PROCESSING>{}</PRE_PROCESSING>".format(pre_process_output)
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
            search_results = retrieve_{kb_name}(question)
            kb_prompt_templated = KB_GENERATION_TEMPLATE.replace("$search_results$", search_results)
            response = inference(llm_KNOWLEDGE_BASE_RESPONSE_GENERATION, [make_msg("user", question)], system_prompt=kb_prompt_templated)
            first_turn = False
"""

        # Post-processing code
        post_process_code = (
            """
        post_process_prompt = POST_PROCESSING_TEMPLATE.replace("$question$", question).replace("$latest_response$", str(response)).replace("$responses$", str(agent.messages))
        post_process_output = inference(llm_POST_PROCESSING, [make_msg("user", post_process_prompt)])
        return post_process_output"""
            if "POST_PROCESSING" in self.enabled_prompts
            else "return response"
        )

        # Combine it all into the invoke_agent function
        agent_code += f"""
    def invoke_agent(question: str{relay_param_def}):
        {"global last_agent" if self.supervision_type == "SUPERVISOR_ROUTER" else ""}
        {"global first_turn" if self.single_kb_optimization_enabled else ""}
        global last_input, memory_id
        last_input = question
        agent = get_agent()
        {relay_code}
        {routing_code}
        {preprocess_code}
        {memory_add_user}

        original_stdout = sys.stdout
        sys.stdout = io.StringIO()
        response = agent(question)
        sys.stdout = original_stdout
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

            formatted_messages = [(agent_query, "USER"), (str(agent_result), "ASSISTANT")]

            tools_used.update(list(agent_result.metrics.tool_metrics.keys()))
            sources = []
            response_content = str(agent_result)

            urls = re.findall(r'(?:https?://|www\.)(?:[a-zA-Z0-9\-]+\.)+[a-zA-Z]{2,}(?:/[^/\s]*)*', response_content)
            source_tags = re.findall(r"<source>(.*?)</source>", response_content)

            if urls: sources.extend(urls)
            if source_tags: sources.extend(source_tags)

            sources = list(set(sources))

            %s

            return {"result": {"response": response_content, "sources": sources, "tools_used": tools_used, "messages": formatted_messages}}
        except Exception as e:
            return {"error": str(e)}
        """
            % agentcore_memory_code
        )

        return agent_code

    def generate_routing_code(self):
        """Generate routing code for supervisor router."""
        if not self.multi_agent_enabled or self.supervision_type != "SUPERVISOR_ROUTER":
            return ""

        code = """
        messages = str(agent.messages)

        routing_template = ROUTING_TEMPLATE
        routing_template = routing_template.replace("$last_user_request$", question).replace("$conversation$", messages).replace("$last_most_specialized_agent$", last_agent)
        routing_choice = inference(llm_ROUTING_CLASSIFIER, [make_msg("user", question)], system_prompt=ROUTING_TEMPLATE)

        choice = str(re.findall(r'<a.*?>(.*?)</a>', routing_choice)[0])"""

        if self.debug:
            code += """
        print("Routing to agent: {}. Last used agent was {}.".format(choice, last_agent))"""

        code += """
        if choice == "undecidable":
            pass"""

        for agent in self.collaborators:
            agent_name = agent.get("collaboratorName", "")
            code += f"""
        elif choice == "{agent_name}":
            last_agent = "{agent_name}"
            return invoke_{agent_name}_collaborator(question)"""

        code += """
        elif choice == "keep_previous_agent":
            return eval(f"invoke_{last_agent}_collaborator")(question)"""

        return code

    def translate_bedrock_to_strands(self, output_path) -> str:
        """Translate Bedrock agent configuration to Strands code."""
        self.translate(output_path, self.code_sections)
