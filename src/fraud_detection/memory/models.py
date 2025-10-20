"""
Data models for the memory and learning system.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Any, Optional
from enum import Enum


class FraudDecision(Enum):
    APPROVED = "approved"
    DECLINED = "declined"
    FLAGGED = "flagged"
    REVIEW_REQUIRED = "review_required"


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Location:
    country: str
    city: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    ip_address: Optional[str] = None


@dataclass
class DeviceInfo:
    device_id: str
    device_type: str
    os: str
    browser: Optional[str] = None
    fingerprint: Optional[str] = None


@dataclass
class Transaction:
    id: str
    user_id: str
    amount: Decimal
    currency: str
    merchant: str
    category: str
    location: Location
    timestamp: datetime
    card_type: str
    device_info: DeviceInfo
    ip_address: str
    session_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DecisionContext:
    transaction_id: str
    user_id: str
    decision: FraudDecision
    confidence_score: float
    reasoning_steps: List[str]
    evidence: List[str]
    timestamp: datetime
    processing_time_ms: float
    agent_version: str
    external_tools_used: List[str] = field(default_factory=list)


@dataclass
class UserBehaviorProfile:
    user_id: str
    typical_spending_range: Dict[str, float]  # min, max, avg
    frequent_merchants: List[str]
    common_locations: List[Location]
    preferred_categories: List[str]
    transaction_frequency: Dict[str, int]  # daily, weekly, monthly averages
    risk_score: float
    last_updated: datetime
    transaction_count: int


@dataclass
class FraudPattern:
    pattern_id: str
    pattern_type: str
    description: str
    indicators: List[str]
    confidence_threshold: float
    detection_count: int
    false_positive_rate: float
    created_at: datetime
    last_seen: datetime
    effectiveness_score: float


@dataclass
class SimilarCase:
    case_id: str
    transaction_id: str
    similarity_score: float
    decision: FraudDecision
    outcome: Optional[str]  # confirmed_fraud, false_positive, etc.
    reasoning: str
    timestamp: datetime


@dataclass
class RiskProfile:
    user_id: str
    overall_risk_level: RiskLevel
    risk_factors: Dict[str, float]
    geographic_risk: float
    behavioral_risk: float
    transaction_risk: float
    temporal_risk: float
    last_assessment: datetime
    risk_evolution: List[Dict[str, Any]]  # Historical risk changes