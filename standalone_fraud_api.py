#!/usr/bin/env python3
"""Standalone fraud detection API (no Bedrock dependency)"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from currency_converter import CurrencyConverter
from transaction_generator import TransactionGenerator
from data_loader import DataLoader

# Create Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for web requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize components (without Bedrock)
converter = CurrencyConverter()
generator = TransactionGenerator()
data_loader = DataLoader()

# Simple in-memory fraud detection (no AI for standalone version)
class StandaloneFraudDetector:
    """Fraud detection without AI/Bedrock dependency"""
    
    def __init__(self):
        self.transaction_history = []
        self.max_amount_threshold = 5000  # USD
        self.max_transactions_per_hour = 10
        self.suspicious_merchants = ["UNKNOWN_MERCHANT", "CASH_ADVANCE", "CRYPTO_EXCHANGE"]
        self.risky_locations = ["FOREIGN_COUNTRY", "HIGH_RISK_COUNTRY", "OFFSHORE_TERRITORY"]
        
    def analyze_transaction(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze transaction for fraud (rule-based only)"""
        flags = []
        risk_score = 0
        
        # Extract transaction data
        amount = float(transaction.get('amount', 0))
        currency = transaction.get('currency', 'USD')
        merchant = transaction.get('merchant', '')
        location = transaction.get('location', '')
        user_id = transaction.get('user_id', '')
        
        # Convert to USD for consistent analysis
        usd_amount = converter.convert_to_usd(amount, currency)
        
        # Rule 1: High amount check
        if usd_amount > self.max_amount_threshold:
            formatted_amount = converter.format_amount(amount, currency)
            flags.append(f"High amount: {formatted_amount} (${usd_amount:.2f} USD)")
            risk_score += 40
        
        # Rule 2: Suspicious merchant
        if merchant in self.suspicious_merchants:
            flags.append(f"Suspicious merchant: {merchant}")
            risk_score += 35
        
        # Rule 3: Risky location
        if location in self.risky_locations:
            flags.append(f"Risky location: {location}")
            risk_score += 25
        
        # Rule 4: Currency risk
        currency_info = converter.get_currency_info(currency)
        if currency_info and currency_info.risk_level == "high":
            flags.append(f"High-risk currency: {currency}")
            risk_score += 20
        
        # Rule 5: Velocity check
        recent_count = self._count_recent_transactions(user_id, minutes=60)
        if recent_count > self.max_transactions_per_hour:
            flags.append(f"High velocity: {recent_count} transactions in last hour")
            risk_score += 30
        
        # Rule 6: Currency-location mismatch
        if self._is_currency_location_mismatch(currency, location):
            flags.append(f"Currency-location mismatch: {currency} in {location}")
            risk_score += 15
        
        # Store transaction for velocity analysis
        self.transaction_history.append({
            'user_id': user_id,
            'timestamp': datetime.now(),
            'amount': amount,
            'currency': currency
        })
        
        # Keep only last 1000 transactions
        if len(self.transaction_history) > 1000:
            self.transaction_history = self.transaction_history[-1000:]
        
        is_flagged = len(flags) > 0 or risk_score > 50
        
        return {
            'transaction_id': transaction.get('id', 'unknown'),
            'is_flagged': is_flagged,
            'risk_score': risk_score,
            'flags': flags,
            'usd_equivalent': usd_amount,
            'analysis_type': 'rule_based',
            'timestamp': datetime.now().isoformat()
        }
    
    def _count_recent_transactions(self, user_id: str, minutes: int = 60) -> int:
        """Count recent transactions for velocity check"""
        cutoff = datetime.now().timestamp() - (minutes * 60)
        count = 0
        
        for tx in self.transaction_history:
            if (tx['user_id'] == user_id and 
                tx['timestamp'].timestamp() > cutoff):
                count += 1
        
        return count
    
    def _is_currency_location_mismatch(self, currency: str, location: str) -> bool:
        """Check if currency doesn't match location"""
        location_currency_map = {
            'NEW_YORK_NY': ['USD'],
            'LOS_ANGELES_CA': ['USD'],
            'CHICAGO_IL': ['USD'],
            'FOREIGN_COUNTRY': ['EUR', 'GBP', 'JPY'],
            'HIGH_RISK_COUNTRY': ['KES', 'UGX', 'TZS', 'NGN'],
        }
        
        expected_currencies = location_currency_map.get(location, [currency])
        return currency not in expected_currencies

# Initialize fraud detector
fraud_detector = StandaloneFraudDetector()

# API Routes

