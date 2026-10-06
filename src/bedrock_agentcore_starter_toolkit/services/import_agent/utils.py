"""Utility functions for Bedrock Agent import service."""

import hashlib
import json
import keyword
import os
import re
import textwrap
from collections.abc import Hashable
from typing import Any, Dict, List, Union


def json_to_obj_fixed(json_string: str):
    """Convert a JSON string to a Python object, handling common formatting issues."""
    json_string = json_string.strip()
    json_string = " ".join(json_string.split())

    try:
        output = json.loads(json_string)
    except json.JSONDecodeError:
        output = json_string

    return output


def fix_field(obj, field=None):
    """Fixes the field in the object by converting it to a JSON object if it's a string."""
    if field is None:
        return json_to_obj_fixed(obj)
    else:
        # Create a new dict to avoid modifying the original
        new_obj = obj.copy()
        new_obj[field] = json_to_obj_fixed(obj[field])

        return new_obj


def clean_variable_name(text):
    """Clean a string to create a valid Python variable name. Useful for cleaning Bedrock Agents fields."""
    text = str(text)
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", text)
    cleaned = cleaned.lower()
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = cleaned.strip()
    cleaned = cleaned.replace(" ", "_")
    if cleaned and cleaned[0].isdigit():
        cleaned = f"_{cleaned}"

    if not cleaned:
        cleaned = "variable"
    if keyword.iskeyword(cleaned):
        cleaned += "_"

    return cleaned


IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class IdentifierAllocator:
    """Allocate unique Python identifiers within one scope.

    Bedrock names are free-form, so several distinct names ("user-id", "user id",
    "user_id") can clean down to the same identifier. Generated code needs unique
    identifiers, while Lambda payloads need the original names.
    """

    def __init__(self) -> None:
        """Create an empty allocator scope."""
        self._by_key: Dict[Hashable, str] = {}
        self._used_names: set[str] = set()

    def allocate(self, key: Hashable, preferred_name: Any = None) -> str:
        """Return the identifier for ``key``, using ``preferred_name`` as its source."""
        if key in self._by_key:
            return self._by_key[key]

        base_name = clean_variable_name(key if preferred_name is None else preferred_name)
        if not IDENTIFIER_PATTERN.match(base_name):
            base_name = "variable"

        candidate = base_name
        suffix = 2
        while candidate in self._used_names:
            candidate = f"{base_name}_{suffix}"
            suffix += 1

        self._used_names.add(candidate)
        self._by_key[key] = candidate
        return candidate

    def reserve(self, *names: str) -> None:
        """Mark identifiers as taken so allocation never collides with them."""
        self._used_names.update(names)


def python_string_literal(value: Any) -> str:
    """Encode a value as an inert Python string literal for generated source."""
    return repr(str(value))


def python_data_literal(value: Any) -> str:
    """Encode JSON-compatible data as an inert Python literal for generated source.

    JSON normalization rejects values that would require constructors in generated
    source, while ``repr`` emits Python spellings for booleans and null values.
    """
    normalized = json.loads(json.dumps(value, ensure_ascii=False))
    return repr(normalized)


def assert_local_references_only(node, path: str = "$") -> None:
    """Reject any OpenAPI ``$ref`` that is not a fragment-only reference.

    External references make the parser fetch attacker-controlled URLs and local
    files while importing an agent. Only in-document pointers such as
    ``#/components/schemas/Request`` are permitted.
    """
    if isinstance(node, dict):
        reference = node.get("$ref")
        if isinstance(reference, str) and not reference.startswith("#/"):
            raise ValueError(
                f"External OpenAPI references are not supported: {reference!r} at {path}. "
                "Inline the referenced schema, or replace it with an in-document "
                "reference such as '#/components/schemas/Name'."
            )
        for key, child in node.items():
            assert_local_references_only(child, f"{path}.{key}")
    elif isinstance(node, list):
        for index, child in enumerate(node):
            assert_local_references_only(child, f"{path}[{index}]")


def clean_gateway_or_target_name(text):
    """Clean a string to create a valid Gateway or Target name."""
    text = str(text)
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", text)
    cleaned = cleaned.lower()
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = cleaned.strip()
    cleaned = cleaned.replace(" ", "-")
    if not cleaned:
        cleaned = "gateway-or-target"

    return cleaned


