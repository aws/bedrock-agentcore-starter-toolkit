"""
Fraud Detection System

A comprehensive fraud detection system with AI agents, memory management,
adaptive reasoning, and real-time streaming capabilities.
"""

__version__ = "1.0.0"
__author__ = "Fraud Detection Team"
__all__ = [
    # Version info
    "__version__",
    "__author__",
    
    # Core classes
    "FraudDetectionAgent",
    "UnifiedFraudDetectionSystem",
    "SystemConfiguration",
    "TransactionProcessingPipeline",
    "TransactionPreprocessor",
    "FraudDetectionClient",
    "Transaction",
    "FraudCriteria",
    "ValidationStatus",
    "ValidationResult",
    "ProcessingResult",
    
    # Memory classes
    "MemoryManager",
    "ContextManager",
    "PatternLearningEngine",
    "ContextualInsight",
    "PatternMetrics",
    "LearningFeedback",
    "FraudDecision",
    "RiskLevel",
    "DecisionContext",
    "UserBehaviorProfile",
    "FraudPattern",
    "RiskProfile",
    
    # Reasoning classes
    "ExplanationGenerator",
    "DecisionExplanationInterface",
    "ConfidenceScorer",
    "ExplanationValidator",
    "ReasoningTrailFormatter",
    "ExplanationStyle",
    "ExplanationLevel",
    "ExplanationReport",
    "DecisionExplanation",
    "ConfidenceAssessment",
    "ReasoningTrail",
    "ValidationCriteria",
]

# Core fraud detection
# NOTE: Some imports may fail due to external dependencies that need to be reorganized
# TODO: Fix import paths for currency_converter and infrastructure modules

try:
    from fraud_detection.core.fraud_detection_agent import (
        FraudDetectionAgent,
        Transaction,
        FraudCriteria,
    )
except (ModuleNotFoundError, ImportError):
    FraudDetectionAgent = None
    Transaction = None
    FraudCriteria = None

try:
    from fraud_detection.core.unified_fraud_detection_system import (
        UnifiedFraudDetectionSystem,
        SystemConfiguration,
    )
except (ModuleNotFoundError, ImportError):
    UnifiedFraudDetectionSystem = None
    SystemConfiguration = None

try:
    from fraud_detection.core.transaction_processing_pipeline import (
        TransactionProcessingPipeline,
        TransactionPreprocessor,
        ValidationStatus,
        ValidationResult,
        ProcessingResult,
    )
except (ModuleNotFoundError, ImportError):
    TransactionProcessingPipeline = None
    TransactionPreprocessor = None
    ValidationStatus = None
    ValidationResult = None
    ProcessingResult = None

try:
    from fraud_detection.core.fraud_detection_api import (
        FraudDetectionClient,
    )
except (ModuleNotFoundError, ImportError):
    FraudDetectionClient = None

# Memory management
try:
    from fraud_detection.memory.memory_manager import MemoryManager
except (ModuleNotFoundError, ImportError):
    MemoryManager = None

try:
    from fraud_detection.memory.context_manager import (
        ContextManager,
        ContextualInsight,
    )
except (ModuleNotFoundError, ImportError):
    ContextManager = None
    ContextualInsight = None

try:
    from fraud_detection.memory.pattern_learning import (
        PatternLearningEngine,
        PatternMetrics,
        LearningFeedback,
    )
except (ModuleNotFoundError, ImportError):
    PatternLearningEngine = None
    PatternMetrics = None
    LearningFeedback = None

try:
    from fraud_detection.memory.models import (
        FraudDecision,
        RiskLevel,
        DecisionContext,
        UserBehaviorProfile,
        FraudPattern,
        RiskProfile,
    )
except (ModuleNotFoundError, ImportError):
    FraudDecision = None
    RiskLevel = None
    DecisionContext = None
    UserBehaviorProfile = None
    FraudPattern = None
    RiskProfile = None

# Reasoning engine
try:
    from fraud_detection.reasoning.explanation_generator import (
        ExplanationGenerator,
        ExplanationStyle,
        ExplanationLevel,
        ExplanationReport,
    )
except (ModuleNotFoundError, ImportError):
    ExplanationGenerator = None
    ExplanationStyle = None
    ExplanationLevel = None
    ExplanationReport = None

try:
    from fraud_detection.reasoning.decision_explanation_interface import (
        DecisionExplanationInterface,
        DecisionExplanation,
    )
except (ModuleNotFoundError, ImportError):
    DecisionExplanationInterface = None
    DecisionExplanation = None

try:
    from fraud_detection.reasoning.confidence_scoring import (
        ConfidenceScorer,
        ConfidenceAssessment,
    )
except (ModuleNotFoundError, ImportError):
    ConfidenceScorer = None
    ConfidenceAssessment = None

try:
    from fraud_detection.reasoning.explanation_validator import (
        ExplanationValidator,
        ValidationCriteria,
    )
except (ModuleNotFoundError, ImportError):
    ExplanationValidator = None
    ValidationCriteria = None

try:
    from fraud_detection.reasoning.reasoning_trail import (
        ReasoningTrailFormatter,
        ReasoningTrail,
    )
except (ModuleNotFoundError, ImportError):
    ReasoningTrailFormatter = None
    ReasoningTrail = None
