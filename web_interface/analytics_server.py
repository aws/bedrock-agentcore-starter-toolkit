"""
Analytics Dashboard Server

Flask server for the advanced analytics dashboard.
"""

from flask import Flask, jsonify, send_file, request
from flask_cors import CORS
from analytics_dashboard_api import AnalyticsDashboardAPI
import os

app = Flask(__name__)
CORS(app)

# Initialize analytics API
analytics_api = AnalyticsDashboardAPI()


@app.route('/')
def index():
    """Serve the analytics dashboard HTML"""
    return send_file('analytics_dashboard.html')


@app.route('/api/analytics/summary')
def get_analytics_summary():
    """Get comprehensive analytics summary"""
    return jsonify(analytics_api.get_analytics_summary())


@app.route('/api/analytics/patterns')
def get_fraud_patterns():
    """Get all fraud patterns"""
    return jsonify(analytics_api.get_fraud_patterns())


@app.route('/api/analytics/patterns/<pattern_type>/trends')
def get_pattern_trends(pattern_type):
    """Get trend data for a specific pattern"""
    hours = int(request.args.get('hours', 24))
    return jsonify(analytics_api.get_pattern_trends(pattern_type, hours))


@app.route('/api/analytics/decision-metrics')
def get_decision_metrics():
    """Get decision accuracy metrics"""
    return jsonify(analytics_api.get_decision_metrics())


@app.route('/api/analytics/decision-accuracy-trend')
def get_decision_accuracy_trend():
    """Get decision accuracy trend"""
    days = int(request.args.get('days', 7))
    return jsonify(analytics_api.get_decision_accuracy_trend(days))


@app.route('/api/analytics/statistics')
def get_fraud_statistics():
    """Get fraud detection statistics"""
    return jsonify(analytics_api.get_fraud_statistics())


@app.route('/api/analytics/explainable-decision/<transaction_id>')
def get_explainable_decision(transaction_id):
    """Get explainable AI decision for a transaction"""
    decision = analytics_api.get_explainable_decision(transaction_id)
    if decision:
        return jsonify(decision)
    return jsonify({"error": "Decision not found"}), 404


@app.route('/api/analytics/heatmap')
def get_fraud_heatmap():
    """Get fraud detection heatmap"""
    return jsonify(analytics_api.get_fraud_heatmap())


@app.route('/api/analytics/risk-distribution')
def get_risk_distribution():
    """Get risk score distribution"""
    return jsonify(analytics_api.get_risk_distribution())


@app.route('/api/analytics/top-indicators')
def get_top_indicators():
    """Get top fraud indicators"""
    limit = int(request.args.get('limit', 10))
    return jsonify(analytics_api.get_top_fraud_indicators(limit))


@app.route('/api/analytics/simulate')
def simulate_activity():
    """Simulate analytics activity"""
    analytics_api.simulate_analytics_activity()
    return jsonify({"status": "success", "message": "Activity simulated"})


if __name__ == '__main__':
    print("\n" + "="*70)
    print("🚀 ANALYTICS DASHBOARD SERVER STARTING")
    print("="*70)
    print("\n📊 Advanced Analytics Dashboard")
    print("   URL: http://127.0.0.1:5001")
    print("\n📡 API Endpoints:")
    print("   GET  /api/analytics/summary              - Analytics summary")
    print("   GET  /api/analytics/patterns             - Fraud patterns")
    print("   GET  /api/analytics/decision-metrics     - Decision metrics")
    print("   GET  /api/analytics/statistics           - Fraud statistics")
    print("   GET  /api/analytics/explainable-decision/<id> - Explainable decision")
    print("   GET  /api/analytics/heatmap              - Fraud heatmap")
    print("   GET  /api/analytics/risk-distribution    - Risk distribution")
    print("   GET  /api/analytics/top-indicators       - Top indicators")
    print("   GET  /api/analytics/simulate             - Simulate activity")
    print("\n" + "="*70)
    print("Press Ctrl+C to stop the server")
    print("="*70 + "\n")
    
    app.run(host='127.0.0.1', port=5001, debug=True)
