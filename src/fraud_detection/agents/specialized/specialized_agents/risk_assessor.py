"""
Risk Assessment Agent

Specialized agent for multi-factor risk scoring, geographic and temporal risk analysis,
cross-reference systems for known fraud indicators, and risk threshold management.
"""

import logging
import math
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import statistics

from .base_agent import BaseAgent, AgentConfiguration, AgentCapability, ProcessingResult
from memory_system.models import Transaction, RiskProfile, RiskLevel, Location, DecisionContext
from memory_system.memory_manager import MemoryManager

logger = logging.getLogger(__name__)


@dataclass
class RiskFactor:
    """Individual risk factor assessment."""
    factor_name: str
    risk_score: float  # 0-1, higher = more risky
    confidence: float  # 0-1, confidence in the assessment
    description: str
    evidence: List[str] = field(default_factory=list)
    weight: float = 1.0  # Relative importance of this factor


@dataclass
class GeographicRisk:
    """Geographic risk assessment result."""
    location_risk_score: float
    country_risk_level: str  # "low", "medium", "high", "critical"
    travel_pattern_risk: float
    ip_location_mismatch: bool
    distance_from_home: float  # km
    risk_factors: List[str] = field(default_factory=list)


@dataclass
class TemporalRisk:
    """Temporal risk assessment result."""
    time_risk_score: float
    unusual_hour_risk: float
    frequency_risk: float
    velocity_risk: float
    pattern_deviation: float
    risk_factors: List[str] = field(default_factory=list)


@dataclass
class CrossReferenceResult:
    """Cross-reference check result."""
    reference_type: str  # "blacklist", "watchlist", "fraud_database"
    match_found: bool
    match_confidence: float
    match_details: Dict[str, Any] = field(default_factory=dict)
    risk_impact: float = 0.0


@dataclass
class RiskAssessmentResult:
    """Complete risk assessment result."""
    transaction_id: str
    overall_risk_score: float  # 0-1
    risk_level: str  # "low", "medium", "high", "critical"
    confidence: float
    risk_factors: List[RiskFactor] = field(default_factory=list)
    geographic_risk: Optional[GeographicRisk] = None
    temporal_risk: Optional[TemporalRisk] = None
    cross_reference_results: List[CrossReferenceResult] = field(default_factory=list)
    risk_threshold_breaches: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    risk_mitigation_suggestions: List[str] = field(default_factory=list)


