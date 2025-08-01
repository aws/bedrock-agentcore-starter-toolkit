# pylint: disable=consider-using-f-string, line-too-long
# ruff: noqa: E501
"""Bedrock Agent to LangChain Translator.

This script translates AWS Bedrock Agent configurations into equivalent LangChain code.
"""

import os
import textwrap

from .base_bedrock_translate import BaseBedrockTranslator


class BedrockLangchainTranslation(BaseBedrockTranslator):
    """Class to translate Bedrock Agent configurations to LangChain code."""

    def __init__(self, agent_config, debug: bool, output_dir: str, enabled_primitives: dict):
        """Initialize the BedrockLangchainTranslation class."""
        super().__init__(agent_config, debug, output_dir, enabled_primitives)

        self.imports_code += self.generate_imports()
        self.tools_code = self.generate_action_groups_code(platform="langchain")
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

        # Observability
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

    from langchain_aws import ChatBedrock
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
    # {prompt_type} LLM configuration
    llm_{prompt_type} = ChatBedrock(
        model_id="{self.model_id}",
        region_name="{self.agent_region}",
        provider="{self.agent_info["model"]["providerName"].lower()}",
        model_kwargs={{
            {f'"top_k": {inference_config.get("topK", 250)},' if self.agent_info["model"]["providerName"].lower() in ["anthropic", "amazon"] else ""}
            "top_p":{inference_config.get("topP", 1.0)},
            "temperature": {inference_config.get("temperature", 0)},
            "max_tokens": {inference_config.get("maximumLength", 2048)},
            {f'"stop_sequences": {repr(inference_config.get("stopSequences", []))},'.strip() if self.agent_info["model"]["providerName"].lower() in ["anthropic", "amazon"] else ""}
        }}"""

            # Add guardrails if available
            if self.guardrail_config:
                model_config += f""",
        guardrails={self.guardrail_config}"""

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

    def generate_agent_setup(self) -> str:
        """Generate agent setup code."""
        agent_code = f"tools = [{','.join(self.tools)}]\ntools_used = set()"

        if self.action_groups and self.tools_code:
            agent_code += """\ntools += action_group_tools"""

        if self.gateway_enabled:
            agent_code += """\ntools += mcp_tools"""

        memory_retrieve_code = (
            ""
            if not self.memory_enabled
            else (
                "memory_synopsis = memory_manager.get_memory_synopsis()"
                if not self.agentcore_memory_enabled
                else """
            memories = memory_client.retrieve_memories(memory_id=memory_id, namespace=f'/summaries/{user_id}', query="Retrieve the most recent session sumamries.", actor_id=user_id, top_k=20)
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
    def get_agent():

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
        agent = get_agent()
        {relay_code}
        {routing_code}
        {preprocess_code}
        {memory_add_user}

        response = asyncio.run(agent.ainvoke({{"messages": [{{"role": "user", "content": question}}]}}, config))
        {memory_add_assistant}
        {kb_code}
        {post_process_code}
        """

        agent_code += self.generate_entrypoint_code("langchain")

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

    def translate_bedrock_to_langchain(self, output_path: str) -> dict:
        """Translate Bedrock agent config to LangChain code."""
        return self.translate(output_path, self.code_sections, "langchain")
