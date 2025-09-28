"""
Context Manager for Context-Aware Decision Making

Handles retrieval and analysis of historical context for fraud detection decisions.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from .models import (
    Transaction, DecisionContext, UserBehaviorProfile, 
    FraudPattern, SimilarCase, RiskProfile, FraudDecision
)
from .memory_manager import MemoryManager

logger = logging.getLogger(__name__)


@dataclass
class ContextualInsight:
    """Contextual insight derived from historical data."""
    insight_type: str
    description: str
    confidence: float
    supporting_evidence: List[str]
    risk_impact: float  # -1 to 1, negative reduces risk, positive increases


class ContextManager:
    """
    Manages context-aware decision making for fraud detection.
    
    Provides capabilities for:
    - Context retrieval for similar transaction analysis
    - Historical decision reference mechanism
    - User risk profile evolution tracking
    - Contextual insights generation
    """
    
    def __init__(self, memory_manager: MemoryManager):
        """
        Initialize the Context Manager.
        
        Args:
            memory_manager: MemoryManager instance for data access
        """
        self.memory_manager = memory_manager
        self.similarity_threshold = 0.7
        self.context_window_days = 90
        self.risk_evolution_cache = {}  # Cache for risk profile evolution
    
    def get_transaction_context(self, transaction: Transaction) -> Dict[str, Any]:
        """
        Get comprehensive context for a transaction.
        
        Args:
            transaction: Transaction to analyze
            
        Returns:
            Dictionary containing contextual information
        """
        try:
            logger.info(f"Retrieving context for transaction {transaction.id}")
            
            context = {
                "transaction_id": transaction.id,
                "user_id": transaction.user_id,
                "timestamp": transaction.timestamp,
                "similar_cases": [],
                "user_profile": None,
                "risk_profile": None,
                "contextual_insights": [],
                "decision_history": [],
                "risk_factors": {}
            }
            
            # Get similar transactions
            similar_cases = self.memory_manager.get_similar_transactions(
                transaction, self.similarity_threshold, limit=10
            )
            context["similar_cases"] = similar_cases
            
            # Get user behavior profile
            user_profile = self.memory_manager.get_user_profile(transaction.user_id)
            context["user_profile"] = user_profile
            
            # Get risk profile
            risk_profile = self.memory_manager.get_risk_profile(transaction.user_id)
            context["risk_profile"] = risk_profile
            
            # Get decision history
            decision_history = self.memory_manager.get_user_decision_history(
                transaction.user_id, days_back=self.context_window_days
            )
            context["decision_history"] = decision_history
            
            # Generate contextual insights
            insights = self._generate_contextual_insights(transaction, context)
            context["contextual_insights"] = insights
            
            # Analyze risk factors
            risk_factors = self._analyze_risk_factors(transaction, context)
            context["risk_factors"] = risk_factors
            
            logger.info(f"Retrieved context with {len(similar_cases)} similar cases, "
                       f"{len(insights)} insights, and {len(risk_factors)} risk factors")
            
            return context
            
        except Exception as e:
            logger.error(f"Error retrieving transaction context: {str(e)}")
            return {"error": str(e)}
    
    def _generate_contextual_insights(
        self, 
        transaction: Transaction, 
        context: Dict[str, Any]
    ) -> List[ContextualInsight]:
        """Generate contextual insights from historical data."""
        insights = []
        
        try:
            # Analyze similar cases
            similar_cases = context.get("similar_cases", [])
            if similar_cases:
                fraud_cases = [case for case in similar_cases if case.decision == FraudDecision.DECLINED]
                fraud_rate = len(fraud_cases) / len(similar_cases)
                
                if fraud_rate > 0.5:
                    insights.append(ContextualInsight(
                        insight_type="similar_case_analysis",
                        description=f"High fraud rate ({fraud_rate:.1%}) in similar transactions",
                        confidence=0.8,
                        supporting_evidence=[f"Found {len(fraud_cases)} fraud cases out of {len(similar_cases)} similar transactions"],
                        risk_impact=0.6
                    ))
                elif fraud_rate < 0.1:
                    insights.append(ContextualInsight(
                        insight_type="similar_case_analysis",
                        description=f"Low fraud rate ({fraud_rate:.1%}) in similar transactions",
                        confidence=0.7,
                        supporting_evidence=[f"Only {len(fraud_cases)} fraud cases out of {len(similar_cases)} similar transactions"],
                        risk_impact=-0.3
                    ))
            
            # Analyze user behavior
            user_profile = context.get("user_profile")
            if user_profile:
                # Check if amount is within typical range
                typical_range = user_profile.typical_spending_range
                amount = float(transaction.amount)
                
                if amount > typical_range.get("max", 0) * 2:
                    insights.append(ContextualInsight(
                        insight_type="spending_behavior",
                        description="Transaction amount significantly exceeds user's typical spending",
                        confidence=0.9,
                        supporting_evidence=[f"Amount ${amount:.2f} is {amount/typical_range.get('max', 1):.1f}x user's max typical amount"],
                        risk_impact=0.7
                    ))
                elif typical_range.get("min", 0) <= amount <= typical_range.get("max", 0):
                    insights.append(ContextualInsight(
                        insight_type="spending_behavior",
                        description="Transaction amount within user's typical spending range",
                        confidence=0.8,
                        supporting_evidence=[f"Amount ${amount:.2f} is within typical range ${typical_range.get('min', 0):.2f}-${typical_range.get('max', 0):.2f}"],
                        risk_impact=-0.2
                    ))
                
                # Check merchant familiarity
                if transaction.merchant in user_profile.frequent_merchants:
                    insights.append(ContextualInsight(
                        insight_type="merchant_familiarity",
                        description="User frequently transacts with this merchant",
                        confidence=0.9,
                        supporting_evidence=[f"Merchant '{transaction.merchant}' is in user's frequent merchants list"],
                        risk_impact=-0.4
                    ))
            
            # Analyze decision history
            decision_history = context.get("decision_history", [])
            if decision_history:
                recent_decisions = [d for d in decision_history if d.timestamp > datetime.now() - timedelta(days=7)]
                fraud_decisions = [d for d in recent_decisions if d.decision in [FraudDecision.DECLINED, FraudDecision.FLAGGED]]
                
                if len(fraud_decisions) > 3:
                    insights.append(ContextualInsight(
                        insight_type="recent_activity",
                        description="Multiple recent fraud flags for this user",
                        confidence=0.8,
                        supporting_evidence=[f"{len(fraud_decisions)} fraud-related decisions in the last 7 days"],
                        risk_impact=0.5
                    ))
                elif len(recent_decisions) > 10 and len(fraud_decisions) == 0:
                    insights.append(ContextualInsight(
                        insight_type="recent_activity",
                        description="High recent activity with no fraud flags",
                        confidence=0.7,
                        supporting_evidence=[f"{len(recent_decisions)} recent transactions with no fraud flags"],
                        risk_impact=-0.2
                    ))
            
            return insights
            
        except Exception as e:
            logger.error(f"Error generating contextual insights: {str(e)}")
            return []
    
    def _analyze_risk_factors(
        self, 
        transaction: Transaction, 
        context: Dict[str, Any]
    ) -> Dict[str, float]:
        """Analyze various risk factors based on context."""
        risk_factors = {}
        
        try:
            # Geographic risk
            user_profile = context.get("user_profile")
            if user_profile and user_profile.common_locations:
                common_countries = [loc.country for loc in user_profile.common_locations]
                if transaction.location.country not in common_countries:
                    risk_factors["geographic_anomaly"] = 0.6
                else:
                    risk_factors["geographic_anomaly"] = 0.1
            else:
                risk_factors["geographic_anomaly"] = 0.3  # Unknown location history
            
            # Temporal risk
            hour = transaction.timestamp.hour
            if 2 <= hour <= 6:  # Late night/early morning
                risk_factors["temporal_anomaly"] = 0.4
            elif 9 <= hour <= 17:  # Business hours
                risk_factors["temporal_anomaly"] = 0.1
            else:
                risk_factors["temporal_anomaly"] = 0.2
            
            # Amount risk
            if user_profile:
                typical_max = user_profile.typical_spending_range.get("max", 100)
                amount_ratio = float(transaction.amount) / typical_max
                if amount_ratio > 3:
                    risk_factors["amount_anomaly"] = 0.8
                elif amount_ratio > 1.5:
                    risk_factors["amount_anomaly"] = 0.4
                else:
                    risk_factors["amount_anomaly"] = 0.1
            else:
                risk_factors["amount_anomaly"] = 0.3
            
            # Velocity risk
            decision_history = context.get("decision_history", [])
            recent_transactions = [
                d for d in decision_history 
                if d.timestamp > datetime.now() - timedelta(hours=1)
            ]
            if len(recent_transactions) > 5:
                risk_factors["velocity_risk"] = 0.7
            elif len(recent_transactions) > 2:
                risk_factors["velocity_risk"] = 0.4
            else:
                risk_factors["velocity_risk"] = 0.1
            
            return risk_factors
            
        except Exception as e:
            logger.error(f"Error analyzing risk factors: {str(e)}")
            return {}
    
    def get_contextual_recommendation(self, transaction: Transaction) -> Dict[str, Any]:
        """
        Get contextual recommendation for a transaction decision.
        
        Args:
            transaction: Transaction to analyze
            
        Returns:
            Dictionary containing recommendation and reasoning
        """
        try:
            context = self.get_transaction_context(transaction)
            
            # Calculate overall risk score from insights and risk factors
            risk_score = 0.0
            confidence = 0.0
            reasoning = []
            
            # Process contextual insights
            insights = context.get("contextual_insights", [])
            for insight in insights:
                weighted_impact = insight.risk_impact * insight.confidence
                risk_score += weighted_impact
                reasoning.append(f"{insight.description} (impact: {insight.risk_impact:+.2f}, confidence: {insight.confidence:.2f})")
            
            # Process risk factors
            risk_factors = context.get("risk_factors", {})
            for factor_name, factor_value in risk_factors.items():
                risk_score += factor_value * 0.3  # Weight risk factors
                reasoning.append(f"{factor_name.replace('_', ' ').title()}: {factor_value:.2f}")
            
            # Normalize risk score
            risk_score = max(-1.0, min(1.0, risk_score))
            
            # Determine recommendation
            if risk_score > 0.5:
                recommendation = "DECLINE"
                confidence = min(0.95, 0.6 + risk_score * 0.3)
            elif risk_score > 0.2:
                recommendation = "FLAG_FOR_REVIEW"
                confidence = 0.7
            elif risk_score < -0.3:
                recommendation = "APPROVE"
                confidence = min(0.95, 0.8 + abs(risk_score) * 0.2)
            else:
                recommendation = "APPROVE"
                confidence = 0.6
            
            return {
                "transaction_id": transaction.id,
                "recommendation": recommendation,
                "confidence": confidence,
                "risk_score": risk_score,
                "reasoning": reasoning,
                "context_summary": {
                    "similar_cases_count": len(context.get("similar_cases", [])),
                    "insights_count": len(insights),
                    "risk_factors_count": len(risk_factors),
                    "has_user_profile": context.get("user_profile") is not None,
                    "has_risk_profile": context.get("risk_profile") is not None
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating contextual recommendation: {str(e)}")
            return {
                "transaction_id": transaction.id,
                "recommendation": "MANUAL_REVIEW",
                "confidence": 0.0,
                "risk_score": 0.0,
                "reasoning": [f"Error in contextual analysis: {str(e)}"],
                "context_summary": {}
            }    
    d
ef track_risk_profile_evolution(self, user_id: str) -> Dict[str, Any]:
        """
        Track the evolution of a user's risk profile over time.
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary containing risk evolution analysis
        """
        try:
            logger.info(f"Tracking risk profile evolution for user {user_id}")
            
            # Get current risk profile
            current_risk = self.memory_manager.get_risk_profile(user_id)
            if not current_risk:
                return {"error": "No risk profile found for user"}
            
            # Get decision history for trend analysis
            decision_history = self.memory_manager.get_user_decision_history(
                user_id, days_back=self.context_window_days
            )
            
            # Analyze risk evolution from decision history
            risk_evolution = self._analyze_risk_evolution(decision_history)
            
            # Calculate risk trend
            risk_trend = self._calculate_risk_trend(current_risk, risk_evolution)
            
            evolution_analysis = {
                "user_id": user_id,
                "current_risk_level": current_risk.overall_risk_level.value,
                "current_risk_factors": current_risk.risk_factors,
                "risk_evolution": risk_evolution,
                "risk_trend": risk_trend,
                "evolution_summary": self._generate_evolution_summary(risk_trend, risk_evolution),
                "recommendations": self._generate_risk_recommendations(risk_trend, current_risk)
            }
            
            # Cache the analysis
            self.risk_evolution_cache[user_id] = evolution_analysis
            
            return evolution_analysis
            
        except Exception as e:
            logger.error(f"Error tracking risk profile evolution: {str(e)}")
            return {"error": str(e)}
    
    def _analyze_risk_evolution(self, decision_history: List[DecisionContext]) -> List[Dict[str, Any]]:
        """Analyze risk evolution from decision history."""
        evolution_points = []
        
        # Group decisions by time periods (weekly)
        from collections import defaultdict
        weekly_decisions = defaultdict(list)
        
        for decision in decision_history:
            # Get week number
            week_key = decision.timestamp.strftime("%Y-W%U")
            weekly_decisions[week_key].append(decision)
        
        # Analyze each week
        for week, decisions in sorted(weekly_decisions.items()):
            fraud_count = sum(1 for d in decisions if d.decision in [FraudDecision.DECLINED, FraudDecision.FLAGGED])
            total_count = len(decisions)
            fraud_rate = fraud_count / total_count if total_count > 0 else 0
            
            avg_confidence = sum(d.confidence_score for d in decisions) / total_count if total_count > 0 else 0
            
            evolution_points.append({
                "period": week,
                "transaction_count": total_count,
                "fraud_count": fraud_count,
                "fraud_rate": fraud_rate,
                "avg_confidence": avg_confidence,
                "risk_indicators": self._extract_risk_indicators(decisions)
            })
        
        return evolution_points
    
    def _extract_risk_indicators(self, decisions: List[DecisionContext]) -> Dict[str, int]:
        """Extract risk indicators from decisions."""
        indicators = defaultdict(int)
        
        for decision in decisions:
            # Count common risk indicators in reasoning steps
            for step in decision.reasoning_steps:
                step_lower = step.lower()
                if "velocity" in step_lower or "rapid" in step_lower:
                    indicators["velocity_risk"] += 1
                if "location" in step_lower or "geographic" in step_lower:
                    indicators["location_risk"] += 1
                if "amount" in step_lower or "spending" in step_lower:
                    indicators["amount_risk"] += 1
                if "device" in step_lower or "fingerprint" in step_lower:
                    indicators["device_risk"] += 1
                if "merchant" in step_lower:
                    indicators["merchant_risk"] += 1
        
        return dict(indicators)
    
    def _calculate_risk_trend(self, current_risk: RiskProfile, evolution: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate risk trend from evolution data."""
        if len(evolution) < 2:
            return {"trend": "insufficient_data", "direction": "stable", "magnitude": 0.0}
        
        # Calculate trend in fraud rate
        recent_periods = evolution[-4:]  # Last 4 weeks
        older_periods = evolution[:-4] if len(evolution) > 4 else evolution[:len(evolution)//2]
        
        if not older_periods:
            return {"trend": "insufficient_data", "direction": "stable", "magnitude": 0.0}
        
        recent_avg_fraud_rate = sum(p["fraud_rate"] for p in recent_periods) / len(recent_periods)
        older_avg_fraud_rate = sum(p["fraud_rate"] for p in older_periods) / len(older_periods)
        
        fraud_rate_change = recent_avg_fraud_rate - older_avg_fraud_rate
        
        # Determine trend direction
        if fraud_rate_change > 0.1:
            direction = "increasing"
        elif fraud_rate_change < -0.1:
            direction = "decreasing"
        else:
            direction = "stable"
        
        # Calculate confidence trend
        recent_avg_confidence = sum(p["avg_confidence"] for p in recent_periods) / len(recent_periods)
        older_avg_confidence = sum(p["avg_confidence"] for p in older_periods) / len(older_periods)
        
        confidence_change = recent_avg_confidence - older_avg_confidence
        
        return {
            "trend": "calculated",
            "direction": direction,
            "magnitude": abs(fraud_rate_change),
            "fraud_rate_change": fraud_rate_change,
            "confidence_change": confidence_change,
            "recent_fraud_rate": recent_avg_fraud_rate,
            "historical_fraud_rate": older_avg_fraud_rate
        }
    
    def _generate_evolution_summary(self, risk_trend: Dict[str, Any], evolution: List[Dict[str, Any]]) -> str:
        """Generate human-readable evolution summary."""
        if risk_trend["trend"] == "insufficient_data":
            return "Insufficient historical data to determine risk evolution trend."
        
        direction = risk_trend["direction"]
        magnitude = risk_trend["magnitude"]
        
        if direction == "increasing":
            severity = "significantly" if magnitude > 0.3 else "moderately" if magnitude > 0.1 else "slightly"
            return f"User's risk profile is {severity} increasing over time. Recent fraud rate: {risk_trend['recent_fraud_rate']:.1%}"
        elif direction == "decreasing":
            severity = "significantly" if magnitude > 0.3 else "moderately" if magnitude > 0.1 else "slightly"
            return f"User's risk profile is {severity} improving over time. Recent fraud rate: {risk_trend['recent_fraud_rate']:.1%}"
        else:
            return f"User's risk profile remains stable. Consistent fraud rate around {risk_trend['recent_fraud_rate']:.1%}"
    
    def _generate_risk_recommendations(self, risk_trend: Dict[str, Any], current_risk: RiskProfile) -> List[str]:
        """Generate recommendations based on risk evolution."""
        recommendations = []
        
        if risk_trend["direction"] == "increasing":
            recommendations.append("Consider increasing monitoring frequency for this user")
            recommendations.append("Review recent transaction patterns for emerging fraud indicators")
            if risk_trend["magnitude"] > 0.2:
                recommendations.append("Escalate to manual review for high-value transactions")
        
        elif risk_trend["direction"] == "decreasing":
            recommendations.append("User shows improving risk profile - consider reducing restrictions")
            if current_risk.overall_risk_level.value == "high":
                recommendations.append("Consider downgrading risk level if trend continues")
        
        # Factor-specific recommendations
        if current_risk.geographic_risk > 0.7:
            recommendations.append("High geographic risk detected - verify location patterns")
        
        if current_risk.behavioral_risk > 0.7:
            recommendations.append("Unusual behavioral patterns - review spending habits")
        
        if current_risk.velocity_risk > 0.7:
            recommendations.append("High velocity risk - monitor transaction frequency")
        
        return recommendations
    
    def get_historical_decision_patterns(self, user_id: str) -> Dict[str, Any]:
        """
        Analyze historical decision patterns for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary containing decision pattern analysis
        """
        try:
            logger.info(f"Analyzing historical decision patterns for user {user_id}")
            
            # Get decision history
            decision_history = self.memory_manager.get_user_decision_history(
                user_id, days_back=self.context_window_days
            )
            
            if not decision_history:
                return {"error": "No decision history found for user"}
            
            # Analyze patterns
            decision_counts = defaultdict(int)
            confidence_by_decision = defaultdict(list)
            reasoning_patterns = defaultdict(int)
            
            for decision in decision_history:
                decision_counts[decision.decision.value] += 1
                confidence_by_decision[decision.decision.value].append(decision.confidence_score)
                
                # Analyze reasoning patterns
                for step in decision.reasoning_steps:
                    # Extract key patterns
                    if "velocity" in step.lower():
                        reasoning_patterns["velocity_concerns"] += 1
                    if "location" in step.lower() or "geographic" in step.lower():
                        reasoning_patterns["location_concerns"] += 1
                    if "amount" in step.lower():
                        reasoning_patterns["amount_concerns"] += 1
                    if "merchant" in step.lower():
                        reasoning_patterns["merchant_concerns"] += 1
            
            # Calculate statistics
            total_decisions = len(decision_history)
            fraud_rate = (decision_counts["declined"] + decision_counts["flagged"]) / total_decisions
            
            avg_confidence_by_decision = {
                decision: sum(confidences) / len(confidences) if confidences else 0
                for decision, confidences in confidence_by_decision.items()
            }
            
            return {
                "user_id": user_id,
                "analysis_period_days": self.context_window_days,
                "total_decisions": total_decisions,
                "decision_distribution": dict(decision_counts),
                "fraud_rate": fraud_rate,
                "avg_confidence_by_decision": avg_confidence_by_decision,
                "common_reasoning_patterns": dict(reasoning_patterns),
                "pattern_insights": self._generate_pattern_insights(decision_counts, reasoning_patterns, fraud_rate)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing historical decision patterns: {str(e)}")
            return {"error": str(e)}
    
    def _generate_pattern_insights(
        self, 
        decision_counts: Dict[str, int], 
        reasoning_patterns: Dict[str, int], 
        fraud_rate: float
    ) -> List[str]:
        """Generate insights from decision patterns."""
        insights = []
        
        # Fraud rate insights
        if fraud_rate > 0.3:
            insights.append(f"High fraud rate ({fraud_rate:.1%}) indicates elevated risk profile")
        elif fraud_rate < 0.05:
            insights.append(f"Low fraud rate ({fraud_rate:.1%}) indicates good user behavior")
        
        # Reasoning pattern insights
        top_concern = max(reasoning_patterns.items(), key=lambda x: x[1]) if reasoning_patterns else None
        if top_concern and top_concern[1] > 5:
            insights.append(f"Primary risk factor: {top_concern[0].replace('_', ' ')} ({top_concern[1]} occurrences)")
        
        # Decision distribution insights
        if decision_counts.get("review_required", 0) > decision_counts.get("declined", 0):
            insights.append("Transactions often require manual review rather than automatic decline")
        
        return insights
    
    def compare_with_similar_users(self, user_id: str, transaction: Transaction) -> Dict[str, Any]:
        """
        Compare user's context with similar users for benchmarking.
        
        Args:
            user_id: User identifier
            transaction: Current transaction for context
            
        Returns:
            Dictionary containing similarity comparison
        """
        try:
            logger.info(f"Comparing user {user_id} with similar users")
            
            # Get user's profile
            user_profile = self.memory_manager.get_user_profile(user_id)
            if not user_profile:
                return {"error": "No user profile found"}
            
            # This would typically query for similar users based on:
            # - Spending patterns
            # - Geographic location
            # - Transaction frequency
            # - Risk profile
            
            # For demo purposes, create a simulated comparison
            similar_users_analysis = {
                "user_id": user_id,
                "comparison_metrics": {
                    "spending_percentile": self._calculate_spending_percentile(user_profile, transaction),
                    "risk_percentile": self._calculate_risk_percentile(user_profile),
                    "activity_percentile": self._calculate_activity_percentile(user_profile)
                },
                "peer_group_insights": self._generate_peer_insights(user_profile),
                "relative_risk_assessment": self._assess_relative_risk(user_profile)
            }
            
            return similar_users_analysis
            
        except Exception as e:
            logger.error(f"Error comparing with similar users: {str(e)}")
            return {"error": str(e)}
    
    def _calculate_spending_percentile(self, user_profile: UserBehaviorProfile, transaction: Transaction) -> float:
        """Calculate user's spending percentile compared to similar users."""
        # Simplified calculation - in practice, this would query actual user data
        user_avg = user_profile.typical_spending_range.get("avg", 100)
        transaction_amount = float(transaction.amount)
        
        # Simulate percentile based on spending patterns
        if transaction_amount > user_avg * 2:
            return 95.0  # High spender
        elif transaction_amount > user_avg:
            return 75.0
        elif transaction_amount > user_avg * 0.5:
            return 50.0
        else:
            return 25.0  # Low spender
    
    def _calculate_risk_percentile(self, user_profile: UserBehaviorProfile) -> float:
        """Calculate user's risk percentile."""
        # Simplified calculation based on risk score
        risk_score = user_profile.risk_score
        
        if risk_score > 0.8:
            return 95.0  # High risk
        elif risk_score > 0.6:
            return 80.0
        elif risk_score > 0.4:
            return 60.0
        elif risk_score > 0.2:
            return 40.0
        else:
            return 20.0  # Low risk
    
    def _calculate_activity_percentile(self, user_profile: UserBehaviorProfile) -> float:
        """Calculate user's activity percentile."""
        monthly_transactions = user_profile.transaction_frequency.get("monthly", 10)
        
        if monthly_transactions > 100:
            return 95.0  # Very active
        elif monthly_transactions > 50:
            return 80.0
        elif monthly_transactions > 20:
            return 60.0
        elif monthly_transactions > 10:
            return 40.0
        else:
            return 20.0  # Low activity
    
    def _generate_peer_insights(self, user_profile: UserBehaviorProfile) -> List[str]:
        """Generate insights about user compared to peers."""
        insights = []
        
        risk_score = user_profile.risk_score
        monthly_txns = user_profile.transaction_frequency.get("monthly", 10)
        
        if risk_score < 0.3 and monthly_txns > 20:
            insights.append("User shows low risk with high activity - typical of established customers")
        elif risk_score > 0.7:
            insights.append("User in high-risk category - requires enhanced monitoring")
        elif monthly_txns < 5:
            insights.append("Low activity user - limited behavioral data available")
        
        return insights
    
    def _assess_relative_risk(self, user_profile: UserBehaviorProfile) -> str:
        """Assess user's risk relative to peer group."""
        risk_score = user_profile.risk_score
        
        if risk_score > 0.8:
            return "significantly_higher_than_peers"
        elif risk_score > 0.6:
            return "higher_than_peers"
        elif risk_score > 0.4:
            return "similar_to_peers"
        elif risk_score > 0.2:
            return "lower_than_peers"
        else:
            return "significantly_lower_than_peers"