"""Base class for Bedrock Agent translation services.

This module provides a base class with common functionality for translating
AWS Bedrock Agent configurations into different frameworks.

Contains all the common logic between Langchain and Strands translations.
"""

import os
import uuid
from typing import Dict, Tuple

import autopep8
from bedrock_agentcore.memory import MemoryClient

from ..utils import get_base_dir, get_template_fixtures, safe_substitute_placeholders, unindent_by_one


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

        # AgentCore
        self.enabled_primitives = enabled_primitives
        # gateway currently not supported
        # self.gateway_enabled = enabled_primitives.get("gateway", False)
        self.agentcore_memory_enabled = enabled_primitives.get("memory", False)
        self.observability_enabled = enabled_primitives.get("observability", False)
        self.code1p = enabled_primitives.get("code_interpreter", False)

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

        # Initialize imports
        self.imports_code = """
    import json, sys, os, re, io, uuid
    from typing import Union, Optional, Annotated, Dict, List, Any, Literal
    from inputimeout import inputimeout, TimeoutOccurred
    from pydantic import BaseModel, Field
    import boto3

    from bedrock_agentcore.runtime.context import RequestContext
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

        if self.memory_enabled and self.agentcore_memory_enabled:
            self.imports_code += "\nfrom bedrock_agentcore.memory import MemoryClient\n"

            memory_client = MemoryClient(region_name=self.agent_region, environment="prod")

            memory = memory_client.create_memory_and_wait(
                name=f"{self.cleaned_agent_name}_memory_{uuid.uuid4().hex[:8].lower()}",
                strategies=[
                    {
                        "summaryMemoryStrategy": {
                            "name": "ConversationSummary",
                            "namespaces": ["summaries/{actorId}/{sessionId}"],
                        }
                    }
                ],  # Use actorId for multi-agent
                event_expiry_days=self.agent_info["memoryConfiguration"].get("storageDays", 30),
            )

            memory_id = memory["id"]

            output += f"""
    memory_client = MemoryClient(region_name='{self.agent_region}', environment="prod")
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

    def generate_example_usage(self) -> str:
        """Generate example usage code for the agent."""
        memory_code = (
            "LongTermMemoryManager.end_all_sessions()"
            if (self.multi_agent_enabled or self.memory_enabled) and not self.agentcore_memory_enabled
            else ""
        )
        run_code = "else: app.run()" if not self.is_collaborator else ""
        return f"""

    def cli():
        user_id = "{uuid.uuid4().hex[:8].lower()}" # change user_id if necessary
        session_id = uuid.uuid4().hex[:8].lower()
        try:
            while True:
                try:
                    query = inputimeout("\\nEnter your question (or 'exit' to quit): ", timeout={self.idle_timeout})

                    if query.lower() == "exit":
                        break

                    result = endpoint({{"prompt": query}}, RequestContext(session_id=session_id)).get('result', {{}})
                    if not result:
                        print("  Error:" + str(result.get('error', {{}})))
                        continue

                    print(f"\\nAgent Response: {{result.get('response', '')}}\\n")
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
                max_parallel_tools=1)

            return str(coding_agent(original_question))
            """

            return code_1p

    def translate(self, output_path: str, code_sections: list):
        """Translate Bedrock agent config to LangChain code."""
        code = "\n".join(code_sections)
        code = unindent_by_one(code)

        code = autopep8.fix_code(code, options={"aggressive": 1, "max_line_length": 120})

        with open(output_path, "a+", encoding="utf-8") as f:
            f.truncate(0)
            f.write(code)

        # Copy over requirements.txt
        requirements_path = os.path.join(get_base_dir(__file__), "assets", "requirements.txt")
        if os.path.exists(requirements_path):
            with (
                open(requirements_path, "r", encoding="utf-8") as src_file,
                open(os.path.join(self.output_dir, "requirements.txt"), "w", encoding="utf-8") as dest_file,
            ):
                dest_file.truncate(0)
                dest_file.write(src_file.read())


# ruff: noqa: E501
