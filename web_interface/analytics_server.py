"""
Analytics Dashboard Server

Flask server for the advanced analytics dashboard with WebSocket support.
"""

from flask import Flask, jsonify, send_file, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from analytics_dashboard_api import AnalyticsDashboardAPI
import os
import threading
import time

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

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


@app.route('/api/analytics/stress-test-metrics')
def get_stress_test_metrics():
    """Get stress test specific metrics"""
    return jsonify(analytics_api.get_stress_test_metrics())


# WebSocket event handlers
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print('Client connected to analytics dashboard')
    emit('connection_response', {'status': 'connected'})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print('Client disconnected from analytics dashboard')


@socketio.on('subscribe_metrics')
def handle_subscribe(data):
    """Handle metrics subscription"""
    print(f'Client subscribed to metrics: {data}')
    emit('subscription_confirmed', {'metrics': data.get('metrics', [])})


# Background thread for streaming metrics
streaming_active = False
streaming_thread = None


def stream_metrics():
    """Background thread to stream metrics to connected clients"""
    global streaming_active
    
    while streaming_active:
        try:
            # Collect latest metrics
            metrics_data = {
                'stress_test_metrics': analytics_api.get_stress_test_metrics(),
                'fraud_statistics': analytics_api.get_fraud_statistics(),
                'decision_metrics': analytics_api.get_decision_metrics(),
                'timestamp': time.time()
            }
            
            # Broadcast to all connected clients
            socketio.emit('metrics_update', metrics_data)
            
            # Simulate some activity
            analytics_api.simulate_analytics_activity()
            
            # Wait before next update (2 seconds for smooth updates)
            time.sleep(2)
            
        except Exception as e:
            print(f'Error streaming metrics: {e}')
            time.sleep(5)


@app.route('/api/analytics/streaming/start')
def start_streaming():
    """Start metrics streaming"""
    global streaming_active, streaming_thread
    
    if not streaming_active:
        streaming_active = True
        streaming_thread = threading.Thread(target=stream_metrics, daemon=True)
        streaming_thread.start()
        return jsonify({"status": "success", "message": "Streaming started"})
    
    return jsonify({"status": "info", "message": "Streaming already active"})


@app.route('/api/analytics/streaming/stop')
def stop_streaming():
    """Stop metrics streaming"""
    global streaming_active
    
    streaming_active = False
    return jsonify({"status": "success", "message": "Streaming stopped"})


if __name__ == '__main__':
    # Get port from environment variable (for Render deployment) or use default
    port = int(os.environ.get('PORT', 5001))
    host = os.environ.get('HOST', '0.0.0.0')
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    print("\n" + "="*70)
    print("🚀 ANALYTICS DASHBOARD SERVER STARTING")
    print("="*70)
    print("\n📊 Advanced Analytics Dashboard")
    print(f"   URL: http://{host}:{port}")
    print("\n📡 API Endpoints:")
    print("   GET  /api/analytics/summary              - Analytics summary")
    print("   GET  /api/analytics/patterns             - Fraud patterns")
    print("   GET  /api/analytics/decision-metrics     - Decision metrics")
    print("   GET  /api/analytics/statistics           - Fraud statistics")
    print("   GET  /api/analytics/stress-test-metrics  - Stress test metrics")
    print("   GET  /api/analytics/explainable-decision/<id> - Explainable decision")
    print("   GET  /api/analytics/heatmap              - Fraud heatmap")
    print("   GET  /api/analytics/risk-distribution    - Risk distribution")
    print("   GET  /api/analytics/top-indicators       - Top indicators")
    print("   GET  /api/analytics/simulate             - Simulate activity")
    print("   GET  /api/analytics/streaming/start      - Start WebSocket streaming")
    print("   GET  /api/analytics/streaming/stop       - Stop WebSocket streaming")
    print("\n🔌 WebSocket Events:")
    print("   connect                                  - Client connection")
    print("   subscribe_metrics                        - Subscribe to metrics")
    print("   metrics_update                           - Real-time metrics broadcast")
    print("\n" + "="*70)
    print("Press Ctrl+C to stop the server")
    print("="*70 + "\n")
    
    socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)
