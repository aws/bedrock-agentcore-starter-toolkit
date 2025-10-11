"""
Demo script for the Advanced Analytics Dashboard

Demonstrates:
- Fraud pattern visualization and trend analysis
- Decision accuracy tracking and performance metrics
- Explainable AI interface for decision investigation
- Real-time fraud detection statistics and alerts
"""

import sys
import os

# Add project root to path
CURRENT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from web_interface.analytics_dashboard_api import AnalyticsDashboardAPI


def demo_fraud_patterns():
    """Demonstrate fraud pattern visualization"""
    print("=" * 70)
    print("ANALYTICS DASHBOARD DEMO - FRAUD PATTERN VISUALIZATION")
    print("=" * 70)
    
    api = AnalyticsDashboardAPI()
    
    patterns = api.get_fraud_patterns()
    
    print(f"\n📊 Active Fraud Patterns: {len(patterns)}")
    print("-" * 70)
    
    for pattern in patterns:
        severity_icon = "🔴" if pattern['severity'] == "critical" else "🟡" if pattern['severity'] == "high" else "🟢"
        trend_icon = "📈" if pattern['trend'] == "increasing" else "📉" if pattern['trend'] == "decreasing" else "➡️"
        
        print(f"\n{severity_icon} {pattern['pattern_type'].replace('_', ' ').title()}")
        print(f"   Severity: {pattern['severity'].upper()}")
        print(f"   Occurrences: {pattern['occurrences']}")
        print(f"   Detection Rate: {pattern['detection_rate']*100:.1f}%")
        print(f"   Avg Amount: ${pattern['avg_amount']:.2f}")
        print(f"   Trend: {trend_icon} {pattern['trend']}")
        print(f"   Last Detected: {pattern['last_detected'][:19]}")


def demo_decision_metrics():
    """Demonstrate decision accuracy tracking"""
    print("\n" + "=" * 70)
    print("ANALYTICS DASHBOARD DEMO - DECISION ACCURACY METRICS")
    print("=" * 70)
    
    api = AnalyticsDashboardAPI()
    
    metrics = api.get_decision_metrics()
    
    print(f"\n🎯 Decision Performance Metrics")
    print("-" * 70)
    print(f"Total Decisions: {metrics['total_decisions']:,}")
    print(f"\n✅ Correct Decisions:")
    print(f"   True Positives:  {metrics['true_positives']:,} (correctly identified fraud)")
    print(f"   True Negatives:  {metrics['true_negatives']:,} (correctly identified legitimate)")
    print(f"\n❌ Incorrect Decisions:")
    print(f"   False Positives: {metrics['false_positives']:,} (incorrectly flagged as fraud)")
    print(f"   False Negatives: {metrics['false_negatives']:,} (missed fraud)")
    print(f"\n📈 Performance Scores:")
    print(f"   Accuracy:  {metrics['accuracy']*100:.2f}%")
    print(f"   Precision: {metrics['precision']*100:.2f}%")
    print(f"   Recall:    {metrics['recall']*100:.2f}%")
    print(f"   F1 Score:  {metrics['f1_score']*100:.2f}%")
    
    # Show accuracy trend
    print(f"\n📊 Accuracy Trend (Last 7 Days)")
    print("-" * 70)
    
    trend = api.get_decision_accuracy_trend(days=7)
    
    # Sample every 24 hours
    daily_trend = trend[::24]
    
    for point in daily_trend[:7]:
        print(f"   {point['label']}: Accuracy {point['accuracy']*100:.1f}% | "
              f"Precision {point['precision']*100:.1f}% | "
              f"Recall {point['recall']*100:.1f}%")


