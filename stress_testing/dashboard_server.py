"""
Unified Dashboard Server - Serves all dashboards and provides WebSocket updates.

Simplified Flask server for fast-track implementation.
"""

from flask import Flask, render_template, jsonify, send_from_directory
from flask_cors import CORS
import asyncio
import logging
from pathlib import Path

app = Flask(__name__, 
            template_folder='dashboards',
            static_folder='dashboards')
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.route('/')
def index():
    """Serve main dashboard selection page."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Stress Testing Dashboards</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
            }
            .container {
                text-align: center;
            }
            h1 {
                font-size: 3em;
                margin-bottom: 50px;
            }
            .dashboard-links {
                display: flex;
                gap: 30px;
                justify-content: center;
            }
            .dashboard-card {
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px);
                border-radius: 15px;
                padding: 40px;
                min-width: 250px;
                transition: transform 0.3s ease;
                cursor: pointer;
            }
            .dashboard-card:hover {
                transform: translateY(-10px);
            }
            .dashboard-card h2 {
                margin-bottom: 15px;
            }
            a {
                color: white;
                text-decoration: none;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 Stress Testing Dashboards</h1>
            <div class="dashboard-links">
                <a href="/investor">
                    <div class="dashboard-card">
                        <h2>💼 Investor Dashboard</h2>
                        <p>Business metrics and presentation</p>
                    </div>
                </a>
            </div>
        </div>
    </body>
    </html>
    """


@app.route('/investor')
def investor_dashboard():
    """Serve investor presentation dashboard."""
    dashboard_path = Path(__file__).parent / 'dashboards' / 'investor_dashboard.html'
    with open(dashboard_path, 'r') as f:
        return f.read()


@app.route('/api/presentation-data')
def get_presentation_data():
    """API endpoint for presentation data."""
    # Return mock data for now
    return jsonify({
        'hero_metrics': {
            'total_transactions': 125000,
            'fraud_blocked': 2500,
            'money_saved': 750000,
            'throughput_tps': 5000,
            'ai_accuracy': 0.95,
            'roi_percentage': 180
        },
        'status': 'success'
    })


@app.route('/api/health')
def health_check():
    """Health check endpoint."""
    return jsonify({'status': 'healthy', 'service': 'dashboard-server'})


def run_server(host='0.0.0.0', port=5000, debug=False):
    """
    Run the dashboard server.
    
    Args:
        host: Host to bind to
        port: Port to listen on
        debug: Enable debug mode
    """
    logger.info(f"Starting dashboard server on {host}:{port}")
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    run_server(debug=True)
