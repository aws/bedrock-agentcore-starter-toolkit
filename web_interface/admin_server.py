"""
Administrative Interface Server

Flask server for the administrative interface.
"""

from flask import Flask, jsonify, send_file, request
from flask_cors import CORS
from admin_interface_api import AdminInterfaceAPI

app = Flask(__name__)
CORS(app)

# Initialize admin API
admin_api = AdminInterfaceAPI()


@app.route('/')
def index():
    """Serve the admin interface HTML"""
    return send_file('admin_interface.html')


@app.route('/api/admin/summary')
def get_admin_summary():
    """Get administrative dashboard summary"""
    return jsonify(admin_api.get_admin_summary())


@app.route('/api/admin/users')
def get_users():
    """Get all users"""
    return jsonify(admin_api.get_all_users())


@app.route('/api/admin/users/<user_id>')
def get_user(user_id):
    """Get specific user"""
    user = admin_api.get_user(user_id)
    if user:
        return jsonify(user)
    return jsonify({"error": "User not found"}), 404


@app.route('/api/admin/rules')
def get_rules():
    """Get all rules"""
    return jsonify(admin_api.get_all_rules())


@app.route('/api/admin/rules/<rule_id>')
def get_rule(rule_id):
    """Get specific rule"""
    rule = admin_api.get_rule(rule_id)
    if rule:
        return jsonify(rule)
    return jsonify({"error": "Rule not found"}), 404


@app.route('/api/admin/configs')
def get_configs():
    """Get all configurations"""
    return jsonify(admin_api.get_all_configs())


@app.route('/api/admin/configs/category/<category>')
def get_configs_by_category(category):
    """Get configurations by category"""
    return jsonify(admin_api.get_configs_by_category(category))


@app.route('/api/admin/audit-logs')
def get_audit_logs():
    """Get audit logs with filtering"""
    limit = int(request.args.get('limit', 100))
    offset = int(request.args.get('offset', 0))
    user_id = request.args.get('user_id')
    action = request.args.get('action')
    
    return jsonify(admin_api.get_audit_logs(
        limit=limit,
        offset=offset,
        user_id=user_id,
        action=action
    ))


@app.route('/api/admin/audit-logs/search')
def search_audit_logs():
    """Search audit logs"""
    query = request.args.get('q', '')
    limit = int(request.args.get('limit', 50))
    
    return jsonify(admin_api.search_audit_logs(query, limit))


if __name__ == '__main__':
    print("\n" + "="*70)
    print("🚀 ADMINISTRATIVE INTERFACE SERVER STARTING")
    print("="*70)
    print("\n⚙️  Administrative Interface")
    print("   URL: http://127.0.0.1:5002")
    print("\n📡 API Endpoints:")
    print("   GET  /api/admin/summary          - Admin summary")
    print("   GET  /api/admin/users            - All users")
    print("   GET  /api/admin/rules            - All rules")
    print("   GET  /api/admin/configs          - All configurations")
    print("   GET  /api/admin/audit-logs       - Audit logs")
    print("   GET  /api/admin/audit-logs/search - Search logs")
    print("\n" + "="*70)
    print("Press Ctrl+C to stop the server")
    print("="*70 + "\n")
    
    app.run(host='127.0.0.1', port=5002, debug=True)
