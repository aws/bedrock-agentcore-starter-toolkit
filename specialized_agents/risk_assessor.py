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
from enum import Enum

from .base_agent import BaseAgent, AgentConfiguration, AgentCapability, ProcessingResult
from memory_system.models import Transaction, RiskProfile, RiskLevel, Location, FraudDecision
from memory_system.memory_manager import MemoryManager

logger = logging.getLogger(__name__)


class RiskCategory(Enum):
    """Risk assessment categories."""
    GEOGRAPHIC = "geographic"
    TEMPORAL = "temporal"
    BEHAVIORAL = "behavioral"
    TRANSACTIONAL = "transactional"
    DEVICE = "device"
    NETWORK = "network"


@dataclass
class RiskFactor:
    """Individual risk factor assessment."""
    factor_name: str
    category: RiskCategory
    risk_score: float  # 0-1, higher = more risky
    confidence: float  # 0-1, confidence in assessment
    description: str
    evidence: List[str] = field(default_factory=list)
    weight: float = 1.0  # Importance weight for this factor


@dataclass
class GeographicRiskAssessment:
    """Geographic risk analysis result."""
    location_risk_score: float
    country_risk_level: str  # "low", "medium", "high"
    travel_pattern_anomaly: float
    ip_location_mismatch: bool
    high_risk_jurisdiction: bool
    distance_from_usual: float  # km
    evidence: List[str] = field(default_factory=list)


@dataclass
class TemporalRiskAssessment:
    """Temporal risk analysis result."""
    time_risk_score: float
    unusual_hour: bool
    frequency_anomaly: float
    velocity_risk: float
    time_since_last_transaction: float  # hours
    business_hours_compliance: bool
    evidence: List[str] = field(default_factory=list)


@dataclass
class RiskAssessmentResult:
    """Complete risk assessment result."""
    transaction_id: str
    overall_risk_score: float
    risk_level: RiskLevel
    confidence: float
    risk_factors: List[RiskFactor] = field(default_factory=list)
    geographic_assessment: Optional[GeographicRiskAssessment] = None
    temporal_assessment: Optional[TemporalRiskAssessment] = None
    fraud_indicators: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    risk_threshold_breaches: List[str] = field(default_factory=list)


