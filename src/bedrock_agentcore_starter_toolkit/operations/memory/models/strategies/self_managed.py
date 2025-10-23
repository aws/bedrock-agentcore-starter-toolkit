"""Self managed memory strategy implementation."""

from typing import Any, Dict, List, Union

from pydantic import BaseModel, Field

from .base import BaseStrategy


class MessageBasedTrigger(BaseModel):
    """Trigger configuration based on message."""

    message_count: int = Field(default=6, description="Number of messages that trigger memory processing.")


class TokenBasedTrigger(BaseModel):
    """Trigger configuration based on tokens."""

    token_count: int = Field(default=5000, description="Number of tokens that trigger memory processing.")


class TimeBasedTrigger(BaseModel):
    """Trigger configuration based on time."""

    idle_session_timeout: int = Field(
        default=20, description="Idle session timeout (seconds) that triggers memory processing."
    )


class InvocationConfig(BaseModel):
    """Configuration to invoke customer-owned memory processing pipeline."""

    topic_arn: str = Field(..., description="The ARN of the SNS topic for job notifications.")
    payload_delivery_bucket_name: str = Field(..., description="S3 bucket name for event payload delivery.")


class SelfManagedStrategy(BaseStrategy):
    """Self-managed memory strategy with custom processing pipeline.

    This strategy allows complete control over memory processing through
    customer-owned pipelines triggered by configurable conditions.

    Attributes:
        trigger_conditions: List of conditions that trigger memory processing
        invocation_config: Configuration for invoking memory processing pipeline
        historical_context_window_size: Number of historical messages to include

    Example:
        strategy = SelfManagedStrategy(
            name="SelfManagedStrategy",
            description="Self-managed processing with SNS notifications",
            trigger_conditions=[
                MessageBasedTrigger(message_count=10),
                TokenBasedTrigger(token_count=8000)
            ],
            invocation_config=InvocationConfig(
                topic_arn="arn:aws:sns:us-east-1:123456789012:memory-processing",
                payload_delivery_bucket_name="my-memory-bucket"
            ),
            historical_context_window_size=6
        )
    """

    trigger_conditions: List[Union[MessageBasedTrigger, TokenBasedTrigger, TimeBasedTrigger]] = Field(
        default_factory=list
    )
    invocation_config: InvocationConfig
    historical_context_window_size: int = Field(
        default=4, description="Number of historical messages to include in processing context."
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for API calls."""
        config = {
            "name": self.name,
            "configuration": {
                "selfManagedConfiguration": {
                    "triggerConditions": self._convert_trigger_conditions(),
                    "invocationConfiguration": self._convert_invocation_config(),
                    "historicalContextWindowSize": self.historical_context_window_size,
                }
            },
        }

        if self.description is not None:
            config["description"] = self.description

        return {"customMemoryStrategy": config}

    def _convert_trigger_conditions(self) -> List[Dict[str, Any]]:
        """Convert trigger conditions to API format."""
        conditions = []
        for condition in self.trigger_conditions:
            if isinstance(condition, MessageBasedTrigger):
                conditions.append({"messageBasedTrigger": {"messageCount": condition.message_count}})
            elif isinstance(condition, TokenBasedTrigger):
                conditions.append({"tokenBasedTrigger": {"tokenCount": condition.token_count}})
            elif isinstance(condition, TimeBasedTrigger):
                conditions.append({"timeBasedTrigger": {"idleSessionTimeout": condition.idle_session_timeout}})
        return conditions

    def _convert_invocation_config(self) -> Dict[str, Any]:
        """Convert invocation config to API format."""
        return {
            "topicArn": self.invocation_config.topic_arn,
            "payloadDeliveryBucketName": self.invocation_config.payload_delivery_bucket_name,
        }
