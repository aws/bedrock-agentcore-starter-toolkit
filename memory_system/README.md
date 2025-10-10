# Memory Manager with AWS DynamoDB Integration

The Memory Manager is a comprehensive system for storing and retrieving transaction history, decision context, user behavior profiles, and fraud patterns using AWS DynamoDB. It provides the persistent memory capabilities required for the AI agent's learning and context-aware decision making.

## Features

### Core Functionality
- **Transaction History Management**: Store and retrieve transaction data with efficient indexing
- **Decision Context Storage**: Maintain detailed records of fraud detection decisions and reasoning
- **User Behavior Profiling**: Track and analyze user spending patterns and behaviors
- **Fraud Pattern Storage**: Manage known fraud patterns and their effectiveness
- **Risk Profile Management**: Store and update user risk assessments
- **Similarity Matching**: Find similar transactions for pattern analysis
- **Batch Operations**: Efficient bulk data operations for high-volume processing

### Advanced Features
- **Memory Optimization**: Automatic data cleanup and storage management
- **Performance Monitoring**: Track table usage and memory statistics
- **Context-Aware Retrieval**: Intelligent data retrieval based on similarity and relevance
- **Indexing Strategy**: Optimized DynamoDB indexes for fast queries
- **Error Handling**: Robust error handling with graceful degradation

## Architecture

### Data Models

#### Transaction
```python
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
    metadata: Dict[str, Any]
```

#### Decision Context
```python
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
    external_tools_used: List[str]
```

#### User Behavior Profile
```python
@dataclass
class UserBehaviorProfile:
    user_id: str
    typical_spending_range: Dict[str, float]
    frequent_merchants: List[str]
    common_locations: List[Location]
    preferred_categories: List[str]
    transaction_frequency: Dict[str, int]
    risk_score: float
    last_updated: datetime
    transaction_count: int
```

### DynamoDB Tables

1. **TransactionHistory**: Stores all transaction data with user_id and timestamp as composite key
2. **DecisionContext**: Stores fraud detection decisions with transaction_id as primary key
3. **UserBehaviorProfiles**: Stores user behavior profiles with user_id as primary key
4. **FraudPatterns**: Stores known fraud patterns with pattern_id as primary key
5. **RiskProfiles**: Stores user risk assessments with user_id as primary key

### Indexing Strategy

- **TransactionIdIndex**: Global secondary index for fast transaction lookup by ID
- **MerchantIndex**: Global secondary index for merchant-based queries
- **UserDecisionIndex**: Global secondary index for user decision history queries
- **PatternTypeIndex**: Global secondary index for fraud pattern type queries

## Usage

### Basic Setup

```python
from memory_system.memory_manager import MemoryManager

# Initialize Memory Manager
memory_manager = MemoryManager(region_name='us-east-1')

# Set up DynamoDB tables
success = memory_manager.setup_tables()
```

### Transaction Management

```python
# Store a transaction
transaction = Transaction(
    id="tx_123",
    user_id="user_456",
    amount=Decimal("150.00"),
    currency="USD",
    merchant="Amazon",
    # ... other fields
)

success = memory_manager.store_transaction(transaction)

# Retrieve user transaction history
history = memory_manager.get_user_transaction_history("user_456", days_back=30)

# Get transaction statistics
stats = memory_manager.get_user_transaction_stats("user_456")
```

### Decision Context Management

```python
# Store decision context
decision = DecisionContext(
    transaction_id="tx_123",
    user_id="user_456",
    decision=FraudDecision.APPROVED,
    confidence_score=0.85,
    reasoning_steps=["Amount within normal range", "Known merchant"],
    # ... other fields
)

success = memory_manager.store_decision_context(decision)

# Retrieve decision history
decisions = memory_manager.get_user_decision_history("user_456")
```

### User Profile Management

```python
# Store user behavior profile
profile = UserBehaviorProfile(
    user_id="user_456",
    typical_spending_range={"min": 10.0, "max": 500.0, "avg": 125.0},
    frequent_merchants=["Amazon", "Starbucks"],
    # ... other fields
)

success = memory_manager.store_user_profile(profile)

# Update specific profile fields
updates = {"risk_score": 0.4, "transaction_count": 155}
success = memory_manager.update_user_profile("user_456", updates)
```

### Similarity Matching

```python
# Find similar transactions
similar_cases = memory_manager.get_similar_transactions(
    transaction, 
    similarity_threshold=0.7,
    limit=10
)

for case in similar_cases:
    print(f"Similar transaction: {case.transaction_id}, "
          f"similarity: {case.similarity_score:.2f}, "
          f"decision: {case.decision.value}")
```