def demo_fraud_statistics():
    """Demonstrate real-time fraud statistics"""
    print("\n" + "=" * 70)
    print("ANALYTICS DASHBOARD DEMO - REAL-TIME FRAUD STATISTICS")
    print("=" * 70)
    
    api = AnalyticsDashboardAPI()
    
    stats = api.get_fraud_statistics()
    
    print(f"\n📈 Transaction Statistics")
    print("-" * 70)
    print(f"Total Transactions:   {stats['total_transactions']:,}")
    print(f"Flagged Transactions: {stats['flagged_transactions']:,}")
    print(f"Blocked Transactions: {stats['blocked_transactions']:,}")
    print(f"Fraud Rate:           {stats['fraud_rate']*100:.2f}%")
    print(f"\n💰 Financial Impact")
    print("-" * 70)
    print(f"Avg Transaction Amount: ${stats['avg_transaction_amount']:.2f}")
    print(f"Total Amount Saved:     ${stats['total_amount_saved']:,.2f}")
    print(f"\n⚠️ Risk Indicators")
    print("-" * 70)
    print(f"High Risk Users:    {stats['high_risk_users']}")
    print(f"Active Patterns:    {stats['active_patterns']}")
    
    # Show risk distribution
    print(f"\n📊 Risk Score Distribution")
    print("-" * 70)
    
    risk_dist = api.get_risk_distribution()
    
    for risk_level, count in risk_dist['distribution'].items():
        percentage = risk_dist['percentages'][risk_level]
        bar_length = int(percentage / 2)
        bar = "█" * bar_length
        print(f"   {risk_level.upper():10} {bar} {count:,} ({percentage:.1f}%)")


def demo_explainable_ai():
    """Demonstrate explainable AI interface"""
    print("\n" + "=" * 70)
    print("ANALYTICS DASHBOARD DEMO - EXPLAINABLE AI DECISION")
    print("=" * 70)
    
    api = AnalyticsDashboardAPI()
    
    transaction_id = "tx_sample_001"
    decision = api.get_explainable_decision(transaction_id)
    
    print(f"\n💡 Explainable Decision for Transaction: {decision['transaction_id']}")
    print("-" * 70)
    print(f"Decision:   {decision['decision'].upper()}")
    print(f"Confidence: {decision['confidence']*100:.0f}%")
    print(f"Timestamp:  {decision['timestamp'][:19]}")
    
    print(f"\n🔍 Reasoning Steps:")
    print("-" * 70)
    for i, step in enumerate(decision['reasoning_steps'], 1):
        print(f"   {i}. {step}")
    
    print(f"\n📋 Evidence:")
    print("-" * 70)
    for evidence in decision['evidence']:
        risk_icon = "🔴" if evidence['risk'] == "high" else "🟡" if evidence['risk'] == "medium" else "🟢"
        print(f"   {risk_icon} {evidence['type'].title()}: {evidence['value']} "
              f"(Risk: {evidence['risk']}, Weight: {evidence['weight']*100:.0f}%)")
    
    print(f"\n⚠️ Risk Factors:")
    print("-" * 70)
    for factor in decision['risk_factors']:
        impact_icon = "🔴" if factor['impact'] == "high" else "🟡" if factor['impact'] == "medium" else "🟢"
        print(f"   {impact_icon} {factor['factor']}: {factor['score']:.1f}/10 ({factor['impact']} impact)")
    
    print(f"\n🔄 Alternative Outcomes:")
    print("-" * 70)
    for alt in decision['alternative_outcomes']:
        print(f"   • {alt['decision'].upper()} ({alt['confidence']*100:.0f}% confidence)")
        print(f"     Reason: {alt['reason']}")


def demo_top_indicators():
    """Demonstrate top fraud indicators"""
    print("\n" + "=" * 70)
    print("ANALYTICS DASHBOARD DEMO - TOP FRAUD INDICATORS")
    print("=" * 70)
    
    api = AnalyticsDashboardAPI()
    
    indicators = api.get_top_fraud_indicators(limit=10)
    
    print(f"\n🔝 Top 10 Fraud Indicators")
    print("-" * 70)
    
    for i, indicator in enumerate(indicators, 1):
        accuracy_bar = "█" * int(indicator['accuracy'] * 20)
        print(f"\n{i:2}. {indicator['indicator']}")
        print(f"    Occurrences: {indicator['occurrences']:3} | "
              f"Accuracy: {accuracy_bar} {indicator['accuracy']*100:.0f}%")


