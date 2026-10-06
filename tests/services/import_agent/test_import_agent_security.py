"""Security regression tests for import-agent source generation."""

import ast
import json
import keyword
import os
from unittest.mock import MagicMock, patch

import pytest
from prance.util.resolver import RESOLVE_INTERNAL

from bedrock_agentcore_starter_toolkit.cli.create.import_agent.agent_info import get_agent_info
from bedrock_agentcore_starter_toolkit.services.import_agent.scripts.base_bedrock_translate import (
    BaseBedrockTranslator,
)
from bedrock_agentcore_starter_toolkit.services.import_agent.scripts.bedrock_to_langchain import (
    BedrockLangchainTranslation,
)
from bedrock_agentcore_starter_toolkit.services.import_agent.scripts.bedrock_to_strands import (
    BedrockStrandsTranslation,
)
from bedrock_agentcore_starter_toolkit.services.import_agent.utils import (
    IDENTIFIER_PATTERN,
    IdentifierAllocator,
    assert_local_references_only,
    generate_pydantic_models,
    prune_tool_name,
    python_data_literal,
    python_string_literal,
    unindent_by_one,
)

INJECTION_TEXT = '"""); INJECTED_SENTINEL = 1; # quotes \' slash \\\\ and\nnew line'


def assert_inert_generated_source(source):
    """Assert the marker remains string data and never becomes an assignment."""
    tree = ast.parse(unindent_by_one(source))
    assigned_names = {
        target.id
        for node in ast.walk(tree)
        if isinstance(node, (ast.Assign, ast.AnnAssign))
        for target in ([node.target] if isinstance(node, ast.AnnAssign) else node.targets)
        if isinstance(target, ast.Name)
    }
    assert "INJECTED_SENTINEL" not in assigned_names
    assert any(
        isinstance(node, ast.Constant) and isinstance(node.value, str) and "INJECTED_SENTINEL" in node.value
        for node in ast.walk(tree)
    )


def test_pydantic_model_generation_encodes_descriptions_and_aliases_invalid_names():
    """Schema text must be inert and wire names must survive identifier cleanup."""
    schema = {
        "type": "object",
        "description": INJECTION_TEXT,
        "properties": {
            "class": {"type": "string", "description": INJECTION_TEXT},
            "user-id": {"type": "string", "description": INJECTION_TEXT},
            "user id": {"type": "integer"},
        },
        "required": ["class", "user-id"],
    }

    generated, _ = generate_pydantic_models({"schema": schema})

    assert_inert_generated_source(generated)
    assert "class_: str = Field(...," in generated
    assert "alias='class'" in generated
    assert "user_id: str = Field(...," in generated
    assert "alias='user-id'" in generated
    assert "user_id_2: Optional[int] = Field(None, alias='user id')" in generated


@pytest.mark.parametrize(
    ("prompt_type", "base_prompt"),
    [
        ("PRE_PROCESSING", {"system": INJECTION_TEXT}),
        ("MEMORY_SUMMARIZATION", {"messages": [{"content": INJECTION_TEXT}]}),
        ("POST_PROCESSING", {"messages": [{"content": [{"text": INJECTION_TEXT}]}]}),
    ],
)
def test_prompt_generation_keeps_text_inert(prompt_type, base_prompt):
    """Prompt text must remain inert in generated source."""
    translator = BaseBedrockTranslator.__new__(BaseBedrockTranslator)
    translator.enabled_prompts = []
    translator.prompts_code = ""
    translator.knowledge_bases = []

    translator.generate_prompt({"promptType": prompt_type, "basePromptTemplate": base_prompt})

    assert_inert_generated_source(translator.prompts_code)


def test_orchestration_collaboration_instruction_is_inert():
    """Collaboration instructions must remain inert when substituted into orchestration prompts."""
    translator = BaseBedrockTranslator.__new__(BaseBedrockTranslator)
    translator.enabled_prompts = []
    translator.prompts_code = ""
    translator.knowledge_bases = []
    translator.memory_enabled_types = []
    translator.user_input_enabled = False
    translator.action_groups = []
    translator.code_interpreter_enabled = False
    translator.instruction = INJECTION_TEXT
    translator.collaborator_descriptions = [INJECTION_TEXT]

    translator.generate_prompt(
        {
            "promptType": "ORCHESTRATION",
            "basePromptTemplate": {
                "system": "$instruction$\n$agent_collaborators$ ",
            },
        }
    )

    assert_inert_generated_source(translator.prompts_code)


