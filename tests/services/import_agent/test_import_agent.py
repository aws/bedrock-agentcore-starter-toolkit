"""Tests for Bedrock AgentCore ECR service integration."""

import json
import os

from bedrock_agentcore_starter_toolkit.services.import_agent.scripts import (
    bedrock_to_langchain,
    bedrock_to_strands,
)


class TestImportAgent:
    """Test Import Agent functionality."""

    def test_bedrock_to_strands(self, mock_boto3_clients):
        """Test Bedrock to Strands import functionality."""

        base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)))
        agent_config = json.load(
            open(os.path.join(base_dir, "data", "bedrock_config_multi_agent.json"), "r", encoding="utf-8")
        )
        output_dir = os.path.join(base_dir, "output", "strands")
        os.makedirs(output_dir, exist_ok=True)

        bedrock_to_strands.BedrockStrandsTranslation(
            agent_config=agent_config, debug=False, output_dir=output_dir, enabled_primitives={}
        ).translate_bedrock_to_strands(os.path.join(output_dir, "strands_agent.py"))

    def test_bedrock_to_langchain(self, mock_boto3_clients):
        """Test Bedrock to LangChain import functionality."""

        base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)))
        agent_config = json.load(
            open(os.path.join(base_dir, "data", "bedrock_config_multi_agent.json"), "r", encoding="utf-8")
        )
        output_dir = os.path.join(base_dir, "output", "langchain")
        os.makedirs(output_dir, exist_ok=True)

        bedrock_to_langchain.BedrockLangchainTranslation(
            agent_config=agent_config, debug=False, output_dir=output_dir, enabled_primitives={}
        ).translate_bedrock_to_langchain(os.path.join(output_dir, "langchain_agent.py"))

    def test_bedrock_to_langchain_with_primitives(self, mock_boto3_clients):
        """Test Bedrock to LangChain import with AgentCore memory enabled."""

        base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)))
        agent_config = json.load(open(os.path.join(base_dir, "data", "bedrock_config.json"), "r", encoding="utf-8"))
        output_dir = os.path.join(base_dir, "output", "langchain_with_primitives")
        os.makedirs(output_dir, exist_ok=True)

        # Enable AgentCore memory primitive
        enabled_primitives = {"memory": True, "code_interpreter": True, "observability": True}

        translator = bedrock_to_langchain.BedrockLangchainTranslation(
            agent_config=agent_config, debug=False, output_dir=output_dir, enabled_primitives=enabled_primitives
        )

        # This should use the mocked MemoryClient
        translator.translate_bedrock_to_langchain(os.path.join(output_dir, "langchain_with_primitives.py"))

        # Verify that the mock was called
        memory_client_mock = mock_boto3_clients["bedrock_agentcore"]
        memory_client_mock.create_memory.assert_called_once()

    def test_bedrock_to_strands_with_primitives(self, mock_boto3_clients):
        """Test Bedrock to Strands import with AgentCore memory enabled."""

        base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)))
        agent_config = json.load(open(os.path.join(base_dir, "data", "bedrock_config.json"), "r", encoding="utf-8"))
        output_dir = os.path.join(base_dir, "output", "strands_with_primitives")
        os.makedirs(output_dir, exist_ok=True)

        # Enable AgentCore memory primitive
        enabled_primitives = {"memory": True, "code_interpreter": True, "observability": True}

        translator = bedrock_to_strands.BedrockStrandsTranslation(
            agent_config=agent_config, debug=False, output_dir=output_dir, enabled_primitives=enabled_primitives
        )

        # This should use the mocked MemoryClient
        translator.translate_bedrock_to_strands(os.path.join(output_dir, "strands_with_primitives.py"))

        # Verify that the mock was called
        memory_client_mock = mock_boto3_clients["bedrock_agentcore"]
        memory_client_mock.create_memory.assert_called_once()
