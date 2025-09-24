#!/usr/bin/env python3
"""Generate realistic transaction data for testing"""

import json
import time
import random
from datetime import datetime, timedelta
from faker import Faker
import requests
from data_loader import DataLoader

fake = Faker()

class TransactionGenerator:
    """Generate realistic bank transactions using file data"""
    
    def __init__(self):
        # Load data from files
        self.data_loader = DataLoader()
        
        # Use loaded data instead of hardcoded lists
        self.merchants = self.data_loader.get_all_merchants()
        self.normal_merchants = self.data_loader.get_normal_merchants()
        self.suspicious_merchants = self.data_loader.get_suspicious_merchants()
        
        self.categories = self.data_loader.get_category_names()
        
        self.locations = self.data_loader.get_all_locations()
        self.safe_locations = self.data_loader.get_safe_locations()
        self.risky_locations = self.data_loader.get_risky_locations()
        
        self.users = self.data_loader.get_all_user_ids()
        
        print(f"🔄 Transaction Generator initialized with file data:")
        print(f"  📊 {len(self.merchants)} merchants loaded")
        print(f"  👥 {len(self.users)} users loaded")
    
    def generate_normal_transaction(self) -> dict:
        """Generate a normal transaction using file data"""
        user_id = random.choice(self.users)
        user_profile = self.data_loader.get_user_profile(user_id)
        category = random.choice(self.categories)
        
        # Get category-specific amount range
        category_info = self.data_loader.get_category_by_name(category)
        if category_info and category_info['risk_level'] != 'high':
            min_amt, max_amt = category_info['typical_amount_range']
            amount = round(random.uniform(min_amt, max_amt), 2)
        else:
            amount = round(random.uniform(5.0, 500.0), 2)
        
        # Choose currency based on location
        currency = self._get_currency_for_location(user_profile.location if user_profile else random.choice(self.safe_locations))
        
        # Convert amount to chosen currency if not USD
        if currency != "USD":
            amount = self.data_loader.currency_converter.convert_from_usd(amount, currency)
        
        return {
            "id": fake.uuid4(),
            "user_id": user_id,
            "amount": round(amount, 2),
            "currency": currency,
            "merchant": random.choice(self.normal_merchants),
            "category": category,
            "timestamp": datetime.now().isoformat(),
            "location": user_profile.location if user_profile else random.choice(self.safe_locations),
            "card_type": random.choice(["DEBIT", "CREDIT"])
        }
    
    def generate_suspicious_transaction(self) -> dict:
        """Generate a potentially fraudulent transaction"""
        transaction = self.generate_normal_transaction()
        
        # Make it suspicious
        fraud_type = random.choice([
            "high_amount", "suspicious_merchant", "unusual_location", 
            "high_velocity", "foreign_location"
        ])
        
        if fraud_type == "high_amount":
            transaction["amount"] = round(random.uniform(5000.0, 50000.0), 2)
        elif fraud_type == "suspicious_merchant":
            transaction["merchant"] = random.choice(self.suspicious_merchants)
        elif fraud_type == "unusual_location":
            transaction["location"] = random.choice(self.risky_locations)
        elif fraud_type == "foreign_location":
            transaction["location"] = "FOREIGN_COUNTRY"
            transaction["amount"] = round(random.uniform(1000.0, 10000.0), 2)
            # Use high-risk currency for foreign transactions
            transaction["currency"] = random.choice(["KES", "UGX", "NGN", "TZS"])
            
        return transaction
    
    def _get_currency_for_location(self, location: str) -> str:
        """Get appropriate currency based on location"""
        location_currency_map = {
            "NEW_YORK_NY": "USD",
            "LOS_ANGELES_CA": "USD", 
            "CHICAGO_IL": "USD",
            "HOUSTON_TX": "USD",
            "PHOENIX_AZ": "USD",
            "PHILADELPHIA_PA": "USD",
            "SAN_ANTONIO_TX": "USD",
            "SAN_DIEGO_CA": "USD",
            "DALLAS_TX": "USD",
            "SAN_JOSE_CA": "USD",
            "FOREIGN_COUNTRY": random.choice(["EUR", "GBP", "JPY"]),
            "HIGH_RISK_COUNTRY": random.choice(["KES", "UGX", "TZS", "NGN"]),
            "SANCTIONED_REGION": random.choice(["INR", "CNY"]),
            "OFFSHORE_TERRITORY": random.choice(["EUR", "CHF"]),
            "UNKNOWN_LOCATION": random.choice(["USD", "EUR", "GBP"])
        }
        
        return location_currency_map.get(location, "USD")
    
    def generate_transaction_stream(self, duration_minutes: int = 60, 
                                  transactions_per_minute: int = 10,
                                  fraud_percentage: float = 0.05):
        """Generate continuous stream of transactions"""
        
        print(f"🏦 Starting transaction stream for {duration_minutes} minutes")
        print(f"📊 Rate: {transactions_per_minute} transactions/minute")
        print(f"🚨 Fraud rate: {fraud_percentage*100}% suspicious transactions")
        
        end_time = datetime.now() + timedelta(minutes=duration_minutes)
        transaction_count = 0
        
        while datetime.now() < end_time:
            # Generate transaction
            if random.random() < fraud_percentage:
                transaction = self.generate_suspicious_transaction()
                print(f"🚨 Generated suspicious transaction: {transaction['id']}")
            else:
                transaction = self.generate_normal_transaction()
                print(f"✅ Generated normal transaction: {transaction['id']}")
            
            # Send to fraud detection agent (if running)
            self.send_to_agent(transaction)
            
            transaction_count += 1
            
            # Wait before next transaction
            time.sleep(60 / transactions_per_minute)
        
        print(f"🏁 Generated {transaction_count} transactions")
    
    def send_to_agent(self, transaction: dict):
        """Send transaction to fraud detection agent"""
        try:
            payload = {"transaction": transaction}
            
            # If agent is running as a service, send HTTP request
            # For now, just print the transaction
            currency = transaction.get('currency', 'USD')
            converter = self.data_loader.currency_converter if hasattr(self, 'data_loader') else None
            if converter:
                formatted_amount = converter.format_amount(transaction['amount'], currency)
            else:
                formatted_amount = f"{transaction['amount']} {currency}"
            print(f"💳 Transaction: {formatted_amount} at {transaction['merchant']}")
            
            # Uncomment if agent is running as HTTP service:
            # response = requests.post("http://localhost:8080/invoke", json=payload)
            # print(f"Agent response: {response.json()}")
            
        except Exception as e:
            print(f"❌ Error sending to agent: {e}")

def main():
    """Main function to run transaction generator"""
    generator = TransactionGenerator()
    
    print("🏦 Bank Transaction Generator")
    print("1. Generate single transaction")
    print("2. Generate transaction stream")
    print("3. Generate test batch")
    
    choice = input("Choose option (1-3): ")
    
    if choice == "1":
        transaction = generator.generate_normal_transaction()
        print(json.dumps(transaction, indent=2))
        
    elif choice == "2":
        duration = int(input("Duration in minutes (default 5): ") or "5")
        rate = int(input("Transactions per minute (default 10): ") or "10")
        fraud_rate = float(input("Fraud percentage (default 0.05): ") or "0.05")
        
        generator.generate_transaction_stream(duration, rate, fraud_rate)
        
    elif choice == "3":
        print("Generating test batch...")
        for i in range(20):
            if i % 5 == 0:  # Every 5th transaction is suspicious
                transaction = generator.generate_suspicious_transaction()
            else:
                transaction = generator.generate_normal_transaction()
            
            print(f"Transaction {i+1}: ${transaction['amount']} at {transaction['merchant']}")
            generator.send_to_agent(transaction)
            time.sleep(1)

if __name__ == "__main__":
    main()