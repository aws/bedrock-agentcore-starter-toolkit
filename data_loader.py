#!/usr/bin/env python3
"""Load test data from files"""

import json
import csv
import os
from typing import Dict, List, Any
from dataclasses import dataclass
from currency_converter import CurrencyConverter

@dataclass
class UserProfile:
    """User profile from CSV data"""
    user_id: str
    name: str
    account_type: str
    credit_limit: float
    risk_profile: str
    location: str

class DataLoader:
    """Load transaction data from files"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.merchants = {}
        self.locations = {}
        self.categories = []
        self.users = {}
        self.sample_transactions = []
        self.currency_converter = CurrencyConverter(data_dir)
        
        self.load_all_data()
    
    def load_all_data(self):
        """Load all data files"""
        try:
            self.load_merchants()
            self.load_locations()
            self.load_categories()
            self.load_users()
            self.load_sample_transactions()
            print(f"✅ Loaded all data from {self.data_dir}/")
        except Exception as e:
            print(f"❌ Error loading data: {e}")
    
    def load_merchants(self):
        """Load merchants from JSON file"""
        file_path = os.path.join(self.data_dir, "merchants.json")
        with open(file_path, 'r') as f:
            self.merchants = json.load(f)
        print(f"📊 Loaded {len(self.merchants['normal_merchants'])} normal merchants, {len(self.merchants['suspicious_merchants'])} suspicious")
    
    def load_locations(self):
        """Load locations from JSON file"""
        file_path = os.path.join(self.data_dir, "locations.json")
        with open(file_path, 'r') as f:
            self.locations = json.load(f)
        print(f"🌍 Loaded {len(self.locations['safe_locations'])} safe locations, {len(self.locations['risky_locations'])} risky")
    
    def load_categories(self):
        """Load categories from JSON file"""
        file_path = os.path.join(self.data_dir, "categories.json")
        with open(file_path, 'r') as f:
            data = json.load(f)
            self.categories = data['categories']
        print(f"🏷️ Loaded {len(self.categories)} transaction categories")
    
    def load_users(self):
        """Load users from CSV file"""
        file_path = os.path.join(self.data_dir, "users.csv")
        with open(file_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                user = UserProfile(
                    user_id=row['user_id'],
                    name=row['name'],
                    account_type=row['account_type'],
                    credit_limit=float(row['credit_limit']),
                    risk_profile=row['risk_profile'],
                    location=row['location']
                )
                self.users[user.user_id] = user
        print(f"👥 Loaded {len(self.users)} user profiles")
    
    def load_sample_transactions(self):
        """Load sample transactions from CSV file"""
        file_path = os.path.join(self.data_dir, "sample_transactions.csv")
        with open(file_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                transaction = {
                    'id': row['transaction_id'],
                    'user_id': row['user_id'],
                    'amount': float(row['amount']),
                    'merchant': row['merchant'],
                    'category': row['category'],
                    'location': row['location'],
                    'timestamp': row['timestamp'],
                    'is_fraud': row['is_fraud'].lower() == 'true'
                }
                self.sample_transactions.append(transaction)
        print(f"💳 Loaded {len(self.sample_transactions)} sample transactions")
    
    def get_all_merchants(self) -> List[str]:
        """Get all merchants (normal + suspicious)"""
        return self.merchants['normal_merchants'] + self.merchants['suspicious_merchants']
    
    def get_normal_merchants(self) -> List[str]:
        """Get only normal merchants"""
        return self.merchants['normal_merchants']
    
    def get_suspicious_merchants(self) -> List[str]:
        """Get only suspicious merchants"""
        return self.merchants['suspicious_merchants']
    
    def get_all_locations(self) -> List[str]:
        """Get all locations (safe + risky)"""
        return self.locations['safe_locations'] + self.locations['risky_locations']
    
    def get_safe_locations(self) -> List[str]:
        """Get only safe locations"""
        return self.locations['safe_locations']
    
    def get_risky_locations(self) -> List[str]:
        """Get only risky locations"""
        return self.locations['risky_locations']
    
    def get_category_names(self) -> List[str]:
        """Get all category names"""
        return [cat['name'] for cat in self.categories]
    
    def get_category_by_name(self, name: str) -> Dict[str, Any]:
        """Get category details by name"""
        for cat in self.categories:
            if cat['name'] == name:
                return cat
        return None
    
    def get_user_profile(self, user_id: str) -> UserProfile:
        """Get user profile by ID"""
        return self.users.get(user_id)
    
    def get_all_user_ids(self) -> List[str]:
        """Get all user IDs"""
        return list(self.users.keys())
    
    def get_sample_transactions(self, fraud_only: bool = False) -> List[Dict[str, Any]]:
        """Get sample transactions, optionally filter for fraud only"""
        if fraud_only:
            return [tx for tx in self.sample_transactions if tx['is_fraud']]
        return self.sample_transactions
    
    def get_currency_converter(self) -> CurrencyConverter:
        """Get currency converter instance"""
        return self.currency_converter
    
    def print_data_summary(self):
        """Print summary of loaded data"""
        print("\n📋 Data Summary:")
        print(f"  Merchants: {len(self.get_all_merchants())} total")
        print(f"  Locations: {len(self.get_all_locations())} total")
        print(f"  Categories: {len(self.categories)} total")
        print(f"  Users: {len(self.users)} profiles")
        print(f"  Sample Transactions: {len(self.sample_transactions)} total")
        print(f"  Currencies: {len(self.currency_converter.get_supported_currencies())} supported")
        
        fraud_count = len(self.get_sample_transactions(fraud_only=True))
        print(f"  Fraudulent Transactions: {fraud_count}")

if __name__ == "__main__":
    # Test the data loader
    loader = DataLoader()
    loader.print_data_summary()
    
    # Show some examples
    print("\n🔍 Sample Data:")
    print(f"Normal merchants: {loader.get_normal_merchants()[:3]}...")
    print(f"Suspicious merchants: {loader.get_suspicious_merchants()}")
    print(f"User profile example: {loader.get_user_profile('user_0001')}")
    print(f"Sample fraud transaction: {loader.get_sample_transactions(fraud_only=True)[0]}")