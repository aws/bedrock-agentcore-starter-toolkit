# Fraud Detection API Documentation

## Overview

The Fraud Detection API provides a production-ready REST API and WebSocket interface for real-time fraud detection. It includes authentication, rate limiting, comprehensive error handling, and client SDKs.

## Quick Start

### Installation

```bash
pip install flask flask-cors flask-limiter flask-socketio
```

### Running the Server

```bash
python fraud_detection_api.py
```

The server will start on `http://localhost:5000`

### Getting Your API Key

On first startup, a default API key is automatically generated and logged to the console. Look for:

```
Default API key created: fds_...
```

You can also create additional API keys using the `/api/v1/keys` endpoint (requires admin permission).

## Authentication

All API endpoints require authentication using an API key.

**Header Format:**
```
X-API-Key: fds_your_api_key_here
```

**Permissions:**
- `read`: Access to GET endpoints (statistics, status)
- `write`: Access to POST endpoints (transaction submission)
- `admin`: Access to administrative endpoints (key creation)

## Rate Limiting

Default rate limits:
- **Standard endpoints**: 100 requests per minute
- **Transaction submission**: 60 requests per minute
- **Batch processing**: 10 requests per minute

Rate limits are enforced per API key. Exceeding limits returns a `429 Too Many Requests` error.

## REST API Endpoints

### 1. Submit Transaction

Submit a single transaction for fraud detection.

**Endpoint:** `POST /api/v1/transactions`

**Authentication:** Required (write permission)

**Rate Limit:** 60 per minute

**Request Body:**
```json
{
  "id": "txn_123",
  "user_id": "user_456",
  "amount": 150.00,
  "currency": "USD",
  "merchant": "Amazon",
  "category": "retail",
  "timestamp": "2024-01-01T12:00:00Z",
  "location": {
    "country": "US",
    "city": "New York",
    "latitude": 40.7128,
    "longitude": -74.0060
  },
  "card_type": "credit",
  "device_info": {
    "device_id": "dev_001",
    "device_type": "mobile",
    "os": "iOS"
  },
  "ip_address": "192.168.1.1"
}
```

**Response:**
```json
{
  "transaction_id": "txn_123",
  "decision": "APPROVE",
  "is_fraud": false,
  "confidence_score": 0.95,
  "risk_level": "LOW",
  "reasoning": "Transaction appears legitimate based on user history and patterns",
  "evidence": [
    "Amount within normal range for user",
    "Location matches user profile",
    "Device recognized"
  ],
  "recommendations": [
    "Approve transaction"
  ],
  "processing_time_ms": 150.5,
  "timestamp": "2024-01-01T12:00:01Z"
}
```

**Decision Values:**
- `APPROVE`: Transaction is legitimate, approve
- `DECLINE`: Transaction is fraudulent, decline
- `FLAG`: Transaction is suspicious, flag for review
- `REVIEW`: Manual review required
- `BLOCK`: Block transaction immediately

**Risk Levels:**
- `LOW`: Low risk transaction
- `MEDIUM`: Medium risk, monitor
- `HIGH`: High risk, requires attention
- `CRITICAL`: Critical risk, immediate action needed

### 