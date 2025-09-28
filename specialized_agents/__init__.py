"""
Specialized Agents for AWS AI Agent Enhancement

This module provides specialized agents for different aspects of fraud detection:
- Transaction Analyzer Agent
- Pattern Detection Agent  
- Risk Assessment Agent
- Compliance Agent
"""

from .base_agent import BaseAgent, AgentCapability, AgentStatus
from .transaction_analyzer import TransactionAnalyzer

__all__ = [
    'BaseAgent',
    'AgentCapability', 
    'AgentStatus',
    'TransactionAnalyzer'
]