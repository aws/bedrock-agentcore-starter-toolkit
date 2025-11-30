"""Client for interacting with Bedrock AgentCore Policy services."""

import logging
import time
from typing import Any, Dict, Optional

import boto3

from .constants import (
    DEFAULT_MAX_ATTEMPTS,
    DEFAULT_POLL_DELAY,
    DEFAULT_REGION,
    PolicyEngineStatus,
    PolicyStatus,
)
from .exceptions import (
    PolicyEngineNotFoundException,
    PolicyGenerationNotFoundException,
    PolicyNotFoundException,
    PolicySetupException,
)


class PolicyClient:
    """High-level client for Bedrock AgentCore Policy operations.

    This client supports Control Plane operations for policy engine, policy CRUD,
    and policy generation operations.
    """

    def __init__(self, region_name: Optional[str] = None):
        """Initialize the Policy client.

        Args:
            region_name: AWS region name (defaults to us-east-1)
        """
        self.region = region_name or DEFAULT_REGION
        self.client = boto3.client("bedrock-agentcore-control", region_name=self.region)
        self.session = boto3.Session(region_name=self.region)

        # Initialize the logger - write to stderr to avoid mixing with JSON output
        self.logger = logging.getLogger("bedrock_agentcore.policy")
        if not self.logger.handlers:
            import sys

            handler = logging.StreamHandler(sys.stderr)
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    # ==================== Policy Engine Operations ====================

    def create_policy_engine(
        self,
        name: str,
        description: Optional[str] = None,
        client_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new policy engine.

        Args:
            name: Name of the policy engine
            description: Optional description
            client_token: Optional client token for idempotency

        Returns:
            Policy engine details including policyEngineId, ARN, and status
        """
        self.logger.info("Creating Policy Engine: %s", name)

        request = {"name": name}

        if description:
            request["description"] = description
        if client_token:
            request["clientToken"] = client_token

        try:
            response = self.client.create_policy_engine(**request)
            self.logger.info("✓ Created Policy Engine: %s", response["policyEngineArn"])
            return response
        except Exception as e:
            raise PolicySetupException(f"Failed to create policy engine: {e}") from e

    def create_or_get_policy_engine(
        self,
        name: str,
        description: Optional[str] = None,
        client_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new policy engine or get existing one with the same name.

        This method is idempotent - it will reuse existing policy engines with
        the same name instead of throwing a ConflictException.

        The policy engine will be in ACTIVE state when this method returns.

        Args:
            name: Name of the policy engine
            description: Optional description (only used when creating)
            client_token: Optional client token for idempotency

        Returns:
            Policy engine details including policyEngineId, ARN, and status (ACTIVE)
        """
        self.logger.info("Creating or getting Policy Engine: %s", name)

        # Try to find existing engine with same name
        try:
            all_engines = []
            next_token = None

            while True:
                params = {"max_results": 100}
                if next_token:
                    params["next_token"] = next_token

                response = self.list_policy_engines(**params)
                all_engines.extend(response.get("policyEngines", []))

                next_token = response.get("nextToken")
                if not next_token:
                    break

            # Search all engines for matching name
            for engine in all_engines:
                if engine["name"] == name:
                    self.logger.info("✓ Found existing Policy Engine: %s", name)
                    # Wait for active if not already
                    if engine.get("status") != PolicyEngineStatus.ACTIVE.value:
                        self.logger.info("Waiting for Policy Engine to be active...")
                        engine = self._wait_for_policy_engine_active(engine["policyEngineId"])
                        self.logger.info("✓ Policy Engine is active")
                    return engine

        except Exception as e:
            self.logger.warning("Could not list policy engines: %s", e)

        # Not found, create new one
        try:
            engine = self.create_policy_engine(name=name, description=description, client_token=client_token)

            # Wait for active before returning
            self.logger.info("Waiting for Policy Engine to be active...")
            engine = self._wait_for_policy_engine_active(engine["policyEngineId"])
            self.logger.info("✓ Policy Engine is active")

            return engine
        except PolicySetupException as e:
            # Check if it's a conflict exception (race condition)
            if "ConflictException" in str(e) or "already exists" in str(e):
                self.logger.info("Policy engine was just created, fetching...")

                # List again to find the newly created engine
                all_engines = []
                next_token = None

                while True:
                    params = {"max_results": 100}
                    if next_token:
                        params["next_token"] = next_token

                    response = self.list_policy_engines(**params)
                    all_engines.extend(response.get("policyEngines", []))

                    next_token = response.get("nextToken")
                    if not next_token:
                        break

                for engine in all_engines:
                    if engine["name"] == name:
                        self.logger.info("✓ Found Policy Engine: %s", name)
                        # Wait for active
                        self.logger.info("Waiting for Policy Engine to be active...")
                        engine = self._wait_for_policy_engine_active(engine["policyEngineId"])
                        self.logger.info("✓ Policy Engine is active")
                        return engine

                # If still not found, raise original error
                raise
            raise

    def get_policy_engine(self, policy_engine_id: str) -> Dict[str, Any]:
        """Get policy engine details.

        Args:
            policy_engine_id: ID of the policy engine

        Returns:
            Policy engine details
        """
        try:
            response = self.client.get_policy_engine(policyEngineId=policy_engine_id)
            return response
        except self.client.exceptions.ResourceNotFoundException as e:
            raise PolicyEngineNotFoundException(f"Policy engine not found: {policy_engine_id}") from e
        except Exception as e:
            raise PolicySetupException(f"Failed to get policy engine: {e}") from e

    def update_policy_engine(
        self,
        policy_engine_id: str,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update a policy engine.

        Args:
            policy_engine_id: ID of the policy engine
            description: Optional updated description

        Returns:
            Updated policy engine details
        """
        self.logger.info("Updating Policy Engine: %s", policy_engine_id)

        request = {"policyEngineId": policy_engine_id}

        if description is not None:
            request["description"] = description

        try:
            response = self.client.update_policy_engine(**request)
            self.logger.info("✓ Updated Policy Engine: %s", response["policyEngineArn"])
            return response
        except self.client.exceptions.ResourceNotFoundException as e:
            raise PolicyEngineNotFoundException(f"Policy engine not found: {policy_engine_id}") from e
        except Exception as e:
            raise PolicySetupException(f"Failed to update policy engine: {e}") from e

    def list_policy_engines(
        self,
        max_results: Optional[int] = None,
        next_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List policy engines.

        Args:
            max_results: Maximum number of results to return
            next_token: Token for pagination

        Returns:
            List of policy engines
        """
        request = {}
        if max_results is not None:
            request["maxResults"] = max_results
        if next_token is not None:
            request["nextToken"] = next_token

        try:
            response = self.client.list_policy_engines(**request)
            return response
        except Exception as e:
            raise PolicySetupException(f"Failed to list policy engines: {e}") from e

    def delete_policy_engine(self, policy_engine_id: str) -> Dict[str, Any]:
        """Delete a policy engine.

        Args:
            policy_engine_id: ID of the policy engine

        Returns:
            Deletion status
        """
        self.logger.info("Deleting Policy Engine: %s", policy_engine_id)

        try:
            response = self.client.delete_policy_engine(policyEngineId=policy_engine_id)
            self.logger.info("✓ Policy Engine deletion initiated: %s", policy_engine_id)
            return response
        except self.client.exceptions.ResourceNotFoundException as e:
            raise PolicyEngineNotFoundException(f"Policy engine not found: {policy_engine_id}") from e
        except Exception as e:
            raise PolicySetupException(f"Failed to delete policy engine: {e}") from e

    # ==================== Policy Operations ====================

    def create_policy(
        self,
        policy_engine_id: str,
        name: str,
        definition: Dict[str, Any],
        description: Optional[str] = None,
        validation_mode: Optional[str] = None,
        client_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new policy.

        Args:
            policy_engine_id: ID of the policy engine
            name: Name of the policy
            definition: Policy definition (e.g., {"cedar": {"statement": "permit(...)"}})
            description: Optional description
            validation_mode: Optional validation mode (FAIL_ON_ANY_FINDINGS, IGNORE_ALL_FINDINGS)
            client_token: Optional client token for idempotency

        Returns:
            Policy details including policyId, ARN, and status
        """
        self.logger.info("Creating Policy: %s", name)

        request = {
            "policyEngineId": policy_engine_id,
            "name": name,
            "definition": definition,
        }

        if description:
            request["description"] = description
        if validation_mode:
            request["validationMode"] = validation_mode
        if client_token:
            request["clientToken"] = client_token

        try:
            response = self.client.create_policy(**request)
            self.logger.info("✓ Created Policy: %s", response["policyArn"])
            return response
        except self.client.exceptions.ResourceNotFoundException as e:
            raise PolicyEngineNotFoundException(f"Policy engine not found: {policy_engine_id}") from e
        except Exception as e:
            raise PolicySetupException(f"Failed to create policy: {e}") from e

    def create_or_get_policy(
        self,
        policy_engine_id: str,
        name: str,
        definition: Dict[str, Any],
        description: Optional[str] = None,
        validation_mode: Optional[str] = None,
        client_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new policy or get existing one with the same name.

        This method is idempotent - it will reuse existing policies with
        the same name instead of throwing a ConflictException.

        The policy will be in ACTIVE state when this method returns.

        Args:
            policy_engine_id: ID of the policy engine
            name: Name of the policy
            definition: Policy definition (only used when creating)
            description: Optional description (only used when creating)
            validation_mode: Optional validation mode (only used when creating)
            client_token: Optional client token for idempotency

        Returns:
            Policy details including policyId, ARN, and status (ACTIVE)
        """
        self.logger.info("Creating or getting Policy: %s", name)

        # Try to find existing policy with same name
        try:
            all_policies = []
            next_token = None

            while True:
                params = {"policy_engine_id": policy_engine_id, "max_results": 100}
                if next_token:
                    params["next_token"] = next_token

                response = self.list_policies(**params)
                all_policies.extend(response.get("policies", []))

                next_token = response.get("nextToken")
                if not next_token:
                    break

            # Search all policies for matching name
            for policy in all_policies:
                if policy["name"] == name:
                    self.logger.info("✓ Found existing Policy: %s", name)
                    # Wait for active if not already
                    if policy.get("status") != PolicyStatus.ACTIVE.value:
                        self.logger.info("Waiting for Policy to be active...")
                        policy = self._wait_for_policy_active(policy_engine_id, policy["policyId"])
                        self.logger.info("✓ Policy is active")
                    return policy

        except Exception as e:
            self.logger.warning("Could not list policies: %s", e)

        # Not found, create new one
        try:
            policy = self.create_policy(
                policy_engine_id=policy_engine_id,
                name=name,
                definition=definition,
                description=description,
                validation_mode=validation_mode,
                client_token=client_token,
            )

            # Wait for active before returning
            self.logger.info("Waiting for Policy to be active...")
            policy = self._wait_for_policy_active(policy_engine_id, policy["policyId"])
            self.logger.info("✓ Policy is active")

            return policy
        except PolicySetupException as e:
            # Check if it's a conflict exception (race condition)
            if "ConflictException" in str(e) or "already exists" in str(e):
                self.logger.info("Policy was just created, fetching...")

                # List again to find the newly created policy
                all_policies = []
                next_token = None

                while True:
                    params = {"policy_engine_id": policy_engine_id, "max_results": 100}
                    if next_token:
                        params["next_token"] = next_token

                    response = self.list_policies(**params)
                    all_policies.extend(response.get("policies", []))

                    next_token = response.get("nextToken")
                    if not next_token:
                        break

                for policy in all_policies:
                    if policy["name"] == name:
                        self.logger.info("✓ Found Policy: %s", name)
                        # Wait for active
                        self.logger.info("Waiting for Policy to be active...")
                        policy = self._wait_for_policy_active(policy_engine_id, policy["policyId"])
                        self.logger.info("✓ Policy is active")
                        return policy

                # If still not found, raise original error
                raise
            raise

    def get_policy(self, policy_engine_id: str, policy_id: str) -> Dict[str, Any]:
        """Get policy details.

        Args:
            policy_engine_id: ID of the policy engine
            policy_id: ID of the policy

        Returns:
            Policy details
        """
        try:
            response = self.client.get_policy(
                policyEngineId=policy_engine_id,
                policyId=policy_id,
            )
            return response
        except self.client.exceptions.ResourceNotFoundException as e:
            raise PolicyNotFoundException(f"Policy not found: {policy_id}") from e
        except Exception as e:
            raise PolicySetupException(f"Failed to get policy: {e}") from e

    def update_policy(
        self,
        policy_engine_id: str,
        policy_id: str,
        definition: Dict[str, Any],
        description: Optional[str] = None,
        validation_mode: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update a policy.

        Args:
            policy_engine_id: ID of the policy engine
            policy_id: ID of the policy
            definition: Updated policy definition
            description: Optional updated description
            validation_mode: Optional validation mode

        Returns:
            Updated policy details
        """
        self.logger.info("Updating Policy: %s", policy_id)

        request = {
            "policyEngineId": policy_engine_id,
            "policyId": policy_id,
            "definition": definition,
        }

        if description is not None:
            request["description"] = description
        if validation_mode is not None:
            request["validationMode"] = validation_mode

        try:
            response = self.client.update_policy(**request)
            self.logger.info("✓ Updated Policy: %s", response["policyArn"])
            return response
        except self.client.exceptions.ResourceNotFoundException as e:
            raise PolicyNotFoundException(f"Policy not found: {policy_id}") from e
        except Exception as e:
            raise PolicySetupException(f"Failed to update policy: {e}") from e

    def list_policies(
        self,
        policy_engine_id: str,
        target_resource_scope: Optional[str] = None,
        max_results: Optional[int] = None,
        next_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List policies.

        Args:
            policy_engine_id: ID of the policy engine
            target_resource_scope: Optional filter by resource ARN
            max_results: Maximum number of results to return
            next_token: Token for pagination

        Returns:
            List of policies
        """
        request = {"policyEngineId": policy_engine_id}

        if target_resource_scope is not None:
            request["targetResourceScope"] = target_resource_scope
        if max_results is not None:
            request["maxResults"] = max_results
        if next_token is not None:
            request["nextToken"] = next_token

        try:
            response = self.client.list_policies(**request)
            return response
        except self.client.exceptions.ResourceNotFoundException as e:
            raise PolicyEngineNotFoundException(f"Policy engine not found: {policy_engine_id}") from e
        except Exception as e:
            raise PolicySetupException(f"Failed to list policies: {e}") from e

    def delete_policy(self, policy_engine_id: str, policy_id: str) -> Dict[str, Any]:
        """Delete a policy.

        Args:
            policy_engine_id: ID of the policy engine
            policy_id: ID of the policy

        Returns:
            Deletion status
        """
        self.logger.info("Deleting Policy: %s", policy_id)

        try:
            response = self.client.delete_policy(
                policyEngineId=policy_engine_id,
                policyId=policy_id,
            )
            self.logger.info("✓ Policy deletion initiated: %s", policy_id)
            return response
        except self.client.exceptions.ResourceNotFoundException as e:
            raise PolicyNotFoundException(f"Policy not found: {policy_id}") from e
        except Exception as e:
            raise PolicySetupException(f"Failed to delete policy: {e}") from e

    # ==================== Policy Generation Operations ====================

    def start_policy_generation(
        self,
        policy_engine_id: str,
        name: str,
        resource: Dict[str, Any],
        content: Dict[str, Any],
        client_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Start a policy generation.

        Args:
            policy_engine_id: ID of the policy engine
            name: Name for the generation
            resource: Resource for which policies will be generated (e.g., {"arn": "..."})
            content: Natural language input (e.g., {"rawText": "allow refunds..."})
            client_token: Optional client token for idempotency

        Returns:
            Generation details including policyGenerationId, ARN, and status
        """
        self.logger.info("Starting Policy Generation: %s", name)

        request = {
            "policyEngineId": policy_engine_id,
            "name": name,
            "resource": resource,
            "content": content,
        }

        if client_token:
            request["clientToken"] = client_token

        try:
            response = self.client.start_policy_generation(**request)
            self.logger.info("✓ Started Policy Generation: %s", response["policyGenerationArn"])
            return response
        except self.client.exceptions.ResourceNotFoundException as e:
            raise PolicyEngineNotFoundException(f"Policy engine not found: {policy_engine_id}") from e
        except Exception as e:
            raise PolicySetupException(f"Failed to start policy generation: {e}") from e

    def get_policy_generation(
        self,
        policy_engine_id: str,
        policy_generation_id: str,
    ) -> Dict[str, Any]:
        """Get policy generation details.

        Args:
            policy_engine_id: ID of the policy engine
            policy_generation_id: ID of the generation

        Returns:
            Generation details
        """
        try:
            response = self.client.get_policy_generation(
                policyEngineId=policy_engine_id,
                policyGenerationId=policy_generation_id,
            )
            return response
        except self.client.exceptions.ResourceNotFoundException as e:
            raise PolicyGenerationNotFoundException(f"Policy generation not found: {policy_generation_id}") from e
        except Exception as e:
            raise PolicySetupException(f"Failed to get policy generation: {e}") from e

    def list_policy_generation_assets(
        self,
        policy_engine_id: str,
        policy_generation_id: str,
        max_results: Optional[int] = None,
        next_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get policy generation assets (generated policies).

        Args:
            policy_engine_id: ID of the policy engine
            policy_generation_id: ID of the generation
            max_results: Maximum number of results to return
            next_token: Token for pagination

        Returns:
            Generation assets including generated policy definitions
        """
        request = {
            "policyEngineId": policy_engine_id,
            "policyGenerationId": policy_generation_id,
        }

        if max_results is not None:
            request["maxResults"] = max_results
        if next_token is not None:
            request["nextToken"] = next_token

        try:
            response = self.client.list_policy_generation_assets(**request)
            return response
        except self.client.exceptions.ResourceNotFoundException as e:
            raise PolicyGenerationNotFoundException(f"Policy generation not found: {policy_generation_id}") from e
        except Exception as e:
            raise PolicySetupException(f"Failed to get policy generation assets: {e}") from e

    def list_policy_generations(
        self,
        policy_engine_id: str,
        max_results: Optional[int] = None,
        next_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List policy generations.

        Args:
            policy_engine_id: ID of the policy engine
            max_results: Maximum number of results to return
            next_token: Token for pagination

        Returns:
            List of generations
        """
        request = {"policyEngineId": policy_engine_id}

        if max_results is not None:
            request["maxResults"] = max_results
        if next_token is not None:
            request["nextToken"] = next_token

        try:
            response = self.client.list_policy_generations(**request)
            return response
        except self.client.exceptions.ResourceNotFoundException as e:
            raise PolicyEngineNotFoundException(f"Policy engine not found: {policy_engine_id}") from e
        except Exception as e:
            raise PolicySetupException(f"Failed to list policy generations: {e}") from e

    def generate_policy(
        self,
        policy_engine_id: str,
        name: str,
        resource: Dict[str, Any],
        content: Dict[str, Any],
        client_token: Optional[str] = None,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        delay: int = DEFAULT_POLL_DELAY,
        fetch_assets: bool = False,
    ) -> Dict[str, Any]:
        """Generate Cedar policies from natural language and wait for completion.

        This is a convenience method that combines start_policy_generation()
        with automatic polling until the generation is complete.

        Args:
            policy_engine_id: ID of the policy engine
            name: Name for the generation
            resource: Resource for which policies will be generated (e.g., {"arn": "..."})
            content: Natural language input (e.g., {"rawText": "allow refunds..."})
            client_token: Optional client token for idempotency
            max_attempts: Maximum number of polling attempts (default: 30)
            delay: Delay between polling attempts in seconds (default: 2)
            fetch_assets: If True, also fetch generated policies and include in response (default: False)

        Returns:
            Generation details when complete. If fetch_assets=True, includes
            'generatedPolicies' field with the Cedar policy statements.

        Raises:
            TimeoutError: If generation doesn't complete within max_attempts
            PolicySetupException: If generation fails or encounters an error
        """
        self.logger.info("Generating policies from natural language: %s", name)

        # Step 1: Start the generation
        generation = self.start_policy_generation(
            policy_engine_id=policy_engine_id,
            name=name,
            resource=resource,
            content=content,
            client_token=client_token,
        )

        policy_generation_id = generation["policyGenerationId"]
        self.logger.info("Started generation %s, waiting for completion...", policy_generation_id)

        # Step 2: Poll until generation is complete (max_attempts prevents infinite loop)
        for attempt in range(max_attempts):
            generation = self.get_policy_generation(
                policy_engine_id=policy_engine_id,
                policy_generation_id=policy_generation_id,
            )

            status = generation.get("status")

            if status == "GENERATED":
                self.logger.info("✓ Policy generation complete")

                # Step 3: Optionally fetch the generated policies
                if fetch_assets:
                    # Wait for assets to become available (eventual consistency)
                    time.sleep(2)

                    self.logger.info("Fetching generated policy assets...")
                    assets_response = self.list_policy_generation_assets(
                        policy_engine_id=policy_engine_id,
                        policy_generation_id=policy_generation_id,
                    )

                    generation["generatedPolicies"] = assets_response.get("policyGenerationAssets", [])
                    self.logger.info("✓ Fetched %d generated policies", len(generation["generatedPolicies"]))

                return generation

            elif status == "GENERATING":
                self.logger.info("Generation in progress (attempt %d/%d)...", attempt + 1, max_attempts)
                time.sleep(delay)
                continue

            else:  # GENERATE_FAILED or other error states
                reasons = generation.get("statusReasons", [])
                reason_text = ", ".join(reasons) if reasons else "Unknown reason"
                raise PolicySetupException(f"Policy generation failed with status: {status}. Reason: {reason_text}")

        raise TimeoutError(
            f"Policy generation did not complete after {max_attempts} attempts ({max_attempts * delay} seconds)"
        )

    # ==================== Helper Methods ====================

    def _wait_for_policy_engine_active(
        self,
        policy_engine_id: str,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        delay: int = DEFAULT_POLL_DELAY,
    ) -> Dict[str, Any]:
        """Wait for a policy engine to become active.

        Args:
            policy_engine_id: ID of the policy engine
            max_attempts: Maximum number of polling attempts
            delay: Delay between attempts in seconds

        Returns:
            Policy engine details when active

        Raises:
            TimeoutError: If max attempts exceeded
            PolicySetupException: If status is failed
        """
        for _attempt in range(max_attempts):
            engine = self.get_policy_engine(policy_engine_id)
            status = engine.get("status")

            if status == PolicyEngineStatus.ACTIVE.value:
                return engine
            elif status == PolicyEngineStatus.CREATING.value:
                time.sleep(delay)
                continue
            else:
                raise PolicySetupException(f"Policy engine entered unexpected status: {status}")

        raise TimeoutError(f"Policy engine did not become active after {max_attempts} attempts")

    def _wait_for_policy_active(
        self,
        policy_engine_id: str,
        policy_id: str,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        delay: int = DEFAULT_POLL_DELAY,
    ) -> Dict[str, Any]:
        """Wait for a policy to become active.

        Args:
            policy_engine_id: ID of the policy engine
            policy_id: ID of the policy
            max_attempts: Maximum number of polling attempts
            delay: Delay between attempts in seconds

        Returns:
            Policy details when active

        Raises:
            TimeoutError: If max attempts exceeded
            PolicySetupException: If status is failed
        """
        for _attempt in range(max_attempts):
            policy = self.get_policy(policy_engine_id, policy_id)
            status = policy.get("status")

            if status == PolicyStatus.ACTIVE.value:
                return policy
            elif status == PolicyStatus.CREATING.value:
                time.sleep(delay)
                continue
            else:
                raise PolicySetupException(f"Policy entered unexpected status: {status}")

        raise TimeoutError(f"Policy did not become active after {max_attempts} attempts")

    def _wait_for_policy_deleted(
        self,
        policy_engine_id: str,
        policy_id: str,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        delay: int = DEFAULT_POLL_DELAY,
    ) -> None:
        """Wait for a policy to be fully deleted.

        Args:
            policy_engine_id: ID of the policy engine
            policy_id: ID of the policy
            max_attempts: Maximum number of polling attempts
            delay: Delay between attempts in seconds

        Raises:
            TimeoutError: If max attempts exceeded
            PolicySetupException: If deletion fails
        """
        for _attempt in range(max_attempts):
            try:
                policy = self.get_policy(policy_engine_id, policy_id)
                status = policy.get("status")

                if status == PolicyStatus.DELETING.value:
                    time.sleep(delay)
                    continue
                else:
                    raise PolicySetupException(f"Policy in unexpected status during deletion: {status}")
            except PolicyNotFoundException:
                # Policy no longer exists - deletion complete
                return

        raise TimeoutError(f"Policy was not deleted after {max_attempts} attempts")

    def cleanup_policy_engine(self, policy_engine_id: str) -> None:
        """Clean up a policy engine by deleting all policies then the engine itself.

        This method provides a convenient way to delete all resources associated with
        a policy engine in the correct order:
        1. Lists all policies in the engine
        2. Deletes each policy and waits for deletion to complete
        3. Deletes the policy engine itself

        Args:
            policy_engine_id: ID of the policy engine to clean up
        """
        self.logger.info("🧹 Cleaning up Policy Engine: %s", policy_engine_id)

        # Step 1: List all policies in the engine
        try:
            all_policies = []
            next_token = None

            while True:
                params = {"policy_engine_id": policy_engine_id, "max_results": 100}
                if next_token:
                    params["next_token"] = next_token

                response = self.list_policies(**params)
                all_policies.extend(response.get("policies", []))

                next_token = response.get("nextToken")
                if not next_token:
                    break

            self.logger.info("Found %d policies to delete", len(all_policies))
        except Exception as e:
            self.logger.warning("⚠️  Could not list policies: %s", e)
            all_policies = []

        # Step 2: Delete each policy and wait for deletion to complete
        for policy in all_policies:
            try:
                policy_id = policy["policyId"]
                policy_name = policy.get("name", policy_id)
                self.logger.info("  • Deleting policy: %s", policy_name)
                self.delete_policy(policy_engine_id, policy_id)
                self.logger.info("    ✓ Policy deletion initiated: %s", policy_name)

                # Wait for policy to be fully deleted
                self._wait_for_policy_deleted(policy_engine_id, policy_id)
                self.logger.info("    ✓ Policy deleted")
            except Exception as e:
                self.logger.warning("    ⚠️ Error deleting policy %s: %s", policy_name, e)

        # Step 3: Delete the policy engine
        try:
            self.logger.info("  • Deleting policy engine: %s", policy_engine_id)
            self.delete_policy_engine(policy_engine_id)
            self.logger.info("    ✓ Policy engine deleted")
        except Exception as e:
            self.logger.warning("    ⚠️ Error deleting policy engine: %s", e)

        self.logger.info("✅ Policy Engine cleanup complete")
