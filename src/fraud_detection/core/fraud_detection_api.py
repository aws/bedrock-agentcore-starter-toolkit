#!/usr/bin/env python3
"""
Production-Ready Fraud Detection API

Provides REST API endpoints and WebSocket support for fraud detection:
- Transaction submission endpoints
- Real-time fraud detection updates via WebSocket
- API authentication and rate limiting
- Comprehensive API documentation
"""

import logging
import asyncio
import json
import time
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict
from collections import defaultdict
from functools import wraps

from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_socketio import SocketIO, emit, join_room, leave_room

from src.fraud_detection.core.transaction_processing_pipeline import TransactionProcessingPipeline, SystemConfiguration

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(32)
CORS(app)

# Initialize rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["100 per minute", "1000 per hour"],
    storage_uri="memory://"
)

# Initialize SocketIO for WebSocket support
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Initialize processing pipeline
pipeline_config = SystemConfiguration(
    region_name="us-east-1",
    enable_streaming=True,
    enable_adaptive_reasoning=True,
    enable_external_tools=True,
    max_stream_workers=10
)
processing_pipeline = TransactionProcessingPipeline(system_config=pipeline_config)


# API Key Management
@dataclass
class APIKey:
    """API key configuration."""
    key: str
    name: str
    created_at: datetime
    rate_limit: int  # requests per minute
    permissions: List[str]
    active: bool = True


class APIKeyManager:
    """Manages API keys and authentication."""
    
    def __init__(self):
        """Initialize API key manager."""
        self.api_keys: Dict[str, APIKey] = {}
        self._initialize_default_keys()
    
    def _initialize_default_keys(self):
        """Initialize default API keys for testing."""
        # Create a default API key
        default_key = self.generate_key(
            name="default",
            rate_limit=100,
            permissions=["read", "write", "admin"]
        )
        logger.info(f"Default API key created: {default_key}")
    
    def generate_key(
        self,
        name: str,
        rate_limit: int = 60,
        permissions: List[str] = None
    ) -> str:
        """Generate a new API key."""
        key = f"fds_{secrets.token_urlsafe(32)}"
        
        api_key = APIKey(
            key=key,
            name=name,
            created_at=datetime.now(),
            rate_limit=rate_limit,
            permissions=permissions or ["read", "write"]
        )
        
        self.api_keys[key] = api_key
        logger.info(f"Generated API key for {name}")
        return key
    
    def validate_key(self, key: str) -> Optional[APIKey]:
        """Validate an API key."""
        if key in self.api_keys:
            api_key = self.api_keys[key]
            if api_key.active:
                return api_key
        return None
    
    def has_permission(self, key: str, permission: str) -> bool:
        """Check if API key has specific permission."""
        api_key = self.validate_key(key)
        if api_key:
            return permission in api_key.permissions
        return False


# Initialize API key manager
api_key_manager = APIKeyManager()


# Rate limiting tracker
class RateLimitTracker:
    """Track API usage for rate limiting."""
    
    def __init__(self):
        """Initialize rate limit tracker."""
        self.requests: Dict[str, List[datetime]] = defaultdict(list)
    
    def check_rate_limit(self, api_key: str, limit: int) -> bool:
        """Check if request is within rate limit."""
        now = datetime.now()
        cutoff = now - timedelta(minutes=1)
        
        # Clean old requests
        self.requests[api_key] = [
            req_time for req_time in self.requests[api_key]
            if req_time > cutoff
        ]
        
        # Check limit
        if len(self.requests[api_key]) >= limit:
            return False
        
        # Record request
        self.requests[api_key].append(now)
        return True


rate_limit_tracker = RateLimitTracker()


