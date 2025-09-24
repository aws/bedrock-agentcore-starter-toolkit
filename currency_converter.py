#!/usr/bin/env python3
"""Multi-currency support for fraud detection"""

import json
import os
from typing import Dict, Tuple, List
from dataclasses import dataclass

@dataclass
class CurrencyInfo:
    """Currency information"""
    code: str
    name: str
    symbol: str
    exchange_rate: float
    risk_level: str
    typical_range: Tuple[float, float]
    high_threshold: float

class CurrencyConverter:
    """Handle multi-currency transactions and conversions"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.currencies = {}
        self.base_currency = "USD"
        self.risk_rules = {}
        
        self.load_currency_data()
    
    def load_currency_data(self):
        """Load currency data from JSON file"""
        file_path = os.path.join(self.data_dir, "currencies.json")
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            self.base_currency = data['base_currency']
            self.risk_rules = data['currency_risk_rules']
            
            # Load currency information
            for code, info in data['supported_currencies'].items():
                self.currencies[code] = CurrencyInfo(
                    code=code,
                    name=info['name'],
                    symbol=info['symbol'],
                    exchange_rate=info['exchange_rate'],
                    risk_level=info['risk_level'],
                    typical_range=(info['typical_transaction_range'][0], info['typical_transaction_range'][1]),
                    high_threshold=info['high_amount_threshold']
                )
            
            print(f"💱 Loaded {len(self.currencies)} currencies with {self.base_currency} as base")
            
        except Exception as e:
            print(f"❌ Error loading currency data: {e}")
            # Fallback to USD only
            self.currencies = {
                "USD": CurrencyInfo("USD", "US Dollar", "$", 1.0, "low", (1, 10000), 5000)
            }
    
    def get_supported_currencies(self) -> List[str]:
        """Get list of supported currency codes"""
        return list(self.currencies.keys())
    
    def get_currency_info(self, currency_code: str) -> CurrencyInfo:
        """Get currency information"""
        return self.currencies.get(currency_code.upper())
    
    def convert_to_usd(self, amount: float, from_currency: str) -> float:
        """Convert amount from any currency to USD"""
        if from_currency.upper() == "USD":
            return amount
        
        currency_info = self.get_currency_info(from_currency)
        if not currency_info:
            raise ValueError(f"Unsupported currency: {from_currency}")
        
        # Convert to USD (divide by exchange rate since rates are in terms of foreign currency per USD)
        usd_amount = amount / currency_info.exchange_rate
        return round(usd_amount, 2)
    
    def convert_from_usd(self, usd_amount: float, to_currency: str) -> float:
        """Convert USD amount to any currency"""
        if to_currency.upper() == "USD":
            return usd_amount
        
        currency_info = self.get_currency_info(to_currency)
        if not currency_info:
            raise ValueError(f"Unsupported currency: {to_currency}")
        
        # Convert from USD (multiply by exchange rate)
        converted_amount = usd_amount * currency_info.exchange_rate
        return round(converted_amount, 2)
    
    def convert_currency(self, amount: float, from_currency: str, to_currency: str) -> float:
        """Convert between any two currencies"""
        if from_currency.upper() == to_currency.upper():
            return amount
        
        # Convert through USD
        usd_amount = self.convert_to_usd(amount, from_currency)
        return self.convert_from_usd(usd_amount, to_currency)
    
    def format_amount(self, amount: float, currency_code: str) -> str:
        """Format amount with currency symbol"""
        currency_info = self.get_currency_info(currency_code)
        if not currency_info:
            return f"{amount} {currency_code}"
        
        # Format based on currency (some currencies don't use decimals for large amounts)
        if currency_code in ["JPY", "KRW", "UGX", "TZS"]:
            return f"{currency_info.symbol}{amount:,.0f}"
        else:
            return f"{currency_info.symbol}{amount:,.2f}"
    
    def analyze_currency_risk(self, amount: float, currency: str, user_location: str = None) -> Dict[str, any]:
        """Analyze currency-specific fraud risks"""
        currency_info = self.get_currency_info(currency)
        if not currency_info:
            return {"risk_score": 0, "flags": [f"Unknown currency: {currency}"]}
        
        flags = []
        risk_score = 0
        
        # Convert to USD for consistent analysis
        usd_amount = self.convert_to_usd(amount, currency)
        
        # High amount check (currency-specific)
        if amount > currency_info.high_threshold:
            flags.append(f"High amount in {currency}: {self.format_amount(amount, currency)}")
            risk_score += 30
        
        # Currency risk level
        if currency_info.risk_level == "high":
            flags.append(f"High-risk currency: {currency}")
            risk_score += 20
        elif currency_info.risk_level == "medium":
            risk_score += 10
        
        # Cross-currency transaction risk
        if usd_amount > self.risk_rules['cross_currency_threshold'] and currency != "USD":
            flags.append(f"Large cross-currency transaction: {self.format_amount(amount, currency)} → ${usd_amount}")
            risk_score += 15
        
        # Suspicious currency pairs (if we had previous transaction data)
        # This would require transaction history to implement fully
        
        return {
            "risk_score": risk_score,
            "flags": flags,
            "usd_equivalent": usd_amount,
            "currency_risk_level": currency_info.risk_level
        }
    
    def get_currency_stats(self) -> Dict[str, any]:
        """Get statistics about supported currencies"""
        stats = {
            "total_currencies": len(self.currencies),
            "by_risk_level": {"low": 0, "medium": 0, "high": 0},
            "base_currency": self.base_currency
        }
        
        for currency_info in self.currencies.values():
            stats["by_risk_level"][currency_info.risk_level] += 1
        
        return stats
    
    def print_currency_summary(self):
        """Print summary of all supported currencies"""
        print("\n💱 Supported Currencies:")
        print("=" * 60)
        
        for code, info in sorted(self.currencies.items()):
            usd_equiv = f"1 USD = {info.exchange_rate} {code}" if code != "USD" else "Base currency"
            risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}[info.risk_level]
            
            print(f"{risk_emoji} {code} - {info.name} ({info.symbol})")
            print(f"    Exchange rate: {usd_equiv}")
            print(f"    Risk level: {info.risk_level}")
            print(f"    High threshold: {self.format_amount(info.high_threshold, code)}")
            print()

if __name__ == "__main__":
    # Test the currency converter
    converter = CurrencyConverter()
    converter.print_currency_summary()
    
    # Test conversions
    print("🧪 Testing Currency Conversions:")
    print("=" * 40)
    
    test_cases = [
        (1000, "USD", "EUR"),
        (5000, "EUR", "GBP"),
        (100000, "JPY", "USD"),
        (50000, "INR", "USD"),
        (1000000, "UGX", "USD"),
        (500000, "NGN", "EUR")
    ]
    
    for amount, from_curr, to_curr in test_cases:
        converted = converter.convert_currency(amount, from_curr, to_curr)
        print(f"{converter.format_amount(amount, from_curr)} → {converter.format_amount(converted, to_curr)}")
    
    # Test risk analysis
    print("\n🔍 Testing Currency Risk Analysis:")
    print("=" * 40)
    
    risk_tests = [
        (10000, "USD"),
        (50000, "EUR"),
        (1000000, "JPY"),
        (5000000, "UGX"),
        (2000000, "NGN")
    ]
    
    for amount, currency in risk_tests:
        risk_analysis = converter.analyze_currency_risk(amount, currency)
        print(f"\n{converter.format_amount(amount, currency)}:")
        print(f"  Risk Score: {risk_analysis['risk_score']}")
        print(f"  USD Equivalent: ${risk_analysis['usd_equivalent']}")
        print(f"  Flags: {risk_analysis['flags']}")