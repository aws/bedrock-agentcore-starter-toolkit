"""
Stress Testing Framework for AWS Bedrock AI Agent Fraud Detection System.

This module provides comprehensive stress testing capabilities including:
- High-volume load generation
- Multi-agent coordination testing
- AWS infrastructure validation
- Real-time metrics collection
- Investor-grade presentation dashboards
- Resilience validation and recovery testing
"""

__version__ = "1.0.0"

# Import key components for easy access
from .resilience_validator import (
    ResilienceValidator,
    RecoveryStatus,
    CircuitBreakerState,
    RecoveryEvent,
    CircuitBreakerValidation,
    RetryValidation,
    DLQValidation
)

__all__ = [
    'ResilienceValidator',
    'RecoveryStatus',
    'CircuitBreakerState',
    'RecoveryEvent',
    'CircuitBreakerValidation',
    'RetryValidation',
    'DLQValidation'
]
