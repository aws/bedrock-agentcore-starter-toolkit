#!/usr/bin/env python3
"""Test multi-currency fraud detection"""

from currency_converter import CurrencyConverter
from fraud_detection_agent import fraud_detection_handler
from transaction_generator import TransactionGenerator
from datetime import datetime

def test_multicurrency_fraud_detection():
    """Test fraud detection with multiple currencies"""
    
    converter = CurrencyConverter()
    generator = TransactionGenerator()
    
    print("🌍 Multi-Currency Fraud Detection Test")
    print("=" * 50)
    
    # Show currency support
    converter.print_currency_summary()
    
    print("\n🧪 Testing Currency-Specific Transactions:")
    print("=" * 50)
    
    # Test 1: High amount in different currencies
    print("\n1. High Amount Tests (Different Currencies):")
    
    high_amount_tests = [
        (10000, "USD"),    # $10,000 USD
        (8000, "EUR"),     # €8,000 EUR  
        (15000000, "UGX"), # 15M Ugandan Shillings
        (5000000, "NGN"),  # 5M Nigerian Naira
        (1000000, "JPY"),  # 1M Japanese Yen
    ]
    
    for amount, currency in high_amount_tests:
        print(f"\n--- Testing {converter.format_amount(amount, currency)} ---")
        
        # Create transaction
        tx = generator.generate_normal_transaction()
        tx["amount"] = amount
        tx["currency"] = currency
        tx["location"] = generator._get_currency_for_location("FOREIGN_COUNTRY")
        
        # Test fraud detection
        payload = {"transaction": tx}
        result = fraud_detection_handler(payload)
        
        usd_equiv = converter.convert_to_usd(amount, currency)
        print(f"Amount: {converter.format_amount(amount, currency)} (${usd_equiv:.2f} USD)")
        
        if result.get('result'):
            print(f"  - Flagged: {result['result']['is_flagged']}")
            print(f"  - Risk Score: {result['result']['risk_score']}")
            print(f"  - Flags: {result['result']['flags']}")
    
    # Test 2: Currency-Location Mismatches
    print("\n2. Currency-Location Mismatch Tests:")
    
    mismatch_tests = [
        ("USD", "FOREIGN_COUNTRY"),      # USD in foreign country
        ("EUR", "NEW_YORK_NY"),          # EUR in New York
        ("UGX", "LOS_ANGELES_CA"),       # Ugandan Shillings in LA
        ("NGN", "CHICAGO_IL"),           # Nigerian Naira in Chicago
    ]
    
    for currency, location in mismatch_tests:
        print(f"\n--- {currency} transaction in {location} ---")
        
        tx = generator.generate_normal_transaction()
        tx["currency"] = currency
        tx["location"] = location
        tx["amount"] = 500  # Moderate amount
        
        # Convert amount to appropriate currency
        if currency != "USD":
            tx["amount"] = converter.convert_from_usd(500, currency)
        
        payload = {"transaction": tx}
        result = fraud_detection_handler(payload)
        
        print(f"Transaction: {converter.format_amount(tx['amount'], currency)} in {location}")
        if result.get('result'):
            print(f"  - Flagged: {result['result']['is_flagged']}")
            print(f"  - Risk Score: {result['result']['risk_score']}")
            print(f"  - Flags: {result['result']['flags']}")
    
    # Test 3: High-Risk Currency Transactions
    print("\n3. High-Risk Currency Tests:")
    
    high_risk_currencies = ["KES", "UGX", "TZS", "NGN"]
    
    for currency in high_risk_currencies:
        print(f"\n--- {currency} Transaction ---")
        
        currency_info = converter.get_currency_info(currency)
        # Use moderate amount in local currency
        local_amount = currency_info.typical_range[1] * 0.3  # 30% of max typical
        
        tx = generator.generate_normal_transaction()
        tx["currency"] = currency
        tx["amount"] = local_amount
        tx["location"] = "HIGH_RISK_COUNTRY"
        
        payload = {"transaction": tx}
        result = fraud_detection_handler(payload)
        
        usd_equiv = converter.convert_to_usd(local_amount, currency)
        print(f"Amount: {converter.format_amount(local_amount, currency)} (${usd_equiv:.2f} USD)")
        print(f"Currency Risk: {currency_info.risk_level}")
        
        if result.get('result'):
            print(f"  - Flagged: {result['result']['is_flagged']}")
            print(f"  - Risk Score: {result['result']['risk_score']}")
            print(f"  - Flags: {result['result']['flags']}")
    
    # Test 4: Cross-Currency Velocity
    print("\n4. Cross-Currency Velocity Test:")
    
    user_id = "user_0001"
    currencies = ["USD", "EUR", "GBP", "JPY", "INR"]
    
    print(f"Testing rapid transactions across multiple currencies for {user_id}:")
    
    for i, currency in enumerate(currencies):
        print(f"\n--- Transaction {i+1}: {currency} ---")
        
        tx = generator.generate_normal_transaction()
        tx["user_id"] = user_id
        tx["currency"] = currency
        tx["amount"] = 1000 if currency == "USD" else converter.convert_from_usd(1000, currency)
        
        payload = {"transaction": tx}
        result = fraud_detection_handler(payload)
        
        print(f"Amount: {converter.format_amount(tx['amount'], currency)}")
        if result.get('result'):
            print(f"  - Flagged: {result['result']['is_flagged']}")
            print(f"  - Risk Score: {result['result']['risk_score']}")
            if result['result']['flags']:
                print(f"  - Flags: {result['result']['flags']}")

def test_currency_conversions():
    """Test currency conversion accuracy"""
    
    print("\n💱 Currency Conversion Tests:")
    print("=" * 40)
    
    converter = CurrencyConverter()
    
    # Test round-trip conversions
    test_amounts = [100, 1000, 10000]
    test_currencies = ["EUR", "GBP", "JPY", "INR", "UGX", "NGN"]
    
    for amount in test_amounts:
        print(f"\nTesting ${amount} USD conversions:")
        
        for currency in test_currencies:
            # Convert USD to foreign currency
            foreign_amount = converter.convert_from_usd(amount, currency)
            
            # Convert back to USD
            back_to_usd = converter.convert_to_usd(foreign_amount, currency)
            
            # Check accuracy (should be very close to original)
            accuracy = abs(amount - back_to_usd) / amount * 100
            
            print(f"  ${amount} → {converter.format_amount(foreign_amount, currency)} → ${back_to_usd:.2f} (±{accuracy:.2f}%)")

if __name__ == "__main__":
    print("🌍 Multi-Currency Fraud Detection System")
    print("=" * 45)
    
    # Test currency conversions first
    test_currency_conversions()
    
    print("\n" + "="*45)
    
    # Test fraud detection with multiple currencies
    test_multicurrency_fraud_detection()