class RiskAssessor(BaseAgent):
    """
    Specialized agent for comprehensive risk assessment.
    
    Capabilities:
    - Multi-factor risk scoring algorithms
    - Geographic and temporal risk analysis
    - Cross-reference system for known fraud indicators
    - Risk threshold management and adaptation
    - Real-time risk monitoring
    """
    
    def __init__(
        self,
        memory_manager: MemoryManager,
        config: Optional[AgentConfiguration] = None
    ):
        """
        Initialize the Risk Assessment Agent.
        
        Args:
            memory_manager: Memory manager for data access
            config: Agent configuration (optional)
        """
        if config is None:
            config = AgentConfiguration(
                agent_id="risk_assessor_001",
                agent_name="RiskAssessor",
                version="1.0.0",
                capabilities=[
                    AgentCapability.RISK_ASSESSMENT,
                    AgentCapability.REAL_TIME_PROCESSING,
                    AgentCapability.PATTERN_DETECTION
                ],
                max_concurrent_requests=40,
                timeout_seconds=12,
                custom_parameters={
                    "risk_thresholds": {
                        "low": 0.3,
                        "medium": 0.6,
                        "high": 0.8
                    },
                    "geographic_risk_enabled": True,
                    "temporal_risk_enabled": True,
                    "cross_reference_enabled": True,
                    "adaptive_thresholds": True
                }
            )
        
        self.memory_manager = memory_manager
        
        # Risk assessment configuration
        self.risk_weights = {
            "amount_risk": 0.25,
            "geographic_risk": 0.20,
            "temporal_risk": 0.15,
            "behavioral_risk": 0.20,
            "cross_reference_risk": 0.15,
            "velocity_risk": 0.05
        }
        
        # Geographic risk databases
        self.high_risk_countries = {
            "XX", "YY", "ZZ"  # Placeholder high-risk countries
        }
        
        self.country_risk_scores = {
            "US": 0.1, "CA": 0.1, "GB": 0.15, "DE": 0.15, "FR": 0.15,
            "AU": 0.2, "JP": 0.2, "BR": 0.4, "IN": 0.3, "CN": 0.35,
            "RU": 0.6, "XX": 0.9, "YY": 0.85, "ZZ": 0.8
        }
        
        # Fraud indicators database
        self.fraud_indicators = {
            "blacklisted_ips": set(),
            "suspicious_merchants": set(),
            "known_fraud_patterns": [],
            "watchlist_users": set()
        }
        
        super().__init__(config)
    
    def _initialize_agent(self) -> None:
        """Initialize risk assessor specific components."""
        self.logger.info("Initializing Risk Assessment Agent")
        
        # Initialize risk thresholds
        self.risk_thresholds = self.config.custom_parameters.get("risk_thresholds", {
            "low": 0.3,
            "medium": 0.6,
            "high": 0.8
        })
        
        # Initialize fraud indicators (in production, load from external sources)
        self._initialize_fraud_indicators()
        
        # Initialize geographic risk data
        self._initialize_geographic_data()
        
        self.logger.info("Risk Assessment Agent initialized successfully")
    
    def process_request(self, request_data: Dict[str, Any]) -> ProcessingResult:
        """
        Process a risk assessment request.
        
        Args:
            request_data: Dictionary containing transaction data and assessment parameters
            
        Returns:
            ProcessingResult with risk assessment analysis
        """
        try:
            # Extract transaction and assessment parameters
            transaction = self._extract_transaction(request_data)
            assessment_type = request_data.get("assessment_type", "comprehensive")
            
            if not transaction:
                return ProcessingResult(
                    success=False,
                    result_data={},
                    processing_time_ms=0.0,
                    confidence_score=0.0,
                    error_message="Invalid transaction data"
                )
            
            # Perform risk assessment
            risk_assessment = self._assess_risk(transaction, assessment_type)
            
            return ProcessingResult(
                success=True,
                result_data={
                    "risk_assessment": risk_assessment.__dict__,
                    "transaction_id": transaction.id,
                    "assessment_type": assessment_type,
                    "timestamp": datetime.now().isoformat()
                },
                processing_time_ms=0.0,  # Will be set by base class
                confidence_score=risk_assessment.confidence,
                metadata={
                    "agent_type": "risk_assessor",
                    "assessment_version": "1.0.0"
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error in risk assessment: {str(e)}")
            return ProcessingResult(
                success=False,
                result_data={},
                processing_time_ms=0.0,
                confidence_score=0.0,
                error_message=str(e)
            )
    
    def _extract_transaction(self, request_data: Dict[str, Any]) -> Optional[Transaction]:
        """Extract transaction from request data."""
        try:
            if "transaction" in request_data:
                tx_data = request_data["transaction"]
            else:
                tx_data = request_data
            
            # Create transaction object (simplified for demo)
            from memory_system.models import Location, DeviceInfo
            
            location = Location(
                country=tx_data.get("location", {}).get("country", ""),
                city=tx_data.get("location", {}).get("city", ""),
                latitude=tx_data.get("location", {}).get("latitude"),
                longitude=tx_data.get("location", {}).get("longitude"),
                ip_address=tx_data.get("location", {}).get("ip_address")
            )
            
            device_info = DeviceInfo(
                device_id=tx_data.get("device_info", {}).get("device_id", ""),
                device_type=tx_data.get("device_info", {}).get("device_type", ""),
                os=tx_data.get("device_info", {}).get("os", "")
            )
            
            transaction = Transaction(
                id=tx_data.get("id", ""),
                user_id=tx_data.get("user_id", ""),
                amount=Decimal(str(tx_data.get("amount", 0))),
                currency=tx_data.get("currency", "USD"),
                merchant=tx_data.get("merchant", ""),
                category=tx_data.get("category", ""),
                location=location,
                timestamp=datetime.fromisoformat(tx_data.get("timestamp", datetime.now().isoformat())),
                card_type=tx_data.get("card_type", ""),
                device_info=device_info,
                ip_address=tx_data.get("ip_address", ""),
                session_id=tx_data.get("session_id", ""),
                metadata=tx_data.get("metadata", {})
            )
            
            return transaction
            
        except Exception as e:
            self.logger.error(f"Error extracting transaction: {str(e)}")
            return None
    
    def _assess_risk(self, transaction: Transaction, assessment_type: str) -> RiskAssessmentResult:
        """Perform comprehensive risk assessment."""
        result = RiskAssessmentResult(
            transaction_id=transaction.id,
            overall_risk_score=0.0,
            risk_level="low",
            confidence=0.0
        )
        
        # 1. Multi-factor risk scoring
        risk_factors = self._calculate_risk_factors(transaction)
        result.risk_factors = risk_factors
        
        # 2. Geographic risk analysis
        if self.config.custom_parameters.get("geographic_risk_enabled", True):
            geographic_risk = self._assess_geographic_risk(transaction)
            result.geographic_risk = geographic_risk
        
        # 3. Temporal risk analysis
        if self.config.custom_parameters.get("temporal_risk_enabled", True):
            temporal_risk = self._assess_temporal_risk(transaction)
            result.temporal_risk = temporal_risk
        
        # 4. Cross-reference checks
        if self.config.custom_parameters.get("cross_reference_enabled", True):
            cross_ref_results = self._perform_cross_reference_checks(transaction)
            result.cross_reference_results = cross_ref_results
        
        # 5. Calculate overall risk score
        result.overall_risk_score = self._calculate_overall_risk_score(result)
        
        # 6. Determine risk level
        result.risk_level = self._determine_risk_level(result.overall_risk_score)
        
        # 7. Calculate confidence
        result.confidence = self._calculate_assessment_confidence(result)
        
        # 8. Check threshold breaches
        result.risk_threshold_breaches = self._check_threshold_breaches(result)
        
        # 9. Generate recommendations
        result.recommendations = self._generate_risk_recommendations(result)
        
        # 10. Generate risk mitigation suggestions
        result.risk_mitigation_suggestions = self._generate_mitigation_suggestions(result)
        
        return result
    
    def _calculate_risk_factors(self, transaction: Transaction) -> List[RiskFactor]:
        """Calculate individual risk factors."""
        risk_factors = []
        
        # Amount risk factor
        amount_risk = self._assess_amount_risk(transaction)
        if amount_risk:
            risk_factors.append(amount_risk)
        
        # Merchant risk factor
        merchant_risk = self._assess_merchant_risk(transaction)
        if merchant_risk:
            risk_factors.append(merchant_risk)
        
        # Device risk factor
        device_risk = self._assess_device_risk(transaction)
        if device_risk:
            risk_factors.append(device_risk)
        
        # Behavioral risk factor
        behavioral_risk = self._assess_behavioral_risk(transaction)
        if behavioral_risk:
            risk_factors.append(behavioral_risk)
        
        # Velocity risk factor
        velocity_risk = self._assess_velocity_risk(transaction)
        if velocity_risk:
            risk_factors.append(velocity_risk)
        
        return risk_factors
    
    def _assess_amount_risk(self, transaction: Transaction) -> Optional[RiskFactor]:
        """Assess risk based on transaction amount."""
        amount = float(transaction.amount)
        
        # Get user's typical spending pattern
        user_profile = self.memory_manager.get_user_profile(transaction.user_id)
        
        if user_profile:
            typical_range = user_profile.typical_spending_range
            max_typical = typical_range.get("max", 500)
            avg_typical = typical_range.get("avg", 100)
            
            # Calculate amount risk based on deviation from typical spending
            if amount > max_typical * 3:  # 3x typical maximum
                risk_score = min(1.0, amount / (max_typical * 5))
                return RiskFactor(
                    factor_name="amount_risk",
                    risk_score=risk_score,
                    confidence=0.8,
                    description=f"Transaction amount ${amount:.2f} significantly exceeds typical spending",
                    evidence=[
                        f"Amount: ${amount:.2f}",
                        f"User's typical max: ${max_typical:.2f}",
                        f"Ratio: {amount/max_typical:.1f}x typical maximum"
                    ],
                    weight=self.risk_weights.get("amount_risk", 0.25)
                )
            elif amount > max_typical * 1.5:  # 1.5x typical maximum
                risk_score = 0.4 + (amount - max_typical * 1.5) / (max_typical * 1.5) * 0.3
                return RiskFactor(
                    factor_name="amount_risk",
                    risk_score=min(1.0, risk_score),
                    confidence=0.6,
                    description=f"Transaction amount ${amount:.2f} above typical spending range",
                    evidence=[
                        f"Amount: ${amount:.2f}",
                        f"User's typical max: ${max_typical:.2f}"
                    ],
                    weight=self.risk_weights.get("amount_risk", 0.25)
                )
        else:
            # No user profile - assess based on absolute thresholds
            if amount > 5000:
                risk_score = min(1.0, amount / 10000)
                return RiskFactor(
                    factor_name="amount_risk",
                    risk_score=risk_score,
                    confidence=0.5,
                    description=f"High transaction amount ${amount:.2f} (no user baseline)",
                    evidence=[f"Amount: ${amount:.2f}", "No user spending history available"],
                    weight=self.risk_weights.get("amount_risk", 0.25)
                )
        
        return None
    
    def _assess_merchant_risk(self, transaction: Transaction) -> Optional[RiskFactor]:
        """Assess risk based on merchant characteristics."""
        merchant = transaction.merchant.lower()
        
        # Check for high-risk merchant categories
        high_risk_keywords = [
            "casino", "gambling", "crypto", "bitcoin", "forex", "adult", 
            "escort", "pharmacy", "offshore", "anonymous", "proxy"
        ]
        
        for keyword in high_risk_keywords:
            if keyword in merchant:
                risk_score = 0.7 if keyword in ["casino", "gambling", "crypto"] else 0.5
                return RiskFactor(
                    factor_name="merchant_risk",
                    risk_score=risk_score,
                    confidence=0.9,
                    description=f"High-risk merchant category detected: {keyword}",
                    evidence=[
                        f"Merchant: {transaction.merchant}",
                        f"Risk keyword: {keyword}",
                        f"Category: {transaction.category}"
                    ],
                    weight=0.2
                )
        
        # Check if merchant is in suspicious merchants list
        if merchant in self.fraud_indicators["suspicious_merchants"]:
            return RiskFactor(
                factor_name="merchant_risk",
                risk_score=0.8,
                confidence=0.95,
                description="Merchant flagged in suspicious merchants database",
                evidence=[f"Merchant: {transaction.merchant}"],
                weight=0.2
            )
        
        return None
    
    def _assess_device_risk(self, transaction: Transaction) -> Optional[RiskFactor]:
        """Assess risk based on device characteristics."""
        device_info = transaction.device_info
        
        # Check for suspicious device characteristics
        risk_indicators = []
        risk_score = 0.0
        
        # Unknown or suspicious device type
        if device_info.device_type.lower() in ["unknown", "emulator", "bot"]:
            risk_indicators.append("Unknown or suspicious device type")
            risk_score += 0.4
        
        # Missing device fingerprint
        if not device_info.fingerprint:
            risk_indicators.append("Missing device fingerprint")
            risk_score += 0.2
        
        # Suspicious OS
        if device_info.os.lower() in ["unknown", "custom", "modified"]:
            risk_indicators.append("Suspicious operating system")
            risk_score += 0.3
        
        if risk_indicators:
            return RiskFactor(
                factor_name="device_risk",
                risk_score=min(1.0, risk_score),
                confidence=0.7,
                description="Suspicious device characteristics detected",
                evidence=risk_indicators,
                weight=0.15
            )
        
        return None
    
    def _assess_behavioral_risk(self, transaction: Transaction) -> Optional[RiskFactor]:
        """Assess risk based on behavioral patterns."""
        # Get user's recent transaction history
        recent_transactions = self.memory_manager.get_user_transaction_history(
            transaction.user_id, days_back=30, limit=50
        )
        
        if len(recent_transactions) < 5:
            # New user or insufficient history
            return RiskFactor(
                factor_name="behavioral_risk",
                risk_score=0.4,
                confidence=0.6,
                description="Insufficient transaction history for behavioral analysis",
                evidence=[f"Transaction count: {len(recent_transactions)}"],
                weight=self.risk_weights.get("behavioral_risk", 0.2)
            )
        
        # Analyze behavioral deviations
        risk_indicators = []
        risk_score = 0.0
        
        # Check for unusual merchant
        user_merchants = [tx.merchant for tx in recent_transactions]
        if transaction.merchant not in user_merchants:
            risk_indicators.append("Transaction with new merchant")
            risk_score += 0.3
        
        # Check for unusual category
        user_categories = [tx.category for tx in recent_transactions]
        if transaction.category not in user_categories:
            risk_indicators.append("Transaction in new category")
            risk_score += 0.2
        
        # Check for unusual time pattern
        user_hours = [tx.timestamp.hour for tx in recent_transactions]
        common_hours = set(h for h in user_hours if user_hours.count(h) >= 2)
        if transaction.timestamp.hour not in common_hours:
            risk_indicators.append("Transaction at unusual time")
            risk_score += 0.2
        
        if risk_indicators:
            return RiskFactor(
                factor_name="behavioral_risk",
                risk_score=min(1.0, risk_score),
                confidence=0.7,
                description="Behavioral deviations from user's typical patterns",
                evidence=risk_indicators,
                weight=self.risk_weights.get("behavioral_risk", 0.2)
            )
        
        return None
    
    def _assess_velocity_risk(self, transaction: Transaction) -> Optional[RiskFactor]:
        """Assess risk based on transaction velocity."""
        # Get recent transactions for velocity analysis
        recent_transactions = self.memory_manager.get_user_transaction_history(
            transaction.user_id, days_back=1, limit=20
        )
        
        # Count transactions in different time windows
        now = transaction.timestamp
        
        # Last hour
        hour_transactions = [tx for tx in recent_transactions 
                           if (now - tx.timestamp).total_seconds() <= 3600]
        
        # Last 10 minutes
        ten_min_transactions = [tx for tx in recent_transactions 
                              if (now - tx.timestamp).total_seconds() <= 600]
        
        risk_indicators = []
        risk_score = 0.0
        
        if len(ten_min_transactions) >= 3:
            risk_indicators.append(f"{len(ten_min_transactions)} transactions in last 10 minutes")
            risk_score += 0.6
        elif len(hour_transactions) >= 5:
            risk_indicators.append(f"{len(hour_transactions)} transactions in last hour")
            risk_score += 0.4
        
        if risk_indicators:
            return RiskFactor(
                factor_name="velocity_risk",
                risk_score=min(1.0, risk_score),
                confidence=0.8,
                description="High transaction velocity detected",
                evidence=risk_indicators,
                weight=self.risk_weights.get("velocity_risk", 0.05)
            )
        
        return None
    
    def _assess_geographic_risk(self, transaction: Transaction) -> GeographicRisk:
        """Assess geographic risk factors."""
        location = transaction.location
        
        # Base country risk
        country_risk = self.country_risk_scores.get(location.country, 0.5)
        
        # Determine country risk level
        if country_risk >= 0.8:
            country_risk_level = "critical"
        elif country_risk >= 0.6:
            country_risk_level = "high"
        elif country_risk >= 0.3:
            country_risk_level = "medium"
        else:
            country_risk_level = "low"
        
        # Travel pattern analysis
        travel_pattern_risk = self._assess_travel_pattern_risk(transaction)
        
        # IP location mismatch detection
        ip_mismatch = self._detect_ip_location_mismatch(transaction)
        
        # Distance from user's home location
        distance_from_home = self._calculate_distance_from_home(transaction)
        
        # Compile risk factors
        risk_factors = []
        if country_risk >= 0.5:
            risk_factors.append(f"High-risk country: {location.country}")
        if travel_pattern_risk > 0.5:
            risk_factors.append("Unusual travel pattern detected")
        if ip_mismatch:
            risk_factors.append("IP address location mismatch")
        if distance_from_home > 1000:
            risk_factors.append(f"Transaction far from home: {distance_from_home:.0f}km")
        
        # Calculate overall location risk score
        location_risk_score = (
            country_risk * 0.4 +
            travel_pattern_risk * 0.3 +
            (0.3 if ip_mismatch else 0.0) * 0.2 +
            min(1.0, distance_from_home / 5000) * 0.1
        )
        
        return GeographicRisk(
            location_risk_score=min(1.0, location_risk_score),
            country_risk_level=country_risk_level,
            travel_pattern_risk=travel_pattern_risk,
            ip_location_mismatch=ip_mismatch,
            distance_from_home=distance_from_home,
            risk_factors=risk_factors
        )
    
    def _assess_temporal_risk(self, transaction: Transaction) -> TemporalRisk:
        """Assess temporal risk factors."""
        timestamp = transaction.timestamp
        
        # Unusual hour risk
        hour = timestamp.hour
        unusual_hour_risk = 0.0
        
        if 2 <= hour <= 5:  # Late night/early morning
            unusual_hour_risk = 0.7
        elif hour < 7 or hour > 23:  # Very early or very late
            unusual_hour_risk = 0.4
        elif 7 <= hour <= 9 or 17 <= hour <= 19:  # Rush hours
            unusual_hour_risk = 0.1
        else:  # Normal business hours
            unusual_hour_risk = 0.0
        
        # Frequency risk (transactions per day)
        frequency_risk = self._assess_frequency_risk(transaction)
        
        # Velocity risk (rapid successive transactions)
        velocity_risk = self._assess_temporal_velocity_risk(transaction)
        
        # Pattern deviation risk
        pattern_deviation = self._assess_temporal_pattern_deviation(transaction)
        
        # Compile risk factors
        risk_factors = []
        if unusual_hour_risk > 0.5:
            risk_factors.append(f"Transaction at unusual hour: {hour:02d}:00")
        if frequency_risk > 0.5:
            risk_factors.append("High transaction frequency")
        if velocity_risk > 0.5:
            risk_factors.append("Rapid successive transactions")
        if pattern_deviation > 0.5:
            risk_factors.append("Deviation from typical timing patterns")
        
        # Calculate overall temporal risk score
        time_risk_score = (
            unusual_hour_risk * 0.3 +
            frequency_risk * 0.25 +
            velocity_risk * 0.25 +
            pattern_deviation * 0.2
        )
        
        return TemporalRisk(
            time_risk_score=min(1.0, time_risk_score),
            unusual_hour_risk=unusual_hour_risk,
            frequency_risk=frequency_risk,
            velocity_risk=velocity_risk,
            pattern_deviation=pattern_deviation,
            risk_factors=risk_factors
        )
    
    def _perform_cross_reference_checks(self, transaction: Transaction) -> List[CrossReferenceResult]:
        """Perform cross-reference checks against fraud databases."""
        results = []
        
        # IP blacklist check
        ip_result = self._check_ip_blacklist(transaction.ip_address)
        if ip_result:
            results.append(ip_result)
        
        # User watchlist check
        user_result = self._check_user_watchlist(transaction.user_id)
        if user_result:
            results.append(user_result)
        
        # Merchant blacklist check
        merchant_result = self._check_merchant_blacklist(transaction.merchant)
        if merchant_result:
            results.append(merchant_result)
        
        # Device fingerprint check
        if transaction.device_info.fingerprint:
            device_result = self._check_device_blacklist(transaction.device_info.fingerprint)
            if device_result:
                results.append(device_result)
        
        return results
    
    def _calculate_overall_risk_score(self, result: RiskAssessmentResult) -> float:
        """Calculate overall risk score from all risk factors."""
        total_weighted_score = 0.0
        total_weight = 0.0
        
        # Risk factors
        for factor in result.risk_factors:
            weighted_score = factor.risk_score * factor.confidence * factor.weight
            total_weighted_score += weighted_score
            total_weight += factor.weight
        
        # Geographic risk
        if result.geographic_risk:
            geo_weight = self.risk_weights.get("geographic_risk", 0.2)
            total_weighted_score += result.geographic_risk.location_risk_score * geo_weight
            total_weight += geo_weight
        
        # Temporal risk
        if result.temporal_risk:
            temp_weight = self.risk_weights.get("temporal_risk", 0.15)
            total_weighted_score += result.temporal_risk.time_risk_score * temp_weight
            total_weight += temp_weight
        
        # Cross-reference results
        if result.cross_reference_results:
            cross_ref_weight = self.risk_weights.get("cross_reference_risk", 0.15)
            max_cross_ref_risk = max(cr.risk_impact for cr in result.cross_reference_results)
            total_weighted_score += max_cross_ref_risk * cross_ref_weight
            total_weight += cross_ref_weight
        
        # Calculate final score
        if total_weight > 0:
            return min(1.0, total_weighted_score / total_weight)
        else:
            return 0.0
    
    def _determine_risk_level(self, risk_score: float) -> str:
        """Determine risk level based on risk score."""
        thresholds = self.risk_thresholds
        
        if risk_score >= thresholds.get("high", 0.8):
            return "critical" if risk_score >= 0.9 else "high"
        elif risk_score >= thresholds.get("medium", 0.6):
            return "medium"
        elif risk_score >= thresholds.get("low", 0.3):
            return "low"
        else:
            return "minimal"
    
    def _calculate_assessment_confidence(self, result: RiskAssessmentResult) -> float:
        """Calculate confidence in the risk assessment."""
        confidence_factors = []
        
        # Confidence from risk factors
        if result.risk_factors:
            avg_factor_confidence = sum(f.confidence for f in result.risk_factors) / len(result.risk_factors)
            confidence_factors.append(avg_factor_confidence)
        
        # Confidence from geographic assessment
        if result.geographic_risk:
            confidence_factors.append(0.8)  # Geographic data is generally reliable
        
        # Confidence from temporal assessment
        if result.temporal_risk:
            confidence_factors.append(0.7)  # Temporal patterns have moderate reliability
        
        # Confidence from cross-reference checks
        if result.cross_reference_results:
            avg_cross_ref_confidence = sum(cr.match_confidence for cr in result.cross_reference_results) / len(result.cross_reference_results)
            confidence_factors.append(avg_cross_ref_confidence)
        
        if confidence_factors:
            return sum(confidence_factors) / len(confidence_factors)
        else:
            return 0.5  # Default confidence
    
    def _check_threshold_breaches(self, result: RiskAssessmentResult) -> List[str]:
        """Check for risk threshold breaches."""
        breaches = []
        
        # Overall risk threshold
        if result.overall_risk_score >= self.risk_thresholds.get("high", 0.8):
            breaches.append(f"Overall risk score ({result.overall_risk_score:.3f}) exceeds high threshold")
        
        # Individual factor thresholds
        for factor in result.risk_factors:
            if factor.risk_score >= 0.8:
                breaches.append(f"{factor.factor_name} ({factor.risk_score:.3f}) exceeds critical threshold")
        
        # Geographic risk threshold
        if result.geographic_risk and result.geographic_risk.location_risk_score >= 0.7:
            breaches.append(f"Geographic risk ({result.geographic_risk.location_risk_score:.3f}) exceeds threshold")
        
        return breaches
    
    def _generate_risk_recommendations(self, result: RiskAssessmentResult) -> List[str]:
        """Generate risk-based recommendations."""
        recommendations = []
        
        # Overall risk level recommendations
        if result.risk_level in ["critical", "high"]:
            recommendations.append("RECOMMEND: DECLINE transaction due to high risk")
        elif result.risk_level == "medium":
            recommendations.append("RECOMMEND: FLAG for manual review")
        else:
            recommendations.append("RECOMMEND: APPROVE transaction - acceptable risk level")
        
        # Specific risk factor recommendations
        for factor in result.risk_factors:
            if factor.risk_score >= 0.8:
                recommendations.append(f"HIGH RISK: {factor.description}")
        
        # Geographic recommendations
        if result.geographic_risk and result.geographic_risk.country_risk_level in ["high", "critical"]:
            recommendations.append("Consider additional identity verification for high-risk location")
        
        # Cross-reference recommendations
        if result.cross_reference_results:
            for cr in result.cross_reference_results:
                if cr.match_found and cr.risk_impact >= 0.7:
                    recommendations.append(f"ALERT: Match found in {cr.reference_type}")
        
        return recommendations
    
    def _generate_mitigation_suggestions(self, result: RiskAssessmentResult) -> List[str]:
        """Generate risk mitigation suggestions."""
        suggestions = []
        
        # High amount risk mitigation
        amount_factors = [f for f in result.risk_factors if f.factor_name == "amount_risk"]
        if amount_factors and amount_factors[0].risk_score >= 0.6:
            suggestions.append("Consider step-up authentication for high-value transactions")
            suggestions.append("Implement transaction amount limits based on user history")
        
        # Geographic risk mitigation
        if result.geographic_risk and result.geographic_risk.location_risk_score >= 0.5:
            suggestions.append("Require additional location verification")
            suggestions.append("Consider travel notification requirements")
        
        # Velocity risk mitigation
        velocity_factors = [f for f in result.risk_factors if f.factor_name == "velocity_risk"]
        if velocity_factors and velocity_factors[0].risk_score >= 0.5:
            suggestions.append("Implement velocity controls and cooling-off periods")
            suggestions.append("Consider transaction frequency limits")
        
        # Device risk mitigation
        device_factors = [f for f in result.risk_factors if f.factor_name == "device_risk"]
        if device_factors and device_factors[0].risk_score >= 0.5:
            suggestions.append("Require device registration and verification")
            suggestions.append("Implement device fingerprinting")
        
        return suggestions
    
    # Helper methods for risk assessment components
    
    def _assess_travel_pattern_risk(self, transaction: Transaction) -> float:
        """Assess risk based on travel patterns."""
        # Simplified travel pattern analysis
        # In production, this would analyze user's location history
        return 0.2  # Default low travel risk
    
    def _detect_ip_location_mismatch(self, transaction: Transaction) -> bool:
        """Detect mismatch between IP location and transaction location."""
        # Simplified IP geolocation check
        # In production, this would use IP geolocation services
        return False  # Default no mismatch
    
    def _calculate_distance_from_home(self, transaction: Transaction) -> float:
        """Calculate distance from user's home location."""
        # Simplified distance calculation
        # In production, this would use user's registered address
        return 50.0  # Default 50km from home
    
    def _assess_frequency_risk(self, transaction: Transaction) -> float:
        """Assess risk based on transaction frequency."""
        recent_transactions = self.memory_manager.get_user_transaction_history(
            transaction.user_id, days_back=1, limit=10
        )
        
        daily_count = len([tx for tx in recent_transactions 
                          if tx.timestamp.date() == transaction.timestamp.date()])
        
        if daily_count >= 10:
            return 0.8
        elif daily_count >= 5:
            return 0.5
        else:
            return 0.1
    
    def _assess_temporal_velocity_risk(self, transaction: Transaction) -> float:
        """Assess velocity risk in temporal context."""
        recent_transactions = self.memory_manager.get_user_transaction_history(
            transaction.user_id, days_back=1, limit=5
        )
        
        # Check for rapid successive transactions
        if len(recent_transactions) >= 3:
            time_diffs = []
            for i in range(1, len(recent_transactions)):
                diff = (recent_transactions[i-1].timestamp - recent_transactions[i].timestamp).total_seconds()
                time_diffs.append(diff)
            
            avg_interval = sum(time_diffs) / len(time_diffs) if time_diffs else 3600
            
            if avg_interval < 300:  # Less than 5 minutes average
                return 0.8
            elif avg_interval < 900:  # Less than 15 minutes average
                return 0.5
        
        return 0.1
    
    def _assess_temporal_pattern_deviation(self, transaction: Transaction) -> float:
        """Assess deviation from user's typical temporal patterns."""
        # Simplified pattern deviation analysis
        # In production, this would analyze user's historical timing patterns
        return 0.2  # Default low deviation
    
    def _check_ip_blacklist(self, ip_address: str) -> Optional[CrossReferenceResult]:
        """Check IP address against blacklist."""
        if ip_address in self.fraud_indicators["blacklisted_ips"]:
            return CrossReferenceResult(
                reference_type="ip_blacklist",
                match_found=True,
                match_confidence=0.95,
                match_details={"ip_address": ip_address},
                risk_impact=0.9
            )
        return None
    
    def _check_user_watchlist(self, user_id: str) -> Optional[CrossReferenceResult]:
        """Check user against watchlist."""
        if user_id in self.fraud_indicators["watchlist_users"]:
            return CrossReferenceResult(
                reference_type="user_watchlist",
                match_found=True,
                match_confidence=0.9,
                match_details={"user_id": user_id},
                risk_impact=0.8
            )
        return None
    
    def _check_merchant_blacklist(self, merchant: str) -> Optional[CrossReferenceResult]:
        """Check merchant against blacklist."""
        if merchant.lower() in self.fraud_indicators["suspicious_merchants"]:
            return CrossReferenceResult(
                reference_type="merchant_blacklist",
                match_found=True,
                match_confidence=0.85,
                match_details={"merchant": merchant},
                risk_impact=0.7
            )
        return None
    
    def _check_device_blacklist(self, device_fingerprint: str) -> Optional[CrossReferenceResult]:
        """Check device fingerprint against blacklist."""
        # Simplified device check
        # In production, this would check against device fraud databases
        return None
    
    def _initialize_fraud_indicators(self) -> None:
        """Initialize fraud indicators database."""
        # In production, these would be loaded from external fraud databases
        self.fraud_indicators = {
            "blacklisted_ips": {"192.0.2.1", "198.51.100.1", "203.0.113.1"},
            "suspicious_merchants": {"fraud merchant", "scam store", "fake shop"},
            "known_fraud_patterns": [],
            "watchlist_users": {"suspicious_user_001", "flagged_user_002"}
        }
    
    def _initialize_geographic_data(self) -> None:
        """Initialize geographic risk data."""
        # Country risk scores are already initialized in __init__
        # In production, this would load from external geographic risk databases
        pass
    
    def update_risk_thresholds(self, new_thresholds: Dict[str, float]) -> bool:
        """Update risk assessment thresholds."""
        try:
            self.risk_thresholds.update(new_thresholds)
            self.logger.info(f"Updated risk thresholds: {new_thresholds}")
            return True
        except Exception as e:
            self.logger.error(f"Error updating risk thresholds: {str(e)}")
            return False
    
    def get_risk_statistics(self) -> Dict[str, Any]:
        """Get risk assessment statistics."""
        return {
            "risk_thresholds": self.risk_thresholds,
            "risk_weights": self.risk_weights,
            "fraud_indicators_count": {
                "blacklisted_ips": len(self.fraud_indicators["blacklisted_ips"]),
                "suspicious_merchants": len(self.fraud_indicators["suspicious_merchants"]),
                "watchlist_users": len(self.fraud_indicators["watchlist_users"])
            },
            "country_risk_levels": len(self.country_risk_scores)
        }