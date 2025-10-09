# pylint: disable=consider-using-f-string, line-too-long
# ruff: noqa: E501
"""Bedrock Agent to Strands Translator.

This script translates AWS Bedrock Agent configurations into equivalent Strands code.
"""

import os
import textwrap

from .base_bedrock_translate import BaseBedrockTranslator


class BedrockStrandsTranslation(BaseBedrockTranslator):
    """Class to translate Bedrock Agent configurations to Strands code."""

    def __init__(self, agent_config, debug: bool, output_dir: str, enabled_primitives: dict):
        """Initialize the BedrockStrandsTranslation class."""
        super().__init__(agent_config, debug, output_dir, enabled_primitives)

        self.imports_code += self.generate_imports()
        self.tools_code = self.generate_action_groups_code(platform="strands")
        self.memory_code = self.generate_memory_configuration(memory_saver="SlidingWindowConversationManager")
        self.collaboration_code = self.generate_collaboration_code()
        self.kb_code = self.generate_knowledge_base_code()
        self.models_code = self.generate_model_configurations()
        self.agent_setup_code = self.generate_agent_setup()
        self.usage_code = self.generate_example_usage()

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

            # NOTE: Converse Models support guardrails, but they are applied too eagerly on 2nd invocations.
            # Disabling guardrail support for Strands for now.

            # Add guardrails if available
            #     if self.guardrail_config and prompt_type != "MEMORY_SUMMARIZATION":
            #         model_config += f""",
            # guardrail_id="{self.guardrail_config["guardrailIdentifier"]}",
            # guardrail_version="{self.guardrail_config["guardrailVersion"]}\""""

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

    def generate_agent_setup(self) -> str:
        """Generate agent setup code."""
        agent_code = f"tools = [{','.join(self.tools)}]\ntools_used = set()"

        if self.gateway_enabled:
            agent_code += """\ntools += mcp_tools"""

        if self.debug:
            self.imports_code += "\nfrom strands.telemetry import StrandsTelemetry"
            agent_code += """
    strands_telemetry = StrandsTelemetry()
    strands_telemetry.setup_meter(enable_console_exporter=True)
    strands_telemetry.setup_console_exporter()
        """

        if self.action_groups and self.tools_code:
            agent_code += """\ntools += action_group_tools"""

        memory_retrieve_code = (
            ""
            if not self.memory_enabled
            else (
                "memory_synopsis = memory_manager.get_memory_synopsis()"
                if not self.agentcore_memory_enabled
                else """
            memories = memory_client.retrieve_memories(memory_id=memory_id, namespace=f'/summaries/{user_id}', query="Retrieve the most recent session sumamries.", top_k=20)
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
        async def run_inference():
            results = []
            async for event in model.stream(messages=messages, system_prompt=system_prompt):
                results.append(event)
            return results

        response = asyncio.run(run_inference())

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
        global last_input
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

        agent_code += self.generate_entrypoint_code("strands")

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

    def translate_bedrock_to_strands(self, output_path) -> dict:
        """Translate Bedrock agent configuration to Strands code."""
        return self.translate(output_path, self.code_sections, "strands")