def demo_analytics_summary():
    """Demonstrate comprehensive analytics summary"""
    print("\n" + "=" * 70)
    print("ANALYTICS DASHBOARD DEMO - COMPREHENSIVE SUMMARY")
    print("=" * 70)
    
    api = AnalyticsDashboardAPI()
    
    summary = api.get_analytics_summary()
    
    print(f"\n📊 Overall Analytics Summary")
    print("-" * 70)
    
    fraud_stats = summary['fraud_statistics']
    decision_metrics = summary['decision_metrics']
    pattern_summary = summary['pattern_summary']
    
    print(f"\n🎯 Key Performance Indicators:")
    print(f"   Total Transactions:    {fraud_stats['total_transactions']:,}")
    print(f"   Fraud Rate:            {fraud_stats['fraud_rate']*100:.2f}%")
    print(f"   Detection Accuracy:    {decision_metrics['accuracy']*100:.2f}%")
    print(f"   Amount Saved:          ${fraud_stats['total_amount_saved']:,.2f}")
    
    print(f"\n📈 Pattern Analysis:")
    print(f"   Active Patterns:       {summary['active_patterns']}")
    print(f"   Total Occurrences:     {pattern_summary['total_occurrences']}")
    print(f"   Avg Detection Rate:    {pattern_summary['avg_detection_rate']*100:.1f}%")
    print(f"   Critical Patterns:     {pattern_summary['critical_patterns']}")
    
    print(f"\n🎯 Decision Quality:")
    print(f"   Precision:             {decision_metrics['precision']*100:.2f}%")
    print(f"   Recall:                {decision_metrics['recall']*100:.2f}%")
    print(f"   F1 Score:              {decision_metrics['f1_score']*100:.2f}%")


def demo_activity_simulation():
    """Demonstrate activity simulation"""
    print("\n" + "=" * 70)
    print("ANALYTICS DASHBOARD DEMO - ACTIVITY SIMULATION")
    print("=" * 70)
    
    api = AnalyticsDashboardAPI()
    
    print(f"\n🔄 Simulating Analytics Activity...")
    print("-" * 70)
    
    # Get initial stats
    initial_stats = api.get_fraud_statistics()
    print(f"\nInitial State:")
    print(f"   Total Transactions: {initial_stats['total_transactions']:,}")
    print(f"   Flagged: {initial_stats['flagged_transactions']:,}")
    print(f"   Blocked: {initial_stats['blocked_transactions']:,}")
    
    # Simulate activity
    for i in range(5):
        api.simulate_analytics_activity()
        print(f"\n   Simulation {i+1} completed...")
    
    # Get updated stats
    updated_stats = api.get_fraud_statistics()
    print(f"\nUpdated State:")
    print(f"   Total Transactions: {updated_stats['total_transactions']:,} "
          f"(+{updated_stats['total_transactions'] - initial_stats['total_transactions']})")
    print(f"   Flagged: {updated_stats['flagged_transactions']:,} "
          f"(+{updated_stats['flagged_transactions'] - initial_stats['flagged_transactions']})")
    print(f"   Blocked: {updated_stats['blocked_transactions']:,} "
          f"(+{updated_stats['blocked_transactions'] - initial_stats['blocked_transactions']})")
    print(f"   Fraud Rate: {updated_stats['fraud_rate']*100:.2f}%")


def main():
    """Run all analytics dashboard demos"""
    print("🔍 ADVANCED ANALYTICS DASHBOARD DEMONSTRATION")
    print("=" * 70)
    print("This demo showcases the advanced analytics dashboard with:")
    print("• Fraud pattern visualization and trend analysis")
    print("• Decision accuracy tracking and performance metrics")
    print("• Explainable AI interface for decision investigation")
    print("• Real-time fraud detection statistics and alerts")
    print("=" * 70)
    
    try:
        demo_fraud_patterns()
        demo_decision_metrics()
        demo_fraud_statistics()
        demo_explainable_ai()
        demo_top_indicators()
        demo_analytics_summary()
        demo_activity_simulation()
        
        print("\n" + "=" * 70)
        print("✅ ANALYTICS DASHBOARD DEMO COMPLETED SUCCESSFULLY")
        print("=" * 70)
        print("\nThe analytics dashboard demonstrated:")
        print("• ✓ Fraud pattern detection and visualization")
        print("• ✓ Decision accuracy metrics (92.7% accuracy)")
        print("• ✓ Real-time fraud statistics tracking")
        print("• ✓ Explainable AI decision breakdown")
        print("• ✓ Top fraud indicators analysis")
        print("• ✓ Comprehensive analytics summary")
        print("• ✓ Activity simulation capabilities")
        print("\n💡 To view the interactive dashboard:")
        print("   1. Run: python web_interface/analytics_server.py")
        print("   2. Open: http://127.0.0.1:5001")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
