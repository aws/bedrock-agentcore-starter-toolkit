"""
Fraud Database Integration

Provides integration with external fraud databases for pattern matching,
similarity search, and real-time fraud pattern updates.
"""

import logging
import time
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

from .tool_integrator import ExternalTool, ToolConfiguration, ToolResponse, ToolType

logger = logging.getLogger(__name__)


class FraudCaseStatus(Enum):
    """Status of fraud cases in database."""
    CONFIRMED = "confirmed"
    SUSPECTED = "suspected"
    INVESTIGATING = "investigating"
    FALSE_POSITIVE = "false_positive"
    RESOLVED = "resolved"


class FraudType(Enum):
    """Types of fraud patterns."""
    CARD_NOT_PRESENT = "card_not_present"
    ACCOUNT_TAKEOVER = "account_takeover"
    IDENTITY_THEFT = "identity_theft"
    SYNTHETIC_IDENTITY = "synthetic_identity"
    VELOCITY_FRAUD = "velocity_fraud"
    MERCHANT_FRAUD = "merchant_fraud"
    CHARGEBACK_FRAUD = "chargeback_fraud"
    MONEY_LAUNDERING = "money_laundering"
    BUST_OUT_FRAUD = "bust_out_fraud"
    FRIENDLY_FRAUD = "friendly_fraud"


class SimilarityMetric(Enum):
    """Metrics for similarity calculation."""
    EXACT_MATCH = "exact_match"
    FUZZY_MATCH = "fuzzy_match"
    PATTERN_MATCH = "pattern_match"
    BEHAVIORAL_MATCH = "behavioral_match"
    TEMPORAL_MATCH = "temporal_match"


@dataclass
class FraudCase:
    """Fraud case record."""
    case_id: str
    fraud_type: FraudType
    status: FraudCaseStatus
    transaction_data: Dict[str, Any]
    user_data: Dict[str, Any]
    detection_method: str
    confidence_score: float
    financial_impact: float
    created_date: datetime
    updated_date: datetime
    tags: List[str] = field(default_factory=list)
    related_cases: List[str] = field(default_factory=list)
    investigation_notes: str = ""
    resolution_notes: str = ""


@dataclass
class SimilarCase:
    """Similar fraud case match."""
    case_id: str
    similarity_score: float
    similarity_metrics: Dict[SimilarityMetric, float]
    fraud_type: FraudType
    status: FraudCaseStatus
    match_reasons: List[str]
    transaction_data: Dict[str, Any]
    confidence_score: float
    created_date: datetime


@dataclass
class FraudPattern:
    """Fraud pattern definition."""
    pattern_id: str
    pattern_name: str
    fraud_type: FraudType
    pattern_rules: Dict[str, Any]
    detection_criteria: List[str]
    confidence_threshold: float
    false_positive_rate: float
    effectiveness_score: float
    case_count: int
    last_updated: datetime
    active: bool = True


@dataclass
class PatternMatch:
    """Pattern match result."""
    pattern_id: str
    pattern_name: str
    match_score: float
    fraud_type: FraudType
    matched_criteria: List[str]
    risk_indicators: List[str]
    recommended_action: str
    confidence_level: str