def unindent_by_one(input_code, spaces_per_indent=4):
    """Unindents the input code by one level of indentation.

    Note: text dedent does not work as expected in this context, so we implement our own logic.

    Args:
        input_code (str): The code to unindent.
        spaces_per_indent (int): The number of spaces per indentation level (default is 4).

    Returns:
        str: The unindented code.
    """
    lines = input_code.splitlines(True)  # Keep the line endings
    # Process each line
    unindented = []
    for line in lines:
        if line.strip():  # If line is not empty
            current_indent = len(line) - len(line.lstrip())
            # Remove one level of indentation if possible
            if current_indent >= spaces_per_indent:
                line = line[spaces_per_indent:]
        unindented.append(line)

    return "".join(unindented)


def generate_pydantic_models(
    schema_input: Union[Dict[str, Any], List[Dict[str, Any]], str],
    root_model_name: str = "RequestModel",
    content_type_annotation: str = "",
) -> str:
    """Generate Pydantic models from OpenAPI schema objects. Works recursively for nested objects.

    Args:
        schema_input: The OpenAPI schema, parameter object or parameter array as dictionary/list or JSON string
        root_model_name: Name for the root model
        content_type_annotation: Optional content type annotation for the root model

    Returns:
        String containing Python code for the Pydantic models
    """
    # Convert JSON string to dictionary/list if needed
    if isinstance(schema_input, str):
        try:
            schema_input = json.loads(schema_input)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON input: {e}") from e

    # Start with the imports
    code = "\n"

    # Dictionary to keep track of models we've created
    models = {}

    def clean_class_name(name: str) -> str:
        """Create a valid Python class name."""
        # Replace non-alphanumeric characters with underscores
        cleaned = re.sub(r"[^a-zA-Z0-9]", "_", name)
        # Ensure it starts with a letter
        if cleaned and not cleaned[0].isalpha():
            cleaned = "Model_" + cleaned
        # Convert to CamelCase
        class_name = "".join(word.capitalize() for word in cleaned.split("_"))
        return class_name or "Model"

    def get_field_definition(
        original_name: str,
        field_name: str,
        is_required: bool,
        description: Any = None,
    ) -> str:
        """Build a Pydantic Field expression with safe literals and wire-name aliases."""
        field_args = ["..." if is_required else "None"]
        if description is not None:
            field_args.append(f"description={python_string_literal(description)}")
        if field_name != original_name:
            field_args.append(f"alias={python_string_literal(original_name)}")

        if len(field_args) == 1 and is_required:
            return ""
        if len(field_args) == 1:
            return " = None"
        return f" = Field({', '.join(field_args)})"

    def process_schema(schema_obj: Dict[str, Any], name: str) -> str:
        """Process a schema object and return the model class name."""
        # Handle schema wrapper
        if "schema" in schema_obj:
            schema_obj = schema_obj["schema"]

        # Handle $ref
        if "$ref" in schema_obj:
            ref_name = schema_obj["$ref"].split("/")[-1]
            return clean_class_name(ref_name)

        obj_type = schema_obj.get("type")

        # Default to object type if not specified
        if obj_type is None:
            obj_type = "object"

        if obj_type == "object":
            # Generate a valid Python class name
            class_name = clean_class_name(name)

            # Avoid duplicate model names
            if class_name in models:
                return class_name

            properties = schema_obj.get("properties", {})
            required = schema_obj.get("required", [])

            class_def = f"class {class_name}(BaseModel):\n"

            if "description" in schema_obj:
                class_def += f"    {python_string_literal(schema_obj['description'])}\n"

            # Add content type annotation if provided
            if content_type_annotation:
                class_def += f"    content_type_annotation: Literal[{python_string_literal(content_type_annotation)}]\n"

            if not properties:
                class_def += "    pass\n"
                models[class_name] = class_def
                return class_name

            field_names = IdentifierAllocator()
            field_names.reserve("content_type_annotation")
            for prop_name, prop_schema in properties.items():
                field_name = field_names.allocate(prop_name)
                field_type = get_type_hint(prop_schema, f"{name}_{prop_name}")

                # Check if required
                is_required = prop_name in required

                # Build the field definition
                if not is_required:
                    field_type = f"Optional[{field_type}]"
                field_def = get_field_definition(
                    prop_name,
                    field_name,
                    is_required,
                    prop_schema.get("description"),
                )

                class_def += f"    {field_name}: {field_type}{field_def}\n"

            models[class_name] = class_def
            return class_name
        elif obj_type == "array":
            items = schema_obj.get("items", {})
            item_type = get_type_hint(items, f"{name}_item")
            return f"List[{item_type}]"
        else:
            return get_python_type(obj_type)

    def get_type_hint(prop_schema: Dict[str, Any], name: str) -> str:
        """Get the Python type hint for a property schema."""
        if "$ref" in prop_schema:
            ref_name = prop_schema["$ref"].split("/")[-1]
            return clean_class_name(ref_name)

        prop_type = prop_schema.get("type")

        # Default to Any if type is not specified
        if prop_type is None:
            return "Any"

        if prop_type == "object":
            # This is a nested object, create a new model for it
            return process_schema(prop_schema, name)
        elif prop_type == "array":
            items = prop_schema.get("items", {})
            item_type = get_type_hint(items, name)
            return f"List[{item_type}]"
        else:
            return get_python_type(prop_type)

    def get_python_type(openapi_type: str) -> str:
        """Convert OpenAPI type to Python type."""
        type_mapping = {
            "string": "str",
            "integer": "int",
            "number": "float",
            "boolean": "bool",
            "null": "None",
            "object": "Dict[str, Any]",
        }
        return type_mapping.get(openapi_type, "Any")

    def process_parameter_list(params: List[Dict[str, Any]], name: str) -> str:
        """Process OpenAPI parameter array and create a model."""
        class_name = clean_class_name(name)
        if class_name in models:
            return class_name

        class_def = f"class {class_name}(BaseModel):\n"

        if not params:
            class_def += "    pass\n"
            models[class_name] = class_def
            return class_name

        # Group parameters by 'in' value to potentially create separate models
        param_groups = {}
        for param in params:
            param_in = param.get("in", "query")  # Default to query if not specified
            if param_in not in param_groups:
                param_groups[param_in] = []
            param_groups[param_in].append(param)

        # If only one type or specifically requested, create a single model
        if len(param_groups) == 1 or name != "RequestModel":
            field_names = IdentifierAllocator()
            for param in params:
                param_name = param.get("name", "")
                if not param_name:
                    continue
                field_name = field_names.allocate(param_name)

                # Get the parameter type
                if "schema" in param:
                    # OpenAPI 3.0 style
                    field_type = get_type_hint(param["schema"], f"{name}_{param_name}")
                else:
                    # OpenAPI 2.0 style
                    field_type = get_python_type(param.get("type", "string"))

                # Check if required
                is_required = param.get("required", False)

                # Build the field definition
                if not is_required:
                    field_type = f"Optional[{field_type}]"
                field_def = get_field_definition(
                    param_name,
                    field_name,
                    is_required,
                    param.get("description"),
                )

                class_def += f"    {field_name}: {field_type}{field_def}\n"
        else:
            # Create separate models for each parameter type
            field_names = IdentifierAllocator()
            for param_in, param_list in param_groups.items():
                in_type_name = f"{name}_{param_in.capitalize()}Params"
                in_class_name = process_parameter_list(param_list, in_type_name)
                field_name = field_names.allocate(f"{param_in}_params")
                class_def += f"    {field_name}: {in_class_name}\n"

        models[class_name] = class_def
        return class_name

    def process_parameter_dict(params: Dict[str, Dict[str, Any]], name: str) -> str:
        """Process a dictionary of named parameters."""
        class_name = clean_class_name(name)
        if class_name in models:
            return class_name

        class_def = f"class {class_name}(BaseModel):\n"

        if not params:
            class_def += "    pass\n"
            models[class_name] = class_def
            return class_name

        field_names = IdentifierAllocator()
        for param_name, param_def in params.items():
            field_name = field_names.allocate(param_name)
            # Get the parameter type
            if "schema" in param_def:
                # OpenAPI 3.0 style
                field_type = get_type_hint(param_def["schema"], f"{name}_{param_name}")
            else:
                # OpenAPI 2.0 style or simplified parameter
                field_type = get_python_type(param_def.get("type", "string"))

            # Check if required
            is_required = param_def.get("required", False)

            # Build the field definition
            if not is_required:
                field_type = f"Optional[{field_type}]"
            field_def = get_field_definition(
                param_name,
                field_name,
                is_required,
                param_def.get("description"),
            )

            class_def += f"    {field_name}: {field_type}{field_def}\n"

        models[class_name] = class_def
        return class_name

    # Determine the type of input and process accordingly
    if isinstance(schema_input, list):
        # This is likely a parameter array
        process_parameter_list(schema_input, root_model_name)
    elif isinstance(schema_input, dict):
        if "schema" in schema_input:
            # This is likely a request body schema
            process_schema(schema_input, root_model_name)
        elif "parameters" in schema_input:
            # This is an operation object with parameters
            process_parameter_list(schema_input["parameters"], root_model_name)
        elif all(isinstance(value, dict) and ("name" in value and "in" in value) for value in schema_input.values()):
            # This appears to be a parameter dict with name/in properties
            process_parameter_list(list(schema_input.values()), root_model_name)
        elif all(isinstance(value, dict) for value in schema_input.values()):
            # This appears to be a dictionary of named parameters
            process_parameter_dict(schema_input, root_model_name)
        else:
            # Try to process as a schema object
            process_schema({"type": "object", "properties": schema_input}, root_model_name)

    # Add all models to the code
    for model_code in models.values():
        code += model_code + "\n\n"

    code = code.rstrip() + "\n"
    return textwrap.indent(code, "    "), clean_class_name(root_model_name)


