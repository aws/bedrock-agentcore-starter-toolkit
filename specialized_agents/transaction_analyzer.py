"""
Transaction Analyzer Agent

Specialized agent for real-time transaction analysis with streaming support,
velocity pattern detection, and comprehensive transaction validation.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque

from .base_agent import BaseSpecializedAgent, AgentConfiguration, AgentCapability, AgentStatus
from memory_system.models import Transaction, FraudDecision, Location, DeviceInfo
from memory_system.memory_manager import MemoryManager
from reasoning_engine.chain_of_thought import ReasoningEngine

logger = logging.getLogger(__name__)


@dataclass
class VelocityWindow:
    """Sliding window for velocity analysis."""
    user_id: str
    transactions: deque = field(default_factory=deque)
    window_size_minutes: int = 60
    max_transactions: int = 100
    
    def add_transaction(self, transaction: Transaction):
        """Add transaction to velocity window."""
        # Remove old transactions outside the window
        cutoff_time = datetime.now() - timedelta(minutes=self.window_size_minutes)
        while self.transactions and self.transactions[0].timestamp < cutoff_time:
            self.transactions.popleft()
        
        # Add new transaction
        self.transactions.append(transaction)
        
        # Limit window size
        if len(self.transactions) > self.max_transactions:
            self.transactions.popleft()
    
    def get_transaction_count(self, minutes: int = None) -> int:
        """Get transaction count in specified time window."""
        if minutes is None:
            return len(self.transactions)
        
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        return sum(1 for tx in self.transactions if tx.timestamp >= cutoff_time)
    
    def get_total_amount(self, minutes: int = None) -> Decimal:
        """Get total transaction amount in specified time window."""
        if minutes is None:
            return sum(tx.amount for tx in self.transactions)
        
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        return sum(tx.amount for tx in self.transactions if tx.timestamp >= cutoff_time)
    
    def get_unique_merchants(self, minutes: int = None) -> int:
        """Get count of unique merchants in specified time window."""
        if minutes is None:
            merchants = {tx.merchant for tx in self.transactions}
        else:
            cutoff_time = datetime.now() - timedelta(minutes=minutes)
            merchants = {tx.merchant for tx in self.transactions if tx.timestamp >= cutoff_time}
        
        return len(merchants)


@dataclass
class TransactionAnalysisResult:
    """Result of transaction analysis."""
    transaction_id: str
    user_id: str
    analysis_timestamp: datetime
    risk_score: float
    decision_recommendation: FraudDecision
    confidence: float
    analysis_details: Dict[str, Any]
    velocity_flags: List[str]
    validation_results: Dict[str, bool]
    processing_time_ms: float
    agent_id: str


class TransactionAnalyzerAgent(BaseSpecializedAgent):
    """
    Specialized agent for transaction analysis.
    
    Capabilities:
    - Real-time transaction processing
    - Velocity pattern detection
    - Transaction validation
    - Streaming support
    - Risk scoring
    """
    
    def __init__(
        self, 
        config: AgentConfiguration,
        memory_manager: MemoryManager,
        reasoning_engine: ReasoningEngine
    ):
        """
        Initialize the Transaction Analyzer Agent.
        
        Args:
            config: Agent configuration
            memory_manager: Memory manager for data access
            reasoning_engine: Reasoning engine for analysis
        """
        super().__init__(config)
        
        self.memory_manager = memory_manager
        self.reasoning_engine = reasoning_engine
        
        # Velocity tracking
        self.velocity_windows: Dict[str, VelocityWindow] = {}
        self.velocity_thresholds = {
            "max_transactions_per_hour": 10,
            "max_transactions_per_10min": 5,
            "max_amount_per_hour": Decimal("5000.00"),
            "max_unique_merchants_per_hour": 5
        }
        
        # Transaction validation rules
        self.validation_rules = {
            "min_amount": Decimal("0.01"),
            "max_amount": Decimal("50000.00"),
            "required_fields": ["id", "user_id", "amount", "merchant", "timestamp"],
            "valid_currencies": ["USD", "EUR", "GBP", "CAD", "AUD"],
            "valid_card_types": ["credit", "debit", "prepaid"]
        }
        
        # Risk scoring weights
        self.risk_weights = {
            "velocity_risk": 0.3,
            "amount_risk": 0.2,
            "location_risk": 0.2,
            "merchant_risk": 0.15,
            "device_risk": 0.1,
            "temporal_risk": 0.05
        }
        
        # Streaming support
        self.stream_buffer = asyncio.Queue(maxsize=1000)
        self.batch_size = 10
        self.batch_timeout_seconds = 5
        
        self.logger.info(f"Transaction Analyzer Agent {self.agent_id} initialized")
    
    async def initialize(self) -> bool:
        """Initialize the transaction analyzer agent."""
        try:
            self.logger.info("Initializing Transaction Analyzer Agent...")
            
            # Test memory manager connection
            if not await self._test_memory_manager():
                raise Exception("Memory manager connection failed")
            
            # Test reasoning engine
            if not await self._test_reasoning_engine():
                raise Exception("Reasoning engine initialization failed")
            
            # Start background tasks
            asyncio.create_task(self._process_stream_buffer())
            asyncio.create_task(self._cleanup_velocity_windows())
            
            self._set_status(AgentStatus.ACTIVE)
            self.logger.info("Transaction Analyzer Agent initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Transaction Analyzer Agent: {str(e)}")
            self._set_status(AgentStatus.ERROR)
            return False
    
    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a transaction analysis request.
        
        Args:
            request: Request containing transaction data
            
        Returns:
            Analysis results
        """
        start_time = time.time()
        self.active_requests += 1
        
        try:
            self._set_status(AgentStatus.BUSY)
            
            # Extract transaction from request
            transaction_data = request.get("transaction")
            if not transaction_data:
                raise ValueError("No transaction data provided")
            
            # Parse transaction
            transaction = self._parse_transaction(transaction_data)
            
            # Perform analysis
            analysis_result = await self._analyze_transaction(transaction)
            
            # Update metrics
            processing_time = (time.time() - start_time) * 1000
            self._update_metrics(processing_time, True)
            
            return {
                "success": True,
                "analysis_result": analysis_result.__dict__,
                "processing_time_ms": processing_time,
                "agent_id": self.agent_id
            }
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            self._update_metrics(processing_time, False, str(e))
            
            self.logger.error(f"Transaction analysis failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "processing_time_ms": processing_time,
                "agent_id": self.agent_id
            }
            
        finally:
            self.active_requests -= 1
            if self.active_requests == 0:
                self._set_status(AgentStatus.ACTIVE)
    
    async def process_stream(self, transaction_stream: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process a stream of transactions for real-time analysis.
        
        Args:
            transaction_stream: List of transaction data
            
        Returns:
            List of analysis results
        """
        try:
            self.logger.info(f"Processing transaction stream with {len(transaction_stream)} transactions")
            
            results = []
            for transaction_data in transaction_stream:
                # Add to stream buffer for batch processing
                await self.stream_buffer.put(transaction_data)
                
                # For immediate processing, analyze directly
                if transaction_data.get("priority") == "high":
                    result = await self.process_request({"transaction": transaction_data})
                    results.append(result)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Stream processing failed: {str(e)}")
            return [{"success": False, "error": str(e)}]
    
    async def _analyze_transaction(self, transaction: Transaction) -> TransactionAnalysisResult:
        """
        Perform comprehensive transaction analysis.
        
        Args:
            transaction: Transaction to analyze
            
        Returns:
            Analysis result
        """
        start_time = time.time()
        
        # Update velocity tracking
        self._update_velocity_tracking(transaction)
        
        # Perform validation
        validation_results = self._validate_transaction(transaction)
        
        # Detect velocity patterns
        velocity_flags = self._detect_velocity_patterns(transaction)
        
        # Calculate risk scores
        risk_scores = await self._calculate_risk_scores(transaction)
        
        # Overall risk score
        overall_risk = sum(
            risk_scores.get(factor, 0) * weight 
            for factor, weight in self.risk_weights.items()
        )
        
        # Determine recommendation
        decision_recommendation, confidence = self._determine_recommendation(
            overall_risk, velocity_flags, validation_results
        )
        
        # Compile analysis details
        analysis_details = {
            "risk_scores": risk_scores,
            "overall_risk_score": overall_risk,
            "velocity_analysis": {
                "transactions_last_hour": self._get_velocity_window(transaction.user_id).get_transaction_count(60),
                "transactions_last_10min": self._get_velocity_window(transaction.user_id).get_transaction_count(10),
                "amount_last_hour": float(self._get_velocity_window(transaction.user_id).get_total_amount(60)),
                "unique_merchants_last_hour": self._get_velocity_window(transaction.user_id).get_unique_merchants(60)
            },
            "validation_summary": {
                "total_checks": len(validation_results),
                "passed_checks": sum(1 for passed in validation_results.values() if passed),
                "failed_checks": sum(1 for passed in validation_results.values() if not passed)
            }
        }
        
        processing_time = (time.time() - start_time) * 1000
        
        return TransactionAnalysisResult(
            transaction_id=transaction.id,
            user_id=transaction.user_id,
            analysis_timestamp=datetime.now(),
            risk_score=overall_risk,
            decision_recommendation=decision_recommendation,
            confidence=confidence,
            analysis_details=analysis_details,
            velocity_flags=velocity_flags,
            validation_results=validation_results,
            processing_time_ms=processing_time,
            agent_id=self.agent_id
        )
    
    def _parse_transaction(self, transaction_data: Dict[str, Any]) -> Transaction:
        """Parse transaction data into Transaction object."""
        try:
            # Parse location
            location_data = transaction_data.get("location", {})
            location = Location(
                country=location_data.get("country", ""),
                city=location_data.get("city", ""),
                latitude=location_data.get("latitude"),
                longitude=location_data.get("longitude"),
                ip_address=location_data.get("ip_address")
            )
            
            # Parse device info
            device_data = transaction_data.get("device_info", {})
            device_info = DeviceInfo(
                device_id=device_data.get("device_id", ""),
                device_type=device_data.get("device_type", ""),
                os=device_data.get("os", ""),
                browser=device_data.get("browser"),
                fingerprint=device_data.get("fingerprint")
            )
            
            # Parse timestamp
            timestamp_str = transaction_data.get("timestamp")
            if isinstance(timestamp_str, str):
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            else:
                timestamp = timestamp_str or datetime.now()
            
            return Transaction(
                id=transaction_data["id"],
                user_id=transaction_data["user_id"],
                amount=Decimal(str(transaction_data["amount"])),
                currency=transaction_data.get("currency", "USD"),
                merchant=transaction_data["merchant"],
                category=transaction_data.get("category", "unknown"),
                location=location,
                timestamp=timestamp,
                card_type=transaction_data.get("card_type", "credit"),
                device_info=device_info,
                ip_address=transaction_data.get("ip_address", ""),
                session_id=transaction_data.get("session_id", ""),
                metadata=transaction_data.get("metadata", {})
            )
            
        except Exception as e:
            raise ValueError(f"Invalid transaction data: {str(e)}")
    
    def _validate_transaction(self, transaction: Transaction) -> Dict[str, bool]:
        """Validate transaction against business rules."""
        results = {}
        
        # Required fields validation
        for field in self.validation_rules["required_fields"]:
            value = getattr(transaction, field, None)
            results[f"has_{field}"] = value is not None and str(value).strip() != ""
        
        # Amount validation
        results["amount_above_minimum"] = transaction.amount >= self.validation_rules["min_amount"]
        results["amount_below_maximum"] = transaction.amount <= self.validation_rules["max_amount"]
        
        # Currency validation
        results["valid_currency"] = transaction.currency in self.validation_rules["valid_currencies"]
        
        # Card type validation
        results["valid_card_type"] = transaction.card_type in self.validation_rules["valid_card_types"]
        
        # Timestamp validation
        now = datetime.now()
        results["timestamp_not_future"] = transaction.timestamp <= now
        results["timestamp_not_too_old"] = transaction.timestamp >= now - timedelta(days=30)
        
        # Location validation
        results["has_location"] = bool(transaction.location.country and transaction.location.city)
        
        # Device validation
        results["has_device_info"] = bool(transaction.device_info.device_id and transaction.device_info.device_type)
        
        return results
    
    def _update_velocity_tracking(self, transaction: Transaction):
        """Update velocity tracking for the user."""
        if transaction.user_id not in self.velocity_windows:
            self.velocity_windows[transaction.user_id] = VelocityWindow(user_id=transaction.user_id)
        
        self.velocity_windows[transaction.user_id].add_transaction(transaction)
    
    def _get_velocity_window(self, user_id: str) -> VelocityWindow:
        """Get velocity window for user."""
        if user_id not in self.velocity_windows:
            self.velocity_windows[user_id] = VelocityWindow(user_id=user_id)
        return self.velocity_windows[user_id]
    
    def _detect_velocity_patterns(self, transaction: Transaction) -> List[str]:
        """Detect velocity-based fraud patterns."""
        flags = []
        window = self._get_velocity_window(transaction.user_id)
        
        # Check transaction count thresholds
        if window.get_transaction_count(60) > self.velocity_thresholds["max_transactions_per_hour"]:
            flags.append("excessive_transactions_per_hour")
        
        if window.get_transaction_count(10) > self.velocity_thresholds["max_transactions_per_10min"]:
            flags.append("excessive_transactions_per_10min")
        
        # Check amount thresholds
        if window.get_total_amount(60) > self.velocity_thresholds["max_amount_per_hour"]:
            flags.append("excessive_amount_per_hour")
        
        # Check merchant diversity
        if window.get_unique_merchants(60) > self.velocity_thresholds["max_unique_merchants_per_hour"]:
            flags.append("excessive_merchant_diversity")
        
        # Check for rapid-fire pattern (multiple transactions in very short time)
        recent_count = window.get_transaction_count(2)  # Last 2 minutes
        if recent_count >= 3:
            flags.append("rapid_fire_pattern")
        
        return flags
    
    async def _calculate_risk_scores(self, transaction: Transaction) -> Dict[str, float]:
        """Calculate risk scores for different factors."""
        risk_scores = {}
        
        # Velocity risk
        window = self._get_velocity_window(transaction.user_id)
        velocity_score = min(1.0, window.get_transaction_count(60) / self.velocity_thresholds["max_transactions_per_hour"])
        risk_scores["velocity_risk"] = velocity_score
        
        # Amount risk
        amount_score = min(1.0, float(transaction.amount) / float(self.validation_rules["max_amount"]))
        risk_scores["amount_risk"] = amount_score
        
        # Location risk (simplified - would use geolocation services in production)
        location_risk = 0.1  # Default low risk
        if not transaction.location.country or transaction.location.country == "XX":
            location_risk = 0.8  # High risk for unknown countries
        risk_scores["location_risk"] = location_risk
        
        # Merchant risk (simplified - would use merchant reputation database)
        merchant_risk = 0.1  # Default low risk
        high_risk_keywords = ["casino", "gambling", "crypto", "bitcoin"]
        if any(keyword in transaction.merchant.lower() for keyword in high_risk_keywords):
            merchant_risk = 0.7
        risk_scores["merchant_risk"] = merchant_risk
        
        # Device risk
        device_risk = 0.1  # Default low risk
        if not transaction.device_info.device_id or transaction.device_info.device_id == "unknown":
            device_risk = 0.6
        risk_scores["device_risk"] = device_risk
        
        # Temporal risk (time of day)
        hour = transaction.timestamp.hour
        if 2 <= hour <= 6:  # Late night/early morning
            temporal_risk = 0.6
        elif 22 <= hour <= 23 or 0 <= hour <= 1:  # Late evening/night
            temporal_risk = 0.3
        else:
            temporal_risk = 0.1
        risk_scores["temporal_risk"] = temporal_risk
        
        return risk_scores
    
    def _determine_recommendation(
        self, 
        risk_score: float, 
        velocity_flags: List[str], 
        validation_results: Dict[str, bool]
    ) -> Tuple[FraudDecision, float]:
        """Determine fraud decision recommendation and confidence."""
        
        # Check for validation failures
        critical_validations = ["has_id", "has_user_id", "has_amount", "amount_above_minimum"]
        validation_failures = [
            check for check in critical_validations 
            if not validation_results.get(check, False)
        ]
        
        if validation_failures:
            return FraudDecision.DECLINED, 0.95
        
        # Check for high-risk velocity patterns
        high_risk_flags = ["rapid_fire_pattern", "excessive_transactions_per_10min"]
        if any(flag in velocity_flags for flag in high_risk_flags):
            return FraudDecision.DECLINED, 0.85
        
        # Risk-based decision
        if risk_score >= 0.8:
            return FraudDecision.DECLINED, 0.9
        elif risk_score >= 0.6:
            return FraudDecision.FLAGGED, 0.75
        elif risk_score >= 0.4:
            return FraudDecision.REVIEW_REQUIRED, 0.6
        else:
            return FraudDecision.APPROVED, 0.8
    
    async def _process_stream_buffer(self):
        """Background task to process streaming transactions in batches."""
        while True:
            try:
                batch = []
                timeout_start = time.time()
                
                # Collect batch
                while len(batch) < self.batch_size and (time.time() - timeout_start) < self.batch_timeout_seconds:
                    try:
                        transaction_data = await asyncio.wait_for(
                            self.stream_buffer.get(), 
                            timeout=1.0
                        )
                        batch.append(transaction_data)
                    except asyncio.TimeoutError:
                        break
                
                # Process batch if not empty
                if batch:
                    self.logger.info(f"Processing batch of {len(batch)} transactions")
                    for transaction_data in batch:
                        try:
                            await self.process_request({"transaction": transaction_data})
                        except Exception as e:
                            self.logger.error(f"Failed to process transaction in batch: {str(e)}")
                
                # Small delay to prevent busy waiting
                await asyncio.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"Stream buffer processing error: {str(e)}")
                await asyncio.sleep(1)
    
    async def _cleanup_velocity_windows(self):
        """Background task to cleanup old velocity windows."""
        while True:
            try:
                current_time = datetime.now()
                cleanup_threshold = current_time - timedelta(hours=2)
                
                # Remove old velocity windows
                users_to_remove = []
                for user_id, window in self.velocity_windows.items():
                    if window.transactions and window.transactions[-1].timestamp < cleanup_threshold:
                        users_to_remove.append(user_id)
                
                for user_id in users_to_remove:
                    del self.velocity_windows[user_id]
                    self.logger.debug(f"Cleaned up velocity window for user {user_id}")
                
                # Sleep for 10 minutes before next cleanup
                await asyncio.sleep(600)
                
            except Exception as e:
                self.logger.error(f"Velocity window cleanup error: {str(e)}")
                await asyncio.sleep(60)
    
    async def _test_memory_manager(self) -> bool:
        """Test memory manager connectivity."""
        try:
            # Simple test - this would be more comprehensive in production
            return self.memory_manager is not None
        except Exception as e:
            self.logger.error(f"Memory manager test failed: {str(e)}")
            return False
    
    async def _test_reasoning_engine(self) -> bool:
        """Test reasoning engine connectivity."""
        try:
            # Simple test - this would be more comprehensive in production
            return self.reasoning_engine is not None
        except Exception as e:
            self.logger.error(f"Reasoning engine test failed: {str(e)}")
            return False
    
    async def shutdown(self) -> bool:
        """Shutdown the transaction analyzer agent."""
        try:
            self.logger.info("Shutting down Transaction Analyzer Agent...")
            
            self._set_status(AgentStatus.SHUTDOWN)
            
            # Wait for active requests to complete
            timeout = 30  # 30 seconds timeout
            start_time = time.time()
            while self.active_requests > 0 and (time.time() - start_time) < timeout:
                await asyncio.sleep(0.1)
            
            # Clear velocity windows
            self.velocity_windows.clear()
            
            # Clear stream buffer
            while not self.stream_buffer.empty():
                try:
                    self.stream_buffer.get_nowait()
                except asyncio.QueueEmpty:
                    break
            
            self.logger.info("Transaction Analyzer Agent shutdown complete")
            return True
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {str(e)}")
            return False