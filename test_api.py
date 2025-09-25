#!/usr/bin/env python3
"""Test the standalone fraud detection API"""

import requests
import json
import time

API_BASE = "http://localhost:5000"

def test_api():
    """Test all API endpoints"""
    
    print("🧪 Testing Standalone Fraud Detection API")
    print("=" * 50)
    
    # Test 1: Health check
    print("\n1. Testing Health Check:")
    try:
        response = requests.get(f"{API_BASE}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return
    
    # Test 2: Get currencies
    print("\n2. Testing Currency Endpoint:")
    try:
        response = requests.get(f"{API_BASE}/currencies")
        data = response.json()
        print(f"Status: {response.status_code}")
        print(f"Supported currencies: {data['total_supported']}")
        print(f"Base currency: {data['base_currency']}")
        
        # Show a few currencies
        currencies = list(data['currencies'].keys())[:5]
        print(f"Sample currencies: {currencies}")
    except Exception as e:
        print(f"❌ Currency test failed: {e}")
    
    # Test 3: Analyze normal transaction
    print("\n3. Testing Normal Transaction Analysis:")
    normal_transaction = {
        "transaction": {
            "id": "test_001",
            "user_id": "user_test",
            "amount": 50.0,
            "currency": "USD",
            "merchant": "STARBUCKS",
            "category": "RESTAURANT",
            "location": "NEW_YORK_NY",
            "card_type": "CREDIT"
        }
    }
    
    try:
        response = requests.post(f"{API_BASE}/analyze", json=normal_transaction)
        data = response.json()
        print(f"Status: {response.status_code}")
        print(f"Flagged: {data['result']['is_flagged']}")
        print(f"Risk Score: {data['result']['risk_score']}")
        print(f"Flags: {data['result']['flags']}")
    except Exception as e:
        print(f"❌ Normal transaction test failed: {e}")
    
    # Test 4: Analyze suspicious transaction
    print("\n4. Testing Suspicious Transaction Analysis:")
    suspicious_transaction = {
        "transaction": {
            "id": "test_002",
            "user_id": "user_test",
            "amount": 15000.0,
            "currency": "USD",
            "merchant": "UNKNOWN_MERCHANT",
            "category": "OTHER",
            "location": "FOREIGN_COUNTRY",
            "card_type": "CREDIT"
        }
    }
    
    try:
        response = requests.post(f"{API_BASE}/analyze", json=suspicious_transaction)
        data = response.json()
        print(f"Status: {response.status_code}")
        print(f"Flagged: {data['result']['is_flagged']}")
        print(f"Risk Score: {data['result']['risk_score']}")
        print(f"Flags: {data['result']['flags']}")
    except Exception as e:
        print(f"❌ Suspicious transaction test failed: {e}")
    
    # Test 5: Multi-currency transaction
    print("\n5. Testing Multi-Currency Transaction:")
    multicurrency_transaction = {
        "transaction": {
            "id": "test_003",
            "user_id": "user_test",
            "amount": 5000000.0,  # 5M Nigerian Naira
            "currency": "NGN",
            "merchant": "AMAZON",
            "category": "SHOPPING",
            "location": "HIGH_RISK_COUNTRY",
            "card_type": "CREDIT"
        }
    }
    
    try:
        response = requests.post(f"{API_BASE}/analyze", json=multicurrency_transaction)
        data = response.json()
        print(f"Status: {response.status_code}")
        print(f"Amount: ₦5,000,000 NGN (${data['result']['usd_equivalent']:.2f} USD)")
        print(f"Flagged: {data['result']['is_flagged']}")
        print(f"Risk Score: {data['result']['risk_score']}")
        print(f"Flags: {data['result']['flags']}")
    except Exception as e:
        print(f"❌ Multi-currency test failed: {e}")
    
    # Test 6: Generate test data
    print("\n6. Testing Test Data Generation:")
    try:
        response = requests.post(f"{API_BASE}/generate-test-data", json={
            "count": 5,
            "fraud_rate": 0.4
        })
        data = response.json()
        print(f"Status: {response.status_code}")
        print(f"Generated {data['count']} transactions")
        print(f"Fraud rate: {data['fraud_rate']}")
        
        # Show first transaction
        if data['transactions']:
            tx = data['transactions'][0]
            print(f"Sample: {tx['amount']} {tx.get('currency', 'USD')} at {tx['merchant']}")
    except Exception as e:
        print(f"❌ Test data generation failed: {e}")
    
    # Test 7: Batch analysis
    print("\n7. Testing Batch Analysis:")
    batch_transactions = {
        "transactions": [
            {
                "user_id": "batch_user_1",
                "amount": 100.0,
                "currency": "USD",
                "merchant": "WALMART"
            },
            {
                "user_id": "batch_user_2", 
                "amount": 20000.0,
                "currency": "USD",
                "merchant": "UNKNOWN_MERCHANT"
            },
            {
                "user_id": "batch_user_3",
                "amount": 2000000.0,
                "currency": "UGX",
                "merchant": "SHELL"
            }
        ]
    }
    
    try:
        response = requests.post(f"{API_BASE}/batch-analyze", json=batch_transactions)
        data = response.json()
        print(f"Status: {response.status_code}")
        print(f"Total transactions: {data['summary']['total_transactions']}")
        print(f"Flagged: {data['summary']['flagged_transactions']}")
        print(f"Clean: {data['summary']['clean_transactions']}")
    except Exception as e:
        print(f"❌ Batch analysis failed: {e}")
    
    # Test 8: Update rules
    print("\n8. Testing Rule Updates:")
    try:
        response = requests.post(f"{API_BASE}/update-rules", json={
            "max_amount_threshold": 10000.0,
            "max_transactions_per_hour": 5
        })
        data = response.json()
        print(f"Status: {response.status_code}")
        print(f"Updated rules: {data['updated_rules']}")
    except Exception as e:
        print(f"❌ Rule update failed: {e}")
    
    # Test 9: Get statistics
    print("\n9. Testing Statistics:")
    try:
        response = requests.get(f"{API_BASE}/stats")
        data = response.json()
        print(f"Status: {response.status_code}")
        print(f"Total transactions processed: {data['statistics']['total_transactions_processed']}")
        print(f"Current threshold: ${data['statistics']['current_rules']['max_amount_threshold']}")
    except Exception as e:
        print(f"❌ Statistics test failed: {e}")

def test_velocity():
    """Test velocity detection with rapid transactions"""
    print("\n🚀 Testing Velocity Detection:")
    print("=" * 30)
    
    user_id = "velocity_test_user"
    
    for i in range(7):  # Send 7 rapid transactions
        transaction = {
            "transaction": {
                "id": f"velocity_{i}",
                "user_id": user_id,
                "amount": 500.0,
                "currency": "USD",
                "merchant": "AMAZON"
            }
        }
        
        try:
            response = requests.post(f"{API_BASE}/analyze", json=transaction)
            data = response.json()
            
            print(f"Transaction {i+1}: Flagged={data['result']['is_flagged']}, Score={data['result']['risk_score']}")
            
            if "velocity" in str(data['result']['flags']).lower():
                print(f"  🚨 Velocity flag detected!")
            
            time.sleep(0.1)  # Small delay
            
        except Exception as e:
            print(f"❌ Velocity test {i+1} failed: {e}")

if __name__ == "__main__":
    print("🏦 Fraud Detection API Test Suite")
    print("=" * 40)
    print("Make sure the API is running: python standalone_fraud_api.py")
    print("=" * 40)
    
    # Wait a moment for user to start API
    input("Press Enter when API is running...")
    
    # Run tests
    test_api()
    test_velocity()
    
    print("\n✅ API Testing Complete!")
    print("🌐 Visit http://localhost:5000/ for API documentation")