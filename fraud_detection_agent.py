#!/usr/bin/env python3
"""Real-time fraud detection agent"""

import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any
from dataclasses import dataclass
from dotenv import load_dotenv
from bedrock_agentcore import BedrockAgentCoreApp
from strands import Agent

load_dotenv()

@dataclass
class Transaction:
    """Transaction data structure"""
    id: str
    user_id: str
    amount: float
    merchant: str
    category: str
    timestamp: datetime
    location: str
    card_type: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "amount": self.amount,
            "merchant": self.merchant,
            "category": self.category,
            "timestamp": self.timestamp.isoformat(),
            "location": self.location,
            "card_type": self.card_type
        }

@dataclass
class FraudCriteria:
    """Admin-configurable fraud detection criteria"""
    max_amount_threshold: float = 5000.0
    max_transactions_per_hour: int = 10
    suspicious_merchants: List[str] = None
    unusual_locations: List[str] = None
    velocity_check_minutes: int = 5
    
    def __post_init__(self):
        if self.suspicious_merchants is None:
            self.suspicious_merchants = ["UNKNOWN_MERCHANT", "CASH_ADVANCE"]
        if self.unusual_locations is None:
            self.unusual_locations = ["FOREIGN", "HIGH_RISK_COUNTRY"]

class FraudDetectionAgent:
    """AI-powered fraud detection agent"""
    
    def __init__(self):
        self.app = BedrockAgentCoreApp()
        self.agent = Agent(model="us.anthropic.claude-3-haiku-20240307-v1:0")
        self.criteria = FraudCriteria()
        self.transaction_history: List[Transaction] = []
        
    def update_criteria(self, new_criteria: Dict[str, Any]):
        """Admin interface to update fraud criteria"""
        for key, value in new_criteria.items():
            if hasattr(self.criteria, key):
                setattr(self.criteria, key, value)
        self.app.logger.info(f"Updated fraud criteria: {new_criteria}")
    
    def analyze_transaction(self, transaction: Transaction) -> Dict[str, Any]:
        """Analyze single transaction for fraud indicators"""
        
        # Basic rule-based checks
        flags = []
        risk_score = 0
        
        # Amount threshold check
        if transaction.amount > self.criteria.max_amount_threshold:
            flags.append(f"High amount: ${transaction.amount}")
            risk_score += 30
            
        # Suspicious merchant check
        if transaction.merchant in self.criteria.suspicious_merchants:
            flags.append(f"Suspicious merchant: {transaction.merchant}")
            risk_score += 40
            
        # Location check
        if transaction.location in self.criteria.unusual_locations:
            flags.append(f"Unusual location: {transaction.location}")
            risk_score += 25
            
        # Velocity check - transactions in last N minutes
        recent_transactions = self._get_recent_transactions(
            transaction.user_id, 
            self.criteria.velocity_check_minutes
        )
        
        if len(recent_transactions) > self.criteria.max_transactions_per_hour:
            flags.append(f"High velocity: {len(recent_transactions)} transactions in {self.criteria.velocity_check_minutes} minutes")
            risk_score += 35
            
        # AI analysis for complex patterns
        ai_analysis = self._ai_fraud_analysis(transaction, recent_transactions)
        
        return {
            "transaction_id": transaction.id,
            "is_flagged": len(flags) > 0 or risk_score > 50,
            "risk_score": risk_score,
            "flags": flags,
            "ai_analysis": ai_analysis,
            "timestamp": datetime.now().isoformat()
        }
    
    def _get_recent_transactions(self, user_id: str, minutes: int) -> List[Transaction]:
        """Get recent transactions for velocity analysis"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        return [
            t for t in self.transaction_history 
            if t.user_id == user_id and t.timestamp > cutoff_time
        ]
    
    def _ai_fraud_analysis(self, transaction: Transaction, recent_transactions: List[Transaction]) -> str:
        """Use AI to analyze transaction patterns"""
        
        prompt = f"""
        Analyze this transaction for fraud indicators:
        
        Current Transaction:
        - Amount: ${transaction.amount}
        - Merchant: {transaction.merchant}
        - Category: {transaction.category}
        - Location: {transaction.location}
        - Time: {transaction.timestamp}
        
        Recent Transaction History ({len(recent_transactions)} transactions):
        {self._format_transaction_history(recent_transactions)}
        
        Look for:
        1. Unusual spending patterns
        2. Geographic anomalies
        3. Time-based irregularities
        4. Merchant category deviations
        
        Provide a brief risk assessment (1-2 sentences).
        """
        
        try:
            response = self.agent(prompt)
            return response
        except Exception as e:
            self.app.logger.error(f"AI analysis failed: {e}")
            return "AI analysis unavailable"
    
    def _format_transaction_history(self, transactions: List[Transaction]) -> str:
        """Format transaction history for AI analysis"""
        if not transactions:
            return "No recent transactions"
            
        formatted = []
        for t in transactions[-5:]:  # Last 5 transactions
            formatted.append(f"${t.amount} at {t.merchant} ({t.category}) - {t.timestamp}")
        return "\n".join(formatted)
    
    def process_transaction_stream(self, transaction: Transaction) -> Dict[str, Any]:
        """Main entry point for real-time transaction processing"""
        
        # Add to history
        self.transaction_history.append(transaction)
        
        # Keep only last 1000 transactions for performance
        if len(self.transaction_history) > 1000:
            self.transaction_history = self.transaction_history[-1000:]
        
        # Analyze transaction
        analysis_result = self.analyze_transaction(transaction)
        
        # Log results
        if analysis_result["is_flagged"]:
            self.app.logger.warning(f"FRAUD ALERT: {analysis_result}")
        else:
            self.app.logger.info(f"Transaction approved: {transaction.id}")
            
        return analysis_result

# Initialize the fraud detection agent
fraud_agent = FraudDetectionAgent()

@fraud_agent.app.entrypoint
def fraud_detection_handler(payload):
    """Handler for incoming transactions"""
    
    try:
        # Parse transaction from payload
        transaction_data = payload.get("transaction", {})
        
        transaction = Transaction(
            id=transaction_data.get("id", "unknown"),
            user_id=transaction_data.get("user_id", "unknown"),
            amount=float(transaction_data.get("amount", 0)),
            merchant=transaction_data.get("merchant", "UNKNOWN"),
            category=transaction_data.get("category", "OTHER"),
            timestamp=datetime.fromisoformat(transaction_data.get("timestamp", datetime.now().isoformat())),
            location=transaction_data.get("location", "UNKNOWN"),
            card_type=transaction_data.get("card_type", "DEBIT")
        )
        
        # Process transaction
        result = fraud_agent.process_transaction_stream(transaction)
        
        return {
            "status": "processed",
            "result": result
        }
        
    except Exception as e:
        fraud_agent.app.logger.error(f"Error processing transaction: {e}")
        return {
            "status": "error",
            "message": str(e)
        }

if __name__ == "__main__":
    fraud_agent.app.run()