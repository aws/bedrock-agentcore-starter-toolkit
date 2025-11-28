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
    region: str = typer.Option(None, help="AWS region to use (defaults to us-west-2)"),
    name: Optional[str] = typer.Option(None, help="Name of the gateway (defaults to TestGateway)"),
    role_arn: Optional[str] = typer.Option(
        None, "--role-arn", help="IAM role ARN to use (creates one if not provided)"
    ),
    authorizer_config: Optional[str] = typer.Option(
        None, "--authorizer-config", help="Serialized authorizer config JSON (creates one if not provided)"
    ),
    enable_semantic_search: Optional[bool] = typer.Option(
        True, "--enable_semantic_search", "-sem", help="Enable semantic search tool"
    ),
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
    gateway_arn: str = typer.Option(None, "--gateway-arn", help="ARN of the created gateway (required)"),
    gateway_url: str = typer.Option(None, "--gateway-url", help="URL of the created gateway (required)"),
    role_arn: str = typer.Option(None, "--role-arn", help="IAM role ARN of the created gateway (required)"),
    region: str = typer.Option(None, help="AWS region to use (defaults to us-west-2)"),
    name: Optional[str] = typer.Option(None, help="Name of the target (defaults to TestGatewayTarget)"),
    target_type: Optional[str] = typer.Option(
        None,
        "--target-type",
        help="Type of target: 'lambda', 'openApiSchema', 'mcpServer', or 'smithyModel' (defaults to 'lambda')",
    ),
    target_payload: Optional[str] = typer.Option(
        None, "--target-payload", help="Target specification JSON (required for openApiSchema targets)"
    ),
    credentials: Optional[str] = typer.Option(
        None, help="Credentials JSON for target access (API key or OAuth2, for openApiSchema targets)"
    ),
) -> None:
    """Creates an MCP Gateway Target.

    :param gateway_arn: required - the arn of the created gateway
    :param gateway_url: required - the url of the created gateway
    :param role_arn: required - the role arn of the created gateway
    :param region: optional - the region to use, defaults to us-west-2
    :param name: optional - the name of the target (defaults to TestGatewayTarget).
    :param target_type: optional - the type of the target e.g. one of "lambda" |
                        "openApiSchema" | "mcpServer" | "smithyModel" (defaults to "lambda").
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


@gateway_app.command(name="delete-mcp-gateway")
def delete_mcp_gateway(
    region: str = typer.Option(None, help="AWS region to use (defaults to us-west-2)"),
    gateway_identifier: Optional[str] = typer.Option(None, "--id", help="Gateway ID to delete"),
    name: Optional[str] = typer.Option(None, help="Gateway name to delete"),
    gateway_arn: Optional[str] = typer.Option(None, "--arn", help="Gateway ARN to delete"),
    force: bool = typer.Option(False, "--force", help="Delete all targets before deleting the gateway"),
) -> None:
    """Deletes an MCP Gateway.

    The gateway must have zero targets before deletion, unless --force is used.
    You can specify the gateway by ID, ARN, or name.

    :param region: optional - region to use (defaults to us-west-2).
    :param gateway_identifier: optional - the gateway ID to delete.
    :param name: optional - the gateway name to delete.
    :param gateway_arn: optional - the gateway ARN to delete.
    :param force: optional - if True, delete all targets before deleting the gateway.
    :return:
    """
    client = GatewayClient(region_name=region)
    result = client.delete_gateway(
        gateway_identifier=gateway_identifier,
        name=name,
        gateway_arn=gateway_arn,
        skip_resource_in_use=force,
    )

    # Enhance error message to suggest --force flag
    if result.get("status") == "error" and "target(s)" in result.get("message", ""):
        result["message"] = f"{result['message']} Use --force to delete the gateway and all its targets."

    console.print(result)


@gateway_app.command(name="delete-mcp-gateway-target")
def delete_mcp_gateway_target(
    region: str = typer.Option(None, help="AWS region to use (defaults to us-west-2)"),
    gateway_identifier: Optional[str] = typer.Option(None, "--id", help="Gateway ID"),
    name: Optional[str] = typer.Option(None, help="Gateway name"),
    gateway_arn: Optional[str] = typer.Option(None, "--arn", help="Gateway ARN"),
    target_id: Optional[str] = typer.Option(None, "--target-id", help="Target ID to delete"),
    target_name: Optional[str] = typer.Option(None, "--target-name", help="Target name to delete"),
) -> None:
    """Deletes an MCP Gateway Target.

    You can specify the gateway by ID, ARN, or name.
    You can specify the target by ID or name.

    :param region: optional - region to use (defaults to us-west-2).
    :param gateway_identifier: optional - the gateway ID.
    :param name: optional - the gateway name.
    :param gateway_arn: optional - the gateway ARN.
    :param target_id: optional - the target ID to delete.
    :param target_name: optional - the target name to delete.
    :return:
    """
    client = GatewayClient(region_name=region)
    result = client.delete_gateway_target(
        gateway_identifier=gateway_identifier,
        name=name,
        gateway_arn=gateway_arn,
        target_id=target_id,
        target_name=target_name,
    )
    console.print(result)


@gateway_app.command(name="list-mcp-gateways")
def list_mcp_gateways(
    region: str = typer.Option(None, help="AWS region to use"),
    name: Optional[str] = typer.Option(None, help="Filter by gateway name"),
    max_results: int = typer.Option(50, "--max-results", "-m", min=1, max=1000, help="Maximum number of results"),
) -> None:
    """Lists MCP Gateways.

    Optionally filter by name and limit the number of results.

    :param region: optional - region to use (defaults to us-west-2).
    :param name: optional - filter by gateway name.
    :param max_results: optional - maximum number of results (defaults to 50).
    :return:
    """
    client = GatewayClient(region_name=region)
    result = client.list_gateways(name=name, max_results=max_results)
    console.print(result)


@gateway_app.command(name="get-mcp-gateway")
def get_mcp_gateway(
    region: str = typer.Option(None, help="AWS region to use"),
    gateway_identifier: Optional[str] = typer.Option(None, "--id", help="Gateway ID"),
    name: Optional[str] = typer.Option(None, help="Gateway name"),
    gateway_arn: Optional[str] = typer.Option(None, "--arn", help="Gateway ARN"),
) -> None:
    """Gets details for a specific MCP Gateway.

    You can specify the gateway by ID, ARN, or name.

    :param region: optional - region to use (defaults to us-west-2).
    :param gateway_identifier: optional - the gateway ID.
    :param name: optional - the gateway name.
    :param gateway_arn: optional - the gateway ARN.
    :return:
    """
    client = GatewayClient(region_name=region)
    result = client.get_gateway(
        gateway_identifier=gateway_identifier,
        name=name,
        gateway_arn=gateway_arn,
    )
    console.print(result)


@gateway_app.command(name="list-mcp-gateway-targets")
def list_mcp_gateway_targets(
    region: str = typer.Option(None, help="AWS region to use"),
    gateway_identifier: Optional[str] = typer.Option(None, "--id", help="Gateway ID"),
    name: Optional[str] = typer.Option(None, help="Gateway name"),
    gateway_arn: Optional[str] = typer.Option(None, "--arn", help="Gateway ARN"),
    max_results: int = typer.Option(
        50, "--max-results", "-m", min=1, max=1000, help="Maximum number of results to return"
    ),
) -> None:
    """Lists targets for an MCP Gateway.

    You can specify the gateway by ID, ARN, or name.

    :param region: optional - region to use (defaults to us-west-2).
    :param gateway_identifier: optional - the gateway ID.
    :param name: optional - the gateway name.
    :param gateway_arn: optional - the gateway ARN.
    :param max_results: optional - maximum number of results (defaults to 50).
    :return:
    """
    client = GatewayClient(region_name=region)
    result = client.list_gateway_targets(
        gateway_identifier=gateway_identifier,
        name=name,
        gateway_arn=gateway_arn,
        max_results=max_results,
    )
    console.print(result)


@gateway_app.command(name="get-mcp-gateway-target")
def get_mcp_gateway_target(
    region: str = typer.Option(None, help="AWS region to use"),
    gateway_identifier: Optional[str] = typer.Option(None, "--id", help="Gateway ID"),
    name: Optional[str] = typer.Option(None, help="Gateway name "),
    gateway_arn: Optional[str] = typer.Option(None, "--arn", help="Gateway ARN"),
    target_id: Optional[str] = typer.Option(None, "--target-id", help="Target ID"),
    target_name: Optional[str] = typer.Option(None, "--target-name", help="Target name"),
) -> None:
    """Gets details for a specific Gateway Target.

    You can specify the gateway by ID, ARN, or name.
    You can specify the target by ID or name.

    :param region: optional - region to use (defaults to us-west-2).
    :param gateway_identifier: optional - the gateway ID.
    :param name: optional - the gateway name.
    :param gateway_arn: optional - the gateway ARN.
    :param target_id: optional - the target ID.
    :param target_name: optional - the target name.
    :return:
    """
    client = GatewayClient(region_name=region)
    result = client.get_gateway_target(
        gateway_identifier=gateway_identifier,
        name=name,
        gateway_arn=gateway_arn,
        target_id=target_id,
        target_name=target_name,
    )
    console.print(result)


if __name__ == "__main__":
    gateway_app()