@pytest.mark.parametrize("translator_class", [BedrockStrandsTranslation, BedrockLangchainTranslation])
def test_knowledge_base_description_is_inert_for_each_framework(translator_class):
    """Knowledge-base descriptions must not escape generated strings or docstrings."""
    translator = translator_class.__new__(translator_class)
    translator.knowledge_bases = [
        {
            "name": "class",
            "description": INJECTION_TEXT,
            "knowledgeBaseId": "kb-id",
            "knowledgeBaseArn": "arn:aws:bedrock:us-west-2:123456789012:knowledge-base/kb-id",
        }
    ]
    translator.knowledge_base_code_names = ["class_"]
    translator.tools = []

    generated = translator.generate_knowledge_base_code()

    assert_inert_generated_source(generated)
    assert "class_" in generated


@pytest.mark.parametrize(
    ("translator_class", "child_method"),
    [
        (BedrockStrandsTranslation, "translate_bedrock_to_strands"),
        (BedrockLangchainTranslation, "translate_bedrock_to_langchain"),
    ],
)
def test_collaboration_description_is_inert_for_each_framework(tmp_path, translator_class, child_method):
    """Collaboration instructions must remain inside generated function docstrings."""
    translator = translator_class.__new__(translator_class)
    translator.multi_agent_enabled = True
    translator.collaborators = [
        {
            "collaboratorName": "class",
            "relayConversationHistory": "DISABLED",
        }
    ]
    translator.collaborator_code_names = ["class_"]
    translator.collaborator_map = {"class_": translator.collaborators[0]}
    translator.collaborator_descriptions = [INJECTION_TEXT]
    translator.output_dir = str(tmp_path)
    translator.debug = False
    translator.enabled_primitives = {}
    translator.imports_code = ""
    translator.tools = []

    with (
        patch.object(translator_class, "__init__", return_value=None),
        patch.object(translator_class, child_method, return_value={}),
    ):
        generated = translator.generate_collaboration_code()

    assert_inert_generated_source(generated)
    assert "invoke_class_" in generated


def test_structured_action_group_text_and_parameter_names_are_inert():
    """Function schema values must be encoded and invalid parameter names sanitized."""
    translator = BaseBedrockTranslator.__new__(BaseBedrockTranslator)
    translator.tool_identifiers = IdentifierAllocator()
    translator.agent_info = {
        "agentName": INJECTION_TEXT,
        "agentId": "agent-id",
        "alias": "alias-id",
        "version": "1",
    }
    action_group = {
        "actionGroupName": "1-action-group",
        "description": INJECTION_TEXT,
        "actionGroupExecutor": {"lambda": "arn:aws:lambda:us-west-2:123456789012:function:test"},
        "functionSchema": {
            "functions": [
                {
                    "name": "run",
                    "description": INJECTION_TEXT,
                    "parameters": {
                        "class": {
                            "type": "string",
                            "description": INJECTION_TEXT,
                            "required": True,
                        }
                    },
                }
            ]
        },
    }

    _, generated = translator.generate_structured_ag_code(action_group, "strands")

    assert_inert_generated_source(generated)
    assert "class Model1ActionGroupRunInput(BaseModel):" in generated
    assert "class_: str" in generated
    assert "alias=" not in generated
    assert "'name': 'class'" in generated
    assert "'value': class_" in generated


def test_openapi_action_group_text_is_inert_and_wire_names_are_preserved():
    """OpenAPI metadata must be encoded and model dumps must use original wire aliases."""
    translator = BaseBedrockTranslator.__new__(BaseBedrockTranslator)
    translator.tool_identifiers = IdentifierAllocator()
    translator.agent_info = {
        "agentName": INJECTION_TEXT,
        "agentId": "agent-id",
        "alias": "alias-id",
        "version": "1",
    }
    action_group = {
        "actionGroupName": "action-group",
        "description": INJECTION_TEXT,
        "actionGroupExecutor": {"lambda": "arn:aws:lambda:us-west-2:123456789012:function:test"},
        "apiSchema": {
            "payload": {
                "paths": {
                    "/run": {
                        "post": {
                            "description": INJECTION_TEXT,
                            "parameters": [
                                {
                                    "name": "class",
                                    "in": "query",
                                    "required": True,
                                    "description": INJECTION_TEXT,
                                    "schema": {"type": "string"},
                                }
                            ],
                        }
                    }
                }
            }
        },
    }

    _, generated = translator.generate_openapi_ag_code(action_group, "strands")

    assert_inert_generated_source(generated)
    assert "alias='class'" in generated
    assert "model_dump(exclude_unset=True, by_alias=True)" in generated
    assert "\"apiPath\": '/run'" in generated


