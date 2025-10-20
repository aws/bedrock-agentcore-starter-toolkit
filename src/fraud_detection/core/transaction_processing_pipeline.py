#!/usr/bin/env python3
"""
End-to-End Transaction Processing Pipeline

Main entry point for transaction processing that routes through the full system:
- Transaction preprocessing and validation
- Agent orchestrator for multi-agent analysis
- Decision aggregation and final output
- Comprehensive error handling and fallback mechanisms
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

from src.fraud_detection.core.unified_fraud_detection_system import UnifiedFraudDetectionSystem, SystemConfiguration

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ValidationStatus(Enum):
    """Transaction validation status."""
    VALID = "valid"
    INVALID = "invalid"
    WARNING = "warning"


@dataclass
class ValidationResult:
    """Result of transaction validation."""
    status: ValidationStatus
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    normalized_data: Optional[Dict[str, Any]] = None


@dataclass
class ProcessingResult:
    """Complete processing result."""
    transaction_id: str
    success: bool
    decision: str
    is_fraud: bool
    confidence_score: float
    risk_level: str
    reasoning: str
    evidence: List[str]
    processing_time_ms: float
    validation_result: ValidationResult
    agent_results: Dict[str, Any]
    contextual_analysis: Dict[str, Any]
    recommendations: List[str]
    timestamp: datetime
    error_message: Optional[str] = None


class TransactionPreprocessor:
    """Handles transaction preprocessing and validation."""
    
    def __init__(self):
        """Initialize preprocessor."""
        self.required_fields = [
            'id', 'user_id', 'amount', 'currency', 'merchant', 
            'category', 'timestamp'
        ]
        self.optional_fields = [
            'location', 'card_type', 'device_info', 'ip_address', 
            'session_id', 'metadata'
        ]
    
    def preprocess(self, transaction_data: Dict[str, Any]) -> ValidationResult:
        """
        Preprocess and validate transaction data.
        
        Args:
            transaction_data: Raw transaction data
            
        Returns:
            ValidationResult with validation status and normalized data
        """
        errors = []
        warnings = []
        normalized_data = transaction_data.copy()
        
        # Validate required fields
        for field in self.required_fields:
            if field not in transaction_data or transaction_data[field] is None:
                errors.append(f"Missing required field: {field}")
        
        # Validate and normalize amount
        if 'amount' in transaction_data:
            try:
                amount = float(transaction_data['amount'])
                if amount <= 0:
                    errors.append("Amount must be positive")
                elif amount > 1000000:
                    warnings.append("Unusually high transaction amount")
                normalized_data['amount'] = amount
            except (ValueError, TypeError):
                errors.append("Invalid amount format")
        
        # Validate currency
        if 'currency' in transaction_data:
            valid_currencies = ['USD', 'EUR', 'GBP', 'CAD', 'AUD', 'JPY']
            if transaction_data['currency'] not in valid_currencies:
                warnings.append(f"Unusual currency: {transaction_data['currency']}")
        
        # Validate timestamp
        if 'timestamp' in transaction_data:
            try:
                if isinstance(transaction_data['timestamp'], str):
                    datetime.fromisoformat(transaction_data['timestamp'].replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                errors.append("Invalid timestamp format")
        
        # Normalize location data
        if 'location' not in normalized_data or not normalized_data['location']:
            normalized_data['location'] = {
                'country': 'UNKNOWN',
                'city': 'UNKNOWN',
                'latitude': None,
                'longitude': None,
                'ip_address': normalized_data.get('ip_address')
            }
        
        # Normalize device info
        if 'device_info' not in normalized_data or not normalized_data['device_info']:
            normalized_data['device_info'] = {
                'device_id': 'unknown',
                'device_type': 'unknown',
                'os': 'unknown'
            }
        
        # Set defaults for optional fields
        normalized_data.setdefault('card_type', 'unknown')
        normalized_data.setdefault('ip_address', '0.0.0.0')
        normalized_data.setdefault('session_id', f"session_{transaction_data.get('id', 'unknown')}")
        normalized_data.setdefault('metadata', {})
        
        # Determine validation status
        if errors:
            status = ValidationStatus.INVALID
        elif warnings:
            status = ValidationStatus.WARNING
        else:
            status = ValidationStatus.VALID
        
        return ValidationResult(
            status=status,
            errors=errors,
            warnings=warnings,
            normalized_data=normalized_data
        )



class TransactionProcessingPipeline:
    """
    End-to-end transaction processing pipeline.
    
    Orchestrates the complete fraud detection workflow:
    1. Preprocessing and validation
    2. Multi-agent analysis through orchestrator
    3. Decision aggregation
    4. Result formatting and output
    5. Error handling and fallback mechanisms
    """
    
    def __init__(self, system_config: Optional[SystemConfiguration] = None):
        """Initialize the processing pipeline."""
        logger.info("Initializing Transaction Processing Pipeline")
        
        # Initialize preprocessor
        self.preprocessor = TransactionPreprocessor()
        
        # Initialize unified system
        self.unified_system = UnifiedFraudDetectionSystem(
            config=system_config or SystemConfiguration()
        )
        
        # Processing statistics
        self.stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'validation_errors': 0,
            'fraud_detected': 0,
            'processing_times': []
        }
        
        logger.info("Transaction Processing Pipeline initialized")
    
    def process(self, transaction_data: Dict[str, Any]) -> ProcessingResult:
        """
        Process a transaction through the complete pipeline.
        
        Args:
            transaction_data: Raw transaction data
            
        Returns:
            ProcessingResult with complete analysis
        """
        start_time = datetime.now()
        transaction_id = transaction_data.get('id', 'unknown')
        
        try:
            logger.info(f"Starting pipeline processing for transaction {transaction_id}")
            
            # Step 1: Preprocess and validate
            validation_result = self._preprocess_transaction(transaction_data)
            
            if validation_result.status == ValidationStatus.INVALID:
                return self._create_validation_error_result(
                    transaction_id, validation_result, start_time
                )
            
            # Step 2: Process through unified system
            fraud_result = self._process_through_system(validation_result.normalized_data)
            
            # Step 3: Aggregate and format results
            final_result = self._aggregate_results(
                transaction_id,
                validation_result,
                fraud_result,
                start_time
            )
            
            # Step 4: Update statistics
            self._update_statistics(final_result)
            
            logger.info(f"Pipeline processing completed for {transaction_id}: {final_result.decision}")
            return final_result
            
        except Exception as e:
            logger.error(f"Pipeline error for transaction {transaction_id}: {str(e)}")
            return self._create_error_result(transaction_id, str(e), start_time)
    
    def process_batch(self, transactions: List[Dict[str, Any]]) -> List[ProcessingResult]:
        """
        Process a batch of transactions.
        
        Args:
            transactions: List of transaction data dictionaries
            
        Returns:
            List of ProcessingResult objects
        """
        logger.info(f"Processing batch of {len(transactions)} transactions")
        
        results = []
        for transaction_data in transactions:
            result = self.process(transaction_data)
            results.append(result)
        
        logger.info(f"Batch processing completed: {len(results)} transactions processed")
        return results
    
    def _preprocess_transaction(self, transaction_data: Dict[str, Any]) -> ValidationResult:
        """Preprocess and validate transaction."""
        logger.debug(f"Preprocessing transaction {transaction_data.get('id')}")
        
        try:
            validation_result = self.preprocessor.preprocess(transaction_data)
            
            if validation_result.errors:
                logger.warning(f"Validation errors: {validation_result.errors}")
                self.stats['validation_errors'] += 1
            
            if validation_result.warnings:
                logger.info(f"Validation warnings: {validation_result.warnings}")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Preprocessing error: {str(e)}")
            return ValidationResult(
                status=ValidationStatus.INVALID,
                errors=[f"Preprocessing failed: {str(e)}"],
                normalized_data=transaction_data
            )
    
    def _process_through_system(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process transaction through unified fraud detection system."""
        logger.debug(f"Processing through unified system: {transaction_data.get('id')}")
        
        try:
            # Process through unified system
            result = self.unified_system.process_transaction(transaction_data)
            return result
            
        except Exception as e:
            logger.error(f"System processing error: {str(e)}")
            # Return fallback result
            return self._create_fallback_result(transaction_data, str(e))
    
    def _aggregate_results(
        self,
        transaction_id: str,
        validation_result: ValidationResult,
        fraud_result: Dict[str, Any],
        start_time: datetime
    ) -> ProcessingResult:
        """Aggregate results from all processing stages."""
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # Extract agent results
        agent_results = fraud_result.get('processing_metadata', {})
        
        # Extract contextual analysis
        contextual_analysis = fraud_result.get('contextual_analysis', {})
        
        # Generate recommendations
        recommendations = self._generate_recommendations(fraud_result, validation_result)
        
        return ProcessingResult(
            transaction_id=transaction_id,
            success=True,
            decision=fraud_result.get('decision', 'REVIEW'),
            is_fraud=fraud_result.get('is_fraud', False),
            confidence_score=fraud_result.get('confidence_score', 0.0),
            risk_level=fraud_result.get('risk_level', 'MEDIUM'),
            reasoning=fraud_result.get('reasoning', ''),
            evidence=fraud_result.get('evidence', []),
            processing_time_ms=processing_time,
            validation_result=validation_result,
            agent_results=agent_results,
            contextual_analysis=contextual_analysis,
            recommendations=recommendations,
            timestamp=datetime.now()
        )
    
    def _generate_recommendations(
        self,
        fraud_result: Dict[str, Any],
        validation_result: ValidationResult
    ) -> List[str]:
        """Generate actionable recommendations based on results."""
        recommendations = []
        
        # Decision-based recommendations
        decision = fraud_result.get('decision', 'REVIEW')
        if decision == 'BLOCK' or decision == 'DECLINE':
            recommendations.append("Block transaction immediately")
            recommendations.append("Notify customer of blocked transaction")
            recommendations.append("Investigate for account compromise")
        elif decision == 'FLAG':
            recommendations.append("Flag for manual review")
            recommendations.append("Monitor customer activity closely")
        elif decision == 'REVIEW':
            recommendations.append("Conduct manual review")
            recommendations.append("Request additional verification if needed")
        
        # Risk-based recommendations
        risk_level = fraud_result.get('risk_level', 'MEDIUM')
        if risk_level == 'HIGH':
            recommendations.append("Escalate to fraud investigation team")
            recommendations.append("Consider temporary account restrictions")
        
        # Validation-based recommendations
        if validation_result.warnings:
            recommendations.append("Review transaction details for anomalies")
        
        # Evidence-based recommendations
        evidence = fraud_result.get('evidence', [])
        if any('velocity' in e.lower() for e in evidence):
            recommendations.append("Check for account takeover indicators")
        if any('location' in e.lower() for e in evidence):
            recommendations.append("Verify customer location and travel patterns")
        
        return recommendations
    
    def _create_validation_error_result(
        self,
        transaction_id: str,
        validation_result: ValidationResult,
        start_time: datetime
    ) -> ProcessingResult:
        """Create result for validation errors."""
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        self.stats['failed'] += 1
        
        return ProcessingResult(
            transaction_id=transaction_id,
            success=False,
            decision='REJECT',
            is_fraud=False,
            confidence_score=0.0,
            risk_level='UNKNOWN',
            reasoning=f"Validation failed: {', '.join(validation_result.errors)}",
            evidence=validation_result.errors,
            processing_time_ms=processing_time,
            validation_result=validation_result,
            agent_results={},
            contextual_analysis={},
            recommendations=['Fix validation errors and resubmit'],
            timestamp=datetime.now(),
            error_message=f"Validation errors: {', '.join(validation_result.errors)}"
        )
    
    def _create_error_result(
        self,
        transaction_id: str,
        error_message: str,
        start_time: datetime
    ) -> ProcessingResult:
        """Create result for processing errors."""
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        self.stats['failed'] += 1
        
        return ProcessingResult(
            transaction_id=transaction_id,
            success=False,
            decision='REVIEW',
            is_fraud=True,  # Err on the side of caution
            confidence_score=0.0,
            risk_level='HIGH',
            reasoning=f"Processing error: {error_message}",
            evidence=[f"System error: {error_message}"],
            processing_time_ms=processing_time,
            validation_result=ValidationResult(
                status=ValidationStatus.INVALID,
                errors=[error_message]
            ),
            agent_results={},
            contextual_analysis={},
            recommendations=['Manual review required due to processing error'],
            timestamp=datetime.now(),
            error_message=error_message
        )
    
    def _create_fallback_result(
        self,
        transaction_data: Dict[str, Any],
        error_message: str
    ) -> Dict[str, Any]:
        """Create fallback result when system processing fails."""
        return {
            'transaction_id': transaction_data.get('id', 'unknown'),
            'decision': 'REVIEW',
            'is_fraud': True,
            'confidence_score': 0.0,
            'risk_level': 'HIGH',
            'reasoning': f"Fallback decision due to system error: {error_message}",
            'evidence': [f"System error: {error_message}"],
            'processing_metadata': {'fallback': True, 'error': error_message},
            'contextual_analysis': {}
        }
    
    def _update_statistics(self, result: ProcessingResult):
        """Update processing statistics."""
        self.stats['total_processed'] += 1
        
        if result.success:
            self.stats['successful'] += 1
        else:
            self.stats['failed'] += 1
        
        if result.is_fraud:
            self.stats['fraud_detected'] += 1
        
        self.stats['processing_times'].append(result.processing_time_ms)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get pipeline processing statistics."""
        stats = self.stats.copy()
        
        if stats['processing_times']:
            import statistics as stat_module
            stats['average_processing_time_ms'] = stat_module.mean(stats['processing_times'])
            stats['max_processing_time_ms'] = max(stats['processing_times'])
            stats['min_processing_time_ms'] = min(stats['processing_times'])
        
        if stats['total_processed'] > 0:
            stats['success_rate'] = (stats['successful'] / stats['total_processed']) * 100
            stats['fraud_rate'] = (stats['fraud_detected'] / stats['total_processed']) * 100
        
        return stats
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get complete system status."""
        return {
            'pipeline_statistics': self.get_statistics(),
            'unified_system_status': self.unified_system.get_system_status()
        }
    
    def start_streaming(self):
        """Start streaming mode for real-time processing."""
        logger.info("Starting streaming mode")
        self.unified_system.start_streaming()
    
    def stop_streaming(self):
        """Stop streaming mode."""
        logger.info("Stopping streaming mode")
        self.unified_system.stop_streaming()