### Batch Operations

```python
# Store multiple transactions efficiently
transactions = [tx1, tx2, tx3, ...]
result = memory_manager.batch_store_transactions(transactions)
print(f"Stored: {result['success']}, Failed: {result['failures']}")
```

### Memory Management

```python
# Get memory usage statistics
stats = memory_manager.get_memory_usage_stats()

# Clean up old data
cleanup_result = memory_manager.cleanup_old_data(days_to_keep=365)
```

## Configuration

### Environment Variables

```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key

# For local development with DynamoDB Local
DYNAMODB_ENDPOINT=http://localhost:8000
```

### Local Development

For local development, you can use DynamoDB Local:

```bash
# Download and run DynamoDB Local
java -Djava.library.path=./DynamoDBLocal_lib -jar DynamoDBLocal.jar -sharedDb

# Initialize Memory Manager with local endpoint
memory_manager = MemoryManager(endpoint_url='http://localhost:8000')
```

## Performance Considerations

### Query Optimization
- Use appropriate indexes for common query patterns
- Leverage composite keys for efficient range queries
- Use projection expressions to reduce data transfer

### Batch Operations
- Use batch operations for bulk data processing
- Process data in chunks to avoid DynamoDB limits
- Implement retry logic for failed batch operations

### Memory Management
- Regularly clean up old data to manage costs
- Monitor table sizes and item counts
- Use TTL (Time To Live) for automatic data expiration

## Error Handling

The Memory Manager implements comprehensive error handling:

```python
# All operations return success indicators
success = memory_manager.store_transaction(transaction)
if not success:
    logger.error("Failed to store transaction")

# Retrieval operations return None/empty lists on failure
transaction = memory_manager.get_transaction_by_id("invalid_id")
if transaction is None:
    logger.warning("Transaction not found")
```

## Testing

### Unit Tests
```bash
# Run integration tests
python test_memory_integration.py

# Run with pytest (requires moto for mocking)
pip install moto
python -m pytest memory_system/test_memory_manager.py -v
```

### Demo Script
```bash
# Run the demo to see all features in action
python demo_memory_manager.py
```

## Requirements

### Python Dependencies
```
boto3>=1.26.0
botocore>=1.29.0
```

### AWS Services
- AWS DynamoDB
- AWS IAM (for permissions)

### Development Dependencies
```
pytest>=7.0.0
moto>=4.0.0  # For mocking AWS services in tests
```

## Security

### IAM Permissions

The Memory Manager requires the following DynamoDB permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:CreateTable",
                "dynamodb:DescribeTable",
                "dynamodb:PutItem",
                "dynamodb:GetItem",
                "dynamodb:UpdateItem",
                "dynamodb:DeleteItem",
                "dynamodb:Query",
                "dynamodb:Scan",
                "dynamodb:BatchGetItem",
                "dynamodb:BatchWriteItem"
            ],
            "Resource": [
                "arn:aws:dynamodb:*:*:table/fraud-detection-*",
                "arn:aws:dynamodb:*:*:table/fraud-detection-*/index/*"
            ]
        }
    ]
}
```

### Data Protection
- All data is encrypted at rest using DynamoDB encryption
- Use VPC endpoints for secure communication
- Implement proper access controls and authentication
- Avoid storing sensitive PII in metadata fields

## Monitoring

### CloudWatch Metrics
- Monitor DynamoDB read/write capacity usage
- Track error rates and throttling
- Set up alarms for unusual activity patterns

### Application Metrics
- Transaction processing rates
- Decision accuracy over time
- Memory usage trends
- Query performance metrics

## Troubleshooting

### Common Issues

1. **Table Creation Failures**
   - Check IAM permissions
   - Verify region configuration
   - Ensure table names don't conflict

2. **Query Performance Issues**
   - Review index usage
   - Optimize query patterns
   - Consider data partitioning

3. **Memory Usage Growth**
   - Implement data cleanup policies
   - Monitor table sizes
   - Use appropriate data retention periods

### Debug Mode

Enable debug logging for detailed operation information:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Contributing

When contributing to the Memory Manager:

1. Follow the existing code style and patterns
2. Add comprehensive tests for new features
3. Update documentation for API changes
4. Consider performance implications of changes
5. Test with both local and AWS DynamoDB

## License

This Memory Manager is part of the AWS AI Agent Enhancement project and follows the project's licensing terms.