@app.route('/', methods=['GET'])
def home():
    """API documentation page"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Fraud Detection API</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .endpoint { background: #f5f5f5; padding: 15px; margin: 10px 0; border-radius: 5px; }
            .method { color: #fff; padding: 3px 8px; border-radius: 3px; font-weight: bold; }
            .get { background: #61affe; }
            .post { background: #49cc90; }
            code { background: #f8f8f8; padding: 2px 5px; border-radius: 3px; }
        </style>
    </head>
    <body>
        <h1>🏦 Fraud Detection API</h1>
        <p>Standalone multi-currency fraud detection service</p>
        
        <div class="endpoint">
            <span class="method post">POST</span> <strong>/analyze</strong>
            <p>Analyze a transaction for fraud indicators</p>
            <p><strong>Body:</strong> <code>{"transaction": {...}}</code></p>
        </div>
        
        <div class="endpoint">
            <span class="method post">POST</span> <strong>/batch-analyze</strong>
            <p>Analyze multiple transactions</p>
            <p><strong>Body:</strong> <code>{"transactions": [...]}</code></p>
        </div>
        
        <div class="endpoint">
            <span class="method get">GET</span> <strong>/currencies</strong>
            <p>Get supported currencies and exchange rates</p>
        </div>
        
        <div class="endpoint">
            <span class="method post">POST</span> <strong>/generate-test-data</strong>
            <p>Generate test transactions</p>
            <p><strong>Body:</strong> <code>{"count": 10, "fraud_rate": 0.2}</code></p>
        </div>
        
        <div class="endpoint">
            <span class="method get">GET</span> <strong>/health</strong>
            <p>Health check endpoint</p>
        </div>
        
        <div class="endpoint">
            <span class="method post">POST</span> <strong>/update-rules</strong>
            <p>Update fraud detection rules</p>
            <p><strong>Body:</strong> <code>{"max_amount_threshold": 10000}</code></p>
        </div>
        
        <h3>Example Transaction:</h3>
        <pre><code>{
  "transaction": {
    "id": "tx_12345",
    "user_id": "user_001",
    "amount": 1500.00,
    "currency": "USD",
    "merchant": "AMAZON",
    "category": "SHOPPING",
    "location": "NEW_YORK_NY",
    "timestamp": "2024-09-24T10:30:00",
    "card_type": "CREDIT"
  }
}</code></pre>
    </body>
    </html>
    """
    return html

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'fraud-detection-api',
        'version': '1.0.0',
        'timestamp': datetime.now().isoformat(),
        'supported_currencies': len(converter.get_supported_currencies()),
        'transactions_analyzed': len(fraud_detector.transaction_history)
    })

@app.route('/analyze', methods=['POST'])
def analyze_transaction():
    """Analyze a single transaction for fraud"""
    try:
        data = request.get_json()
        
        if not data or 'transaction' not in data:
            return jsonify({
                'error': 'Missing transaction data',
                'message': 'Request body must contain "transaction" field'
            }), 400
        
        transaction = data['transaction']
        
        # Validate required fields
        required_fields = ['amount', 'merchant', 'user_id']
        missing_fields = [field for field in required_fields if field not in transaction]
        
        if missing_fields:
            return jsonify({
                'error': 'Missing required fields',
                'missing_fields': missing_fields
            }), 400
        
        # Set defaults for optional fields
        transaction.setdefault('currency', 'USD')
        transaction.setdefault('location', 'UNKNOWN')
        transaction.setdefault('category', 'OTHER')
        transaction.setdefault('timestamp', datetime.now().isoformat())
        transaction.setdefault('id', f"tx_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        
        # Analyze transaction
        result = fraud_detector.analyze_transaction(transaction)
        
        logger.info(f"Analyzed transaction {result['transaction_id']}: flagged={result['is_flagged']}")
        
        return jsonify({
            'status': 'success',
            'result': result
        })
        
    except Exception as e:
        logger.error(f"Error analyzing transaction: {str(e)}")
        return jsonify({
            'error': 'Analysis failed',
            'message': str(e)
        }), 500

@app.route('/batch-analyze', methods=['POST'])
def batch_analyze():
    """Analyze multiple transactions"""
    try:
        data = request.get_json()
        
        if not data or 'transactions' not in data:
            return jsonify({
                'error': 'Missing transactions data',
                'message': 'Request body must contain "transactions" array'
            }), 400
        
        transactions = data['transactions']
        
        if not isinstance(transactions, list):
            return jsonify({
                'error': 'Invalid data type',
                'message': 'transactions must be an array'
            }), 400
        
        results = []
        
        for i, transaction in enumerate(transactions):
            try:
                # Set defaults
                transaction.setdefault('currency', 'USD')
                transaction.setdefault('location', 'UNKNOWN')
                transaction.setdefault('id', f"batch_tx_{i}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
                
                result = fraud_detector.analyze_transaction(transaction)
                results.append(result)
                
            except Exception as e:
                results.append({
                    'transaction_id': transaction.get('id', f'tx_{i}'),
                    'error': str(e),
                    'is_flagged': True,  # Flag errors as suspicious
                    'risk_score': 100
                })
        
        flagged_count = sum(1 for r in results if r.get('is_flagged', False))
        
        return jsonify({
            'status': 'success',
            'summary': {
                'total_transactions': len(transactions),
                'flagged_transactions': flagged_count,
                'clean_transactions': len(transactions) - flagged_count
            },
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Error in batch analysis: {str(e)}")
        return jsonify({
            'error': 'Batch analysis failed',
            'message': str(e)
        }), 500

@app.route('/currencies', methods=['GET'])
def get_currencies():
    """Get supported currencies and exchange rates"""
    try:
        currencies = {}
        
        for code in converter.get_supported_currencies():
            currency_info = converter.get_currency_info(code)
            currencies[code] = {
                'name': currency_info.name,
                'symbol': currency_info.symbol,
                'exchange_rate': currency_info.exchange_rate,
                'risk_level': currency_info.risk_level,
                'high_threshold': currency_info.high_threshold
            }
        
        return jsonify({
            'status': 'success',
            'base_currency': converter.base_currency,
            'currencies': currencies,
            'total_supported': len(currencies)
        })
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to get currencies',
            'message': str(e)
        }), 500

@app.route('/generate-test-data', methods=['POST'])
def generate_test_data():
    """Generate test transaction data"""
    try:
        data = request.get_json() or {}
        
        count = data.get('count', 10)
        fraud_rate = data.get('fraud_rate', 0.2)
        
        if count > 100:
            return jsonify({
                'error': 'Too many transactions requested',
                'message': 'Maximum 100 transactions per request'
            }), 400
        
        transactions = []
        
        for i in range(count):
            if i < count * fraud_rate:
                # Generate suspicious transaction
                tx = generator.generate_suspicious_transaction()
            else:
                # Generate normal transaction
                tx = generator.generate_normal_transaction()
            
            transactions.append(tx)
        
        return jsonify({
            'status': 'success',
            'transactions': transactions,
            'count': len(transactions),
            'fraud_rate': fraud_rate
        })
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to generate test data',
            'message': str(e)
        }), 500