def _mock_agent_clients(api_schema_payload):
    bedrock_client = MagicMock()
    bedrock_agent_client = MagicMock()
    bedrock_agent_client.get_agent_alias.return_value = {
        "agentAlias": {"routingConfiguration": [{"agentVersion": "1"}]}
    }
    bedrock_agent_client.get_agent.return_value = {
        "agent": {
            "agentName": "test",
            "agentArn": "arn:aws:bedrock:us-west-2:123456789012:agent/test",
            "agentCollaboration": "DISABLED",
            "foundationModel": "provider.model",
            "orchestrationType": "CUSTOM",
        }
    }
    bedrock_client.get_foundation_model.return_value = {"modelDetails": {}}
    bedrock_agent_client.list_agent_action_groups.return_value = {
        "actionGroupSummaries": [{"actionGroupId": "group-id"}]
    }
    bedrock_agent_client.get_agent_action_group.return_value = {
        "agentActionGroup": {
            "actionGroupName": "group",
            "apiSchema": {"payload": api_schema_payload},
        }
    }
    bedrock_agent_client.list_agent_knowledge_bases.return_value = {"agentKnowledgeBaseSummaries": []}
    return bedrock_client, bedrock_agent_client


@patch("bedrock_agentcore_starter_toolkit.cli.create.import_agent.agent_info.ResolvingParser")
def test_openapi_parser_only_resolves_internal_references(mock_parser):
    """Imported OpenAPI schemas must not resolve HTTP or file references."""
    bedrock_client, bedrock_agent_client = _mock_agent_clients(
        "openapi: 3.0.0\ninfo:\n  title: test\n  version: 1\npaths: {}"
    )
    mock_parser.return_value.specification = {"paths": {}}

    get_agent_info("agent-id", "alias-id", bedrock_client, bedrock_agent_client)

    mock_parser.assert_called_once()
    assert mock_parser.call_args.kwargs["resolve_types"] == RESOLVE_INTERNAL


@patch("bedrock_agentcore_starter_toolkit.cli.create.import_agent.agent_info.ResolvingParser")
def test_get_agent_info_rejects_external_reference_before_parser(mock_parser):
    """The import boundary must reject external references before Prance runs."""
    bedrock_client, bedrock_agent_client = _mock_agent_clients(
        """
openapi: 3.0.0
info:
  title: test
  version: 1
paths:
  /x:
    get:
      parameters:
        - name: value
          in: query
          schema:
            $ref: https://evil.example/schema.json
"""
    )

    with pytest.raises(ValueError, match="External OpenAPI references"):
        get_agent_info("agent-id", "alias-id", bedrock_client, bedrock_agent_client)

    mock_parser.assert_not_called()


def test_external_openapi_references_are_rejected():
    """Only in-document references are accepted; anything fetchable is refused."""
    for reference in (
        "https://evil.example/schema.json",
        "http://169.254.169.254/latest/meta-data/",
        "file:///etc/passwd",
        "/etc/passwd",
        "other.yaml#/components/schemas/Request",
        "//host/schema.yaml",
    ):
        spec = {"paths": {"/x": {"get": {"parameters": [{"schema": {"$ref": reference}}]}}}}
        with pytest.raises(ValueError, match="External OpenAPI references"):
            assert_local_references_only(spec)


def test_local_openapi_references_are_accepted():
    """Fragment-only references and $ref-shaped property names must still pass."""
    assert_local_references_only(
        {
            "components": {"schemas": {"Request": {"type": "string"}}},
            "paths": {"/x": {"get": {"parameters": [{"schema": {"$ref": "#/components/schemas/Request"}}]}}},
        }
    )
    # A property legitimately named "$ref" carries a schema object, not a string
    assert_local_references_only({"properties": {"$ref": {"type": "string"}}})


def test_identifier_allocator_contract():
    """Identifiers must be valid, keyword-free, unique, and stable per raw name."""
    allocator = IdentifierAllocator()
    names = [allocator.allocate(raw) for raw in ("user-id", "user id", "user_id", "class", "1st", "")]

    assert names == ["user_id", "user_id_2", "user_id_3", "class_", "_1st", "variable"]
    assert len(set(names)) == len(names)
    for name in names:
        assert IDENTIFIER_PATTERN.match(name)
        assert not keyword.iskeyword(name)

    # Repeated lookups of the same raw name return the same identifier
    assert allocator.allocate("user-id") == "user_id"

    allocator.reserve("reserved")
    assert allocator.allocate("reserved") == "reserved_2"


