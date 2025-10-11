"""
Demo script for the Administrative Interface

Demonstrates:
- System configuration and rule management
- User access control and permission management
- Audit log viewing and search functionality
- System health monitoring
"""

import sys
import os

CURRENT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from web_interface.admin_interface_api import AdminInterfaceAPI


def demo_user_management():
    """Demonstrate user management"""
    print("=" * 70)
    print("ADMIN INTERFACE DEMO - USER MANAGEMENT")
    print("=" * 70)
    
    api = AdminInterfaceAPI()
    
    users = api.get_all_users()
    
    print(f"\n👥 Total Users: {len(users)}")
    print("-" * 70)
    
    for user in users:
        status_icon = "✅" if user['active'] else "❌"
        mfa_icon = "🔐" if user['mfa_enabled'] else "🔓"
        
        print(f"\n{status_icon} {user['username']} ({user['role'].upper()})")
        print(f"   Email: {user['email']}")
        print(f"   Permissions: {len(user['permissions'])}")
        print(f"   MFA: {mfa_icon}")
        print(f"   Last Login: {user['last_login'][:19] if user['last_login'] else 'Never'}")


def demo_rule_management():
    """Demonstrate rule management"""
    print("\n" + "=" * 70)
    print("ADMIN INTERFACE DEMO - RULE MANAGEMENT")
    print("=" * 70)
    
    api = AdminInterfaceAPI()
    
    rules = api.get_all_rules()
    
    print(f"\n📋 Total Rules: {len(rules)}")
    print(f"   Enabled: {sum(1 for r in rules if r['enabled'])}")
    print(f"   Disabled: {sum(1 for r in rules if not r['enabled'])}")
    print("-" * 70)
    
    for rule in rules:
        status_icon = "✅" if rule['enabled'] else "❌"
        
        print(f"\n{status_icon} {rule['name']}")
        print(f"   Type: {rule['rule_type']}")
        print(f"   Priority: {rule['priority']}")
        print(f"   Executions: {rule['execution_count']}")
        print(f"   Actions: {', '.join(rule['actions'])}")


def demo_configuration():
    """Demonstrate configuration management"""
    print("\n" + "=" * 70)
    print("ADMIN INTERFACE DEMO - CONFIGURATION MANAGEMENT")
    print("=" * 70)
    
    api = AdminInterfaceAPI()
    
    configs = api.get_all_configs()
    
    categories = {}
    for config in configs:
        if config['category'] not in categories:
            categories[config['category']] = []
        categories[config['category']].append(config)
    
    for category, items in categories.items():
        print(f"\n⚙️  {category.upper()}")
        print("-" * 70)
        for config in items:
            print(f"   {config['key']}: {config['value']}")
            print(f"      {config['description']}")


def demo_audit_logs():
    """Demonstrate audit log viewing"""
    print("\n" + "=" * 70)
    print("ADMIN INTERFACE DEMO - AUDIT LOG VIEWER")
    print("=" * 70)
    
    api = AdminInterfaceAPI()
    
    logs_response = api.get_audit_logs(limit=10)
    logs = logs_response['logs']
    
    print(f"\n📜 Recent Audit Logs (showing {len(logs)} of {logs_response['total']})")
    print("-" * 70)
    
    for log in logs:
        print(f"\n[{log['timestamp'][:19]}] {log['user_id']}")
        print(f"   Action: {log['action']}")
        print(f"   Resource: {log['resource']}")
        print(f"   IP: {log['ip_address']}")
        print(f"   Status: {log['status']}")


def demo_admin_summary():
    """Demonstrate admin dashboard summary"""
    print("\n" + "=" * 70)
    print("ADMIN INTERFACE DEMO - DASHBOARD SUMMARY")
    print("=" * 70)
    
    api = AdminInterfaceAPI()
    
    summary = api.get_admin_summary()
    
    print(f"\n📊 System Overview")
    print("-" * 70)
    print(f"Users: {summary['users']['total']} total, {summary['users']['active']} active")
    print(f"Rules: {summary['rules']['total']} total, {summary['rules']['enabled']} enabled")
    print(f"Audit Logs: {summary['audit_logs']['total']} total, {summary['audit_logs']['last_24h']} in last 24h")
    print(f"System Status: {summary['system_health']['status']}")
    print(f"Uptime: {summary['system_health']['uptime_hours']} hours")


def main():
    """Run all admin interface demos"""
    print("⚙️  ADMINISTRATIVE INTERFACE DEMONSTRATION")
    print("=" * 70)
    print("This demo showcases the administrative interface with:")
    print("• System configuration and rule management")
    print("• User access control and permission management")
    print("• Audit log viewing and search functionality")
    print("• System health monitoring and diagnostic tools")
    print("=" * 70)
    
    try:
        demo_admin_summary()
        demo_user_management()
        demo_rule_management()
        demo_configuration()
        demo_audit_logs()
        
        print("\n" + "=" * 70)
        print("✅ ADMINISTRATIVE INTERFACE DEMO COMPLETED SUCCESSFULLY")
        print("=" * 70)
        print("\nThe administrative interface demonstrated:")
        print("• ✓ User management (4 users with role-based access)")
        print("• ✓ Rule management (4 fraud detection rules)")
        print("• ✓ Configuration management (5 system settings)")
        print("• ✓ Audit log viewing (complete activity history)")
        print("• ✓ System health monitoring")
        print("\n💡 To view the interactive interface:")
        print("   1. Run: python web_interface/admin_server.py")
        print("   2. Open: http://127.0.0.1:5002")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