@app.route('/update-rules', methods=['POST'])
def update_rules():
    """Update fraud detection rules"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'error': 'No data provided',
                'message': 'Request body must contain rule updates'
            }), 400
        
        updated_rules = {}
        
        # Update rules if provided
        if 'max_amount_threshold' in data:
            fraud_detector.max_amount_threshold = float(data['max_amount_threshold'])
            updated_rules['max_amount_threshold'] = fraud_detector.max_amount_threshold
        
        if 'max_transactions_per_hour' in data:
            fraud_detector.max_transactions_per_hour = int(data['max_transactions_per_hour'])
            updated_rules['max_transactions_per_hour'] = fraud_detector.max_transactions_per_hour
        
        if 'suspicious_merchants' in data:
            fraud_detector.suspicious_merchants = data['suspicious_merchants']
            updated_rules['suspicious_merchants'] = fraud_detector.suspicious_merchants
        
        logger.info(f"Updated fraud detection rules: {updated_rules}")
        
        return jsonify({
            'status': 'success',
            'message': 'Rules updated successfully',
            'updated_rules': updated_rules,
            'current_rules': {
                'max_amount_threshold': fraud_detector.max_amount_threshold,
                'max_transactions_per_hour': fraud_detector.max_transactions_per_hour,
                'suspicious_merchants': fraud_detector.suspicious_merchants
            }
        })
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to update rules',
            'message': str(e)
        }), 500

@app.route('/stats', methods=['GET'])
def get_stats():
    """Get fraud detection statistics"""
    try:
        total_transactions = len(fraud_detector.transaction_history)
        
        # Calculate stats from recent transactions
        recent_flagged = 0
        currency_counts = {}
        
        for tx in fraud_detector.transaction_history[-100:]:  # Last 100 transactions
            currency = tx.get('currency', 'USD')
            currency_counts[currency] = currency_counts.get(currency, 0) + 1
        
        return jsonify({
            'status': 'success',
            'statistics': {
                'total_transactions_processed': total_transactions,
                'recent_currency_distribution': currency_counts,
                'current_rules': {
                    'max_amount_threshold': fraud_detector.max_amount_threshold,
                    'max_transactions_per_hour': fraud_detector.max_transactions_per_hour,
                    'suspicious_merchants_count': len(fraud_detector.suspicious_merchants)
                },
                'supported_currencies': len(converter.get_supported_currencies())
            }
        })
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to get statistics',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    print("🏦 Starting Standalone Fraud Detection API")
    print("=" * 50)
    print(f"📊 Supported currencies: {len(converter.get_supported_currencies())}")
    print(f"🔍 Detection method: Rule-based (no AI dependency)")
    print(f"🌐 API documentation: http://localhost:5000/")
    print("=" * 50)
    
    # Run Flask app
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )