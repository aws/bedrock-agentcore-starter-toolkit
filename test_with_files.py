#!/usr/bin/env python3
"""Test fraud detection using data from files"""

from data_loader import DataLoader
from fraud_detection_agent import fraud_detection_handler
from transaction_generator import TransactionGenerator

def test_with_file_data():
    """Test fraud detection using file-based data"""
    
    # Load data
    loader = DataLoader()
    loader.print_data_summary()
    
    generator = TransactionGenerator()
    
    print("\n🧪 Testing with File-Based Data")
    print("=" * 50)
    
    # Test 1: Use sample transactions from CSV
    print("\n1. Testing Sample Transactions from CSV:")
    sample_transactions = loader.get_sample_transactions()
    
    for i, tx in enumerate(sample_transactions[:3]):  # Test first 3
        print(f"\n--- Sample Transaction {i+1} ---")
        print(f"Expected fraud: {tx['is_fraud']}")
        
        payload = {"transaction": tx}
        result = fraud_detection_handler(payload)
        
        print(f"Transaction: ${tx['amount']} at {tx['merchant']}")
        if result.get('result'):
            print(f"  - AI Flagged: {result['result']['is_flagged']}")
            print(f"  - Risk Score: {result['result']['risk_score']}")
            print(f"  - Flags: {result['result']['flags']}")
            
            # Check if AI agrees with expected result
            ai_flagged = result['result']['is_flagged']
            expected_fraud = tx['is_fraud']
            match = "✅ MATCH" if ai_flagged == expected_fraud else "❌ MISMATCH"
            print(f"  - {match} (Expected: {expected_fraud}, AI: {ai_flagged})")
    
    # Test 2: Test with different user risk profiles
    print("\n2. Testing User Risk Profiles:")
    
    # High-risk user
    high_risk_user = "user_0005"  # Charlie Wilson (high risk)
    user_profile = loader.get_user_profile(high_risk_user)
    print(f"\n--- High Risk User: {user_profile.name} ---")
    
    tx = generator.generate_normal_transaction()
    tx["user_id"] = high_risk_user
    tx["amount"] = 500.0  # Normal amount
    
    payload = {"transaction": tx}
    result = fraud_detection_handler(payload)
    
    print(f"User: {user_profile.name} ({user_profile.risk_profile} risk)")
    print(f"Transaction: ${tx['amount']} at {tx['merchant']}")
    if result.get('result'):
        print(f"  - Flagged: {result['result']['is_flagged']}")
        print(f"  - Risk Score: {result['result']['risk_score']}")
    
    # Test 3: Test category-based amounts
    print("\n3. Testing Category-Based Transactions:")
    
    categories_to_test = ["GROCERY", "CASH_ADVANCE", "GAMBLING"]
    
    for category in categories_to_test:
        category_info = loader.get_category_by_name(category)
        if category_info:
            print(f"\n--- {category} Category ---")
            print(f"Risk level: {category_info['risk_level']}")
            print(f"Typical range: ${category_info['typical_amount_range'][0]}-${category_info['typical_amount_range'][1]}")
            
            # Generate transaction in typical range
            min_amt, max_amt = category_info['typical_amount_range']
            test_amount = (min_amt + max_amt) / 2  # Middle of range
            
            tx = generator.generate_normal_transaction()
            tx["category"] = category
            tx["amount"] = test_amount
            
            payload = {"transaction": tx}
            result = fraud_detection_handler(payload)
            
            print(f"Test amount: ${test_amount}")
            if result.get('result'):
                print(f"  - Flagged: {result['result']['is_flagged']}")
                print(f"  - Risk Score: {result['result']['risk_score']}")
    
    # Test 4: Location-based risk
    print("\n4. Testing Location-Based Risk:")
    
    safe_location = loader.get_safe_locations()[0]
    risky_location = loader.get_risky_locations()[0]
    
    for location_type, location in [("Safe", safe_location), ("Risky", risky_location)]:
        print(f"\n--- {location_type} Location: {location} ---")
        
        tx = generator.generate_normal_transaction()
        tx["location"] = location
        tx["amount"] = 200.0  # Normal amount
        
        payload = {"transaction": tx}
        result = fraud_detection_handler(payload)
        
        print(f"Transaction: ${tx['amount']} in {location}")
        if result.get('result'):
            print(f"  - Flagged: {result['result']['is_flagged']}")
            print(f"  - Risk Score: {result['result']['risk_score']}")
            print(f"  - Flags: {result['result']['flags']}")

def test_data_loading():
    """Test that data loading works correctly"""
    print("🔍 Testing Data Loading")
    print("=" * 30)
    
    loader = DataLoader()
    
    # Test merchants
    print(f"✅ Normal merchants: {len(loader.get_normal_merchants())}")
    print(f"⚠️ Suspicious merchants: {len(loader.get_suspicious_merchants())}")
    
    # Test locations  
    print(f"✅ Safe locations: {len(loader.get_safe_locations())}")
    print(f"⚠️ Risky locations: {len(loader.get_risky_locations())}")
    
    # Test users
    print(f"👥 Total users: {len(loader.get_all_user_ids())}")
    
    # Show user risk distribution
    risk_counts = {}
    for user_id in loader.get_all_user_ids():
        profile = loader.get_user_profile(user_id)
        risk = profile.risk_profile
        risk_counts[risk] = risk_counts.get(risk, 0) + 1
    
    print("Risk profile distribution:")
    for risk, count in risk_counts.items():
        print(f"  {risk}: {count} users")
    
    # Test sample transactions
    fraud_txs = loader.get_sample_transactions(fraud_only=True)
    total_txs = loader.get_sample_transactions()
    print(f"💳 Sample transactions: {len(total_txs)} total, {len(fraud_txs)} fraudulent")

if __name__ == "__main__":
    print("🏦 File-Based Fraud Detection Testing")
    print("=" * 40)
    
    # First test data loading
    test_data_loading()
    
    print("\n" + "="*40)
    
    # Then test fraud detection
    test_with_file_data()