class FraudDatabaseTool(ExternalTool):
    """
    Fraud database integration tool.
    
    Provides capabilities for:
    - Similarity search for known fraud cases
    - Real-time fraud pattern updates
    - Pattern matching and detection
    - Fraud case management
    """
    
    def __init__(self, config: ToolConfiguration):
        """Initialize fraud database tool."""
        super().__init__(config)
        self.database_type = config.custom_parameters.get("database_type", "generic")
        self.similarity_threshold = config.custom_parameters.get("similarity_threshold", 0.7)
        self.enable_pattern_updates = config.custom_parameters.get("enable_pattern_updates", True)
        self.max_similar_cases = config.custom_parameters.get("max_similar_cases", 10)
        
        logger.info(f"Initialized fraud database tool with type: {self.database_type}")
    
    def call_api(self, endpoint: str, data: Dict[str, Any]) -> ToolResponse:
        """Make API call to fraud database service."""
        start_time = time.time()
        
        try:
            # Check rate limit
            if not self._check_rate_limit():
                return ToolResponse(
                    success=False,
                    data={},
                    response_time_ms=0.0,
                    tool_id=self.config.tool_id,
                    timestamp=datetime.now(),
                    error_message="Rate limit exceeded"
                )
            
            # Check cache
            cache_key = self._get_cache_key(endpoint, data)
            cached_response = self._get_cached_response(cache_key)
            if cached_response:
                return cached_response
            
            # Make actual API call
            response = self._make_request(endpoint, data)
            
            # Update metrics
            self._update_metrics(response)
            
            # Cache successful responses
            if response.success:
                self._cache_response(cache_key, response)
            
            return response
            
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            error_response = ToolResponse(
                success=False,
                data={},
                response_time_ms=response_time_ms,
                tool_id=self.config.tool_id,
                timestamp=datetime.now(),
                error_message=str(e)
            )
            self._update_metrics(error_response)
            return error_response
    
    def search_similar_cases(
        self, 
        transaction_data: Dict[str, Any],
        user_data: Optional[Dict[str, Any]] = None,
        fraud_types: Optional[List[FraudType]] = None
    ) -> List[SimilarCase]:
        """
        Search for similar fraud cases.
        
        Args:
            transaction_data: Transaction information to match
            user_data: User information for matching
            fraud_types: Specific fraud types to search for
            
        Returns:
            List of similar fraud cases
        """
        request_data = {
            "transaction_data": transaction_data,
            "user_data": user_data or {},
            "fraud_types": [ft.value for ft in fraud_types] if fraud_types else [],
            "similarity_threshold": self.similarity_threshold,
            "max_results": self.max_similar_cases
        }
        
        response = self.call_api("search_similar", request_data)
        
        if response.success:
            return self._parse_similar_cases(response.data)
        else:
            logger.error(f"Failed to search similar cases: {response.error_message}")
            return []
    
    def check_fraud_patterns(self, transaction_data: Dict[str, Any]) -> List[PatternMatch]:
        """
        Check transaction against known fraud patterns.
        
        Args:
            transaction_data: Transaction data to analyze
            
        Returns:
            List of pattern matches
        """
        request_data = {
            "transaction_data": transaction_data,
            "check_all_patterns": True,
            "include_inactive": False
        }
        
        response = self.call_api("check_patterns", request_data)
        
        if response.success:
            return self._parse_pattern_matches(response.data)
        else:
            logger.error(f"Failed to check fraud patterns: {response.error_message}")
            return []
    
    def report_fraud_case(self, fraud_case: FraudCase) -> bool:
        """
        Report a new fraud case to the database.
        
        Args:
            fraud_case: Fraud case to report
            
        Returns:
            bool: True if successfully reported
        """
        request_data = {
            "case_id": fraud_case.case_id,
            "fraud_type": fraud_case.fraud_type.value,
            "status": fraud_case.status.value,
            "transaction_data": fraud_case.transaction_data,
            "user_data": fraud_case.user_data,
            "detection_method": fraud_case.detection_method,
            "confidence_score": fraud_case.confidence_score,
            "financial_impact": fraud_case.financial_impact,
            "tags": fraud_case.tags,
            "investigation_notes": fraud_case.investigation_notes
        }
        
        response = self.call_api("report_case", request_data)
        
        if response.success:
            logger.info(f"Successfully reported fraud case: {fraud_case.case_id}")
            return True
        else:
            logger.error(f"Failed to report fraud case: {response.error_message}")
            return False
    
    def update_case_status(self, case_id: str, status: FraudCaseStatus, notes: str = "") -> bool:
        """
        Update the status of an existing fraud case.
        
        Args:
            case_id: Case identifier
            status: New status
            notes: Update notes
            
        Returns:
            bool: True if successfully updated
        """
        request_data = {
            "case_id": case_id,
            "status": status.value,
            "notes": notes,
            "updated_date": datetime.now().isoformat()
        }
        
        response = self.call_api("update_case", request_data)
        
        if response.success:
            logger.info(f"Successfully updated case {case_id} to {status.value}")
            return True
        else:
            logger.error(f"Failed to update case status: {response.error_message}")
            return False
    
    def get_fraud_statistics(
        self, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        fraud_types: Optional[List[FraudType]] = None
    ) -> Dict[str, Any]:
        """
        Get fraud statistics from the database.
        
        Args:
            start_date: Start date for statistics
            end_date: End date for statistics
            fraud_types: Specific fraud types to include
            
        Returns:
            Dictionary containing fraud statistics
        """
        request_data = {
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
            "fraud_types": [ft.value for ft in fraud_types] if fraud_types else []
        }
        
        response = self.call_api("get_statistics", request_data)
        
        if response.success:
            return response.data
        else:
            logger.error(f"Failed to get fraud statistics: {response.error_message}")
            return {}
    
    def get_latest_patterns(self, last_update: Optional[datetime] = None) -> List[FraudPattern]:
        """
        Get latest fraud patterns from the database.
        
        Args:
            last_update: Only get patterns updated after this date
            
        Returns:
            List of fraud patterns
        """
        request_data = {
            "last_update": last_update.isoformat() if last_update else None,
            "include_inactive": False
        }
        
        response = self.call_api("get_patterns", request_data)
        
        if response.success:
            return self._parse_fraud_patterns(response.data)
        else:
            logger.error(f"Failed to get latest patterns: {response.error_message}")
            return []
    
    def _make_request(self, endpoint: str, data: Dict[str, Any]) -> ToolResponse:
        """Make HTTP request to fraud database service."""
        start_time = time.time()
        
        try:
            url = f"{self.config.base_url}/{endpoint}"
            
            # Prepare request based on database type
            if self.database_type == "kount":
                response_data = self._call_kount_api(url, data)
            elif self.database_type == "sift":
                response_data = self._call_sift_api(url, data)
            elif self.database_type == "featurespace":
                response_data = self._call_featurespace_api(url, data)
            else:
                # Generic/mock implementation
                response_data = self._call_generic_api(url, data, endpoint)
            
            response_time_ms = (time.time() - start_time) * 1000
            
            return ToolResponse(
                success=True,
                data=response_data,
                response_time_ms=response_time_ms,
                tool_id=self.config.tool_id,
                timestamp=datetime.now(),
                status_code=200
            )
            
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            return ToolResponse(
                success=False,
                data={},
                response_time_ms=response_time_ms,
                tool_id=self.config.tool_id,
                timestamp=datetime.now(),
                error_message=str(e)
            )
    
    def _call_kount_api(self, url: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Call Kount fraud database API."""
        headers = {
            "Content-Type": "application/json",
            "X-Kount-Api-Key": self.config.api_key
        }
        
        response = self.session.post(
            url,
            json=data,
            headers=headers,
            timeout=self.config.timeout_seconds
        )
        response.raise_for_status()
        
        return response.json()
    
    def _call_sift_api(self, url: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Call Sift fraud database API."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {self.config.api_key}"
        }
        
        response = self.session.post(
            url,
            json=data,
            headers=headers,
            timeout=self.config.timeout_seconds
        )
        response.raise_for_status()
        
        return response.json()
    
    def _call_featurespace_api(self, url: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Call Featurespace fraud database API."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}"
        }
        
        response = self.session.post(
            url,
            json=data,
            headers=headers,
            timeout=self.config.timeout_seconds
        )
        response.raise_for_status()
        
        return response.json()
    
    def _call_generic_api(self, url: str, data: Dict[str, Any], endpoint: str) -> Dict[str, Any]:
        """Generic/mock fraud database implementation."""
        # Simulate processing time
        time.sleep(0.05)
        
        if endpoint == "search_similar":
            return self._mock_similar_search(data)
        elif endpoint == "check_patterns":
            return self._mock_pattern_check(data)
        elif endpoint == "report_case":
            return self._mock_case_report(data)
        elif endpoint == "update_case":
            return self._mock_case_update(data)
        elif endpoint == "get_statistics":
            return self._mock_statistics(data)
        elif endpoint == "get_patterns":
            return self._mock_patterns(data)
        else:
            return {"success": True, "message": "Mock response"}
    
    def _mock_similar_search(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock similar case search."""
        transaction_data = data.get("transaction_data", {})
        amount = transaction_data.get("amount", 0)
        merchant = transaction_data.get("merchant", "")
        
        # Generate mock similar cases
        similar_cases = []
        
        # Create 2-3 similar cases based on amount and merchant
        for i in range(2 if amount > 1000 else 1):
            case_id = f"case_{hash(merchant + str(amount + i)) % 10000}"
            similarity_score = 0.85 - (i * 0.1)
            
            similar_cases.append({
                "case_id": case_id,
                "similarity_score": similarity_score,
                "similarity_metrics": {
                    "exact_match": 0.9 if merchant else 0.0,
                    "fuzzy_match": 0.8,
                    "pattern_match": similarity_score,
                    "behavioral_match": 0.7,
                    "temporal_match": 0.6
                },
                "fraud_type": "card_not_present" if amount > 500 else "velocity_fraud",
                "status": "confirmed",
                "match_reasons": [
                    f"Similar amount: ${amount}",
                    f"Same merchant: {merchant}" if merchant else "Similar merchant pattern",
                    "Similar transaction time"
                ],
                "transaction_data": {
                    "amount": amount + (i * 10),
                    "merchant": merchant or f"Similar Merchant {i}",
                    "currency": "USD"
                },
                "confidence_score": 0.9 - (i * 0.1),
                "created_date": (datetime.now() - timedelta(days=i+1)).isoformat()
            })
        
        return {"similar_cases": similar_cases}
    
    def _mock_pattern_check(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock pattern matching."""
        transaction_data = data.get("transaction_data", {})
        amount = transaction_data.get("amount", 0)
        
        pattern_matches = []
        
        # High amount pattern
        if amount > 1000:
            pattern_matches.append({
                "pattern_id": "high_amount_pattern",
                "pattern_name": "High Amount Transaction",
                "match_score": 0.9,
                "fraud_type": "card_not_present",
                "matched_criteria": ["amount > $1000", "online transaction"],
                "risk_indicators": ["High financial impact", "Unusual amount for user"],
                "recommended_action": "manual_review",
                "confidence_level": "high"
            })
        
        # Velocity pattern (mock based on time)
        if datetime.now().hour < 6:  # Early morning transactions
            pattern_matches.append({
                "pattern_id": "unusual_time_pattern",
                "pattern_name": "Unusual Transaction Time",
                "match_score": 0.7,
                "fraud_type": "velocity_fraud",
                "matched_criteria": ["transaction_time < 06:00"],
                "risk_indicators": ["Unusual transaction time"],
                "recommended_action": "additional_verification",
                "confidence_level": "medium"
            })
        
        return {"pattern_matches": pattern_matches}
    
    def _mock_case_report(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock case reporting."""
        case_id = data.get("case_id")
        return {
            "success": True,
            "case_id": case_id,
            "message": "Fraud case reported successfully",
            "assigned_investigator": "auto_assigned",
            "priority": "medium"
        }
    
    def _mock_case_update(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock case status update."""
        case_id = data.get("case_id")
        status = data.get("status")
        return {
            "success": True,
            "case_id": case_id,
            "status": status,
            "message": "Case status updated successfully"
        }
    
    def _mock_statistics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock fraud statistics."""
        return {
            "total_cases": 1250,
            "confirmed_fraud": 890,
            "false_positives": 180,
            "under_investigation": 180,
            "fraud_types": {
                "card_not_present": 450,
                "account_takeover": 220,
                "identity_theft": 120,
                "velocity_fraud": 100,
                "other": 360
            },
            "average_financial_impact": 2500.50,
            "detection_accuracy": 0.92,
            "false_positive_rate": 0.08
        }
    
    def _mock_patterns(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock fraud patterns."""
        patterns = [
            {
                "pattern_id": "high_velocity_pattern",
                "pattern_name": "High Velocity Transactions",
                "fraud_type": "velocity_fraud",
                "pattern_rules": {
                    "transaction_count": "> 5 in 10 minutes",
                    "amount_threshold": "> $100 per transaction"
                },
                "detection_criteria": [
                    "Multiple transactions in short timeframe",
                    "Increasing transaction amounts",
                    "Different merchants"
                ],
                "confidence_threshold": 0.8,
                "false_positive_rate": 0.05,
                "effectiveness_score": 0.92,
                "case_count": 156,
                "last_updated": datetime.now().isoformat(),
                "active": True
            },
            {
                "pattern_id": "unusual_location_pattern",
                "pattern_name": "Unusual Location Pattern",
                "fraud_type": "card_not_present",
                "pattern_rules": {
                    "location_distance": "> 500 miles from usual",
                    "time_between_transactions": "< 2 hours"
                },
                "detection_criteria": [
                    "Transaction in unusual location",
                    "Impossible travel time",
                    "No prior transactions in area"
                ],
                "confidence_threshold": 0.85,
                "false_positive_rate": 0.03,
                "effectiveness_score": 0.95,
                "case_count": 89,
                "last_updated": datetime.now().isoformat(),
                "active": True
            }
        ]
        
        return {"patterns": patterns}
    
    def _parse_similar_cases(self, data: Dict[str, Any]) -> List[SimilarCase]:
        """Parse API response into SimilarCase objects."""
        similar_cases = []
        
        for case_data in data.get("similar_cases", []):
            # Parse similarity metrics
            metrics_data = case_data.get("similarity_metrics", {})
            similarity_metrics = {}
            for metric_name, score in metrics_data.items():
                try:
                    metric = SimilarityMetric(metric_name)
                    similarity_metrics[metric] = float(score)
                except ValueError:
                    continue
            
            similar_case = SimilarCase(
                case_id=case_data.get("case_id", ""),
                similarity_score=float(case_data.get("similarity_score", 0.0)),
                similarity_metrics=similarity_metrics,
                fraud_type=FraudType(case_data.get("fraud_type", "card_not_present")),
                status=FraudCaseStatus(case_data.get("status", "confirmed")),
                match_reasons=case_data.get("match_reasons", []),
                transaction_data=case_data.get("transaction_data", {}),
                confidence_score=float(case_data.get("confidence_score", 0.0)),
                created_date=datetime.fromisoformat(case_data.get("created_date", datetime.now().isoformat()))
            )
            similar_cases.append(similar_case)
        
        return similar_cases
    
    def _parse_pattern_matches(self, data: Dict[str, Any]) -> List[PatternMatch]:
        """Parse API response into PatternMatch objects."""
        pattern_matches = []
        
        for match_data in data.get("pattern_matches", []):
            pattern_match = PatternMatch(
                pattern_id=match_data.get("pattern_id", ""),
                pattern_name=match_data.get("pattern_name", ""),
                match_score=float(match_data.get("match_score", 0.0)),
                fraud_type=FraudType(match_data.get("fraud_type", "card_not_present")),
                matched_criteria=match_data.get("matched_criteria", []),
                risk_indicators=match_data.get("risk_indicators", []),
                recommended_action=match_data.get("recommended_action", "review"),
                confidence_level=match_data.get("confidence_level", "medium")
            )
            pattern_matches.append(pattern_match)
        
        return pattern_matches
    
    def _parse_fraud_patterns(self, data: Dict[str, Any]) -> List[FraudPattern]:
        """Parse API response into FraudPattern objects."""
        fraud_patterns = []
        
        for pattern_data in data.get("patterns", []):
            fraud_pattern = FraudPattern(
                pattern_id=pattern_data.get("pattern_id", ""),
                pattern_name=pattern_data.get("pattern_name", ""),
                fraud_type=FraudType(pattern_data.get("fraud_type", "card_not_present")),
                pattern_rules=pattern_data.get("pattern_rules", {}),
                detection_criteria=pattern_data.get("detection_criteria", []),
                confidence_threshold=float(pattern_data.get("confidence_threshold", 0.8)),
                false_positive_rate=float(pattern_data.get("false_positive_rate", 0.05)),
                effectiveness_score=float(pattern_data.get("effectiveness_score", 0.9)),
                case_count=int(pattern_data.get("case_count", 0)),
                last_updated=datetime.fromisoformat(pattern_data.get("last_updated", datetime.now().isoformat())),
                active=pattern_data.get("active", True)
            )
            fraud_patterns.append(fraud_pattern)
        
        return fraud_patterns


def create_fraud_database_tool(
    tool_id: str,
    database_type: str = "generic",
    api_key: Optional[str] = None,
    base_url: Optional[str] = None
) -> FraudDatabaseTool:
    """
    Create fraud database tool with common configurations.
    
    Args:
        tool_id: Unique identifier for the tool
        database_type: Database provider (kount, sift, featurespace, generic)
        api_key: API key for the service
        base_url: Base URL for the API
        
    Returns:
        FraudDatabaseTool instance
    """
    # Provider-specific configurations
    provider_configs = {
        "kount": {
            "base_url": base_url or "https://api.kount.com/fraud",
            "rate_limit_per_minute": 300,
            "timeout_seconds": 20
        },
        "sift": {
            "base_url": base_url or "https://api.sift.com/v205",
            "rate_limit_per_minute": 500,
            "timeout_seconds": 15
        },
        "featurespace": {
            "base_url": base_url or "https://api.featurespace.com/fraud",
            "rate_limit_per_minute": 200,
            "timeout_seconds": 25
        },
        "generic": {
            "base_url": base_url or "https://api.mock-fraud-database.com",
            "rate_limit_per_minute": 100,
            "timeout_seconds": 30
        }
    }
    
    config_data = provider_configs.get(database_type, provider_configs["generic"])
    
    config = ToolConfiguration(
        tool_id=tool_id,
        tool_name=f"Fraud Database ({database_type})",
        tool_type=ToolType.FRAUD_DATABASE,
        base_url=config_data["base_url"],
        api_key=api_key,
        timeout_seconds=config_data["timeout_seconds"],
        rate_limit_per_minute=config_data["rate_limit_per_minute"],
        enable_caching=True,
        cache_ttl_seconds=1800,  # Cache for 30 minutes
        custom_parameters={
            "database_type": database_type,
            "similarity_threshold": 0.7,
            "enable_pattern_updates": True,
            "max_similar_cases": 10
        }
    )
    
    return FraudDatabaseTool(config)