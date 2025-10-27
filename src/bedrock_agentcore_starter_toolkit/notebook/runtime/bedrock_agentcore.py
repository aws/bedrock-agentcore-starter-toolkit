"""Bedrock AgentCore Notebook - Jupyter notebook interface for Bedrock AgentCore."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from ...operations.runtime import (
    configure_bedrock_agentcore,
    get_status,
    invoke_bedrock_agentcore,
    launch_bedrock_agentcore,
    stop_runtime_session,
    validate_agent_name,
)
from ...operations.runtime.models import ConfigureResult, LaunchResult, StatusResult

# Setup centralized logging for SDK usage (notebooks, scripts, imports)
from ...utils.logging_config import setup_toolkit_logging
from ...utils.runtime.entrypoint import parse_entrypoint

setup_toolkit_logging(mode="sdk")

# Configure logger for this module
log = logging.getLogger(__name__)


class Runtime:
    """Bedrock AgentCore for Jupyter notebooks - simplified interface for file-based configuration."""

    def __init__(self):
        """Initialize Bedrock AgentCore notebook interface."""
        self._config_path: Optional[Path] = None
        self.name = None

    def configure(
        self,
        entrypoint: str,
        execution_role: Optional[str] = None,
        code_build_execution_role: Optional[str] = None,
        agent_name: Optional[str] = None,
        requirements: Optional[List[str]] = None,
        requirements_file: Optional[str] = None,
        ecr_repository: Optional[str] = None,
        container_runtime: Optional[str] = None,
        auto_create_ecr: bool = True,
        auto_create_execution_role: bool = False,
        authorizer_configuration: Optional[Dict[str, Any]] = None,
        request_header_configuration: Optional[Dict[str, Any]] = None,
        region: Optional[str] = None,
        protocol: Optional[Literal["HTTP", "MCP", "A2A"]] = None,
        disable_otel: bool = False,
        memory_mode: Literal["NO_MEMORY", "STM_ONLY", "STM_AND_LTM"] = "NO_MEMORY",
        non_interactive: bool = True,
        vpc_enabled: bool = False,
        vpc_subnets: Optional[List[str]] = None,
        vpc_security_groups: Optional[List[str]] = None,
        idle_timeout: Optional[int] = None,
        max_lifetime: Optional[int] = None,
    ) -> ConfigureResult:
        """Configure Bedrock AgentCore from notebook using an entrypoint file.

        Args:
            entrypoint: Path to Python file with optional Bedrock AgentCore name
                (e.g., "handler.py" or "handler.py:bedrock_agentcore")
            execution_role: AWS IAM execution role ARN or name (optional if auto_create_execution_role=True)
            code_build_execution_role: Optional separate CodeBuild execution role ARN or name
            agent_name: name of the agent
            requirements: Optional list of requirements to generate requirements.txt
            requirements_file: Optional path to existing requirements file
            ecr_repository: Optional ECR repository URI
            container_runtime: Optional container runtime (docker/podman)
            auto_create_ecr: Whether to auto-create ECR repository
            auto_create_execution_role: Whether to auto-create execution role (makes execution_role optional)
            authorizer_configuration: JWT authorizer configuration dictionary
            request_header_configuration: Request header configuration dictionary
            region: AWS region for deployment
            protocol: agent server protocol, must be either HTTP or MCP or A2A
            disable_otel: Whether to disable OpenTelemetry observability (default: False)
            memory_mode: Memory configuration mode (default: "STM_ONLY")
                - "NO_MEMORY": Disable memory entirely (stateless agent)
                - "STM_ONLY": Short-term memory only (default)
                - "STM_AND_LTM": Short-term + long-term memory with strategy extraction
            non_interactive: Skip interactive prompts and use defaults (default: True)
            vpc_enabled: Enable VPC networking mode (requires vpc_subnets and vpc_security_groups)
            vpc_subnets: List of VPC subnet IDs (required if vpc_enabled=True)
            vpc_security_groups: List of VPC security group IDs (required if vpc_enabled=True)
            idle_timeout: Idle runtime session timeout in seconds (60-28800)
            max_lifetime: Maximum instance lifetime in seconds (60-28800)

        Returns:
            ConfigureResult with configuration details

        Example:
            # Default: STM only (backward compatible)
            runtime.configure(entrypoint='handler.py')

            # With VPC networking
            runtime.configure(
                entrypoint='handler.py',
                vpc_enabled=True,
                vpc_subnets=['subnet-abc123', 'subnet-def456'],
                vpc_security_groups=['sg-xyz789']
            )

            # Explicitly enable LTM
            runtime.configure(entrypoint='handler.py', memory_mode='STM_AND_LTM')

            # Disable memory entirely
            runtime.configure(entrypoint='handler.py', memory_mode='NO_MEMORY')

            # Invalid - raises error
            runtime.configure(entrypoint='handler.py', disable_memory=True, memory_mode='STM_AND_LTM')

            # With lifecycle settings
            runtime.configure(
                entrypoint='handler.py',
                idle_timeout=1800,  # 30 minutes
                max_lifetime=7200   # 2 hours
            )
        """
        if protocol and protocol.upper() not in ["HTTP", "MCP", "A2A"]:
            raise ValueError("protocol must be either HTTP or MCP or A2A")

        # Validate VPC configuration
        if vpc_enabled:
            if not vpc_subnets or not vpc_security_groups:
                raise ValueError(
                    "VPC mode requires both vpc_subnets and vpc_security_groups.\n"
                    "Example: runtime.configure(entrypoint='handler.py', vpc_enabled=True, "
                    "vpc_subnets=['subnet-abc123', 'subnet-def456'], "
                    "vpc_security_groups=['sg-xyz789'])"
                )

            # Validate subnet ID format - UPDATED
            for subnet_id in vpc_subnets:
                if not subnet_id.startswith("subnet-"):
                    raise ValueError(f"Invalid subnet ID format: {subnet_id}\nSubnet IDs must start with 'subnet-'")
                if len(subnet_id) < 15:  # "subnet-" + 8 chars minimum
                    raise ValueError(
                        f"Invalid subnet ID format: {subnet_id}\n"
                        f"Subnet ID is too short. Expected: subnet-xxxxxxxx (at least 8 hex chars)"
                    )

            # Validate security group ID format - UPDATED
            for sg_id in vpc_security_groups:
                if not sg_id.startswith("sg-"):
                    raise ValueError(
                        f"Invalid security group ID format: {sg_id}\nSecurity group IDs must start with 'sg-'"
                    )
                if len(sg_id) < 11:  # "sg-" + 8 chars minimum
                    raise ValueError(
                        f"Invalid security group ID format: {sg_id}\n"
                        f"Security group ID is too short. Expected: sg-xxxxxxxx (at least 8 hex chars)"
                    )

            log.info(
                "VPC mode enabled with %d subnets and %d security groups", len(vpc_subnets), len(vpc_security_groups)
            )

        elif vpc_subnets or vpc_security_groups:
            raise ValueError(
                "vpc_subnets and vpc_security_groups require vpc_enabled=True.\n"
                "Use: runtime.configure(entrypoint='handler.py', vpc_enabled=True, "
                "vpc_subnets=[...], vpc_security_groups=[...])"
            )

        # Parse entrypoint to get agent name
        file_path, file_name = parse_entrypoint(entrypoint)
        agent_name = agent_name or file_name

        valid, error = validate_agent_name(agent_name)
        if not valid:
            raise ValueError(error)

        # Validate execution role configuration
        if not execution_role and not auto_create_execution_role:
            raise ValueError("Must provide either 'execution_role' or set 'auto_create_execution_role=True'")

        # Update our name if not already set
        if not self.name:
            self.name = agent_name

        # Handle requirements
        final_requirements_file = requirements_file

        if requirements and not requirements_file:
            # Create requirements.txt in the same directory as the handler
            handler_dir = Path(file_path).parent
            req_file_path = handler_dir / "requirements.txt"

            all_requirements = []
            all_requirements.extend(requirements)

            req_file_path.write_text("\n".join(all_requirements))
            log.info("Generated requirements.txt: %s", req_file_path)

            final_requirements_file = str(req_file_path)

        if memory_mode == "NO_MEMORY":
            log.info("Memory disabled - agent will be stateless")
        elif memory_mode == "STM_AND_LTM":
            log.info("Memory configured with STM + LTM")
        else:  # STM_ONLY
            log.info("Memory configured with STM only")

        # Configure using the operations module
        result = configure_bedrock_agentcore(
            agent_name=agent_name,
            entrypoint_path=Path(file_path),
            auto_create_execution_role=auto_create_execution_role,
            execution_role=execution_role,
            code_build_execution_role=code_build_execution_role,
            ecr_repository=ecr_repository,
            container_runtime=container_runtime,
            auto_create_ecr=auto_create_ecr,
            enable_observability=not disable_otel,
            memory_mode=memory_mode,
            requirements_file=final_requirements_file,
            authorizer_configuration=authorizer_configuration,
            request_header_configuration=request_header_configuration,
            region=region,
            protocol=protocol.upper() if protocol else None,
            non_interactive=non_interactive,
            vpc_enabled=vpc_enabled,
            vpc_subnets=vpc_subnets,
            vpc_security_groups=vpc_security_groups,
            idle_timeout=idle_timeout,
            max_lifetime=max_lifetime,
        )

        self._config_path = result.config_path
        log.info("Bedrock AgentCore configured: %s", self._config_path)
        return result

    def launch(
        self,
        local: bool = False,
        local_build: bool = False,
        auto_update_on_conflict: bool = False,
        env_vars: Optional[Dict] = None,
    ) -> LaunchResult:
        """Launch Bedrock AgentCore from notebook.

        Args:
            local: Whether to build and run locally (requires Docker/Finch/Podman)
            local_build: Whether to build locally and deploy to cloud (requires Docker/Finch/Podman)
            auto_update_on_conflict: Whether to automatically update resources on conflict (default: False)
            env_vars: environment variables for agent container

        Returns:
            LaunchResult with deployment details
        """
        if not self._config_path:
            log.warning("Configuration required before launching")
            log.info("Call .configure() first to set up your agent")
            log.info("Example: runtime.configure(entrypoint='my_agent.py')")
            raise ValueError("Must configure before launching. Call .configure() first.")

        # Enhanced validation for mutually exclusive options with helpful guidance
        if local and local_build:
            raise ValueError(
                "Cannot use both 'local' and 'local_build' flags together.\n"
                "Choose one deployment mode:\n"
                "• runtime.launch(local=True) - for local development\n"
                "• runtime.launch(local_build=True) - for local build + cloud deployment\n"
                "• runtime.launch() - for CodeBuild deployment (recommended)"
            )

        # Inform user about deployment mode with enhanced migration guidance
        if local:
            log.info("🏠 Local mode: building and running locally")
            log.info("   • Build and run container locally")
            log.info("   • Requires Docker/Finch/Podman to be installed")
            log.info("   • Perfect for development and testing")
        elif local_build:
            log.info("🔧 Local build mode: building locally, deploying to cloud (NEW OPTION!)")
            log.info("   • Build container locally with Docker")
            log.info("   • Deploy to Bedrock AgentCore cloud runtime")
            log.info("   • Requires Docker/Finch/Podman to be installed")
            log.info("   • Use when you need custom build control")
        else:
            log.info("🚀 CodeBuild mode: building in cloud (RECOMMENDED - DEFAULT)")
            log.info("   • Build ARM64 containers in the cloud with CodeBuild")
            log.info("   • No local Docker required")

            # Show deployment options hint for first-time notebook users
            log.info("💡 Available deployment modes:")
            log.info("   • runtime.launch()                           → CodeBuild (current)")
            log.info("   • runtime.launch(local=True)                 → Local development")
            log.info("   • runtime.launch(local_build=True)           → Local build + cloud deploy (NEW)")

        # Map to the underlying operation's use_codebuild parameter
        # use_codebuild=False when local=True OR local_build=True
        use_codebuild = not (local or local_build)

        try:
            result = launch_bedrock_agentcore(
                self._config_path,
                local=local,
                use_codebuild=use_codebuild,
                auto_update_on_conflict=auto_update_on_conflict,
                env_vars=env_vars,
            )
        except RuntimeError as e:
            # Enhance Docker-related error messages
            error_msg = str(e)
            if "docker" in error_msg.lower() or "container runtime" in error_msg.lower():
                if local or local_build:
                    enhanced_msg = (
                        f"Docker/Finch/Podman is required for {'local' if local else 'local-build'} mode.\n\n"
                    )
                    enhanced_msg += "Options to fix this:\n"
                    enhanced_msg += "1. Install Docker/Finch/Podman and try again\n"
                    enhanced_msg += "2. Use CodeBuild mode instead: runtime.launch() - no Docker required\n\n"
                    enhanced_msg += f"Original error: {error_msg}"
                    raise RuntimeError(enhanced_msg) from e
            raise

        if result.mode == "cloud":
            log.info("Deployed to cloud: %s", result.agent_arn)
            # For local_build mode, show minimal output; for pure cloud mode, show log details
            if not local_build and result.agent_id:
                from ...utils.runtime.logs import get_agent_log_paths, get_aws_tail_commands

                runtime_logs, otel_logs = get_agent_log_paths(result.agent_id)
                follow_cmd, since_cmd = get_aws_tail_commands(runtime_logs)
                log.info("🔍 Agent logs available at:")
                log.info("   %s", runtime_logs)
                log.info("   %s", otel_logs)
                log.info("💡 Tail logs with: %s", follow_cmd)
                log.info("💡 Or view recent logs: %s", since_cmd)
        elif result.mode == "codebuild":
            log.info("Built with CodeBuild: %s", result.codebuild_id)
            log.info("Deployed to cloud: %s", result.agent_arn)
            log.info("ECR image: %s", result.ecr_uri)
            # Show log information for CodeBuild deployments
            if result.agent_id:
                from ...utils.runtime.logs import get_agent_log_paths, get_aws_tail_commands

                runtime_logs, otel_logs = get_agent_log_paths(result.agent_id)
                follow_cmd, since_cmd = get_aws_tail_commands(runtime_logs)
                log.info("🔍 Agent logs available at:")
                log.info("   %s", runtime_logs)
                log.info("   %s", otel_logs)
                log.info("💡 Tail logs with: %s", follow_cmd)
                log.info("💡 Or view recent logs: %s", since_cmd)
        else:
            log.info("Built for local: %s", result.tag)

        # For notebook interface, clear verbose build output to keep output clean
        # especially for local_build mode where build logs can be very verbose
        if local_build and hasattr(result, "build_output"):
            result.build_output = None

        return result

    def invoke(
        self,
        payload: Dict[str, Any],
        session_id: Optional[str] = None,
        bearer_token: Optional[str] = None,
        local: Optional[bool] = False,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Invoke deployed Bedrock AgentCore endpoint.

        Args:
            payload: Dictionary payload to send
            session_id: Optional session ID for conversation continuity
            bearer_token: Optional bearer token for HTTP authentication
            local: Send request to a running local container
            user_id: User id for authorization flows

        Returns:
            Response from the Bedrock AgentCore endpoint
        """
        if not self._config_path:
            log.warning("Agent not configured and deployed")
            log.info("Required workflow: .configure() → .launch() → .invoke()")
            log.info("Example:")
            log.info("  runtime.configure(entrypoint='my_agent.py')")
            log.info("  runtime.launch()")
            log.info("  runtime.invoke({'message': 'Hello'})")
            raise ValueError("Must configure and launch first.")

        result = invoke_bedrock_agentcore(
            config_path=self._config_path,
            payload=payload,
            session_id=session_id,
            bearer_token=bearer_token,
            local_mode=local,
            user_id=user_id,
        )
        return result.response

    def stop_session(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Stop an active runtime session.

        Args:
            session_id: Optional session ID to stop. If not provided, uses tracked session.

        Returns:
            Dictionary with stop session result details

        Raises:
            ValueError: If no session ID provided or found, or agent not configured
        """
        if not self._config_path:
            log.warning("Agent not configured")
            log.info("Call .configure() first to set up your agent")
            raise ValueError("Must configure first. Call .configure() first.")

        result = stop_runtime_session(
            config_path=self._config_path,
            session_id=session_id,
        )

        log.info("Session stopped: %s", result.session_id)
        return {
            "session_id": result.session_id,
            "agent_name": result.agent_name,
            "status_code": result.status_code,
            "message": result.message,
        }

    def status(self) -> StatusResult:
        """Get Bedrock AgentCore status including config and runtime details.

        Returns:
            StatusResult with configuration, agent, and endpoint status
        """
        if not self._config_path:
            log.warning("Configuration not found")
            log.info("Call .configure() first to set up your agent")
            log.info("Example: runtime.configure(entrypoint='my_agent.py')")
            raise ValueError("Must configure first. Call .configure() first.")

        result = get_status(self._config_path)
        log.info("Retrieved Bedrock AgentCore status for: %s", self.name or "Bedrock AgentCore")
        return result

    def help_deployment_modes(self):
        """Display information about available deployment modes and migration guidance."""
        print("\n🚀 Bedrock AgentCore Deployment Modes:")
        print("=" * 50)

        print("\n1. 📦 CodeBuild Mode (RECOMMENDED - DEFAULT)")
        print("   Usage: runtime.launch()")
        print("   • Build ARM64 containers in the cloud with CodeBuild")
        print("   • No local Docker/Finch/Podman required")
        print("   • ✅ Works in SageMaker Notebooks, Cloud9, laptops")

        print("\n2. 🏠 Local Development Mode")
        print("   Usage: runtime.launch(local=True)")
        print("   • Build and run container locally")
        print("   • Requires Docker/Finch/Podman installation")
        print("   • Perfect for development and testing")
        print("   • Fast iteration and debugging")

        print("\n3. 🔧 Local Build Mode (NEW!)")
        print("   Usage: runtime.launch(local_build=True)")
        print("   • Build container locally with Docker")
        print("   • Deploy to Bedrock AgentCore cloud runtime")
        print("   • Requires Docker/Finch/Podman installation")
        print("   • Use when you need custom build control")

        print("\n📋 Migration Guide:")
        print("   • CodeBuild is now the default (no code changes needed)")
        print("   • Previous --code-build flag is deprecated")
        print("   • local_build=True option for hybrid workflows")

        print("\n💡 Quick Start:")
        print("   runtime.configure(entrypoint='my_agent.py')")
        print("   runtime.launch()  # Uses CodeBuild by default")
        print('   runtime.invoke({"prompt": "Hello"})')
        print()

    def help_vpc_networking(self):
        """Display information about VPC networking configuration."""
        print("\n🔒 VPC Networking for Bedrock AgentCore")
        print("=" * 50)

        print("\n📋 What is VPC Networking?")
        print("   VPC (Virtual Private Cloud) mode allows your agent to:")
        print("   • Access private resources (databases, internal APIs)")
        print("   • Run in isolated network environments")
        print("   • Comply with enterprise security requirements")

        print("\n⚙️  Prerequisites:")
        print("   You must have existing AWS resources:")
        print("   • VPC with private subnets")
        print("   • Security groups with appropriate rules")
        print("   • (Optional) NAT Gateway for internet access")
        print("   • (Optional) VPC endpoints for AWS services")

        print("\n🚀 Basic Usage:")
        print("   runtime.configure(")
        print("       entrypoint='my_agent.py',")
        print("       vpc_enabled=True,")
        print("       vpc_subnets=['subnet-abc123', 'subnet-def456'],")
        print("       vpc_security_groups=['sg-xyz789']")
        print("   )")
        print("   runtime.launch()")

        print("\n📝 Requirements:")
        print("   • All subnets must be in the same VPC")
        print("   • Security groups must be in the same VPC as subnets")
        print("   • Use subnets from multiple AZs for high availability")
        print("   • Security groups must allow outbound HTTPS (443) traffic")

        print("\n⚠️  Important Notes:")
        print("   • Network configuration is IMMUTABLE after agent creation")
        print("   • Cannot migrate existing PUBLIC agents to VPC mode")
        print("   • Create a new agent if you need to change network settings")
        print("   • Without NAT gateway, agent cannot pull container images")

        print("\n🔍 Security Group Requirements:")
        print("   Your security groups must allow:")
        print("   • Outbound HTTPS (443) - for AWS API calls")
        print("   • Outbound to your private resources (as needed)")
        print("   • Inbound rules are typically not required")

        print("\n💡 Example with All Features:")
        print("   runtime.configure(")
        print("       entrypoint='my_agent.py',")
        print("       execution_role='arn:aws:iam::123456789012:role/MyRole',")
        print("       vpc_enabled=True,")
        print("       vpc_subnets=['subnet-abc123', 'subnet-def456'],")
        print("       vpc_security_groups=['sg-xyz789'],")
        print("       memory_mode='STM_AND_LTM'")
        print("   )")

        print("\n📚 Related Commands:")
        print("   runtime.status()  # View network configuration")
        print("   runtime.help_deployment_modes()  # Deployment options")

        print("\n🔗 More Information:")
        print("   See AWS VPC documentation for networking setup")
        print()
