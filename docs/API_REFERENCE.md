# API Reference

## Overview

The Fraud Detection System provides RESTful APIs and WebSocket endpoints for real-time fraud detection. All endpoints require authentication and return JSON responses.

## Base URL

```
Production: https://api.fraud-detection.example.com/v1
Staging: https://staging-api.fraud-detection.example.com/v1
Development: http://localhost:8000/v1
```

## Authentication

All API requests require authentication using JWT tokens or API keys.

### JWT Authentication

```http
Authorization: Bearer <jwt_token>
```

### API Key Authentication

```http
X-API-Key: <api_key>
```

### Obtaining Tokens

```http
POST /auth/token
Content-Type: application/json

{
  "username": "user@example.com",
  "password": "secure_password"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

## Core Endpoints

### 1. Analyze Transaction

Analyze a single transaction for fraud.

```http
POST /transactions/analyze
Content-Type: application/json
Authorization: Bearer <token>
```

**Request Body:**
```json
{
  "transaction_id": "tx_123456789",
  "user_id": "user_abc123",
  "amount": 1500.00,
  "currency": "USD",
  "merchant": "Online Store",
  "merchant_category": "E-commerce",
  "location": "New York, US",
  "device_id": "device_xyz789",
  "ip_address": "192.168.1.1",
  "timestamp": "2024-01-15T10:30:00Z",
  "metadata": {
    "payment_method": "credit_card",
    "card_last_four": "1234"
  }
}
```

**Response (200 OK):**
```json
{
  "transaction_id": "tx_123456789",
  "decision": "APPROVE",
  "confidence": 0.92,
  "risk_level": "LOW",
  "risk_score": 0.15,
  "reasoning": [
    "Transaction amount within user's normal range",
    "Location matches user's typical patterns",
    "Device recognized from previous transactions",
    "No velocity anomalies detected"
  ],
  "explanation": "This transaction appears legitimate based on the user's historical behavior and current risk factors.",
  "factors": [
    {
      "factor": "amount_analysis",
      "score": 0.1,
      "description": "Amount is consistent with user history"
    },
    {
      "factor": "location_risk",
      "score": 0.05,
      "description": "Location is within user's typical area"
    },
    {
      "factor": "device_trust",
      "score": 0.0,
      "description": "Device is recognized and trusted"
    }
  ],
  "agent_results": [
    {
      "agent_type": "transaction_analyzer",
      "decision": "APPROVE",
      "confidence": 0.95,
      "reasoning": "Normal transaction pattern"
    },
    {
      "agent_type": "pattern_detector",
      "decision": "APPROVE",
      "confidence": 0.90,
      "reasoning": "No anomalies detected"
    },
    {
      "agent_type": "risk_assessor",
      "decision": "APPROVE",
      "confidence": 0.91,
      "reasoning": "Low risk indicators"
    }
  ],
  "processing_time_ms": 245,
  "timestamp": "2024-01-15T10:30:00.245Z"
}
```

**Response (200 OK - Fraud Detected):**
```json
{
  "transaction_id": "tx_987654321",
  "decision": "DECLINE",
  "confidence": 0.88,
  "risk_level": "HIGH",
  "risk_score": 0.85,
  "reasoning": [
    "Transaction amount significantly exceeds user's average",
    "Location is in a high-risk country",
    "Device not recognized",
    "Multiple transactions in short time period"
  ],
  "explanation": "This transaction shows multiple fraud indicators including unusual location, unrecognized device, and velocity anomalies.",
  "factors": [
    {
      "factor": "amount_analysis",
      "score": 0.7,
      "description": "Amount is 10x higher than user average"
    },
    {
      "factor": "location_risk",
      "score": 0.9,
      "description": "High-risk country with no prior history"
    },
    {
      "factor": "device_trust",
      "score": 0.8,
      "description": "Unknown device, never seen before"
    },
    {
      "factor": "velocity_check",
      "score": 0.85,
      "description": "5 transactions in last 10 minutes"
    }
  ],
  "recommended_actions": [
    "Block transaction",
    "Contact user for verification",
    "Flag account for review"
  ],
  "processing_time_ms": 312,
  "timestamp": "2024-01-15T10:35:00.312Z"
}
```

**Error Responses:**

```json
// 400 Bad Request
{
  "error": "validation_error",
  "message": "Invalid transaction data",
  "details": {
    "amount": "Must be a positive number",
    "currency": "Must be a valid ISO currency code"
  }
}

