"""
Dashboard Web Server

Flask-based web server for the Agent Management Dashboard.
Serves the HTML interface and provides REST API endpoints.
"""

from flask import Flask, jsonify, render_template, send_from_directory
from flask_cors import CORS
import os
import sys
from pathlib import Path

# Add project root to path
CURRENT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.agent_dashboard_api import AgentDashboardAPI, AgentStatus

# Initialize Flask app
app = Flask(__name__, 
            static_folder='.',
            template_folder='.')
CORS(app)  # Enable CORS for API access

# Initialize dashboard API
dashboard_api = AgentDashboardAPI()

# Routes
@app.route('/')
def index():
    """Serve the main dashboard page"""
    return send_from_directory('.', 'agent_dashboard.html')

@app.route('/api/summary')
def get_summary():
    """Get dashboard summary"""
    return jsonify(dashboard_api.get_dashboard_summary())

@app.route('/api/agents')
def get_agents():
    """Get all agents"""
    return jsonify({
        "success": True,
        "agents": dashboard_api.get_all_agents()
    })

@app.route('/api/agents/<agent_id>')
def get_agent(agent_id):
    """Get specific agent details"""
    agent = dashboard_api.get_agent(agent_id)
    if agent:
        return jsonify({"success": True, "agent": agent})
    return jsonify({"success": False, "error": "Agent not found"}), 404

@app.route('/api/agents/<agent_id>/metrics/history')
def get_agent_metrics_history(agent_id):
    """Get agent metrics history"""
    return jsonify(dashboard_api.get_agent_metrics_history(agent_id))

@app.route('/api/coordination/events')
def get_coordination_events():
    """Get coordination events"""
    return jsonify(dashboard_api.get_coordination_events(limit=50))

@app.route('/api/coordination/workflow/<transaction_id>')
def get_coordination_workflow(transaction_id):
    """Get coordination workflow for a transaction"""
    return jsonify(dashboard_api.get_coordination_workflow(transaction_id))

@app.route('/api/simulate')
def simulate_activity():
    """Simulate agent activity for demonstration"""
    dashboard_api.simulate_agent_activity()
    return jsonify({"success": True, "message": "Activity simulated"})

def run_server(host='127.0.0.1', port=5000, debug=True):
    """
    Run the dashboard web server
    
    Args:
        host: Host address
        port: Port number
        debug: Enable debug mode
    """
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║        🤖 Agent Management Dashboard Server                 ║
║                                                              ║
║  Dashboard URL: http://{host}:{port}                    ║
║  API Base URL:  http://{host}:{port}/api                ║
║                                                              ║
║  Available Endpoints:                                        ║
║  • GET  /                          - Dashboard UI            ║
║  • GET  /api/summary               - Dashboard summary       ║
║  • GET  /api/agents                - All agents              ║
║  • GET  /api/agents/<id>           - Agent details           ║
║  • GET  /api/agents/<id>/metrics/history - Metrics history   ║
║  • GET  /api/coordination/events   - Coordination events     ║
║  • GET  /api/coordination/workflow/<tx_id> - Workflow        ║
║  • GET  /api/simulate              - Simulate activity       ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    app.run(host=host, port=port, debug=debug)

if __name__ == '__main__':
    run_server()