def prune_tool_name(tool_name: str, length=50) -> str:
    """Prune tool name to avoid maxiumum of 64 characters. If it exceeds, truncate and append a suffix.

    The suffix is derived from the full name so that re-importing the same agent
    produces the same tool names; these names key the Gateway target tool mappings.
    """
    if len(tool_name) > length:
        digest = hashlib.sha256(tool_name.encode("utf-8")).hexdigest()[:6]
        tool_name = f"{tool_name[:length]}_{digest}"
    return tool_name


def get_template_fixtures(field: str = "orchestrationBasePrompts", group: str = "REACT_MULTI_ACTION") -> dict:
    """Extract all templateFixtures from a specified field in template_fixtures_merged.json.

    For orchestrationBasePrompts, uses the specified group (defaults to REACT_MULTI_ACTION).

    Args:
        field: The field to extract templateFixtures from (defaults to "orchestrationBasePrompts")
        group: For orchestrationBasePrompts, which group to use (defaults to "REACT_MULTI_ACTION")

    Returns:
        Dict mapping fixture names to their template strings
    """
    project_root = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(project_root, "assets", "template_fixtures_merged.json")
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if field not in data:
        raise ValueError(f"Field '{field}' not found in template_fixtures_merged.json")

    field_data = data[field]

    # For orchestrationBasePrompts, get the specified group's templateFixtures
    if field == "orchestrationBasePrompts":
        if group not in field_data:
            raise ValueError(f"Group '{group}' not found in orchestrationBasePrompts")
        fixtures = field_data[group].get("templateFixtures", {})
    else:
        # For other fields, get templateFixtures directly
        fixtures = field_data.get("templateFixtures", {})

    result = {}
    for name, fixture in fixtures.items():
        if isinstance(fixture, dict) and "template" in fixture:
            result[name] = fixture["template"]

    return result


def safe_substitute_placeholders(template_str, substitutions):
    """Safely substitute placeholders in a string, leaving non-matching placeholders unchanged."""
    result = template_str
    for key, value in substitutions.items():
        # Only replace if the key exists in the substitutions dict
        if key in template_str:
            result = result.replace(key, value)
    return result


def get_base_dir(file):
    """Get the base directory of the project."""
    return os.path.dirname(os.path.dirname(os.path.abspath(file)))
