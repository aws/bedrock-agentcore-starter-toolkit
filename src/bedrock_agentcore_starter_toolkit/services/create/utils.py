"""Utility functions for the create service."""

import os
import re

import boto3


def get_base_dir(file):
    """Get the base directory of the project."""
    return os.path.dirname(os.path.abspath(file))


def get_clients(credentials, region_name="us-west-2"):
    """Get Bedrock and Bedrock Agent clients using the provided credentials and region.

    Args:
        credentials: AWS credentials
        region_name: AWS region name (default: us-west-2)

    Returns:
        tuple: (bedrock_client, bedrock_agent_client)
    """
    boto3_session = boto3.Session(
        aws_access_key_id=credentials.access_key,
        aws_secret_access_key=credentials.secret_key,
        aws_session_token=credentials.token,
        region_name=region_name,
    )

    bedrock_agent_client = boto3_session.client("bedrock-agent", region_name=region_name)
    bedrock_client = boto3_session.client("bedrock", region_name=region_name)

    return bedrock_client, bedrock_agent_client


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

    return cleaned
