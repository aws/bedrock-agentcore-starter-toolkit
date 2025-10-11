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

from transaction_processing_pipeline import TransactionProcessingPipeline, SystemConfiguration

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
