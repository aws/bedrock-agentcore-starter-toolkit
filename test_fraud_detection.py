#!/usr/bin/env python3
"""Test the fraud detection agent"""

import json
from datetime import datetime
from fraud_detection_agent import fraud_detection_handler, fraud_agent
from transaction_generator import TransactionGenerator

def test_fraud_detection():
    """Test fraud detection with sample transactions"""
    
    generator = TransactionGenerator()
    
    print("🔍 Testing Fraud Detection Agent")
    print("=" * 50)
    
    # Test normal transaction
    print("\n1. Testing Normal Transaction:")
    normal_tx = generator.generate_normal_transaction()
    normal_tx["amount"] = 50.0  # Ensure it's normal
    
    payload = {"transaction": normal_tx}
    result = fraud_detection_handler(payload)
    
    print(f"Transaction: ${normal_tx['amount']} at {normal_tx['merchant']}")
    print(f"Result: {json.dumps(result, indent=2)}")
    
    # Test high amount transaction
    print("\n2. Testing High Amount Transaction:")
    high_amount_tx = generator.generate_normal_transaction()
    high_amount_tx["amount"] = 10000.0  # Trigger high amount flag
    
    payload = {"transaction": high_amount_tx}
    result = fraud_detection_handler(payload)
    
    print(f"Transaction: ${high_amount_tx['amount']} at {high_amount_tx['merchant']}")
    print(f"Result: {json.dumps(result, indent=2)}")
    
    # Test suspicious merchant
    print("\n3. Testing Suspicious Merchant:")
    suspicious_tx = generator.generate_normal_transaction()
    suspicious_tx["merchant"] = "UNKNOWN_MERCHANT"
    suspicious_tx["amount"] = 200.0
    
    payload = {"transaction": suspicious_tx}
    result = fraud_detection_handler(payload)
    
    print(f"Transaction: ${suspicious_tx['amount']} at {suspicious_tx['merchant']}")
    print(f"Result: {json.dumps(result, indent=2)}")
    
    # Test velocity (multiple transactions)
    print("\n4. Testing High Velocity:")
    user_id = "user_0001"
    
    for i in range(6):  # Generate 6 quick transactions
        velocity_tx = generator.generate_normal_transaction()
        velocity_tx["user_id"] = user_id
        velocity_tx["amount"] = 100.0
        
        payload = {"transaction": velocity_tx}
        result = fraud_detection_handler(payload)
        
        print(f"Transaction {i+1}: ${velocity_tx['amount']} - Flagged: {result['result']['is_flagged']}")
    
    # Test admin criteria update
    print("\n5. Testing Admin Criteria Update:")
    print("Current max amount threshold:", fraud_agent.criteria.max_amount_threshold)
    
    # Admin updates criteria
    fraud_agent.update_criteria({
        "max_amount_threshold": 1000.0,  # Lower threshold
        "max_transactions_per_hour": 3   # Stricter velocity
    })
    
    print("Updated max amount threshold:", fraud_agent.criteria.max_amount_threshold)
    
    # Test with new criteria
    test_tx = generator.generate_normal_transaction()
    test_tx["amount"] = 1500.0  # Now exceeds new threshold
    
    payload = {"transaction": test_tx}
    result = fraud_detection_handler(payload)
    
    print(f"Transaction with new criteria: ${test_tx['amount']}")
    print(f"Flagged: {result['result']['is_flagged']}")

if __name__ == "__main__":
    test_fraud_detection()