"""
Memory Manager with AWS DynamoDB Integration

Handles storage and retrieval of transaction history, decision context,
user behavior profiles, and fraud patterns.
"""

import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

from .models import (
    Transaction, DecisionContext, UserBehaviorProfile, 
    FraudPattern, SimilarCase, RiskProfile, FraudDecision, RiskLevel
)
from .dynamodb_config import DynamoDBConfig

logger = logging.getLogger(__name__)


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder for Decimal types."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


class MemoryManager:
    """
    Manages persistent memory for the fraud detection system using DynamoDB.
    
    Provides CRUD operations for:
    - Transaction history
    - Decision context
    - User behavior profiles  
    - Fraud patterns
    - Risk profiles
    """
    
    def __init__(self, region_name: str = 'us-east-1', endpoint_url: str = None):
        """
        Initialize the Memory Manager.
        
        Args:
            region_name: AWS region for DynamoDB
            endpoint_url: Optional endpoint URL for local DynamoDB
        """
        self.config = DynamoDBConfig(region_name, endpoint_url)
        self.dynamodb = self.config.dynamodb
        
        # Get table references
        table_defs = self.config.get_table_definitions()
        self.transaction_table = self.dynamodb.Table(
            table_defs['TransactionHistory']['TableName']
        )
        self.decision_table = self.dynamodb.Table(
            table_defs['DecisionContext']['TableName']
        )
        self.profile_table = self.dynamodb.Table(
            table_defs['UserBehaviorProfiles']['TableName']
        )
        self.pattern_table = self.dynamodb.Table(
            table_defs['FraudPatterns']['TableName']
        )
        self.risk_table = self.dynamodb.Table(
            table_defs['RiskProfiles']['TableName']
        )
    
    def setup_tables(self) -> bool:
        """
        Set up all required DynamoDB tables.
        
        Returns:
            bool: True if setup successful
        """
        return self.config.create_tables()
    
    # Transaction History Operations
    
    def store_transaction(self, transaction: Transaction) -> bool:
        """
        Store a transaction in the history table.
        
        Args:
            transaction: Transaction object to store
            
        Returns:
            bool: True if stored successfully
        """
        try:
            item = {
                'user_id': transaction.user_id,
                'timestamp': transaction.timestamp.isoformat(),
                'transaction_id': transaction.id,
                'amount': transaction.amount,
                'currency': transaction.currency,
                'merchant': transaction.merchant,
                'category': transaction.category,
                'location': {
                    'country': transaction.location.country,
                    'city': transaction.location.city,
                    'latitude': transaction.location.latitude,
                    'longitude': transaction.location.longitude,
                    'ip_address': transaction.location.ip_address
                },
                'card_type': transaction.card_type,
                'device_info': {
                    'device_id': transaction.device_info.device_id,
                    'device_type': transaction.device_info.device_type,
                    'os': transaction.device_info.os,
                    'browser': transaction.device_info.browser,
                    'fingerprint': transaction.device_info.fingerprint
                },
                'ip_address': transaction.ip_address,
                'session_id': transaction.session_id,
                'metadata': transaction.metadata
            }
            
            self.transaction_table.put_item(Item=item)
            logger.info(f"Stored transaction {transaction.id} for user {transaction.user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing transaction {transaction.id}: {str(e)}")
            return False
    
    def get_user_transaction_history(
        self, 
        user_id: str, 
        days_back: int = 30,
        limit: int = 100
    ) -> List[Transaction]:
        """
        Retrieve transaction history for a user.
        
        Args:
            user_id: User identifier
            days_back: Number of days to look back
            limit: Maximum number of transactions to return
            
        Returns:
            List of Transaction objects
        """
        try:
            start_date = datetime.now() - timedelta(days=days_back)
            
            response = self.transaction_table.query(
                KeyConditionExpression=Key('user_id').eq(user_id) & 
                                     Key('timestamp').gte(start_date.isoformat()),
                Limit=limit,
                ScanIndexForward=False  # Most recent first
            )
            
            transactions = []
            for item in response['Items']:
                transactions.append(self._item_to_transaction(item))
            
            logger.info(f"Retrieved {len(transactions)} transactions for user {user_id}")
            return transactions
            
        except Exception as e:
            logger.error(f"Error retrieving transactions for user {user_id}: {str(e)}")
            return []
    
    def get_transaction_by_id(self, transaction_id: str) -> Optional[Transaction]:
        """
        Retrieve a specific transaction by ID.
        
        Args:
            transaction_id: Transaction identifier
            
        Returns:
            Transaction object or None if not found
        """
        try:
            response = self.transaction_table.query(
                IndexName='TransactionIdIndex',
                KeyConditionExpression=Key('transaction_id').eq(transaction_id)
            )
            
            if response['Items']:
                return self._item_to_transaction(response['Items'][0])
            
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving transaction {transaction_id}: {str(e)}")
            return None
    
    # Decision Context Operations
    
    def store_decision_context(self, context: DecisionContext) -> bool:
        """
        Store decision context for a transaction.
        
        Args:
            context: DecisionContext object to store
            
        Returns:
            bool: True if stored successfully
        """
        try:
            item = {
                'transaction_id': context.transaction_id,
                'user_id': context.user_id,
                'decision': context.decision.value,
                'confidence_score': context.confidence_score,
                'reasoning_steps': context.reasoning_steps,
                'evidence': context.evidence,
                'timestamp': context.timestamp.isoformat(),
                'processing_time_ms': context.processing_time_ms,
                'agent_version': context.agent_version,
                'external_tools_used': context.external_tools_used
            }
            
            self.decision_table.put_item(Item=item)
            logger.info(f"Stored decision context for transaction {context.transaction_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing decision context: {str(e)}")
            return False
    
    def get_decision_context(self, transaction_id: str) -> Optional[DecisionContext]:
        """
        Retrieve decision context for a transaction.
        
        Args:
            transaction_id: Transaction identifier
            
        Returns:
            DecisionContext object or None if not found
        """
        try:
            response = self.decision_table.get_item(
                Key={'transaction_id': transaction_id}
            )
            
            if 'Item' in response:
                item = response['Item']
                return DecisionContext(
                    transaction_id=item['transaction_id'],
                    user_id=item['user_id'],
                    decision=FraudDecision(item['decision']),
                    confidence_score=float(item['confidence_score']),
                    reasoning_steps=item['reasoning_steps'],
                    evidence=item['evidence'],
                    timestamp=datetime.fromisoformat(item['timestamp']),
                    processing_time_ms=float(item['processing_time_ms']),
                    agent_version=item['agent_version'],
                    external_tools_used=item.get('external_tools_used', [])
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving decision context: {str(e)}")
            return None
    
    def get_user_decision_history(
        self, 
        user_id: str, 
        days_back: int = 30
    ) -> List[DecisionContext]:
        """
        Retrieve decision history for a user.
        
        Args:
            user_id: User identifier
            days_back: Number of days to look back
            
        Returns:
            List of DecisionContext objects
        """
        try:
            start_date = datetime.now() - timedelta(days=days_back)
            
            response = self.decision_table.query(
                IndexName='UserDecisionIndex',
                KeyConditionExpression=Key('user_id').eq(user_id) & 
                                     Key('timestamp').gte(start_date.isoformat()),
                ScanIndexForward=False
            )
            
            decisions = []
            for item in response['Items']:
                decisions.append(DecisionContext(
                    transaction_id=item['transaction_id'],
                    user_id=item['user_id'],
                    decision=FraudDecision(item['decision']),
                    confidence_score=float(item['confidence_score']),
                    reasoning_steps=item['reasoning_steps'],
                    evidence=item['evidence'],
                    timestamp=datetime.fromisoformat(item['timestamp']),
                    processing_time_ms=float(item['processing_time_ms']),
                    agent_version=item['agent_version'],
                    external_tools_used=item.get('external_tools_used', [])
                ))
            
            return decisions
            
        except Exception as e:
            logger.error(f"Error retrieving decision history for user {user_id}: {str(e)}")
            return []   
 
    # User Behavior Profile Operations
    
    def store_user_profile(self, profile: UserBehaviorProfile) -> bool:
        """
        Store or update user behavior profile.
        
        Args:
            profile: UserBehaviorProfile object to store
            
        Returns:
            bool: True if stored successfully
        """
        try:
            item = {
                'user_id': profile.user_id,
                'typical_spending_range': profile.typical_spending_range,
                'frequent_merchants': profile.frequent_merchants,
                'common_locations': [
                    {
                        'country': loc.country,
                        'city': loc.city,
                        'latitude': loc.latitude,
                        'longitude': loc.longitude,
                        'ip_address': loc.ip_address
                    } for loc in profile.common_locations
                ],
                'preferred_categories': profile.preferred_categories,
                'transaction_frequency': profile.transaction_frequency,
                'risk_score': profile.risk_score,
                'last_updated': profile.last_updated.isoformat(),
                'transaction_count': profile.transaction_count
            }
            
            self.profile_table.put_item(Item=item)
            logger.info(f"Stored user profile for {profile.user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing user profile: {str(e)}")
            return False
    
    def get_user_profile(self, user_id: str) -> Optional[UserBehaviorProfile]:
        """
        Retrieve user behavior profile.
        
        Args:
            user_id: User identifier
            
        Returns:
            UserBehaviorProfile object or None if not found
        """
        try:
            response = self.profile_table.get_item(
                Key={'user_id': user_id}
            )
            
            if 'Item' in response:
                item = response['Item']
                from .models import Location
                
                return UserBehaviorProfile(
                    user_id=item['user_id'],
                    typical_spending_range=item['typical_spending_range'],
                    frequent_merchants=item['frequent_merchants'],
                    common_locations=[
                        Location(
                            country=loc['country'],
                            city=loc['city'],
                            latitude=loc.get('latitude'),
                            longitude=loc.get('longitude'),
                            ip_address=loc.get('ip_address')
                        ) for loc in item['common_locations']
                    ],
                    preferred_categories=item['preferred_categories'],
                    transaction_frequency=item['transaction_frequency'],
                    risk_score=float(item['risk_score']),
                    last_updated=datetime.fromisoformat(item['last_updated']),
                    transaction_count=int(item['transaction_count'])
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving user profile: {str(e)}")
            return None
    
    # Fraud Pattern Operations
    
    def store_fraud_pattern(self, pattern: FraudPattern) -> bool:
        """
        Store or update fraud pattern.
        
        Args:
            pattern: FraudPattern object to store
            
        Returns:
            bool: True if stored successfully
        """
        try:
            item = {
                'pattern_id': pattern.pattern_id,
                'pattern_type': pattern.pattern_type,
                'description': pattern.description,
                'indicators': pattern.indicators,
                'confidence_threshold': pattern.confidence_threshold,
                'detection_count': pattern.detection_count,
                'false_positive_rate': pattern.false_positive_rate,
                'created_at': pattern.created_at.isoformat(),
                'last_seen': pattern.last_seen.isoformat(),
                'effectiveness_score': pattern.effectiveness_score
            }
            
            self.pattern_table.put_item(Item=item)
            logger.info(f"Stored fraud pattern {pattern.pattern_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing fraud pattern: {str(e)}")
            return False
    
    def get_fraud_patterns_by_type(self, pattern_type: str) -> List[FraudPattern]:
        """
        Retrieve fraud patterns by type.
        
        Args:
            pattern_type: Type of fraud pattern
            
        Returns:
            List of FraudPattern objects
        """
        try:
            response = self.pattern_table.query(
                IndexName='PatternTypeIndex',
                KeyConditionExpression=Key('pattern_type').eq(pattern_type),
                ScanIndexForward=False
            )
            
            patterns = []
            for item in response['Items']:
                patterns.append(FraudPattern(
                    pattern_id=item['pattern_id'],
                    pattern_type=item['pattern_type'],
                    description=item['description'],
                    indicators=item['indicators'],
                    confidence_threshold=float(item['confidence_threshold']),
                    detection_count=int(item['detection_count']),
                    false_positive_rate=float(item['false_positive_rate']),
                    created_at=datetime.fromisoformat(item['created_at']),
                    last_seen=datetime.fromisoformat(item['last_seen']),
                    effectiveness_score=float(item['effectiveness_score'])
                ))
            
            return patterns
            
        except Exception as e:
            logger.error(f"Error retrieving fraud patterns: {str(e)}")
            return []
    
    def get_all_fraud_patterns(self) -> List[FraudPattern]:
        """
        Retrieve all fraud patterns.
        
        Returns:
            List of FraudPattern objects
        """
        try:
            response = self.pattern_table.scan()
            
            patterns = []
            for item in response['Items']:
                patterns.append(FraudPattern(
                    pattern_id=item['pattern_id'],
                    pattern_type=item['pattern_type'],
                    description=item['description'],
                    indicators=item['indicators'],
                    confidence_threshold=float(item['confidence_threshold']),
                    detection_count=int(item['detection_count']),
                    false_positive_rate=float(item['false_positive_rate']),
                    created_at=datetime.fromisoformat(item['created_at']),
                    last_seen=datetime.fromisoformat(item['last_seen']),
                    effectiveness_score=float(item['effectiveness_score'])
                ))
            
            return patterns
            
        except Exception as e:
            logger.error(f"Error retrieving all fraud patterns: {str(e)}")
            return []
    
    # Risk Profile Operations
    
    def store_risk_profile(self, risk_profile: RiskProfile) -> bool:
        """
        Store or update user risk profile.
        
        Args:
            risk_profile: RiskProfile object to store
            
        Returns:
            bool: True if stored successfully
        """
        try:
            item = {
                'user_id': risk_profile.user_id,
                'overall_risk_level': risk_profile.overall_risk_level.value,
                'risk_factors': risk_profile.risk_factors,
                'geographic_risk': risk_profile.geographic_risk,
                'behavioral_risk': risk_profile.behavioral_risk,
                'transaction_risk': risk_profile.transaction_risk,
                'temporal_risk': risk_profile.temporal_risk,
                'last_assessment': risk_profile.last_assessment.isoformat(),
                'risk_evolution': risk_profile.risk_evolution
            }
            
            self.risk_table.put_item(Item=item)
            logger.info(f"Stored risk profile for {risk_profile.user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing risk profile: {str(e)}")
            return False
    
    def get_risk_profile(self, user_id: str) -> Optional[RiskProfile]:
        """
        Retrieve user risk profile.
        
        Args:
            user_id: User identifier
            
        Returns:
            RiskProfile object or None if not found
        """
        try:
            response = self.risk_table.get_item(
                Key={'user_id': user_id}
            )
            
            if 'Item' in response:
                item = response['Item']
                return RiskProfile(
                    user_id=item['user_id'],
                    overall_risk_level=RiskLevel(item['overall_risk_level']),
                    risk_factors=item['risk_factors'],
                    geographic_risk=float(item['geographic_risk']),
                    behavioral_risk=float(item['behavioral_risk']),
                    transaction_risk=float(item['transaction_risk']),
                    temporal_risk=float(item['temporal_risk']),
                    last_assessment=datetime.fromisoformat(item['last_assessment']),
                    risk_evolution=item['risk_evolution']
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving risk profile: {str(e)}")
            return None
    
    # Similarity and Pattern Matching
    
    def get_similar_transactions(
        self, 
        transaction: Transaction, 
        similarity_threshold: float = 0.7,
        limit: int = 10
    ) -> List[SimilarCase]:
        """
        Find similar transactions for pattern analysis.
        
        Args:
            transaction: Transaction to find similarities for
            similarity_threshold: Minimum similarity score
            limit: Maximum number of similar cases to return
            
        Returns:
            List of SimilarCase objects
        """
        try:
            # Get recent transactions from same user
            user_transactions = self.get_user_transaction_history(
                transaction.user_id, days_back=90, limit=200
            )
            
            # Get transactions from same merchant
            merchant_response = self.transaction_table.query(
                IndexName='MerchantIndex',
                KeyConditionExpression=Key('merchant').eq(transaction.merchant),
                Limit=100,
                ScanIndexForward=False
            )
            
            merchant_transactions = []
            for item in merchant_response['Items']:
                merchant_transactions.append(self._item_to_transaction(item))
            
            # Calculate similarity scores
            similar_cases = []
            all_transactions = user_transactions + merchant_transactions
            
            for tx in all_transactions:
                if tx.id == transaction.id:
                    continue
                
                similarity_score = self._calculate_similarity(transaction, tx)
                
                if similarity_score >= similarity_threshold:
                    # Get decision context for this transaction
                    decision_context = self.get_decision_context(tx.id)
                    
                    similar_case = SimilarCase(
                        case_id=f"{tx.id}_{transaction.id}",
                        transaction_id=tx.id,
                        similarity_score=similarity_score,
                        decision=decision_context.decision if decision_context else FraudDecision.APPROVED,
                        outcome=None,  # Would be populated from feedback system
                        reasoning=decision_context.reasoning_steps[0] if decision_context and decision_context.reasoning_steps else "",
                        timestamp=tx.timestamp
                    )
                    similar_cases.append(similar_case)
            
            # Sort by similarity score and return top matches
            similar_cases.sort(key=lambda x: x.similarity_score, reverse=True)
            return similar_cases[:limit]
            
        except Exception as e:
            logger.error(f"Error finding similar transactions: {str(e)}")
            return []
    
    def _calculate_similarity(self, tx1: Transaction, tx2: Transaction) -> float:
        """
        Calculate similarity score between two transactions.
        
        Args:
            tx1: First transaction
            tx2: Second transaction
            
        Returns:
            Similarity score between 0 and 1
        """
        score = 0.0
        factors = 0
        
        # Amount similarity (normalized by percentage difference)
        if tx1.amount > 0 and tx2.amount > 0:
            amount_diff = abs(float(tx1.amount) - float(tx2.amount)) / max(float(tx1.amount), float(tx2.amount))
            score += max(0, 1 - amount_diff)
            factors += 1
        
        # Merchant similarity
        if tx1.merchant == tx2.merchant:
            score += 1.0
        factors += 1
        
        # Category similarity
        if tx1.category == tx2.category:
            score += 0.5
        factors += 1
        
        # Location similarity
        if tx1.location.country == tx2.location.country:
            score += 0.3
            if tx1.location.city == tx2.location.city:
                score += 0.2
        factors += 1
        
        # Time similarity (same hour of day)
        if tx1.timestamp.hour == tx2.timestamp.hour:
            score += 0.2
        factors += 1
        
        # Device similarity
        if tx1.device_info.device_id == tx2.device_info.device_id:
            score += 0.3
        factors += 1
        
        return score / factors if factors > 0 else 0.0
    
    def _item_to_transaction(self, item: Dict[str, Any]) -> Transaction:
        """
        Convert DynamoDB item to Transaction object.
        
        Args:
            item: DynamoDB item dictionary
            
        Returns:
            Transaction object
        """
        from .models import Location, DeviceInfo
        
        return Transaction(
            id=item['transaction_id'],
            user_id=item['user_id'],
            amount=Decimal(str(item['amount'])),
            currency=item['currency'],
            merchant=item['merchant'],
            category=item['category'],
            location=Location(
                country=item['location']['country'],
                city=item['location']['city'],
                latitude=item['location'].get('latitude'),
                longitude=item['location'].get('longitude'),
                ip_address=item['location'].get('ip_address')
            ),
            timestamp=datetime.fromisoformat(item['timestamp']),
            card_type=item['card_type'],
            device_info=DeviceInfo(
                device_id=item['device_info']['device_id'],
                device_type=item['device_info']['device_type'],
                os=item['device_info']['os'],
                browser=item['device_info'].get('browser'),
                fingerprint=item['device_info'].get('fingerprint')
            ),
            ip_address=item['ip_address'],
            session_id=item['session_id'],
            metadata=item.get('metadata', {})
        )