# Authentication decorator
def require_api_key(permission: str = "read"):
    """Decorator to require API key authentication."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            api_key = request.headers.get('X-API-Key')
            
            if not api_key:
                return jsonify({
                    'error': 'Missing API key',
                    'message': 'Please provide X-API-Key header'
                }), 401
            
            # Validate API key
            key_obj = api_key_manager.validate_key(api_key)
            if not key_obj:
                return jsonify({
                    'error': 'Invalid API key',
                    'message': 'The provided API key is invalid or inactive'
                }), 401
            
            # Check permission
            if not api_key_manager.has_permission(api_key, permission):
                return jsonify({
                    'error': 'Insufficient permissions',
                    'message': f'API key does not have {permission} permission'
                }), 403
            
            # Check rate limit
            if not rate_limit_tracker.check_rate_limit(api_key, key_obj.rate_limit):
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'message': f'Rate limit of {key_obj.rate_limit} requests per minute exceeded'
                }), 429
            
            # Add API key to request context
            request.api_key = key_obj
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# ============================================================================
# REST API Endpoints
# ============================================================================

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })


@app.route('/api/v1/transactions', methods=['POST'])
@require_api_key('write')
@limiter.limit("60 per minute")
def submit_transaction():
    """
    Submit a transaction for fraud detection.
    
    Request Body:
        {
            "id": "txn_123",
            "user_id": "user_456",
            "amount": 150.00,
            "currency": "USD",
            "merchant": "Amazon",
            "category": "retail",
            "timestamp": "2024-01-01T12:00:00Z",
            "location": {"country": "US", "city": "New York"},
            "card_type": "credit",
            "device_info": {"device_id": "dev_001", "device_type": "mobile"},
            "ip_address": "192.168.1.1"
        }
    
    Response:
        {
            "transaction_id": "txn_123",
            "decision": "APPROVE",
            "is_fraud": false,
            "confidence_score": 0.95,
            "risk_level": "LOW",
            "processing_time_ms": 150.5
        }
    """
    try:
        transaction_data = request.get_json()
        
        if not transaction_data:
            return jsonify({
                'error': 'Invalid request',
                'message': 'Request body must be JSON'
            }), 400
        
        # Process transaction
        result = processing_pipeline.process(transaction_data)
        
        # Emit WebSocket update if transaction is high risk
        if result.risk_level in ['HIGH', 'CRITICAL']:
            socketio.emit('fraud_alert', {
                'transaction_id': result.transaction_id,
                'decision': result.decision,
                'risk_level': result.risk_level,
                'timestamp': result.timestamp.isoformat()
            }, namespace='/fraud-detection')
        
        # Return response
        response = {
            'transaction_id': result.transaction_id,
            'decision': result.decision,
            'is_fraud': result.is_fraud,
            'confidence_score': result.confidence_score,
            'risk_level': result.risk_level,
            'reasoning': result.reasoning,
            'evidence': result.evidence,
            'recommendations': result.recommendations,
            'processing_time_ms': result.processing_time_ms,
            'timestamp': result.timestamp.isoformat()
        }
        
        status_code = 200 if result.success else 400
        return jsonify(response), status_code
        
    except Exception as e:
        logger.error(f"Error processing transaction: {str(e)}")
        return jsonify({
            'error': 'Processing error',
            'message': str(e)
        }), 500


@app.route('/api/v1/transactions/batch', methods=['POST'])
@require_api_key('write')
@limiter.limit("10 per minute")
def submit_batch_transactions():
    """
    Submit multiple transactions for batch processing.
    
    Request Body:
        {
            "transactions": [
                {...transaction1...},
                {...transaction2...}
            ]
        }
    
    Response:
        {
            "results": [...],
            "summary": {
                "total": 10,
                "fraud_detected": 2,
                "processing_time_ms": 1500.5
            }
        }
    """
    try:
        data = request.get_json()
        
        if not data or 'transactions' not in data:
            return jsonify({
                'error': 'Invalid request',
                'message': 'Request must contain "transactions" array'
            }), 400
        
        transactions = data['transactions']
        
        if not isinstance(transactions, list):
            return jsonify({
                'error': 'Invalid request',
                'message': '"transactions" must be an array'
            }), 400
        
        if len(transactions) > 100:
            return jsonify({
                'error': 'Batch too large',
                'message': 'Maximum 100 transactions per batch'
            }), 400
        
        # Process batch
        start_time = datetime.now()
        results = processing_pipeline.process_batch(transactions)
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # Create summary
        fraud_count = sum(1 for r in results if r.is_fraud)
        
        response = {
            'results': [
                {
                    'transaction_id': r.transaction_id,
                    'decision': r.decision,
                    'is_fraud': r.is_fraud,
                    'confidence_score': r.confidence_score,
                    'risk_level': r.risk_level
                }
                for r in results
            ],
            'summary': {
                'total': len(results),
                'fraud_detected': fraud_count,
                'processing_time_ms': processing_time
            }
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Error processing batch: {str(e)}")
        return jsonify({
            'error': 'Processing error',
            'message': str(e)
        }), 500


@app.route('/api/v1/transactions/<transaction_id>', methods=['GET'])
@require_api_key('read')
def get_transaction_result(transaction_id: str):
    """
    Get the fraud detection result for a specific transaction.
    
    Response:
        {
            "transaction_id": "txn_123",
            "decision": "APPROVE",
            "is_fraud": false,
            "confidence_score": 0.95,
            "details": {...}
        }
    """
    try:
        # In a real implementation, this would query from storage
        return jsonify({
            'error': 'Not implemented',
            'message': 'Transaction history retrieval not yet implemented'
        }), 501
        
    except Exception as e:
        logger.error(f"Error retrieving transaction: {str(e)}")
        return jsonify({
            'error': 'Retrieval error',
            'message': str(e)
        }), 500


@app.route('/api/v1/statistics', methods=['GET'])
@require_api_key('read')
def get_statistics():
    """
    Get system statistics and metrics.
    
    Response:
        {
            "total_processed": 1000,
            "fraud_detected": 50,
            "average_processing_time_ms": 150.5,
            "success_rate": 99.5
        }
    """
    try:
        stats = processing_pipeline.get_statistics()
        return jsonify(stats), 200
        
    except Exception as e:
        logger.error(f"Error retrieving statistics: {str(e)}")
        return jsonify({
            'error': 'Statistics error',
            'message': str(e)
        }), 500


@app.route('/api/v1/system/status', methods=['GET'])
@require_api_key('read')
def get_system_status():
    """
    Get comprehensive system status.
    
    Response:
        {
            "status": "operational",
            "components": {...},
            "metrics": {...}
        }
    """
    try:
        status = processing_pipeline.get_system_status()
        return jsonify(status), 200
        
    except Exception as e:
        logger.error(f"Error retrieving system status: {str(e)}")
        return jsonify({
            'error': 'Status error',
            'message': str(e)
        }), 500


@app.route('/api/v1/keys', methods=['POST'])
@require_api_key('admin')
def create_api_key():
    """
    Create a new API key (admin only).
    
    Request Body:
        {
            "name": "my-app",
            "rate_limit": 100,
            "permissions": ["read", "write"]
        }
    
    Response:
        {
            "api_key": "fds_...",
            "name": "my-app",
            "created_at": "2024-01-01T12:00:00Z"
        }
    """
    try:
        data = request.get_json()
        
        if not data or 'name' not in data:
            return jsonify({
                'error': 'Invalid request',
                'message': 'Request must contain "name"'
            }), 400
        
        name = data['name']
        rate_limit = data.get('rate_limit', 60)
        permissions = data.get('permissions', ['read', 'write'])
        
        # Generate new key
        api_key = api_key_manager.generate_key(
            name=name,
            rate_limit=rate_limit,
            permissions=permissions
        )
        
        return jsonify({
            'api_key': api_key,
            'name': name,
            'rate_limit': rate_limit,
            'permissions': permissions,
            'created_at': datetime.now().isoformat()
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating API key: {str(e)}")
        return jsonify({
            'error': 'Creation error',
            'message': str(e)
        }), 500


# ============================================================================
# WebSocket Support for Real-Time Updates
# ============================================================================

# Track connected clients
connected_clients: Set[str] = set()


@socketio.on('connect', namespace='/fraud-detection')
def handle_connect():
    """Handle WebSocket connection."""
    client_id = request.sid
    connected_clients.add(client_id)
    logger.info(f"Client connected: {client_id}")
    
    emit('connection_established', {
        'client_id': client_id,
        'timestamp': datetime.now().isoformat(),
        'message': 'Connected to fraud detection stream'
    })


@socketio.on('disconnect', namespace='/fraud-detection')
def handle_disconnect():
    """Handle WebSocket disconnection."""
    client_id = request.sid
    if client_id in connected_clients:
        connected_clients.remove(client_id)
    logger.info(f"Client disconnected: {client_id}")


@socketio.on('subscribe', namespace='/fraud-detection')
def handle_subscribe(data):
    """
    Subscribe to specific fraud detection events.
    
    Data:
        {
            "filters": {
                "risk_level": ["HIGH", "CRITICAL"],
                "user_id": "user_123"
            }
        }
    """
    client_id = request.sid
    filters = data.get('filters', {})
    
    # Join room based on filters
    if 'risk_level' in filters:
        for level in filters['risk_level']:
            room = f"risk_{level}"
            join_room(room)
            logger.info(f"Client {client_id} subscribed to {room}")
    
    if 'user_id' in filters:
        room = f"user_{filters['user_id']}"
        join_room(room)
        logger.info(f"Client {client_id} subscribed to {room}")
    
    emit('subscription_confirmed', {
        'filters': filters,
        'timestamp': datetime.now().isoformat()
    })


@socketio.on('unsubscribe', namespace='/fraud-detection')
def handle_unsubscribe(data):
    """Unsubscribe from fraud detection events."""
    client_id = request.sid
    filters = data.get('filters', {})
    
    # Leave rooms
    if 'risk_level' in filters:
        for level in filters['risk_level']:
            room = f"risk_{level}"
            leave_room(room)
            logger.info(f"Client {client_id} unsubscribed from {room}")
    
    if 'user_id' in filters:
        room = f"user_{filters['user_id']}"
        leave_room(room)
        logger.info(f"Client {client_id} unsubscribed from {room}")
    
    emit('unsubscription_confirmed', {
        'filters': filters,
        'timestamp': datetime.now().isoformat()
    })


def broadcast_fraud_alert(transaction_id: str, decision: str, risk_level: str, user_id: str):
    """
    Broadcast fraud alert to subscribed clients.
    
    Args:
        transaction_id: Transaction ID
        decision: Fraud decision
        risk_level: Risk level
        user_id: User ID
    """
    alert_data = {
        'transaction_id': transaction_id,
        'decision': decision,
        'risk_level': risk_level,
        'user_id': user_id,
        'timestamp': datetime.now().isoformat()
    }
    
    # Broadcast to all connected clients
    socketio.emit('fraud_alert', alert_data, namespace='/fraud-detection')
    
    # Broadcast to risk level room
    socketio.emit('fraud_alert', alert_data, room=f"risk_{risk_level}", namespace='/fraud-detection')
    
    # Broadcast to user room
    socketio.emit('fraud_alert', alert_data, room=f"user_{user_id}", namespace='/fraud-detection')


# ============================================================================
# API Documentation
# ============================================================================

@app.route('/api/v1/docs', methods=['GET'])
def api_documentation():
    """
    Get API documentation.
    
    Returns comprehensive API documentation in JSON format.
    """
    docs = {
        'version': '1.0.0',
        'title': 'Fraud Detection API',
        'description': 'Production-ready API for real-time fraud detection',
        'base_url': request.host_url + 'api/v1',
        'authentication': {
            'type': 'API Key',
            'header': 'X-API-Key',
            'description': 'Include your API key in the X-API-Key header'
        },
        'rate_limiting': {
            'default': '100 requests per minute',
            'batch': '10 requests per minute'
        },
        'endpoints': [
            {
                'path': '/transactions',
                'method': 'POST',
                'description': 'Submit a single transaction for fraud detection',
                'authentication': 'Required (write permission)',
                'rate_limit': '60 per minute',
                'request_body': {
                    'id': 'string (required)',
                    'user_id': 'string (required)',
                    'amount': 'number (required)',
                    'currency': 'string (required)',
                    'merchant': 'string (required)',
                    'category': 'string (required)',
                    'timestamp': 'string (ISO 8601)',
                    'location': 'object (optional)',
                    'card_type': 'string (optional)',
                    'device_info': 'object (optional)',
                    'ip_address': 'string (optional)'
                },
                'response': {
                    'transaction_id': 'string',
                    'decision': 'string (APPROVE|DECLINE|FLAG|REVIEW)',
                    'is_fraud': 'boolean',
                    'confidence_score': 'number (0-1)',
                    'risk_level': 'string (LOW|MEDIUM|HIGH|CRITICAL)',
                    'reasoning': 'string',
                    'evidence': 'array of strings',
                    'recommendations': 'array of strings',
                    'processing_time_ms': 'number'
                }
            },
            {
                'path': '/transactions/batch',
                'method': 'POST',
                'description': 'Submit multiple transactions for batch processing',
                'authentication': 'Required (write permission)',
                'rate_limit': '10 per minute',
                'request_body': {
                    'transactions': 'array of transaction objects (max 100)'
                },
                'response': {
                    'results': 'array of transaction results',
                    'summary': {
                        'total': 'number',
                        'fraud_detected': 'number',
                        'processing_time_ms': 'number'
                    }
                }
            },
            {
                'path': '/transactions/{transaction_id}',
                'method': 'GET',
                'description': 'Get fraud detection result for a specific transaction',
                'authentication': 'Required (read permission)',
                'response': 'Transaction result object'
            },
            {
                'path': '/statistics',
                'method': 'GET',
                'description': 'Get system statistics and metrics',
                'authentication': 'Required (read permission)',
                'response': {
                    'total_processed': 'number',
                    'fraud_detected': 'number',
                    'average_processing_time_ms': 'number',
                    'success_rate': 'number'
                }
            },
            {
                'path': '/system/status',
                'method': 'GET',
                'description': 'Get comprehensive system status',
                'authentication': 'Required (read permission)',
                'response': 'System status object with component health'
            },
            {
                'path': '/keys',
                'method': 'POST',
                'description': 'Create a new API key',
                'authentication': 'Required (admin permission)',
                'request_body': {
                    'name': 'string (required)',
                    'rate_limit': 'number (optional, default: 60)',
                    'permissions': 'array of strings (optional, default: ["read", "write"])'
                },
                'response': {
                    'api_key': 'string',
                    'name': 'string',
                    'rate_limit': 'number',
                    'permissions': 'array of strings',
                    'created_at': 'string (ISO 8601)'
                }
            }
        ],
        'websocket': {
            'namespace': '/fraud-detection',
            'url': 'ws://' + request.host + '/fraud-detection',
            'events': {
                'connect': 'Establish WebSocket connection',
                'subscribe': 'Subscribe to fraud alerts with filters',
                'unsubscribe': 'Unsubscribe from fraud alerts',
                'fraud_alert': 'Receive real-time fraud alerts',
                'disconnect': 'Close WebSocket connection'
            },
            'subscribe_filters': {
                'risk_level': 'array of risk levels (LOW|MEDIUM|HIGH|CRITICAL)',
                'user_id': 'string - specific user ID'
            }
        },
        'error_codes': {
            '400': 'Bad Request - Invalid input data',
            '401': 'Unauthorized - Missing or invalid API key',
            '403': 'Forbidden - Insufficient permissions',
            '429': 'Too Many Requests - Rate limit exceeded',
            '500': 'Internal Server Error - Processing error',
            '501': 'Not Implemented - Feature not yet available'
        }
    }
    
    return jsonify(docs), 200


# ============================================================================
# Client SDK Generation
# ============================================================================

@app.route('/api/v1/sdk/python', methods=['GET'])
def get_python_sdk():
    """
    Get Python client SDK code.
    
    Returns Python code for a client SDK.
    """
    sdk_code = '''
"""
Fraud Detection API Python Client SDK
"""

import requests
from typing import Dict, List, Optional, Any


class FraudDetectionClient:
    """Client for Fraud Detection API."""
    
    def __init__(self, api_key: str, base_url: str = "http://localhost:5000/api/v1"):
        """
        Initialize the client.
        
        Args:
            api_key: Your API key
            base_url: Base URL of the API
        """
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }
    
    def submit_transaction(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """
        Submit a transaction for fraud detection.
        
        Args:
            transaction: Transaction data dictionary
            
        Returns:
            Fraud detection result
        """
        response = requests.post(
            f"{self.base_url}/transactions",
            json=transaction,
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def submit_batch(self, transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Submit multiple transactions for batch processing.
        
        Args:
            transactions: List of transaction data dictionaries
            
        Returns:
            Batch processing results
        """
        response = requests.post(
            f"{self.base_url}/transactions/batch",
            json={"transactions": transactions},
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get system statistics."""
        response = requests.get(
            f"{self.base_url}/statistics",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get system status."""
        response = requests.get(
            f"{self.base_url}/system/status",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()


# Example usage
if __name__ == "__main__":
    client = FraudDetectionClient(api_key="your_api_key_here")
    
    transaction = {
        "id": "txn_001",
        "user_id": "user_123",
        "amount": 150.00,
        "currency": "USD",
        "merchant": "Amazon",
        "category": "retail",
        "timestamp": "2024-01-01T12:00:00Z"
    }
    
    result = client.submit_transaction(transaction)
    print(f"Decision: {result['decision']}")
    print(f"Is Fraud: {result['is_fraud']}")
    print(f"Confidence: {result['confidence_score']}")
'''
    
    return Response(sdk_code, mimetype='text/plain')


@app.route('/api/v1/sdk/javascript', methods=['GET'])
def get_javascript_sdk():
    """
    Get JavaScript client SDK code.
    
    Returns JavaScript code for a client SDK.
    """
    sdk_code = '''
/**
 * Fraud Detection API JavaScript Client SDK
 */

class FraudDetectionClient {
    /**
     * Initialize the client.
     * @param {string} apiKey - Your API key
     * @param {string} baseUrl - Base URL of the API
     */
    constructor(apiKey, baseUrl = 'http://localhost:5000/api/v1') {
        this.apiKey = apiKey;
        this.baseUrl = baseUrl;
        this.headers = {
            'X-API-Key': apiKey,
            'Content-Type': 'application/json'
        };
    }
    
    /**
     * Submit a transaction for fraud detection.
     * @param {Object} transaction - Transaction data
     * @returns {Promise<Object>} Fraud detection result
     */
    async submitTransaction(transaction) {
        const response = await fetch(`${this.baseUrl}/transactions`, {
            method: 'POST',
            headers: this.headers,
            body: JSON.stringify(transaction)
        });
        
        if (!response.ok) {
            throw new Error(`API error: ${response.statusText}`);
        }
        
        return await response.json();
    }
    
    /**
     * Submit multiple transactions for batch processing.
     * @param {Array<Object>} transactions - List of transactions
     * @returns {Promise<Object>} Batch processing results
     */
    async submitBatch(transactions) {
        const response = await fetch(`${this.baseUrl}/transactions/batch`, {
            method: 'POST',
            headers: this.headers,
            body: JSON.stringify({ transactions })
        });
        
        if (!response.ok) {
            throw new Error(`API error: ${response.statusText}`);
        }
        
        return await response.json();
    }
    
    /**
     * Get system statistics.
     * @returns {Promise<Object>} System statistics
     */
    async getStatistics() {
        const response = await fetch(`${this.baseUrl}/statistics`, {
            headers: this.headers
        });
        
        if (!response.ok) {
            throw new Error(`API error: ${response.statusText}`);
        }
        
        return await response.json();
    }
    
    /**
     * Get system status.
     * @returns {Promise<Object>} System status
     */
    async getSystemStatus() {
        const response = await fetch(`${this.baseUrl}/system/status`, {
            headers: this.headers
        });
        
        if (!response.ok) {
            throw new Error(`API error: ${response.statusText}`);
        }
        
        return await response.json();
    }
}

// Example usage
const client = new FraudDetectionClient('your_api_key_here');

const transaction = {
    id: 'txn_001',
    user_id: 'user_123',
    amount: 150.00,
    currency: 'USD',
    merchant: 'Amazon',
    category: 'retail',
    timestamp: new Date().toISOString()
};

client.submitTransaction(transaction)
    .then(result => {
        console.log('Decision:', result.decision);
        console.log('Is Fraud:', result.is_fraud);
        console.log('Confidence:', result.confidence_score);
    })
    .catch(error => console.error('Error:', error));
'''
    
    return Response(sdk_code, mimetype='text/plain')


# ============================================================================
# Main Application Entry Point
# ============================================================================

def main():
    """Run the Flask application."""
    logger.info("Starting Fraud Detection API Server")
    logger.info(f"API Documentation available at: http://localhost:5000/api/v1/docs")
    logger.info(f"WebSocket endpoint: ws://localhost:5000/fraud-detection")
    
    # Start streaming processor if enabled
    if pipeline_config.enable_streaming:
        processing_pipeline.start_streaming()
    
    # Run the application
    socketio.run(
        app,
        host='0.0.0.0',
        port=5000,
        debug=False,
        use_reloader=False
    )


if __name__ == '__main__':
    main()
