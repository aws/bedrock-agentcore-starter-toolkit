"""
Transaction Analyzer Agent

Specialized agent for real-time transaction analysis with velocity pattern detection,
comprehensive validation, and streaming support.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import statistics
import re

from .base_agent import BaseAgent, AgentConfiguration, AgentCapability, ProcessingResult
from src.models import Transaction, Location, DeviceInfo, FraudDecision
from src.memory_manager import MemoryManager
from src.context_manager import ContextManager

logger = logging.getLogger(__name__)


@dataclass
class VelocityPattern:
    """Velocity pattern detection result."""
    pattern_type: str
    transaction_count: int
    time_window_minutes: int
    total_amount: Decimal
    risk_score: float
    description: str
    evidence: List[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    """Transaction validation result."""
    is_valid: bool
    validation_errors: List[str] = field(default_factory=list)
    validation_warnings: List[str] = field(default_factory=list)
    risk_indicators: List[str] = field(default_factory=list)


@dataclass
class TransactionAnalysis:
    """Complete transaction analysis result."""
    transaction_id: str
    risk_score: float
    recommendation: str
    confidence: float
    velocity_patterns: List[VelocityPattern] = field(default_factory=list)
    validation_result: Optional[ValidationResult] = None
    contextual_factors: Dict[str, Any] = field(default_factory=dict)
    processing_details: Dict[str, Any] = field(default_factory=dict)


class TransactionAnalyzer(BaseAgent):
    """
    Specialized agent for transaction analysis.
    
    Capabilities:
    - Real-time transaction processing
    - Velocity pattern detection
    - Transaction validation
    - Risk scoring and recommendation
    - Streaming support for high-volume processing
    """
    
    def __init__(
        self, 
        memory_manager: MemoryManager,
        context_manager: ContextManager,
        config: Optional[AgentConfiguration] = None
    ):
        """
        Initialize the Transaction Analyzer Agent.
        
        Args:
            memory_manager: Memory manager for data access
            context_manager: Context manager for contextual analysis
            config: Agent configuration (optional)
        """
        if config is None:
            config = AgentConfiguration(
                agent_id="transaction_analyzer_001",
                agent_name="TransactionAnalyzer",
                version="1.0.0",
                capabilities=[
                    AgentCapability.TRANSACTION_ANALYSIS,
                    AgentCapability.REAL_TIME_PROCESSING,
                    AgentCapability.PATTERN_DETECTION
                ],
                max_concurrent_requests=50,
                timeout_seconds=10,
                custom_parameters={
                    "velocity_window_minutes": 60,
                    "max_velocity_transactions": 10,
                    "high_risk_threshold": 0.7,
                    "medium_risk_threshold": 0.4
                }
            )
        
        self.memory_manager = memory_manager
        self.context_manager = context_manager
        
        # Initialize velocity tracking
        self.velocity_cache = {}  # user_id -> list of recent transactions
        self.cache_cleanup_interval = 300  # 5 minutes
        self.last_cache_cleanup = datetime.now()
        
        super().__init__(config)
    
    def _initialize_agent(self) -> None:
        """Initialize transaction analyzer specific components."""
        self.logger.info("Initializing Transaction Analyzer Agent")
        
        # Initialize validation rules
        self.validation_rules = self._load_validation_rules()
        
        # Initialize risk scoring parameters
        self.risk_weights = {
            "amount_anomaly": 0.25,
            "velocity_risk": 0.30,
            "geographic_risk": 0.20,
            "temporal_risk": 0.15,
            "contextual_risk": 0.10
        }
        
        self.logger.info("Transaction Analyzer Agent initialized successfully")
    
    def process_request(self, request_data: Dict[str, Any]) -> ProcessingResult:
        """
        Process a transaction analysis request.
        
        Args:
            request_data: Dictionary containing transaction data
            
        Returns:
            ProcessingResult with transaction analysis
        """
        try:
            # Extract transaction from request
            transaction = self._extract_transaction(request_data)
            if not transaction:
                return ProcessingResult(
                    success=False,
                    result_data={},
                    processing_time_ms=0.0,
                    confidence_score=0.0,
                    error_message="Invalid transaction data"
                )
            
            # Perform comprehensive analysis
            analysis = self._analyze_transaction(transaction)
            
            # Store transaction in memory system
            self.memory_manager.store_transaction(transaction)
            
            # Update velocity cache
            self._update_velocity_cache(transaction)
            
            return ProcessingResult(
                success=True,
                result_data={
                    "analysis": analysis.__dict__,
                    "transaction_id": transaction.id,
                    "timestamp": datetime.now().isoformat()
                },
                processing_time_ms=0.0,  # Will be set by base class
                confidence_score=analysis.confidence,
                metadata={
                    "agent_type": "transaction_analyzer",
                    "analysis_version": "1.0.0"
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error analyzing transaction: {str(e)}")
            return ProcessingResult(
                success=False,
                result_data={},
                processing_time_ms=0.0,
                confidence_score=0.0,
                error_message=str(e)
            )
    
    def _extract_transaction(self, request_data: Dict[str, Any]) -> Optional[Transaction]:
        """Extract and validate transaction from request data."""
        try:
            # Handle different input formats
            if "transaction" in request_data:
                tx_data = request_data["transaction"]
            else:
                tx_data = request_data
            
            # Create Location object
            location_data = tx_data.get("location", {})
            location = Location(
                country=location_data.get("country", ""),
                city=location_data.get("city", ""),
                latitude=location_data.get("latitude"),
                longitude=location_data.get("longitude"),
                ip_address=location_data.get("ip_address")
            )
            
            # Create DeviceInfo object
            device_data = tx_data.get("device_info", {})
            device_info = DeviceInfo(
                device_id=device_data.get("device_id", ""),
                device_type=device_data.get("device_type", ""),
                os=device_data.get("os", ""),
                browser=device_data.get("browser"),
                fingerprint=device_data.get("fingerprint")
            )
            
            # Create Transaction object
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
    
    def _analyze_transaction(self, transaction: Transaction) -> TransactionAnalysis:
        """Perform comprehensive transaction analysis."""
        analysis_start = datetime.now()
        
        # 1. Validate transaction
        validation_result = self._validate_transaction(transaction)
        
        # 2. Detect velocity patterns
        velocity_patterns = self._detect_velocity_patterns(transaction)
        
        # 3. Get contextual analysis
        contextual_factors = self._get_contextual_factors(transaction)
        
        # 4. Calculate risk score
        risk_score = self._calculate_risk_score(
            transaction, validation_result, velocity_patterns, contextual_factors
        )
        
        # 5. Generate recommendation
        recommendation, confidence = self._generate_recommendation(risk_score, validation_result)
        
        # 6. Create analysis result
        analysis = TransactionAnalysis(
            transaction_id=transaction.id,
            risk_score=risk_score,
            recommendation=recommendation,
            confidence=confidence,
            velocity_patterns=velocity_patterns,
            validation_result=validation_result,
            contextual_factors=contextual_factors,
            processing_details={
                "analysis_duration_ms": (datetime.now() - analysis_start).total_seconds() * 1000,
                "rules_applied": len(self.validation_rules),
                "velocity_patterns_detected": len(velocity_patterns)
            }
        )
        
        return analysis
    
    def _validate_transaction(self, transaction: Transaction) -> ValidationResult:
        """Validate transaction against business rules."""
        errors = []
        warnings = []
        risk_indicators = []
        
        # Basic field validation
        if not transaction.id:
            errors.append("Missing transaction ID")
        
        if not transaction.user_id:
            errors.append("Missing user ID")
        
        if transaction.amount <= 0:
            errors.append("Invalid transaction amount")
        
        if not transaction.merchant:
            warnings.append("Missing merchant information")
        
        # Amount validation
        if transaction.amount > Decimal("10000"):
            risk_indicators.append("High transaction amount")
        
        # Currency validation
        valid_currencies = ["USD", "EUR", "GBP", "CAD", "AUD"]
        if transaction.currency not in valid_currencies:
            warnings.append(f"Unusual currency: {transaction.currency}")
        
        # Merchant validation
        if self._is_high_risk_merchant(transaction.merchant):
            risk_indicators.append("High-risk merchant category")
        
        # Location validation
        if not transaction.location.country:
            warnings.append("Missing location information")
        
        # Device validation
        if not transaction.device_info.device_id:
            warnings.append("Missing device information")
        
        # Time validation
        current_time = datetime.now()
        if transaction.timestamp > current_time + timedelta(minutes=5):
            errors.append("Future transaction timestamp")
        
        if transaction.timestamp < current_time - timedelta(days=30):
            warnings.append("Old transaction timestamp")
        
        # Late night transactions
        if 2 <= transaction.timestamp.hour <= 5:
            risk_indicators.append("Late night transaction")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            validation_errors=errors,
            validation_warnings=warnings,
            risk_indicators=risk_indicators
        )
    
    def _detect_velocity_patterns(self, transaction: Transaction) -> List[VelocityPattern]:
        """Detect velocity-based fraud patterns."""
        patterns = []
        
        # Get recent transactions for this user
        recent_transactions = self._get_recent_user_transactions(transaction.user_id)
        recent_transactions.append(transaction)  # Include current transaction
        
        # Sort by timestamp
        recent_transactions.sort(key=lambda tx: tx.timestamp)
        
        # Detect rapid-fire pattern (multiple transactions in short time)
        rapid_fire = self._detect_rapid_fire_pattern(recent_transactions)
        if rapid_fire:
            patterns.append(rapid_fire)
        
        # Detect escalating amounts pattern
        escalating = self._detect_escalating_amounts_pattern(recent_transactions)
        if escalating:
            patterns.append(escalating)
        
        # Detect geographic velocity pattern
        geo_velocity = self._detect_geographic_velocity_pattern(recent_transactions)
        if geo_velocity:
            patterns.append(geo_velocity)
        
        return patterns
    
    def _detect_rapid_fire_pattern(self, transactions: List[Transaction]) -> Optional[VelocityPattern]:
        """Detect rapid-fire transaction pattern."""
        if len(transactions) < 3:
            return None
        
        # Check for multiple transactions in short time windows
        time_windows = [5, 10, 30, 60]  # minutes
        
        for window_minutes in time_windows:
            window_start = transactions[-1].timestamp - timedelta(minutes=window_minutes)
            window_transactions = [
                tx for tx in transactions 
                if tx.timestamp >= window_start
            ]
            
            if len(window_transactions) >= 4:  # 4+ transactions in window
                total_amount = sum(tx.amount for tx in window_transactions)
                
                # Calculate risk score based on frequency and amounts
                frequency_risk = min(1.0, len(window_transactions) / 10)
                amount_risk = min(1.0, float(total_amount) / 5000)
                risk_score = (frequency_risk + amount_risk) / 2
                
                return VelocityPattern(
                    pattern_type="rapid_fire",
                    transaction_count=len(window_transactions),
                    time_window_minutes=window_minutes,
                    total_amount=total_amount,
                    risk_score=risk_score,
                    description=f"{len(window_transactions)} transactions in {window_minutes} minutes",
                    evidence=[
                        f"Transaction frequency: {len(window_transactions)} in {window_minutes}min",
                        f"Total amount: ${total_amount}",
                        f"Average interval: {window_minutes / len(window_transactions):.1f} minutes"
                    ]
                )
        
        return None
    
    def _detect_escalating_amounts_pattern(self, transactions: List[Transaction]) -> Optional[VelocityPattern]:
        """Detect escalating transaction amounts pattern."""
        if len(transactions) < 3:
            return None
        
        # Check last 5 transactions for escalating pattern
        recent = transactions[-5:]
        amounts = [float(tx.amount) for tx in recent]
        
        # Check if amounts are generally increasing
        increases = 0
        for i in range(1, len(amounts)):
            if amounts[i] > amounts[i-1]:
                increases += 1
        
        if increases >= len(amounts) - 2:  # Most transactions are increasing
            amount_range = max(amounts) - min(amounts)
            risk_score = min(1.0, amount_range / 1000)  # Risk based on range
            
            return VelocityPattern(
                pattern_type="escalating_amounts",
                transaction_count=len(recent),
                time_window_minutes=int((recent[-1].timestamp - recent[0].timestamp).total_seconds() / 60),
                total_amount=Decimal(str(sum(amounts))),
                risk_score=risk_score,
                description=f"Escalating amounts from ${min(amounts):.2f} to ${max(amounts):.2f}",
                evidence=[
                    f"Amount increase: {increases}/{len(amounts)-1} transactions",
                    f"Range: ${min(amounts):.2f} - ${max(amounts):.2f}",
                    f"Total escalation: ${amount_range:.2f}"
                ]
            )
        
        return None
    
    def _detect_geographic_velocity_pattern(self, transactions: List[Transaction]) -> Optional[VelocityPattern]:
        """Detect impossible geographic velocity (travel) pattern."""
        if len(transactions) < 2:
            return None
        
        # Check last few transactions for impossible travel
        for i in range(len(transactions) - 1):
            tx1 = transactions[i]
            tx2 = transactions[i + 1]
            
            # Skip if same location
            if (tx1.location.country == tx2.location.country and 
                tx1.location.city == tx2.location.city):
                continue
            
            # Calculate time difference
            time_diff_hours = (tx2.timestamp - tx1.timestamp).total_seconds() / 3600
            
            # Estimate distance (simplified)
            distance_km = self._estimate_distance(tx1.location, tx2.location)
            
            # Check if travel is impossible (assuming max 1000 km/h)
            if distance_km > 0 and time_diff_hours > 0:
                required_speed = distance_km / time_diff_hours
                
                if required_speed > 1000:  # Impossible speed
                    risk_score = min(1.0, required_speed / 2000)
                    
                    return VelocityPattern(
                        pattern_type="geographic_velocity",
                        transaction_count=2,
                        time_window_minutes=int(time_diff_hours * 60),
                        total_amount=tx1.amount + tx2.amount,
                        risk_score=risk_score,
                        description=f"Impossible travel: {distance_km:.0f}km in {time_diff_hours:.1f}h",
                        evidence=[
                            f"Distance: {distance_km:.0f} km",
                            f"Time: {time_diff_hours:.1f} hours",
                            f"Required speed: {required_speed:.0f} km/h",
                            f"Locations: {tx1.location.city}, {tx1.location.country} → {tx2.location.city}, {tx2.location.country}"
                        ]
                    )
        
        return None
    
    def _get_contextual_factors(self, transaction: Transaction) -> Dict[str, Any]:
        """Get contextual factors for the transaction."""
        try:
            # Get contextual recommendation
            context_rec = self.context_manager.get_contextual_recommendation(transaction)
            
            return {
                "contextual_risk_score": context_rec.get("risk_score", 0.0),
                "contextual_recommendation": context_rec.get("recommendation", "UNKNOWN"),
                "contextual_confidence": context_rec.get("confidence", 0.0),
                "similar_cases_count": context_rec.get("context_summary", {}).get("similar_cases_count", 0),
                "has_user_profile": context_rec.get("context_summary", {}).get("has_user_profile", False)
            }
            
        except Exception as e:
            self.logger.warning(f"Error getting contextual factors: {str(e)}")
            return {}
    
    def _calculate_risk_score(
        self, 
        transaction: Transaction,
        validation_result: ValidationResult,
        velocity_patterns: List[VelocityPattern],
        contextual_factors: Dict[str, Any]
    ) -> float:
        """Calculate overall risk score for the transaction."""
        risk_components = {}
        
        # Validation risk
        validation_risk = 0.0
        if not validation_result.is_valid:
            validation_risk += 0.5
        validation_risk += len(validation_result.risk_indicators) * 0.1
        validation_risk = min(1.0, validation_risk)
        risk_components["validation_risk"] = validation_risk
        
        # Velocity risk
        velocity_risk = 0.0
        if velocity_patterns:
            velocity_risk = max(pattern.risk_score for pattern in velocity_patterns)
        risk_components["velocity_risk"] = velocity_risk
        
        # Amount risk
        amount_risk = 0.0
        if transaction.amount > Decimal("1000"):
            amount_risk = min(1.0, float(transaction.amount) / 10000)
        risk_components["amount_risk"] = amount_risk
        
        # Temporal risk
        temporal_risk = 0.0
        hour = transaction.timestamp.hour
        if 2 <= hour <= 6:  # Late night
            temporal_risk = 0.6
        elif hour < 9 or hour > 22:  # Early morning or late evening
            temporal_risk = 0.3
        risk_components["temporal_risk"] = temporal_risk
        
        # Contextual risk
        contextual_risk = contextual_factors.get("contextual_risk_score", 0.0)
        if contextual_risk < 0:
            contextual_risk = 0.0  # Convert negative (good) scores to 0
        risk_components["contextual_risk"] = contextual_risk
        
        # Calculate weighted risk score
        total_risk = 0.0
        for component, weight in self.risk_weights.items():
            if component in risk_components:
                total_risk += risk_components[component] * weight
        
        return min(1.0, max(0.0, total_risk))
    
    def _generate_recommendation(self, risk_score: float, validation_result: ValidationResult) -> Tuple[str, float]:
        """Generate recommendation and confidence based on risk score."""
        # If validation failed, always decline
        if not validation_result.is_valid:
            return "DECLINE", 0.95
        
        # Risk-based recommendations
        high_threshold = self.config.custom_parameters.get("high_risk_threshold", 0.7)
        medium_threshold = self.config.custom_parameters.get("medium_risk_threshold", 0.4)
        
        if risk_score >= high_threshold:
            return "DECLINE", min(0.95, 0.7 + risk_score * 0.25)
        elif risk_score >= medium_threshold:
            return "FLAG_FOR_REVIEW", 0.75
        else:
            return "APPROVE", min(0.95, 0.8 + (1 - risk_score) * 0.15)
    
    def _get_recent_user_transactions(self, user_id: str) -> List[Transaction]:
        """Get recent transactions for velocity analysis."""
        # Check velocity cache first
        if user_id in self.velocity_cache:
            cached_transactions = self.velocity_cache[user_id]
            # Filter to last hour
            cutoff_time = datetime.now() - timedelta(hours=1)
            return [tx for tx in cached_transactions if tx.timestamp >= cutoff_time]
        
        # Fallback to memory manager
        try:
            return self.memory_manager.get_user_transaction_history(user_id, days_back=1, limit=20)
        except Exception as e:
            self.logger.warning(f"Error getting user transaction history: {str(e)}")
            return []
    
    def _update_velocity_cache(self, transaction: Transaction) -> None:
        """Update velocity cache with new transaction."""
        user_id = transaction.user_id
        
        if user_id not in self.velocity_cache:
            self.velocity_cache[user_id] = []
        
        self.velocity_cache[user_id].append(transaction)
        
        # Keep only last hour of transactions
        cutoff_time = datetime.now() - timedelta(hours=1)
        self.velocity_cache[user_id] = [
            tx for tx in self.velocity_cache[user_id] 
            if tx.timestamp >= cutoff_time
        ]
        
        # Periodic cache cleanup
        if (datetime.now() - self.last_cache_cleanup).total_seconds() > self.cache_cleanup_interval:
            self._cleanup_velocity_cache()
    
    def _cleanup_velocity_cache(self) -> None:
        """Clean up old entries from velocity cache."""
        cutoff_time = datetime.now() - timedelta(hours=2)
        
        for user_id in list(self.velocity_cache.keys()):
            self.velocity_cache[user_id] = [
                tx for tx in self.velocity_cache[user_id] 
                if tx.timestamp >= cutoff_time
            ]
            
            # Remove empty entries
            if not self.velocity_cache[user_id]:
                del self.velocity_cache[user_id]
        
        self.last_cache_cleanup = datetime.now()
        self.logger.debug(f"Cleaned velocity cache, {len(self.velocity_cache)} users remaining")
    
    def _load_validation_rules(self) -> List[Dict[str, Any]]:
        """Load transaction validation rules."""
        return [
            {"name": "required_fields", "type": "field_validation"},
            {"name": "amount_limits", "type": "amount_validation"},
            {"name": "merchant_validation", "type": "merchant_validation"},
            {"name": "temporal_validation", "type": "time_validation"}
        ]
    
    def _is_high_risk_merchant(self, merchant: str) -> bool:
        """Check if merchant is in high-risk category."""
        high_risk_keywords = [
            "casino", "gambling", "crypto", "bitcoin", "forex", 
            "adult", "escort", "pharmacy", "offshore"
        ]
        
        merchant_lower = merchant.lower()
        return any(keyword in merchant_lower for keyword in high_risk_keywords)
    
    def _estimate_distance(self, loc1: Location, loc2: Location) -> float:
        """Estimate distance between two locations (simplified)."""
        # Simple distance estimation based on country/city
        if loc1.country != loc2.country:
            # Different countries - assume significant distance
            return 1000.0  # km
        elif loc1.city != loc2.city:
            # Same country, different cities
            return 200.0  # km
        else:
            # Same city
            return 0.0
    
    def get_velocity_statistics(self) -> Dict[str, Any]:
        """Get velocity cache statistics."""
        total_users = len(self.velocity_cache)
        total_transactions = sum(len(transactions) for transactions in self.velocity_cache.values())
        
        return {
            "cached_users": total_users,
            "cached_transactions": total_transactions,
            "cache_size_mb": len(str(self.velocity_cache)) / (1024 * 1024),
            "last_cleanup": self.last_cache_cleanup.isoformat()
        }