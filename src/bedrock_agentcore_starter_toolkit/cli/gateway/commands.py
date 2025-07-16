"""Bedrock AgentCore CLI - Command line interface for Bedrock AgentCore."""

import json
from typing import Optional

import typer

from ...operations.gateway import GatewayClient
from ..common import console

# Create a Typer app for gateway commands
gateway_app = typer.Typer(help="Manage Bedrock AgentCore Gateways")


@gateway_app.command()
def create_mcp_gateway(
    region: str = None,
    name: Optional[str] = None,
    role_arn: Optional[str] = None,
    authorizer_config: Optional[str] = None,
    enable_semantic_search: Optional[bool] = typer.Option(True, "--enable_semantic_search", "-sem"),
) -> None:
    """Creates an MCP Gateway.

    :param region: optional - region to use (defaults to us-west-2).
    :param name: optional - the name of the gateway (defaults to TestGateway).
    :param role_arn: optional - the role arn to use (creates one if none provided).
    :param authorizer_config: optional - the serialized authorizer config (will create one if none provided).
    :param enable_semantic_search: optional - whether to enable search tool (defaults to True).
    :return:
    """
    client = GatewayClient(region_name=region)
    json_authorizer_config = ""
    if authorizer_config:
        json_authorizer_config = json.loads(authorizer_config)
    gateway = client.create_mcp_gateway(name, role_arn, json_authorizer_config, enable_semantic_search)
    console.print(gateway)


@gateway_app.command()
def create_mcp_gateway_target(
    gateway_arn: str = None,
    gateway_url: str = None,
    role_arn: str = None,
    region: str = None,
    name: Optional[str] = None,
    target_type: Optional[str] = None,
    target_payload: Optional[str] = None,
    credentials: Optional[str] = None,
) -> None:
    """Creates an MCP Gateway Target.

    :param gateway_arn: required - the arn of the created gateway
    :param gateway_url: required - the url of the created gateway
    :param role_arn: required - the role arn of the created gateway
    :param region: optional - the region to use, defaults to us-west-2
    :param name: optional - the name of the target (defaults to TestGatewayTarget).
    :param target_type: optional - the type of the target e.g. one of "lambda" |
                        "openApiSchema" | "smithyModel" (defaults to "lambda").
    :param target_payload: only required for openApiSchema target - the specification of that target.
    :param credentials: only use with openApiSchema target - the credentials for calling this target
                        (api key or oauth2).
    :return:
    """
    client = GatewayClient(region_name=region)
    json_credentials = ""
    json_target_payload = ""
    if credentials:
        json_credentials = json.loads(credentials)
    if target_payload:
        json_target_payload = json.loads(target_payload)
    target = client.create_mcp_gateway_target(
        gateway={
            "gatewayArn": gateway_arn,
            "gatewayUrl": gateway_url,
            "gatewayId": gateway_arn.split("/")[-1],
            "roleArn": role_arn,
        },
        name=name,
        target_type=target_type,
        target_payload=json_target_payload,
        credentials=json_credentials,
    )
    console.print(target)


if __name__ == "__main__":
    gateway_app()
