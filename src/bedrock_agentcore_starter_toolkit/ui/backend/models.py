"""Pydantic models for API request/response validation."""

from typing import Dict, List, Literal, Optional, Union

from pydantic import BaseModel


class AgentConfigResponse(BaseModel):
    """Response model for agent configuration."""

    mode: Literal["local", "remote"]
    agent_name: str
    agent_arn: Optional[str] = None
    region: Optional[str] = None
    session_id: str
    auth_method: Literal["iam", "oauth", "none"]
    memory_id: Optional[str] = None


class InvokeRequest(BaseModel):
    """Request model for agent invocation."""

    message: str
    session_id: str
    bearer_token: Optional[str] = None
    user_id: Optional[str] = None


class InvokeResponse(BaseModel):
    """Response model for agent invocation."""

    response: Union[str, dict]
    session_id: str
    timestamp: str


class NewSessionResponse(BaseModel):
    """Response model for new session creation."""

    session_id: str


class MemoryStrategyResponse(BaseModel):
    """Response model for memory strategy."""

    strategy_id: str
    name: str
    type: str
    status: str
    description: Optional[str] = None
    namespaces: Optional[List[str]] = None
    configuration: Optional[Dict] = None


class MemoryResourceResponse(BaseModel):
    """Response model for memory resource."""

    memory_id: str
    name: str
    status: str
    event_expiry_days: int
    memory_type: Literal["short-term", "short-term-and-long-term"]
    strategies: List[MemoryStrategyResponse]


class ErrorResponse(BaseModel):
    """Response model for errors."""

    error: Dict[str, Union[str, dict]]
