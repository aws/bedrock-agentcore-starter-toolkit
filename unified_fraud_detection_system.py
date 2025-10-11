#!/usr/bin/env python3
"""
Unified Fraud Detection System

Integrates all components into a cohesive system:
- Agent Orchestrator with specialized agents
- Reasoning Engine with memory system
- External tools integration
- Streaming processor with event response
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

# Import core components
from aws_bedrock_agent.agent_orchestrator import (
    AgentOrchestrator, Transaction as OrchestratorTransaction, 
    FraudDecision as OrchestratorDecision
)
from specialized_agents.transaction_analyzer import TransactionAnalyzer
from specialized_agents.pattern_detector import PatternDetector
from specialized_agents.risk_assessor import RiskAssessor
from specialized_agents.compliance_agent import ComplianceAgent
from reasoning_engine.adaptive_reasoning import AdaptiveReasoningEngine, LearningMode
from memory_system.memory_manager import MemoryManager
from memory_system.context_manager import ContextManager
from memory_system.pattern_learning import PatternLearningEngine
from external_tools.tool_integrator import ToolIntegrator
from external_tools.identity_verification import IdentityVerificationTool
from external_tools.fraud_database import FraudDatabaseTool
from external_tools.geolocation_services import GeolocationTool
from streaming.transaction_stream_processor import TransactionStreamProcessor, StreamingFraudDetector
from streaming.event_response_system import EventResponseSystem

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SystemConfiguration:
    """Configuration for the unified system."""
    region_name: str = "us-east-1"
    enable_streaming: bool = True
    enable_adaptive_reasoning: bool = True
    enable_external_tools: bool = True
    max_stream_workers: int = 10
    enable_auto_scaling: bool = True
    dynamodb_endpoint: Optional[str] = None


class UnifiedFraudDetectionSystem:
    """
    Unified fraud detection system integrating all components.
    
    Architecture:
    - Agent Orchestrator coordinates specialized agents
    - Reasoning Engine provides adaptive analysis
    - Memory System stores context and learns patterns
    - External Tools provide additional data sources
    - Streaming Processor handles real-time transactions
    """
    
    def __init__(self, config: SystemConfiguration = None):
        """Initialize the unified system."""
        self.config = config or SystemConfiguration()
        logger.info("Initializing Unified Fraud Detection System")
        
        # Initialize memory and learning systems
        self._initialize_memory_systems()
        
        # Initialize reasoning engine
        self._initialize_reasoning_engine()
        
        # Initialize specialized agents
        self._initialize_specialized_agents()
        
        # Initialize agent orchestrator
        self._initialize_orchestrator()
        
        # Initialize external tools
        if self.config.enable_external_tools:
            self._initialize_external_tools()
        
        # Initialize streaming processor
        if self.config.enable_streaming:
            self._initialize_streaming()
        
        logger.info("Unified Fraud Detection System initialized successfully")
    
    def _initialize_memory_systems(self):
        """Initialize memory manager and related systems."""
        logger.info("Initializing memory systems")
        
        # Initialize memory manager with DynamoDB
        self.memory_manager = MemoryManager(
            region_name=self.config.region_name,
            endpoint_url=self.config.dynamodb_endpoint
        )
        
        # Initialize context manager
        self.context_manager = ContextManager(self.memory_manager)
        
        # Initialize pattern learning engine
        self.pattern_learning_engine = PatternLearningEngine(self.memory_manager)
        
        logger.info("Memory systems initialized")
    
    def _initialize_reasoning_engine(self):
        """Initialize adaptive reasoning engine."""
        if not self.config.enable_adaptive_reasoning:
            self.reasoning_engine = None
            return
        
        logger.info("Initializing adaptive reasoning engine")
        
        self.reasoning_engine = AdaptiveReasoningEngine(
            learning_mode=LearningMode.HYBRID_LEARNING
        )
        
        logger.info("Adaptive reasoning engine initialized")
    
    def _initialize_specialized_agents(self):
        """Initialize all specialized agents."""
        logger.info("Initializing specialized agents")
        
        # Transaction Analyzer Agent
        self.transaction_analyzer = TransactionAnalyzer(
            memory_manager=self.memory_manager,
            context_manager=self.context_manager
        )
        
        # Pattern Detection Agent
        self.pattern_detector = PatternDetector(
            memory_manager=self.memory_manager,
            pattern_learning_engine=self.pattern_learning_engine
        )
        
        # Risk Assessment Agent
        self.risk_assessor = RiskAssessor(
            memory_manager=self.memory_manager
        )
        
        # Compliance Agent
        self.compliance_agent = ComplianceAgent(
            memory_manager=self.memory_manager
        )
        
        logger.info("Specialized agents initialized")
    
    def _initialize_orchestrator(self):
        """Initialize agent orchestrator."""
        logger.info("Initializing agent orchestrator")
        
        self.orchestrator = AgentOrchestrator(
            region_name=self.config.region_name
        )
        
        # Wire specialized agents to orchestrator
        self.orchestrator.specialized_agents = {
            "transaction_analyzer": self.transaction_analyzer,
            "pattern_detector": self.pattern_detector,
            "risk_assessor": self.risk_assessor,
            "compliance_agent": self.compliance_agent
        }
        
        logger.info("Agent orchestrator initialized and wired to specialized agents")
    
    def _initialize_external_tools(self):
        """Initialize external tool integrations."""
        logger.info("Initializing external tools")
        
        # Initialize tool integrator
        self.tool_integrator = ToolIntegrator()
        
        # Initialize and register identity verification tool
        self.identity_verification = IdentityVerificationTool()
        self.tool_integrator.register_tool(self.identity_verification)
        
        # Initialize and register fraud database tool
        self.fraud_database = FraudDatabaseTool()
        self.tool_integrator.register_tool(self.fraud_database)
        
        # Initialize and register geolocation tool
        self.geolocation_tool = GeolocationTool()
        self.tool_integrator.register_tool(self.geolocation_tool)
        
        # Wire tools to agents
        self.transaction_analyzer.tool_integrator = self.tool_integrator
        self.risk_assessor.tool_integrator = self.tool_integrator
        
        logger.info("External tools initialized and integrated")
    
    def _initialize_streaming(self):
        """Initialize streaming processor and event response system."""
        logger.info("Initializing streaming processor")
        
        # Initialize stream processor
        self.stream_processor = TransactionStreamProcessor(
            max_workers=self.config.max_stream_workers,
            queue_size=10000,
            batch_size=100
        )
        
        # Initialize streaming fraud detector
        self.streaming_detector = StreamingFraudDetector()
        
        # Set fraud detector for stream processor
        self.stream_processor.set_fraud_detector(self.streaming_detector.detect_fraud)
        
        # Initialize event response system
        self.event_response_system = EventResponseSystem()
        
        # Wire event handlers
        self.stream_processor.add_result_handler(self._handle_stream_result)
        self.stream_processor.add_error_handler(self._handle_stream_error)
        
        logger.info("Streaming processor initialized")
    
    def _handle_stream_result(self, result):
        """Handle streaming processing result."""
        try:
            # Trigger event response for high-risk transactions
            if result.risk_score >= 0.7:
                self.event_response_system.trigger_event({
                    "event_type": "high_risk_transaction",
                    "transaction_id": result.transaction_id,
                    "risk_score": result.risk_score,
                    "decision": result.decision,
                    "timestamp": result.timestamp.isoformat()
                })
            
            logger.debug(f"Processed stream result for {result.transaction_id}")
        except Exception as e:
            logger.error(f"Error handling stream result: {str(e)}")
    
    def _handle_stream_error(self, error, transaction):
        """Handle streaming processing error."""
        logger.error(f"Stream processing error for {transaction.transaction_id}: {str(error)}")
        
        # Log error event
        try:
            self.event_response_system.trigger_event({
                "event_type": "processing_error",
                "transaction_id": transaction.transaction_id,
                "error": str(error),
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Error logging stream error: {str(e)}")
    
    def process_transaction(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a transaction through the unified system.
        
        Args:
            transaction_data: Transaction data dictionary
            
        Returns:
            Complete fraud detection result
        """
        try:
            logger.info(f"Processing transaction {transaction_data.get('id')}")
            
            # Convert to orchestrator transaction format
            transaction = self._convert_to_orchestrator_transaction(transaction_data)
            
            # Use adaptive reasoning to select strategy if enabled
            if self.reasoning_engine:
                strategy, strategy_config = self.reasoning_engine.select_reasoning_strategy(
                    transaction_data, 
                    context={"system": "unified"}
                )
                logger.info(f"Selected reasoning strategy: {strategy.value}")
            
            # Process through orchestrator (coordinates all agents)
            orchestrator_result = self.orchestrator.process_transaction(transaction)
            
            # Get contextual analysis from memory system
            context_recommendation = self.context_manager.get_contextual_recommendation(transaction)
            
            # Combine results
            unified_result = {
                "transaction_id": transaction.id,
                "timestamp": datetime.now().isoformat(),
                "decision": orchestrator_result.recommended_action,
                "is_fraud": orchestrator_result.is_fraud,
                "confidence_score": orchestrator_result.confidence_score,
                "risk_level": orchestrator_result.risk_level,
                "reasoning": orchestrator_result.reasoning,
                "evidence": orchestrator_result.evidence,
                "contextual_analysis": context_recommendation,
                "processing_metadata": {
                    "agents_used": ["transaction_analyzer", "pattern_detector", "risk_assessor", "compliance_agent"],
                    "reasoning_strategy": strategy.value if self.reasoning_engine else "default",
                    "external_tools_used": self._get_tools_used() if self.config.enable_external_tools else []
                }
            }
            
            # Store decision context in memory
            self._store_decision_context(transaction, unified_result)
            
            logger.info(f"Transaction {transaction.id} processed: {unified_result['decision']}")
            return unified_result
            
        except Exception as e:
            logger.error(f"Error processing transaction: {str(e)}")
            return {
                "transaction_id": transaction_data.get('id', 'unknown'),
                "error": str(e),
                "decision": "REVIEW",
                "is_fraud": True,
                "confidence_score": 0.0,
                "timestamp": datetime.now().isoformat()
            }
    
    def process_transaction_stream(self, transaction_data: Dict[str, Any]) -> bool:
        """
        Process transaction through streaming pipeline.
        
        Args:
            transaction_data: Transaction data dictionary
            
        Returns:
            True if successfully queued for processing
        """
        if not self.config.enable_streaming:
            logger.warning("Streaming is not enabled")
            return False
        
        try:
            from streaming.transaction_stream_processor import Transaction as StreamTransaction
            
            # Convert to stream transaction format
            stream_transaction = StreamTransaction.from_dict(transaction_data)
            
            # Submit to stream processor
            success = self.stream_processor.process_transaction(stream_transaction)
            
            if success:
                logger.info(f"Transaction {stream_transaction.transaction_id} queued for stream processing")
            
            return success
            
        except Exception as e:
            logger.error(f"Error queuing transaction for streaming: {str(e)}")
            return False
    
    def start_streaming(self):
        """Start the streaming processor."""
        if not self.config.enable_streaming:
            logger.warning("Streaming is not enabled")
            return
        
        logger.info("Starting streaming processor")
        self.stream_processor.start()
        logger.info("Streaming processor started")
    
    def stop_streaming(self):
        """Stop the streaming processor."""
        if not self.config.enable_streaming:
            return
        
        logger.info("Stopping streaming processor")
        self.stream_processor.stop()
        logger.info("Streaming processor stopped")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        status = {
            "system": "Unified Fraud Detection System",
            "timestamp": datetime.now().isoformat(),
            "configuration": {
                "region": self.config.region_name,
                "streaming_enabled": self.config.enable_streaming,
                "adaptive_reasoning_enabled": self.config.enable_adaptive_reasoning,
                "external_tools_enabled": self.config.enable_external_tools
            },
            "components": {}
        }
        
        # Orchestrator status
        status["components"]["orchestrator"] = self.orchestrator.get_agent_status()
        
        # Specialized agents status
        status["components"]["agents"] = {
            "transaction_analyzer": self.transaction_analyzer.get_status(),
            "pattern_detector": self.pattern_detector.get_status(),
            "risk_assessor": self.risk_assessor.get_status(),
            "compliance_agent": self.compliance_agent.get_status()
        }
        
        # Reasoning engine status
        if self.reasoning_engine:
            status["components"]["reasoning_engine"] = self.reasoning_engine.get_adaptation_statistics()
        
        # External tools status
        if self.config.enable_external_tools:
            status["components"]["external_tools"] = self.tool_integrator.get_all_tools_status()
        
        # Streaming status
        if self.config.enable_streaming:
            status["components"]["streaming"] = self.stream_processor.get_status()
        
        return status
    
    def _convert_to_orchestrator_transaction(self, transaction_data: Dict[str, Any]) -> OrchestratorTransaction:
        """Convert transaction data to orchestrator format."""
        return OrchestratorTransaction(
            id=transaction_data.get('id', ''),
            user_id=transaction_data.get('user_id', ''),
            amount=float(transaction_data.get('amount', 0)),
            currency=transaction_data.get('currency', 'USD'),
            merchant=transaction_data.get('merchant', ''),
            category=transaction_data.get('category', ''),
            location=transaction_data.get('location', ''),
            timestamp=transaction_data.get('timestamp', datetime.now().isoformat()),
            card_type=transaction_data.get('card_type', ''),
            device_info=transaction_data.get('device_info'),
            ip_address=transaction_data.get('ip_address'),
            session_id=transaction_data.get('session_id'),
            metadata=transaction_data.get('metadata')
        )
    
    def _get_tools_used(self) -> List[str]:
        """Get list of external tools that were used."""
        tools_used = []
        
        if hasattr(self, 'identity_verification'):
            tools_used.append("identity_verification")
        if hasattr(self, 'fraud_database'):
            tools_used.append("fraud_database")
        if hasattr(self, 'geolocation_tool'):
            tools_used.append("geolocation")
        
        return tools_used
    
    def _store_decision_context(self, transaction, result: Dict[str, Any]):
        """Store decision context in memory system."""
        try:
            from memory_system.models import DecisionContext, FraudDecision as MemoryFraudDecision
            
            # Map decision to enum
            decision_map = {
                "APPROVE": MemoryFraudDecision.APPROVED,
                "BLOCK": MemoryFraudDecision.DECLINED,
                "DECLINE": MemoryFraudDecision.DECLINED,
                "FLAG": MemoryFraudDecision.FLAGGED,
                "REVIEW": MemoryFraudDecision.FLAGGED
            }
            
            decision_enum = decision_map.get(result['decision'], MemoryFraudDecision.FLAGGED)
            
            context = DecisionContext(
                transaction_id=transaction.id,
                user_id=transaction.user_id,
                decision=decision_enum,
                confidence_score=result['confidence_score'],
                reasoning_steps=[result['reasoning']],
                evidence=result['evidence'],
                timestamp=datetime.now(),
                processing_time_ms=0.0,
                agent_version="unified_system_1.0",
                external_tools_used=result['processing_metadata'].get('external_tools_used', [])
            )
            
            self.memory_manager.store_decision_context(context)
            logger.debug(f"Stored decision context for transaction {transaction.id}")
            
        except Exception as e:
            logger.error(f"Error storing decision context: {str(e)}")


def main():
    """Example usage of the unified system."""
    # Initialize system
    config = SystemConfiguration(
        region_name="us-east-1",
        enable_streaming=True,
        enable_adaptive_reasoning=True,
        enable_external_tools=True,
        max_stream_workers=5
    )
    
    system = UnifiedFraudDetectionSystem(config)
    
    # Example transaction
    transaction_data = {
        "id": "txn_12345",
        "user_id": "user_001",
        "amount": 1500.00,
        "currency": "USD",
        "merchant": "Online Store",
        "category": "retail",
        "location": "NEW_YORK_NY",
        "timestamp": datetime.now().isoformat(),
        "card_type": "credit",
        "device_info": {"device_id": "device_001", "device_type": "mobile", "os": "iOS"},
        "ip_address": "192.168.1.1",
        "session_id": "session_001",
        "metadata": {}
    }
    
    # Process transaction
    result = system.process_transaction(transaction_data)
    print(f"Transaction Result: {result}")
    
    # Get system status
    status = system.get_system_status()
    print(f"System Status: {status}")


if __name__ == "__main__":
    main()