class RiskAssessor(BaseAgent):
    """
    Specialized agent for comprehensive risk assessment.
    
    Capabilities:
    - Multi-factor risk scoring algorithms
    - Geographic and temporal risk analysis
    - Cross-reference system for known fraud indicators
    - Risk threshold management and adaptation
    - Real-time risk evaluation
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
                    "high_risk_threshold": 0.7,
                    "medium_risk_threshold": 0.4,
                    "geographic_risk_weight": 0.25,
                    "temporal_risk_weight": 0.20,
                    "behavioral_risk_weight": 0.30,
                    "transactional_risk_weight": 0.25
                }
            )
        
        self.memory_manager = memory_manager
        
        # Risk assessment configuration
        self.risk_thresholds = {
            "high": config.custom_parameters.get("high_risk_threshold", 0.7),
            "medium": config.custom_parameters.get("medium_risk_threshold", 0.4)
        }
        
        # Risk factor weights
        self.risk_weights = {
            RiskCategory.GEOGRAPHIC: config.custom_parameters.get("geographic_risk_weight", 0.25),
            RiskCategory.TEMPORAL: config.custom_parameters.get("temporal_risk_weight", 0.20),
            RiskCategory.BEHAVIORAL: config.custom_parameters.get("behavioral_risk_weight", 0.30),
            RiskCategory.TRANSACTIONAL: config.custom_parameters.get("transactional_risk_weight", 0.25)
        }
        
        super().__init__(config)    
    
def _initialize_agent(self) -> None:
        """Initialize risk assessor specific components."""
        self.logger.info("Initializing Risk Assessment Agent")
        
        # Initialize fraud indicator databases
        self._initialize_fraud_indicators()
        
        # Initialize geographic risk data
        self._initialize_geographic_risk_data()
        
        # Initialize risk scoring models
        self._initialize_risk_models()
        
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
            # Extract transaction and parameters
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
            
            # Create transaction object
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
                os=tx_data.get("device_info", {}).get("os", ""),
                browser=tx_data.get("device_info", {}).get("browser"),
                fingerprint=tx_data.get("device_info", {}).get("fingerprint")
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
            risk_level=RiskLevel.LOW,
            confidence=0.0
        )
        
        # 1. Geographic Risk Assessment
        if assessment_type in ["comprehensive", "geographic"]:
            geo_assessment = self._assess_geographic_risk(transaction)
            result.geographic_assessment = geo_assessment
            
            # Add geographic risk factors
            geo_factors = self._extract_geographic_risk_factors(geo_assessment)
            result.risk_factors.extend(geo_factors)
        
        # 2. Temporal Risk Assessment
        if assessment_type in ["comprehensive", "temporal"]:
            temporal_assessment = self._assess_temporal_risk(transaction)
            result.temporal_assessment = temporal_assessment
            
            # Add temporal risk factors
            temporal_factors = self._extract_temporal_risk_factors(temporal_assessment)
            result.risk_factors.extend(temporal_factors)
        
        # 3. Behavioral Risk Assessment
        if assessment_type in ["comprehensive", "behavioral"]:
            behavioral_factors = self._assess_behavioral_risk(transaction)
            result.risk_factors.extend(behavioral_factors)
        
        # 4. Transactional Risk Assessment
        if assessment_type in ["comprehensive", "transactional"]:
            transactional_factors = self._assess_transactional_risk(transaction)
            result.risk_factors.extend(transactional_factors)
        
        # 5. Cross-reference fraud indicators
        fraud_indicators = self._check_fraud_indicators(transaction)
        result.fraud_indicators = fraud_indicators
        
        # 6. Calculate overall risk score
        result.overall_risk_score = self._calculate_overall_risk_score(result.risk_factors)
        
        # 7. Determine risk level
        result.risk_level = self._determine_risk_level(result.overall_risk_score)
        
        # 8. Calculate confidence
        result.confidence = self._calculate_confidence(result.risk_factors)
        
        # 9. Check threshold breaches
        result.risk_threshold_breaches = self._check_threshold_breaches(result)
        
        # 10. Generate recommendations
        result.recommendations = self._generate_risk_recommendations(result)
        
        return result    

def _assess_geographic_risk(self, transaction: Transaction) -> GeographicRiskAssessment:
        """Assess geographic risk factors."""
        location = transaction.location
        
        # Initialize assessment
        assessment = GeographicRiskAssessment(
            location_risk_score=0.0,
            country_risk_level="low",
            travel_pattern_anomaly=0.0,
            ip_location_mismatch=False,
            high_risk_jurisdiction=False,
            distance_from_usual=0.0
        )
        
        # Check country risk level
        country_risk = self._get_country_risk_level(location.country)
        assessment.country_risk_level = country_risk
        
        if country_risk == "high":
            assessment.location_risk_score += 0.6
            assessment.evidence.append(f"High-risk country: {location.country}")
        elif country_risk == "medium":
            assessment.location_risk_score += 0.3
            assessment.evidence.append(f"Medium-risk country: {location.country}")
        
        # Check for high-risk jurisdictions
        if self._is_high_risk_jurisdiction(location.country):
            assessment.high_risk_jurisdiction = True
            assessment.location_risk_score += 0.4
            assessment.evidence.append("Transaction in high-risk jurisdiction")
        
        # Analyze travel patterns
        user_locations = self._get_user_typical_locations(transaction.user_id)
        if user_locations:
            distance = self._calculate_distance_from_usual(location, user_locations)
            assessment.distance_from_usual = distance
            
            if distance > 1000:  # More than 1000km from usual locations
                travel_anomaly = min(1.0, distance / 5000)  # Scale to 0-1
                assessment.travel_pattern_anomaly = travel_anomaly
                assessment.location_risk_score += travel_anomaly * 0.5
                assessment.evidence.append(f"Transaction {distance:.0f}km from usual locations")
        
        # Check IP-location mismatch (simplified)
        if self._detect_ip_location_mismatch(transaction):
            assessment.ip_location_mismatch = True
            assessment.location_risk_score += 0.3
            assessment.evidence.append("IP address doesn't match transaction location")
        
        # Normalize risk score
        assessment.location_risk_score = min(1.0, assessment.location_risk_score)
        
        return assessment
    
def _assess_temporal_risk(self, transaction: Transaction) -> TemporalRiskAssessment:
        """Assess temporal risk factors."""
        timestamp = transaction.timestamp
        
        # Initialize assessment
        assessment = TemporalRiskAssessment(
            time_risk_score=0.0,
            unusual_hour=False,
            frequency_anomaly=0.0,
            velocity_risk=0.0,
            time_since_last_transaction=0.0,
            business_hours_compliance=True
        )
        
        # Check for unusual hours
        hour = timestamp.hour
        if 2 <= hour <= 5:  # Late night/early morning
            assessment.unusual_hour = True
            assessment.time_risk_score += 0.6
            assessment.evidence.append(f"Transaction at unusual hour: {hour:02d}:00")
        elif hour < 8 or hour > 22:  # Very early or very late
            assessment.unusual_hour = True
            assessment.time_risk_score += 0.3
            assessment.evidence.append(f"Transaction outside normal hours: {hour:02d}:00")
        
        # Check business hours compliance
        if not (9 <= hour <= 17):  # Outside business hours
            assessment.business_hours_compliance = False
            assessment.time_risk_score += 0.2
        
        # Analyze transaction frequency
        recent_transactions = self.memory_manager.get_user_transaction_history(
            transaction.user_id, days_back=1, limit=20
        )
        
        if recent_transactions:
            # Calculate time since last transaction
            last_tx_time = max(tx.timestamp for tx in recent_transactions)
            time_diff = (timestamp - last_tx_time).total_seconds() / 3600  # hours
            assessment.time_since_last_transaction = time_diff
            
            # Check for velocity risk (multiple transactions in short time)
            recent_count = len([tx for tx in recent_transactions 
                              if (timestamp - tx.timestamp).total_seconds() < 3600])  # Last hour
            
            if recent_count > 5:
                velocity_risk = min(1.0, recent_count / 10)
                assessment.velocity_risk = velocity_risk
                assessment.time_risk_score += velocity_risk * 0.5
                assessment.evidence.append(f"High velocity: {recent_count} transactions in last hour")
            
            # Check for frequency anomaly
            daily_transactions = len([tx for tx in recent_transactions 
                                    if tx.timestamp.date() == timestamp.date()])
            
            if daily_transactions > 10:
                freq_anomaly = min(1.0, daily_transactions / 20)
                assessment.frequency_anomaly = freq_anomaly
                assessment.time_risk_score += freq_anomaly * 0.4
                assessment.evidence.append(f"High frequency: {daily_transactions} transactions today")
        
        # Normalize risk score
        assessment.time_risk_score = min(1.0, assessment.time_risk_score)
        
        return assessment 
   
def _assess_behavioral_risk(self, transaction: Transaction) -> List[RiskFactor]:
        """Assess behavioral risk factors."""
        risk_factors = []
        
        # Get user profile for behavioral analysis
        user_profile = self.memory_manager.get_user_profile(transaction.user_id)
        
        if user_profile:
            # Check spending pattern deviation
            amount = float(transaction.amount)
            typical_range = user_profile.typical_spending_range
            
            if amount > typical_range.get("max", 0) * 3:
                risk_factors.append(RiskFactor(
                    factor_name="excessive_spending",
                    category=RiskCategory.BEHAVIORAL,
                    risk_score=min(1.0, amount / (typical_range.get("max", 1) * 5)),
                    confidence=0.8,
                    description=f"Amount ${amount:.2f} significantly exceeds typical spending",
                    evidence=[f"Typical max: ${typical_range.get('max', 0):.2f}"],
                    weight=1.2
                ))
            
            # Check merchant familiarity
            if transaction.merchant not in user_profile.frequent_merchants:
                risk_factors.append(RiskFactor(
                    factor_name="unfamiliar_merchant",
                    category=RiskCategory.BEHAVIORAL,
                    risk_score=0.4,
                    confidence=0.6,
                    description=f"Transaction with unfamiliar merchant: {transaction.merchant}",
                    evidence=["Merchant not in user's frequent list"],
                    weight=0.8
                ))
            
            # Check category preference
            if transaction.category not in user_profile.preferred_categories:
                risk_factors.append(RiskFactor(
                    factor_name="unusual_category",
                    category=RiskCategory.BEHAVIORAL,
                    risk_score=0.3,
                    confidence=0.5,
                    description=f"Transaction in unusual category: {transaction.category}",
                    evidence=["Category not in user's preferences"],
                    weight=0.6
                ))
        
        # Check for suspicious behavioral patterns
        if self._detect_suspicious_behavior_patterns(transaction):
            risk_factors.append(RiskFactor(
                factor_name="suspicious_behavior",
                category=RiskCategory.BEHAVIORAL,
                risk_score=0.7,
                confidence=0.8,
                description="Suspicious behavioral patterns detected",
                evidence=["Pattern analysis indicates anomalous behavior"],
                weight=1.5
            ))
        
        return risk_factors
    
def _assess_transactional_risk(self, transaction: Transaction) -> List[RiskFactor]:
        """Assess transactional risk factors."""
        risk_factors = []
        
        # Amount-based risk assessment
        amount = float(transaction.amount)
        
        if amount > 10000:
            risk_factors.append(RiskFactor(
                factor_name="high_value_transaction",
                category=RiskCategory.TRANSACTIONAL,
                risk_score=min(1.0, amount / 50000),
                confidence=0.9,
                description=f"High-value transaction: ${amount:.2f}",
                evidence=[f"Amount exceeds ${10000} threshold"],
                weight=1.3
            ))
        
        # Round number analysis
        if amount % 100 == 0 and amount >= 500:
            risk_factors.append(RiskFactor(
                factor_name="round_number_amount",
                category=RiskCategory.TRANSACTIONAL,
                risk_score=0.3,
                confidence=0.6,
                description="Transaction uses round number amount",
                evidence=[f"Amount is exact multiple of 100: ${amount:.2f}"],
                weight=0.7
            ))
        
        # Currency risk
        if transaction.currency not in ["USD", "EUR", "GBP", "CAD", "AUD"]:
            risk_factors.append(RiskFactor(
                factor_name="unusual_currency",
                category=RiskCategory.TRANSACTIONAL,
                risk_score=0.4,
                confidence=0.7,
                description=f"Transaction in unusual currency: {transaction.currency}",
                evidence=["Currency not commonly used"],
                weight=0.8
            ))
        
        # Merchant category risk
        high_risk_categories = ["gambling", "adult", "cryptocurrency", "money_transfer"]
        if transaction.category.lower() in high_risk_categories:
            risk_factors.append(RiskFactor(
                factor_name="high_risk_category",
                category=RiskCategory.TRANSACTIONAL,
                risk_score=0.8,
                confidence=0.9,
                description=f"Transaction in high-risk category: {transaction.category}",
                evidence=["Category associated with higher fraud risk"],
                weight=1.4
            ))
        
        return risk_factors
    
def _check_fraud_indicators(self, transaction: Transaction) -> List[str]:
        """Cross-reference against known fraud indicators."""
        indicators = []
        
        # Check against fraud indicator database
        fraud_indicators = self.fraud_indicator_db
        
        # Check merchant blacklist
        if transaction.merchant.lower() in fraud_indicators.get("blacklisted_merchants", []):
            indicators.append(f"Merchant on blacklist: {transaction.merchant}")
        
        # Check IP address reputation
        if transaction.ip_address in fraud_indicators.get("suspicious_ips", []):
            indicators.append(f"Suspicious IP address: {transaction.ip_address}")
        
        # Check device fingerprint
        if hasattr(transaction.device_info, 'fingerprint') and transaction.device_info.fingerprint:
            if transaction.device_info.fingerprint in fraud_indicators.get("suspicious_devices", []):
                indicators.append(f"Suspicious device fingerprint")
        
        # Check for known fraud patterns
        if self._matches_known_fraud_pattern(transaction):
            indicators.append("Transaction matches known fraud pattern")
        
        return indicators    
 
def _calculate_overall_risk_score(self, risk_factors: List[RiskFactor]) -> float:
        """Calculate overall risk score from individual risk factors."""
        if not risk_factors:
            return 0.0
        
        # Group risk factors by category
        category_scores = defaultdict(list)
        for factor in risk_factors:
            weighted_score = factor.risk_score * factor.confidence * factor.weight
            category_scores[factor.category].append(weighted_score)
        
        # Calculate category averages
        category_averages = {}
        for category, scores in category_scores.items():
            category_averages[category] = sum(scores) / len(scores)
        
        # Apply category weights
        overall_score = 0.0
        total_weight = 0.0
        
        for category, avg_score in category_averages.items():
            weight = self.risk_weights.get(category, 0.1)
            overall_score += avg_score * weight
            total_weight += weight
        
        # Normalize by total weight
        if total_weight > 0:
            overall_score = overall_score / total_weight
        
        return min(1.0, max(0.0, overall_score))
    
def _determine_risk_level(self, risk_score: float) -> RiskLevel:
        """Determine risk level based on risk score."""
        if risk_score >= self.risk_thresholds["high"]:
            return RiskLevel.HIGH
        elif risk_score >= self.risk_thresholds["medium"]:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
def _calculate_confidence(self, risk_factors: List[RiskFactor]) -> float:
        """Calculate overall confidence in risk assessment."""
        if not risk_factors:
            return 0.5  # Default confidence
        
        # Weight confidence by risk factor importance
        weighted_confidences = []
        for factor in risk_factors:
            weighted_confidence = factor.confidence * factor.weight
            weighted_confidences.append(weighted_confidence)
        
        if weighted_confidences:
            return sum(weighted_confidences) / len(weighted_confidences)
        else:
            return 0.5
    
def _check_threshold_breaches(self, result: RiskAssessmentResult) -> List[str]:
        """Check for risk threshold breaches."""
        breaches = []
        
        # Check overall risk threshold
        if result.overall_risk_score >= self.risk_thresholds["high"]:
            breaches.append(f"High risk threshold breached: {result.overall_risk_score:.3f}")
        elif result.overall_risk_score >= self.risk_thresholds["medium"]:
            breaches.append(f"Medium risk threshold breached: {result.overall_risk_score:.3f}")
        
        # Check category-specific thresholds
        category_scores = defaultdict(list)
        for factor in result.risk_factors:
            category_scores[factor.category].append(factor.risk_score)
        
        for category, scores in category_scores.items():
            avg_score = sum(scores) / len(scores)
            if avg_score > 0.8:
                breaches.append(f"High {category.value} risk: {avg_score:.3f}")
        
        return breaches
    
def _generate_risk_recommendations(self, result: RiskAssessmentResult) -> List[str]:
        """Generate risk-based recommendations."""
        recommendations = []
        
        # Overall risk recommendations
        if result.risk_level == RiskLevel.HIGH:
            recommendations.append("RECOMMEND: DECLINE transaction due to high risk")
        elif result.risk_level == RiskLevel.MEDIUM:
            recommendations.append("RECOMMEND: FLAG for manual review")
        else:
            recommendations.append("RECOMMEND: APPROVE transaction - low risk")
        
        # Specific risk factor recommendations
        high_risk_factors = [f for f in result.risk_factors if f.risk_score > 0.7]
        if high_risk_factors:
            factor_names = [f.factor_name for f in high_risk_factors]
            recommendations.append(f"High-risk factors detected: {', '.join(factor_names)}")
        
        # Geographic recommendations
        if result.geographic_assessment and result.geographic_assessment.location_risk_score > 0.6:
            recommendations.append("Consider additional location verification")
        
        # Temporal recommendations
        if result.temporal_assessment and result.temporal_assessment.velocity_risk > 0.5:
            recommendations.append("Monitor for velocity fraud patterns")
        
        # Fraud indicator recommendations
        if result.fraud_indicators:
            recommendations.append("Cross-reference with fraud database confirmed matches")
        
        return recommendations