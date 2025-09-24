#!/usr/bin/env python3
"""Generate realistic transaction data for testing"""

import json
import time
import random
from datetime import datetime, timedelta
from faker import Faker
import requests

fake = Faker()

class TransactionGenerator:
    """Generate realistic bank transactions"""
    
    def __init__(self):
        self.merchants = [
            "WALMART", "AMAZON", "STARBUCKS", "SHELL", "MCDONALDS",
            "TARGET", "COSTCO", "UBER", "NETFLIX", "SPOTIFY",
            "UNKNOWN_MERCHANT",  # Suspicious
            "CASH_ADVANCE"       # Suspicious
        ]
        
        self.categories = [
            "GROCERY", "GAS", "RESTAURANT", "ENTERTAINMENT", "SHOPPING",
            "SUBSCRIPTION", "TRANSPORT", "OTHER"
        ]
        
        self.locations = [
            "NEW_YORK", "LOS_ANGELES", "CHICAGO", "HOUSTON", "PHOENIX",
            "FOREIGN",           # Suspicious
            "HIGH_RISK_COUNTRY"  # Suspicious
        ]
        
        self.users = [f"user_{i:04d}" for i in range(1, 101)]  # 100 users
    
    def generate_normal_transaction(self) -> dict:
        """Generate a normal transaction"""
        return {
            "id": fake.uuid4(),
            "user_id": random.choice(self.users),
            "amount": round(random.uniform(5.0, 500.0), 2),
            "merchant": random.choice(self.merchants[:-2]),  # Exclude suspicious ones
            "category": random.choice(self.categories),
            "timestamp": datetime.now().isoformat(),
            "location": random.choice(self.locations[:-2]),  # Exclude suspicious ones
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
            transaction["merchant"] = random.choice(self.merchants[-2:])
        elif fraud_type == "unusual_location":
            transaction["location"] = random.choice(self.locations[-2:])
        elif fraud_type == "foreign_location":
            transaction["location"] = "FOREIGN"
            transaction["amount"] = round(random.uniform(1000.0, 10000.0), 2)
            
        return transaction
    
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
            print(f"💳 Transaction: ${transaction['amount']} at {transaction['merchant']}")
            
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