def test_identifier_allocator_separates_identity_from_preferred_name():
    """Different source values that clean identically must remain distinct."""
    allocator = IdentifierAllocator()

    assert allocator.allocate(("path", "/users/{id}"), "group_/users/{id}_get") == "group_users_id_get"
    assert allocator.allocate(("path", "/users/id"), "group_/users/id_get") == "group_users_id_get_2"


def test_pruned_tool_names_are_deterministic():
    """Tool names key Gateway target mappings, so re-imports must reproduce them."""
    long_name = "action_group_" + "x" * 80
    assert prune_tool_name(long_name) == prune_tool_name(long_name)
    assert len(prune_tool_name(long_name)) <= 64


@pytest.mark.parametrize(
    "value",
    [
        'quotes """ and slash \\\\',
        "carriage\rreturn",
        "nul\x00character",
    ],
)
def test_python_string_literal_round_trips_control_characters(value):
    """Generated string literals must preserve arbitrary text exactly."""
    assert ast.literal_eval(python_string_literal(value)) == value


@pytest.mark.parametrize("value", [{"enabled": True}, {"value": None}, ["x", 1, False]])
def test_python_data_literal_is_valid_python(value):
    """JSON-compatible data must use Python spellings at runtime."""
    assert ast.literal_eval(python_data_literal(value)) == value


def test_colliding_openapi_paths_receive_distinct_local_tool_names():
    """Local generation must not merge paths that clean to the same identifier."""
    translator = BaseBedrockTranslator.__new__(BaseBedrockTranslator)
    translator.tool_identifiers = IdentifierAllocator()
    translator.agent_info = {"agentName": "agent", "agentId": "id", "alias": "alias", "version": "1"}
    action_group = {
        "actionGroupName": "group",
        "actionGroupExecutor": {"customControl": "RETURN_CONTROL"},
        "apiSchema": {
            "payload": {
                "paths": {
                    "/users/{id}": {"get": {"description": "one"}},
                    "/users/id": {"get": {"description": "two"}},
                }
            }
        },
    }

    tools, generated = translator.generate_openapi_ag_code(action_group, "strands")

    assert tools == ["group_users_id_get", "group_users_id_get_2"]
    ast.parse(unindent_by_one(generated))


@patch("bedrock_agentcore_starter_toolkit.services.import_agent.scripts.base_bedrock_translate.time.sleep")
@patch("bedrock_agentcore_starter_toolkit.services.import_agent.scripts.base_bedrock_translate.boto3.client")
def test_colliding_openapi_paths_receive_distinct_gateway_tool_names(mock_boto_client, _mock_sleep):
    """Gateway mappings must preserve colliding paths and emit inert Lambda source."""
    mock_boto_client.return_value.get_caller_identity.return_value = {"Account": "123456789012"}
    translator = BaseBedrockTranslator.__new__(BaseBedrockTranslator)
    translator.agent_region = "us-west-2"
    translator.agent_info = {
        "agentName": INJECTION_TEXT,
        "agentId": INJECTION_TEXT,
        "alias": INJECTION_TEXT,
        "version": INJECTION_TEXT,
    }
    first_path = f"/users/{{id}}{INJECTION_TEXT}"
    second_path = f"/users/id{INJECTION_TEXT}"
    translator.custom_ags = [
        {
            "actionGroupName": f"group{INJECTION_TEXT}",
            "actionGroupExecutor": {
                "lambda": f"arn:aws:lambda:us-west-2:123456789012:function:handler{INJECTION_TEXT}",
            },
            "apiSchema": {
                "payload": {
                    "paths": {
                        first_path: {"get": {"description": INJECTION_TEXT}},
                        second_path: {"get": {"description": INJECTION_TEXT}},
                    }
                }
            },
        }
    ]
    generated_lambda = {}
    generated_targets = {}
    translator.create_lambda = lambda code, _name: generated_lambda.update(code=code)
    translator.create_gateway_lambda_target = lambda tools, _arn, _name: generated_targets.update(tools=tools)

    translator.create_gateway_proxy_and_targets()

    tool_names = [tool["name"] for tool in generated_targets["tools"]]
    assert len(tool_names) == len(set(tool_names)) == 2
    assert all("\nThis tool is part of the group" in tool["description"] for tool in generated_targets["tools"])

    tree = ast.parse(generated_lambda["code"])
    string_constants = [
        node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]
    assert first_path in string_constants
    assert second_path in string_constants
    assert generated_lambda["code"].count("INJECTED_SENTINEL") == sum(
        value.count("INJECTED_SENTINEL") for value in string_constants
    )