// 401 Unauthorized
{
  "error": "unauthorized",
  "message": "Invalid or expired token"
}

// 429 Too Many Requests
{
  "error": "rate_limit_exceeded",
  "message": "Rate limit exceeded. Try again in 60 seconds.",
  "retry_after": 60
}

// 500 Internal Server Error
{
  "error": "internal_error",
  "message": "An unexpected error occurred",
  "request_id": "req_abc123"
}
```

### 2. Batch Transaction Analysis

Analyze multiple transactions in a single request.

```http
POST /transactions/analyze/batch
Content-Type: application/json
Authorization: Bearer <token>
```

**Request Body:**
```json
{
  "transactions": [
    {
      "transaction_id": "tx_001",
      "user_id": "user_123",
      "amount": 100.00,
      "currency": "USD"
    },
    {
      "transaction_id": "tx_002",
      "user_id": "user_456",
      "amount": 250.00,
      "currency": "USD"
    }
  ]
}
```

**Response (200 OK):**
```json
{
  "results": [
    {
      "transaction_id": "tx_001",
      "decision": "APPROVE",
      "confidence": 0.95,
      "risk_level": "LOW"
    },
    {
      "transaction_id": "tx_002",
      "decision": "FLAG",
      "confidence": 0.65,
      "risk_level": "MEDIUM"
    }
  ],
  "summary": {
    "total": 2,
    "approved": 1,
    "declined": 0,
    "flagged": 1,
    "processing_time_ms": 450
  }
}
```

### 3. Get Transaction History

Retrieve historical transaction analysis results.

```http
GET /transactions/{transaction_id}
Authorization: Bearer <token>
```

**Response (200 OK):**
```json
{
  "transaction_id": "tx_123456789",
  "user_id": "user_abc123",
  "amount": 1500.00,
  "currency": "USD",
  "decision": "APPROVE",
  "confidence": 0.92,
  "risk_level": "LOW",
  "timestamp": "2024-01-15T10:30:00Z",
  "reasoning": [...],
  "factors": [...]
}
```

### 4. Get User Risk Profile

Retrieve a user's risk profile and behavior patterns.

```http
GET /users/{user_id}/profile
Authorization: Bearer <token>
```

**Response (200 OK):**
```json
{
  "user_id": "user_abc123",
  "risk_score": 0.15,
  "risk_level": "LOW",
  "account_age_days": 365,
  "total_transactions": 1250,
  "fraud_incidents": 0,
  "average_transaction_amount": 125.50,
  "typical_locations": ["New York, US", "Boston, US"],
  "typical_merchants": ["Grocery Store", "Gas Station", "Online Store"],
  "typical_devices": ["device_xyz789"],
  "behavior_patterns": {
    "transaction_frequency": "daily",
    "preferred_time": "business_hours",
    "spending_pattern": "consistent"
  },
  "last_updated": "2024-01-15T10:30:00Z"
}
```

### 5. Update User Profile

Update user profile information.

```http
PUT /users/{user_id}/profile
Content-Type: application/json
Authorization: Bearer <token>
```

**Request Body:**
```json
{
  "typical_locations": ["New York, US", "Boston, US", "San Francisco, US"],
  "notification_preferences": {
    "email": true,
    "sms": true,
    "push": false
  }
}
```

**Response (200 OK):**
```json
{
  "user_id": "user_abc123",
  "updated": true,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### 6. Get System Health

Check system health and status.

```http
GET /health
```

**Response (200 OK):**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-15T10:30:00Z",
  "components": {
    "api": "healthy",
    "database": "healthy",
    "agents": "healthy",
    "bedrock": "healthy",
    "streaming": "healthy"
  },
  "metrics": {
    "requests_per_second": 850,
    "average_response_time_ms": 245,
    "error_rate": 0.001
  }
}
```

### 7. Get System Metrics

Retrieve system performance metrics.

```http
GET /metrics
Authorization: Bearer <token>
```

**Response (200 OK):**
```json
{
  "period": "last_hour",
  "metrics": {
    "total_transactions": 50000,
    "approved": 45000,
    "declined": 3000,
    "flagged": 2000,
    "average_response_time_ms": 245,
    "p95_response_time_ms": 450,
    "p99_response_time_ms": 850,
    "throughput_tps": 850,
    "error_rate": 0.001,
    "decision_accuracy": 0.92,
    "false_positive_rate": 0.05,
    "false_negative_rate": 0.02
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## WebSocket API

### Real-Time Transaction Monitoring

Connect to WebSocket for real-time transaction updates.

```javascript
const ws = new WebSocket('wss://api.fraud-detection.example.com/ws/transactions');

// Authentication
ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'auth',
    token: 'your_jwt_token'
  }));
};

// Subscribe to user transactions
ws.send(JSON.stringify({
  type: 'subscribe',
  user_id: 'user_abc123'
}));

// Receive updates
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Transaction update:', data);
};
```

**Message Format:**
```json
{
  "type": "transaction_update",
  "transaction_id": "tx_123456789",
  "user_id": "user_abc123",
  "decision": "APPROVE",
  "confidence": 0.92,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Rate Limiting

API requests are rate-limited to ensure fair usage.

**Limits:**
- **Free Tier**: 100 requests/minute
- **Standard Tier**: 1,000 requests/minute
- **Premium Tier**: 10,000 requests/minute

**Headers:**
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 950
X-RateLimit-Reset: 1642248600
```

## Error Codes

| Code | Description |
|------|-------------|
| 400 | Bad Request - Invalid input |
| 401 | Unauthorized - Invalid or missing authentication |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource doesn't exist |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error - Server error |
| 503 | Service Unavailable - Temporary outage |

## SDKs and Client Libraries

### Python SDK

```python
from fraud_detection_sdk import FraudDetectionClient

client = FraudDetectionClient(
    api_key='your_api_key',
    environment='production'
)

# Analyze transaction
result = client.analyze_transaction({
    'transaction_id': 'tx_123',
    'user_id': 'user_abc',
    'amount': 1500.00,
    'currency': 'USD'
})

print(f"Decision: {result.decision}")
print(f"Confidence: {result.confidence}")
```

### JavaScript SDK

```javascript
import { FraudDetectionClient } from '@fraud-detection/sdk';

const client = new FraudDetectionClient({
  apiKey: 'your_api_key',
  environment: 'production'
});

// Analyze transaction
const result = await client.analyzeTransaction({
  transaction_id: 'tx_123',
  user_id: 'user_abc',
  amount: 1500.00,
  currency: 'USD'
});

console.log(`Decision: ${result.decision}`);
console.log(`Confidence: ${result.confidence}`);
```

## Webhooks

Configure webhooks to receive notifications for fraud events.

### Webhook Configuration

```http
POST /webhooks
Content-Type: application/json
Authorization: Bearer <token>

{
  "url": "https://your-app.com/webhooks/fraud",
  "events": ["fraud_detected", "high_risk_transaction"],
  "secret": "your_webhook_secret"
}
```

### Webhook Payload

```json
{
  "event": "fraud_detected",
  "transaction_id": "tx_987654321",
  "user_id": "user_xyz789",
  "decision": "DECLINE",
  "confidence": 0.88,
  "risk_level": "HIGH",
  "timestamp": "2024-01-15T10:35:00Z",
  "signature": "sha256=..."
}
```

### Verifying Webhook Signatures

```python
import hmac
import hashlib

def verify_webhook(payload, signature, secret):
    expected = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)
```

## Best Practices

### 1. Error Handling

Always handle errors gracefully:

```python
try:
    result = client.analyze_transaction(transaction)
except RateLimitError as e:
    # Wait and retry
    time.sleep(e.retry_after)
    result = client.analyze_transaction(transaction)
except ValidationError as e:
    # Fix input and retry
    print(f"Invalid input: {e.details}")
except APIError as e:
    # Log and alert
    logger.error(f"API error: {e.message}")
```

### 2. Caching

Cache user profiles to reduce API calls:

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_user_profile(user_id):
    return client.get_user_profile(user_id)
```

### 3. Batch Processing

Use batch endpoints for multiple transactions:

```python
# Instead of multiple calls
for tx in transactions:
    result = client.analyze_transaction(tx)

# Use batch endpoint
results = client.analyze_batch(transactions)
```

### 4. Async Processing

Use async for better performance:

```python
import asyncio

async def analyze_transactions(transactions):
    tasks = [
        client.analyze_transaction_async(tx)
        for tx in transactions
    ]
    return await asyncio.gather(*tasks)
```

## Support

For API support:
- Email: api-support@fraud-detection.example.com
- Documentation: https://docs.fraud-detection.example.com
- Status Page: https://status.fraud-detection.example.com