def main():
    """Example usage of the transaction processing pipeline."""
    # Initialize pipeline
    config = SystemConfiguration(
        region_name="us-east-1",
        enable_streaming=False,  # Disable for this example
        enable_adaptive_reasoning=True,
        enable_external_tools=True
    )
    
    pipeline = TransactionProcessingPipeline(system_config=config)
    
    # Example transactions
    transactions = [
        {
            "id": "txn_001",
            "user_id": "user_123",
            "amount": 150.00,
            "currency": "USD",
            "merchant": "Amazon",
            "category": "retail",
            "timestamp": datetime.now().isoformat(),
            "location": {"country": "US", "city": "New York"},
            "card_type": "credit",
            "device_info": {"device_id": "dev_001", "device_type": "mobile", "os": "iOS"},
            "ip_address": "192.168.1.1"
        },
        {
            "id": "txn_002",
            "user_id": "user_456",
            "amount": 5000.00,
            "currency": "USD",
            "merchant": "Crypto Exchange",
            "category": "crypto",
            "timestamp": datetime.now().isoformat(),
            "location": {"country": "RU", "city": "Moscow"},
            "card_type": "debit",
            "device_info": {"device_id": "dev_002", "device_type": "desktop", "os": "Windows"},
            "ip_address": "10.0.0.1"
        }
    ]
    
    # Process transactions
    print("Processing transactions through pipeline...")
    results = pipeline.process_batch(transactions)
    
    # Display results
    for result in results:
        print(f"\nTransaction {result.transaction_id}:")
        print(f"  Decision: {result.decision}")
        print(f"  Is Fraud: {result.is_fraud}")
        print(f"  Confidence: {result.confidence_score:.2f}")
        print(f"  Risk Level: {result.risk_level}")
        print(f"  Processing Time: {result.processing_time_ms:.2f}ms")
        print(f"  Recommendations: {result.recommendations}")
    
    # Display statistics
    print("\nPipeline Statistics:")
    stats = pipeline.get_statistics()
    for key, value in stats.items():
        if key != 'processing_times':
            print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