@pytest.mark.parametrize("translator_class", [BedrockStrandsTranslation, BedrockLangchainTranslation])
def test_colliding_knowledge_base_names_receive_distinct_identifiers(translator_class):
    """Knowledge bases that clean identically must not overwrite each other."""
    translator = translator_class.__new__(translator_class)
    translator.knowledge_bases = [
        {
            "name": "sales-data",
            "description": "one",
            "knowledgeBaseId": "kb-1",
            "knowledgeBaseArn": "arn:aws:bedrock:us-west-2:123456789012:knowledge-base/kb-1",
        },
        {
            "name": "sales data",
            "description": "two",
            "knowledgeBaseId": "kb-2",
            "knowledgeBaseArn": "arn:aws:bedrock:us-west-2:123456789012:knowledge-base/kb-2",
        },
    ]
    allocator = IdentifierAllocator()
    translator.knowledge_base_code_names = [
        allocator.allocate(("knowledge_base", kb["knowledgeBaseId"]), kb["name"]) for kb in translator.knowledge_bases
    ]
    translator.tools = []

    generated = translator.generate_knowledge_base_code()

    assert translator.knowledge_base_code_names == ["sales_data", "sales_data_2"]
    assert "sales_data" in generated
    assert "sales_data_2" in generated
    ast.parse(unindent_by_one(generated))


def _stamp_every_string(node, marker):
    """Return a copy of ``node`` with ``marker`` appended to every string leaf."""
    if isinstance(node, dict):
        return {key: _stamp_every_string(value, marker) for key, value in node.items()}
    if isinstance(node, list):
        return [_stamp_every_string(value, marker) for value in node]
    if isinstance(node, str):
        return f"{node}{marker}"
    return node


@pytest.mark.parametrize(
    ("translator_class", "translate_method", "file_name"),
    [
        (BedrockStrandsTranslation, "translate_bedrock_to_strands", "strands_agent.py"),
        (BedrockLangchainTranslation, "translate_bedrock_to_langchain", "langchain_agent.py"),
    ],
)
def test_generated_agent_compiles_and_keeps_every_config_string_inert(
    tmp_path, translator_class, translate_method, file_name
):
    """Sweep a marker through every config string; it must only ever land in a literal.

    This is the catch-all for the code-injection class: it covers fields no
    targeted test knows about, including ones added later.
    """
    marker = "INJECTED_SENTINEL"
    config_path = os.path.join(os.path.dirname(__file__), "data", "bedrock_config.json")
    with open(config_path, "r", encoding="utf-8") as handle:
        agent_config = json.load(handle)

    stamped = _stamp_every_string(agent_config, INJECTION_TEXT)
    stamped["agent"]["agentArn"] = agent_config["agent"]["agentArn"]
    stamped["agent"]["orchestrationType"] = agent_config["agent"]["orchestrationType"]
    for original, group in zip(agent_config["action_groups"], stamped["action_groups"], strict=True):
        group["actionGroupState"] = original["actionGroupState"]
        if "parentActionSignature" in original:
            group["parentActionSignature"] = original["parentActionSignature"]
    for original, config in zip(
        agent_config["agent"].get("promptOverrideConfiguration", {}).get("promptConfigurations", []),
        stamped["agent"].get("promptOverrideConfiguration", {}).get("promptConfigurations", []),
        strict=True,
    ):
        config["promptType"] = original["promptType"]
        config["promptState"] = original["promptState"]

    output_path = os.path.join(str(tmp_path), file_name)
    translator = translator_class(agent_config=stamped, debug=False, output_dir=str(tmp_path), enabled_primitives={})
    getattr(translator, translate_method)(output_path)

    with open(output_path, "r", encoding="utf-8") as handle:
        generated = handle.read()

    tree = ast.parse(generated)  # fails loudly if the marker broke out of a literal

    string_constants = [
        node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]
    assert any(marker in value for value in string_constants), "marker never reached the generated file"

    # Every occurrence in the file must be accounted for by a string literal
    assert generated.count(marker) == sum(value.count(marker) for value in string_constants)
