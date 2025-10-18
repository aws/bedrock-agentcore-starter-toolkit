"""
Transaction Factory - Generates realistic transaction data for load testing.
"""

import random
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from enum import Enum


class TransactionType(Enum):
    """Types of transactions to generate."""
    LEGITIMATE = "legitimate"
    FRAUDULENT = "fraudulent"
    EDGE_CASE = "edge_case"


class TransactionFactory:
    """Generates realistic transaction data for stress testing."""
    
    # Realistic data pools
    CURRENCIES = ["USD", "EUR", "GBP", "JPY", "CAD", "AUD", "CHF", "CNY"]
    CURRENCY_RATES = {
        "USD": 1.0, "EUR": 0.92, "GBP": 0.79, "JPY": 149.5,
        "CAD": 1.36, "AUD": 1.52, "CHF": 0.88, "CNY": 7.24
    }
    
    COUNTRIES = ["US", "UK", "CA", "AU", "DE", "FR", "JP", "CN", "BR", "IN"]
    CITIES = {
        "US": ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix"],
        "UK": ["London", "Manchester", "Birmingham", "Leeds", "Glasgow"],
        "CA": ["Toronto", "Vancouver", "Montreal", "Calgary", "Ottawa"],
        "AU": ["Sydney", "Melbourne", "Brisbane", "Perth", "Adelaide"],
        "DE": ["Berlin", "Munich", "Hamburg", "Frankfurt", "Cologne"],
        "FR": ["Paris", "Marseille", "Lyon", "Toulouse", "Nice"],
        "JP": ["Tokyo", "Osaka", "Yokohama", "Nagoya", "Sapporo"],
        "CN": ["Beijing", "Shanghai", "Guangzhou", "Shenzhen", "Chengdu"],
        "BR": ["São Paulo", "Rio de Janeiro", "Brasília", "Salvador", "Fortaleza"],
        "IN": ["Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai"]
    }
    
    MERCHANT_CATEGORIES = [
        "retail", "restaurant", "gas_station", "grocery", "online",
        "travel", "entertainment", "healthcare", "utilities", "education"
    ]
    
    MERCHANT_NAMES = {
        "retail": ["MegaMart", "ShopWorld", "RetailHub", "BuyMore", "StoreMax"],
        "restaurant": ["Tasty Bites", "Food Palace", "Dine & Wine", "Quick Eats", "Gourmet House"],
        "gas_station": ["FuelStop", "Gas & Go", "QuickFuel", "PetroMax", "FillUp"],
        "grocery": ["FreshMart", "GroceryPlus", "FoodBasket", "SuperSave", "MarketPlace"],
        "online": ["WebShop", "ClickBuy", "OnlineStore", "E-Commerce Hub", "NetMart"],
        "travel": ["TravelCo", "JetSet", "VacationPro", "TripMaster", "WanderLust"],
        "entertainment": ["FunZone", "PlayTime", "EntertainHub", "ShowPlace", "GameWorld"],
        "healthcare": ["MediCare", "HealthPlus", "WellnessCo", "CareCenter", "MedHub"],
        "utilities": ["PowerCo", "UtilityPro", "ServiceMax", "EnergyPlus", "UtilHub"],
        "education": ["LearnMore", "EduHub", "StudyPro", "AcademyPlus", "SchoolMax"]
    }
    
    def __init__(self, fraud_rate: float = 0.02, edge_case_rate: float = 0.05):
        """
        Initialize transaction factory.
        
        Args:
            fraud_rate: Percentage of fraudulent transactions (0.0-1.0)
            edge_case_rate: Percentage of edge case transactions (0.0-1.0)
        """
        self.fraud_rate = fraud_rate
        self.edge_case_rate = edge_case_rate
        self.transaction_count = 0
    
    def generate_transaction(self, transaction_type: Optional[TransactionType] = None) -> Dict[str, Any]:
        """
        Generate a single transaction.
        
        Args:
            transaction_type: Specific type to generate, or None for random
            
        Returns:
            Transaction dictionary
        """
        self.transaction_count += 1
        
        # Determine transaction type if not specified
        if transaction_type is None:
            rand = random.random()
            if rand < self.fraud_rate:
                transaction_type = TransactionType.FRAUDULENT
            elif rand < self.fraud_rate + self.edge_case_rate:
                transaction_type = TransactionType.EDGE_CASE
            else:
                transaction_type = TransactionType.LEGITIMATE
        
        # Generate based on type
        if transaction_type == TransactionType.FRAUDULENT:
            return self._generate_fraudulent_transaction()
        elif transaction_type == TransactionType.EDGE_CASE:
            return self._generate_edge_case_transaction()
        else:
            return self._generate_legitimate_transaction()
    
    def generate_batch(self, count: int) -> List[Dict[str, Any]]:
        """Generate a batch of transactions."""
        return [self.generate_transaction() for _ in range(count)]
    
    def _generate_legitimate_transaction(self) -> Dict[str, Any]:
        """Generate a legitimate transaction."""
        country = random.choice(self.COUNTRIES)
        currency = random.choice(self.CURRENCIES[:4])  # Prefer major currencies
        category = random.choice(self.MERCHANT_CATEGORIES)
        
        return {
            "transaction_id": str(uuid.uuid4()),
            "user_id": f"user_{random.randint(1000, 9999)}",
            "amount": round(random.uniform(10, 500), 2),
            "currency": currency,
            "merchant_id": f"merchant_{random.randint(100, 999)}",
            "merchant_name": random.choice(self.MERCHANT_NAMES[category]),
            "merchant_category": category,
            "timestamp": datetime.utcnow().isoformat(),
            "location": {
                "country": country,
                "city": random.choice(self.CITIES[country]),
                "latitude": round(random.uniform(-90, 90), 6),
                "longitude": round(random.uniform(-180, 180), 6)
            },
            "device_id": f"device_{random.randint(10000, 99999)}",
            "ip_address": f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}",
            "card_last_four": f"{random.randint(1000, 9999)}",
            "is_fraudulent": False,
            "fraud_indicators": []
        }
    
    def _generate_fraudulent_transaction(self) -> Dict[str, Any]:
        """Generate a fraudulent transaction with red flags."""
        base = self._generate_legitimate_transaction()
        
        # Add fraud indicators
        fraud_type = random.choice([
            "high_amount", "unusual_location", "rapid_succession",
            "new_device", "unusual_time", "multiple_countries"
        ])
        
        if fraud_type == "high_amount":
            base["amount"] = round(random.uniform(5000, 50000), 2)
            base["fraud_indicators"].append("unusually_high_amount")
        
        elif fraud_type == "unusual_location":
            # Transaction from unusual country
            base["location"]["country"] = random.choice(["NG", "RU", "CN", "VN"])
            base["location"]["city"] = "Unknown"
            base["fraud_indicators"].append("unusual_location")
        
        elif fraud_type == "rapid_succession":
            # Multiple transactions in short time
            base["fraud_indicators"].append("rapid_succession")
            base["metadata"] = {"recent_transaction_count": random.randint(5, 20)}
        
        elif fraud_type == "new_device":
            base["device_id"] = f"device_new_{uuid.uuid4().hex[:8]}"
            base["fraud_indicators"].append("new_device")
        
        elif fraud_type == "unusual_time":
            # Transaction at odd hours
            odd_hour = random.choice([2, 3, 4])
            base["timestamp"] = (datetime.utcnow().replace(hour=odd_hour)).isoformat()
            base["fraud_indicators"].append("unusual_time")
        
        elif fraud_type == "multiple_countries":
            base["fraud_indicators"].append("multiple_countries")
            base["metadata"] = {"countries_last_24h": random.randint(3, 8)}
        
        base["is_fraudulent"] = True
        return base
    
    def _generate_edge_case_transaction(self) -> Dict[str, Any]:
        """Generate an edge case transaction."""
        base = self._generate_legitimate_transaction()
        
        edge_case = random.choice([
            "zero_amount", "negative_amount", "very_small", "missing_fields",
            "unusual_currency", "duplicate_id"
        ])
        
        if edge_case == "zero_amount":
            base["amount"] = 0.0
        
        elif edge_case == "negative_amount":
            base["amount"] = -abs(base["amount"])
        
        elif edge_case == "very_small":
            base["amount"] = round(random.uniform(0.01, 0.99), 2)
        
        elif edge_case == "missing_fields":
            # Remove some optional fields
            base.pop("device_id", None)
            base.pop("ip_address", None)
        
        elif edge_case == "unusual_currency":
            base["currency"] = random.choice(["BTC", "XRP", "XXX"])
        
        elif edge_case == "duplicate_id":
            base["transaction_id"] = "duplicate_" + base["transaction_id"]
        
        base["is_edge_case"] = True
        return base
    
    def generate_user_profile(self) -> Dict[str, Any]:
        """Generate a realistic user profile."""
        country = random.choice(self.COUNTRIES)
        return {
            "user_id": f"user_{random.randint(1000, 9999)}",
            "name": f"User {random.randint(1000, 9999)}",
            "email": f"user{random.randint(1000, 9999)}@example.com",
            "country": country,
            "city": random.choice(self.CITIES[country]),
            "account_age_days": random.randint(1, 3650),
            "total_transactions": random.randint(0, 1000),
            "average_transaction_amount": round(random.uniform(50, 500), 2),
            "preferred_currency": random.choice(self.CURRENCIES[:4]),
            "risk_score": round(random.uniform(0, 1), 3)
        }
    
    def generate_merchant_profile(self) -> Dict[str, Any]:
        """Generate a realistic merchant profile."""
        category = random.choice(self.MERCHANT_CATEGORIES)
        return {
            "merchant_id": f"merchant_{random.randint(100, 999)}",
            "name": random.choice(self.MERCHANT_NAMES[category]),
            "category": category,
            "country": random.choice(self.COUNTRIES),
            "reputation_score": round(random.uniform(0.5, 1.0), 3),
            "transaction_volume": random.randint(100, 100000),
            "average_amount": round(random.uniform(20, 300), 2)
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get factory statistics."""
        return {
            "total_generated": self.transaction_count,
            "fraud_rate": self.fraud_rate,
            "edge_case_rate": self.edge_case_rate
        }
