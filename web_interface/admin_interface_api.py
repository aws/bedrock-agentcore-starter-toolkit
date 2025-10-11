"""
Administrative Interface API

Provides system configuration, rule management, user access control,
and audit log viewing capabilities.
"""

import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from enum import Enum
from collections import defaultdict


class UserRole(Enum):
    """User roles for access control"""
    ADMIN = "admin"
    ANALYST = "analyst"
    AUDITOR = "auditor"
    OPERATOR = "operator"
    VIEWER = "viewer"


class Permission(Enum):
    """System permissions"""
    VIEW_DASHBOARD = "view_dashboard"
    VIEW_ANALYTICS = "view_analytics"
    VIEW_AUDIT_LOGS = "view_audit_logs"
    MANAGE_RULES = "manage_rules"
    MANAGE_USERS = "manage_users"
    MANAGE_CONFIG = "manage_config"
    APPROVE_DECISIONS = "approve_decisions"
    BLOCK_TRANSACTIONS = "block_transactions"


class RuleType(Enum):
    """Types of fraud detection rules"""
    AMOUNT_THRESHOLD = "amount_threshold"
    VELOCITY_CHECK = "velocity_check"
    LOCATION_BASED = "location_based"
    MERCHANT_RISK = "merchant_risk"
    PATTERN_MATCH = "pattern_match"
    CUSTOM = "custom"


@dataclass
class User:
    """User account data"""
    user_id: str
    username: str
    email: str
    role: str
    permissions: List[str]
    created_at: str
    last_login: Optional[str]
    active: bool
    mfa_enabled: bool


@dataclass
class FraudRule:
    """Fraud detection rule"""
    rule_id: str
    name: str
    rule_type: str
    description: str
    conditions: Dict[str, Any]
    actions: List[str]
    priority: int
    enabled: bool
    created_by: str
    created_at: str
    last_modified: str
    execution_count: int


@dataclass
class SystemConfig:
    """System configuration"""
    config_id: str
    category: str
    key: str
    value: Any
    description: str
    last_modified: str
    modified_by: str


@dataclass
class AuditLogEntry:
    """Audit log entry"""
    log_id: str
    timestamp: str
    user_id: str
    action: str
    resource: str
    details: Dict[str, Any]
    ip_address: str
    status: str


class AdminInterfaceAPI:
    """
    Administrative interface API for system configuration,
    rule management, user access control, and audit logging.
    """
    
    def __init__(self):
        """Initialize administrative interface API"""
        self.users: Dict[str, User] = {}
        self.rules: Dict[str, FraudRule] = {}
        self.configs: Dict[str, SystemConfig] = {}
        self.audit_logs: List[AuditLogEntry] = []
        
        self._initialize_users()
        self._initialize_rules()
        self._initialize_configs()
        self._initialize_audit_logs()
    
    def _initialize_users(self):
        """Initialize sample users"""
        users = [
            User(
                user_id="user_001",
                username="admin",
                email="admin@frauddetection.com",
                role=UserRole.ADMIN.value,
                permissions=[p.value for p in Permission],
                created_at=(datetime.now() - timedelta(days=365)).isoformat(),
                last_login=datetime.now().isoformat(),
                active=True,
                mfa_enabled=True
            ),
            User(
                user_id="user_002",
                username="analyst_jane",
                email="jane@frauddetection.com",
                role=UserRole.ANALYST.value,
                permissions=[
                    Permission.VIEW_DASHBOARD.value,
                    Permission.VIEW_ANALYTICS.value,
                    Permission.VIEW_AUDIT_LOGS.value,
                    Permission.APPROVE_DECISIONS.value
                ],
                created_at=(datetime.now() - timedelta(days=180)).isoformat(),
                last_login=(datetime.now() - timedelta(hours=2)).isoformat(),
                active=True,
                mfa_enabled=True
            ),
            User(
                user_id="user_003",
                username="auditor_bob",
                email="bob@frauddetection.com",
                role=UserRole.AUDITOR.value,
                permissions=[
                    Permission.VIEW_DASHBOARD.value,
                    Permission.VIEW_AUDIT_LOGS.value
                ],
                created_at=(datetime.now() - timedelta(days=90)).isoformat(),
                last_login=(datetime.now() - timedelta(days=1)).isoformat(),
                active=True,
                mfa_enabled=False
            ),
            User(
                user_id="user_004",
                username="operator_alice",
                email="alice@frauddetection.com",
                role=UserRole.OPERATOR.value,
                permissions=[
                    Permission.VIEW_DASHBOARD.value,
                    Permission.VIEW_ANALYTICS.value,
                    Permission.BLOCK_TRANSACTIONS.value
                ],
                created_at=(datetime.now() - timedelta(days=60)).isoformat(),
                last_login=(datetime.now() - timedelta(hours=5)).isoformat(),
                active=True,
                mfa_enabled=True
            )
        ]
        
        for user in users:
            self.users[user.user_id] = user
    
    def _initialize_rules(self):
        """Initialize sample fraud detection rules"""
        rules = [
            FraudRule(
                rule_id="rule_001",
                name="High Amount Transaction",
                rule_type=RuleType.AMOUNT_THRESHOLD.value,
                description="Flag transactions over $5000",
                conditions={"amount": {"operator": ">", "value": 5000}},
                actions=["flag", "notify_analyst"],
                priority=1,
                enabled=True,
                created_by="admin",
                created_at=(datetime.now() - timedelta(days=300)).isoformat(),
                last_modified=(datetime.now() - timedelta(days=30)).isoformat(),
                execution_count=1245
            ),
            FraudRule(
                rule_id="rule_002",
                name="Velocity Check",
                rule_type=RuleType.VELOCITY_CHECK.value,
                description="Block if more than 5 transactions in 1 hour",
                conditions={"transactions_per_hour": {"operator": ">", "value": 5}},
                actions=["block", "alert"],
                priority=2,
                enabled=True,
                created_by="admin",
                created_at=(datetime.now() - timedelta(days=250)).isoformat(),
                last_modified=(datetime.now() - timedelta(days=15)).isoformat(),
                execution_count=342
            ),
            FraudRule(
                rule_id="rule_003",
                name="Location Anomaly",
                rule_type=RuleType.LOCATION_BASED.value,
                description="Flag transactions from unusual locations",
                conditions={"location_distance": {"operator": ">", "value": 500}},
                actions=["flag", "request_verification"],
                priority=3,
                enabled=True,
                created_by="analyst_jane",
                created_at=(datetime.now() - timedelta(days=120)).isoformat(),
                last_modified=(datetime.now() - timedelta(days=5)).isoformat(),
                execution_count=876
            ),
            FraudRule(
                rule_id="rule_004",
                name="High Risk Merchant",
                rule_type=RuleType.MERCHANT_RISK.value,
                description="Block transactions from high-risk merchants",
                conditions={"merchant_risk_score": {"operator": ">", "value": 8}},
                actions=["block", "alert"],
                priority=1,
                enabled=False,
                created_by="admin",
                created_at=(datetime.now() - timedelta(days=60)).isoformat(),
                last_modified=(datetime.now() - timedelta(days=2)).isoformat(),
                execution_count=0
            )
        ]
        
        for rule in rules:
            self.rules[rule.rule_id] = rule
    
    def _initialize_configs(self):
        """Initialize system configurations"""
        configs = [
            SystemConfig(
                config_id="config_001",
                category="fraud_detection",
                key="max_transaction_amount",
                value=10000.00,
                description="Maximum allowed transaction amount",
                last_modified=datetime.now().isoformat(),
                modified_by="admin"
            ),
            SystemConfig(
                config_id="config_002",
                category="fraud_detection",
                key="velocity_threshold",
                value=5,
                description="Maximum transactions per hour",
                last_modified=datetime.now().isoformat(),
                modified_by="admin"
            ),
            SystemConfig(
                config_id="config_003",
                category="system",
                key="session_timeout_minutes",
                value=30,
                description="User session timeout in minutes",
                last_modified=datetime.now().isoformat(),
                modified_by="admin"
            ),
            SystemConfig(
                config_id="config_004",
                category="alerts",
                key="email_notifications_enabled",
                value=True,
                description="Enable email notifications for alerts",
                last_modified=datetime.now().isoformat(),
                modified_by="admin"
            ),
            SystemConfig(
                config_id="config_005",
                category="security",
                key="mfa_required",
                value=True,
                description="Require multi-factor authentication",
                last_modified=datetime.now().isoformat(),
                modified_by="admin"
            )
        ]
        
        for config in configs:
            self.configs[config.config_id] = config
    
    def _initialize_audit_logs(self):
        """Initialize sample audit logs"""
        actions = [
            ("user_001", "login", "authentication", "Successful login", "192.168.1.100", "success"),
            ("user_002", "view_dashboard", "dashboard", "Accessed main dashboard", "192.168.1.101", "success"),
            ("user_001", "update_rule", "rule_002", "Modified velocity check rule", "192.168.1.100", "success"),
            ("user_003", "view_audit_logs", "audit", "Viewed audit logs", "192.168.1.102", "success"),
            ("user_004", "block_transaction", "tx_12345", "Blocked suspicious transaction", "192.168.1.103", "success"),
            ("user_002", "approve_decision", "tx_67890", "Approved flagged transaction", "192.168.1.101", "success"),
            ("user_001", "create_user", "user_005", "Created new user account", "192.168.1.100", "success"),
            ("user_001", "update_config", "config_002", "Updated velocity threshold", "192.168.1.100", "success"),
        ]
        
        for i, (user_id, action, resource, details, ip, status) in enumerate(actions):
            log = AuditLogEntry(
                log_id=f"log_{i+1:03d}",
                timestamp=(datetime.now() - timedelta(hours=len(actions)-i)).isoformat(),
                user_id=user_id,
                action=action,
                resource=resource,
                details={"description": details},
                ip_address=ip,
                status=status
            )
            self.audit_logs.append(log)
    
    # User Management
    def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all users"""
        return [asdict(user) for user in self.users.values()]
    
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get specific user"""
        user = self.users.get(user_id)
        return asdict(user) if user else None
    
    def create_user(self, username: str, email: str, role: str, 
                   created_by: str) -> Dict[str, Any]:
        """Create new user"""
        user_id = f"user_{len(self.users)+1:03d}"
        
        # Get permissions for role
        role_permissions = self._get_role_permissions(role)
        
        user = User(
            user_id=user_id,
            username=username,
            email=email,
            role=role,
            permissions=role_permissions,
            created_at=datetime.now().isoformat(),
            last_login=None,
            active=True,
            mfa_enabled=False
        )
        
        self.users[user_id] = user
        
        # Log action
        self._log_action(created_by, "create_user", user_id, 
                        f"Created user {username}", "192.168.1.1")
        
        return asdict(user)
    
    def update_user(self, user_id: str, updates: Dict[str, Any], 
                   modified_by: str) -> Optional[Dict[str, Any]]:
        """Update user"""
        if user_id not in self.users:
            return None
        
        user = self.users[user_id]
        
        for key, value in updates.items():
            if hasattr(user, key):
                setattr(user, key, value)
        
        # Log action
        self._log_action(modified_by, "update_user", user_id,
                        f"Updated user {user.username}", "192.168.1.1")
        
        return asdict(user)
    
    def delete_user(self, user_id: str, deleted_by: str) -> bool:
        """Delete user (soft delete by deactivating)"""
        if user_id not in self.users:
            return False
        
        self.users[user_id].active = False
        
        # Log action
        self._log_action(deleted_by, "delete_user", user_id,
                        f"Deactivated user", "192.168.1.1")
        
        return True
    
    def _get_role_permissions(self, role: str) -> List[str]:
        """Get permissions for a role"""
        role_permissions = {
            UserRole.ADMIN.value: [p.value for p in Permission],
            UserRole.ANALYST.value: [
                Permission.VIEW_DASHBOARD.value,
                Permission.VIEW_ANALYTICS.value,
                Permission.VIEW_AUDIT_LOGS.value,
                Permission.APPROVE_DECISIONS.value
            ],
            UserRole.AUDITOR.value: [
                Permission.VIEW_DASHBOARD.value,
                Permission.VIEW_AUDIT_LOGS.value
            ],
            UserRole.OPERATOR.value: [
                Permission.VIEW_DASHBOARD.value,
                Permission.VIEW_ANALYTICS.value,
                Permission.BLOCK_TRANSACTIONS.value
            ],
            UserRole.VIEWER.value: [
                Permission.VIEW_DASHBOARD.value
            ]
        }
        
        return role_permissions.get(role, [])
    
    # Rule Management
    def get_all_rules(self) -> List[Dict[str, Any]]:
        """Get all fraud detection rules"""
        return [asdict(rule) for rule in self.rules.values()]
    
    def get_rule(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """Get specific rule"""
        rule = self.rules.get(rule_id)
        return asdict(rule) if rule else None
    
    def create_rule(self, name: str, rule_type: str, description: str,
                   conditions: Dict[str, Any], actions: List[str],
                   priority: int, created_by: str) -> Dict[str, Any]:
        """Create new fraud detection rule"""
        rule_id = f"rule_{len(self.rules)+1:03d}"
        
        rule = FraudRule(
            rule_id=rule_id,
            name=name,
            rule_type=rule_type,
            description=description,
            conditions=conditions,
            actions=actions,
            priority=priority,
            enabled=True,
            created_by=created_by,
            created_at=datetime.now().isoformat(),
            last_modified=datetime.now().isoformat(),
            execution_count=0
        )
        
        self.rules[rule_id] = rule
        
        # Log action
        self._log_action(created_by, "create_rule", rule_id,
                        f"Created rule {name}", "192.168.1.1")
        
        return asdict(rule)
    
    def update_rule(self, rule_id: str, updates: Dict[str, Any],
                   modified_by: str) -> Optional[Dict[str, Any]]:
        """Update fraud detection rule"""
        if rule_id not in self.rules:
            return None
        
        rule = self.rules[rule_id]
        
        for key, value in updates.items():
            if hasattr(rule, key):
                setattr(rule, key, value)
        
        rule.last_modified = datetime.now().isoformat()
        
        # Log action
        self._log_action(modified_by, "update_rule", rule_id,
                        f"Updated rule {rule.name}", "192.168.1.1")
        
        return asdict(rule)
    
    def delete_rule(self, rule_id: str, deleted_by: str) -> bool:
        """Delete fraud detection rule"""
        if rule_id not in self.rules:
            return False
        
        rule_name = self.rules[rule_id].name
        del self.rules[rule_id]
        
        # Log action
        self._log_action(deleted_by, "delete_rule", rule_id,
                        f"Deleted rule {rule_name}", "192.168.1.1")
        
        return True
    
    def toggle_rule(self, rule_id: str, modified_by: str) -> Optional[Dict[str, Any]]:
        """Toggle rule enabled/disabled"""
        if rule_id not in self.rules:
            return None
        
        rule = self.rules[rule_id]
        rule.enabled = not rule.enabled
        rule.last_modified = datetime.now().isoformat()
        
        # Log action
        status = "enabled" if rule.enabled else "disabled"
        self._log_action(modified_by, "toggle_rule", rule_id,
                        f"{status.capitalize()} rule {rule.name}", "192.168.1.1")
        
        return asdict(rule)
    
    # Configuration Management
    def get_all_configs(self) -> List[Dict[str, Any]]:
        """Get all system configurations"""
        return [asdict(config) for config in self.configs.values()]
    
    def get_configs_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get configurations by category"""
        return [asdict(config) for config in self.configs.values() 
                if config.category == category]
    
    def get_config(self, config_id: str) -> Optional[Dict[str, Any]]:
        """Get specific configuration"""
        config = self.configs.get(config_id)
        return asdict(config) if config else None
    
    def update_config(self, config_id: str, value: Any,
                     modified_by: str) -> Optional[Dict[str, Any]]:
        """Update configuration value"""
        if config_id not in self.configs:
            return None
        
        config = self.configs[config_id]
        old_value = config.value
        config.value = value
        config.last_modified = datetime.now().isoformat()
        config.modified_by = modified_by
        
        # Log action
        self._log_action(modified_by, "update_config", config_id,
                        f"Updated {config.key} from {old_value} to {value}",
                        "192.168.1.1")
        
        return asdict(config)
    
    # Audit Log Management
    def get_audit_logs(self, limit: int = 100, offset: int = 0,
                      user_id: Optional[str] = None,
                      action: Optional[str] = None,
                      start_date: Optional[str] = None,
                      end_date: Optional[str] = None) -> Dict[str, Any]:
        """Get audit logs with filtering and pagination"""
        filtered_logs = self.audit_logs.copy()
        
        # Apply filters
        if user_id:
            filtered_logs = [log for log in filtered_logs if log.user_id == user_id]
        
        if action:
            filtered_logs = [log for log in filtered_logs if log.action == action]
        
        if start_date:
            filtered_logs = [log for log in filtered_logs 
                           if log.timestamp >= start_date]
        
        if end_date:
            filtered_logs = [log for log in filtered_logs 
                           if log.timestamp <= end_date]
        
        # Sort by timestamp (most recent first)
        filtered_logs.sort(key=lambda x: x.timestamp, reverse=True)
        
        # Paginate
        total = len(filtered_logs)
        paginated_logs = filtered_logs[offset:offset+limit]
        
        return {
            "logs": [asdict(log) for log in paginated_logs],
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total
        }
    
    def search_audit_logs(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Search audit logs"""
        query_lower = query.lower()
        results = []
        
        for log in self.audit_logs:
            # Search in action, resource, and details
            if (query_lower in log.action.lower() or
                query_lower in log.resource.lower() or
                query_lower in str(log.details).lower()):
                results.append(asdict(log))
                
                if len(results) >= limit:
                    break
        
        return results
    
    def _log_action(self, user_id: str, action: str, resource: str,
                   description: str, ip_address: str):
        """Log an administrative action"""
        log = AuditLogEntry(
            log_id=f"log_{len(self.audit_logs)+1:03d}",
            timestamp=datetime.now().isoformat(),
            user_id=user_id,
            action=action,
            resource=resource,
            details={"description": description},
            ip_address=ip_address,
            status="success"
        )
        
        self.audit_logs.append(log)
    
    # Dashboard Summary
    def get_admin_summary(self) -> Dict[str, Any]:
        """Get administrative dashboard summary"""
        return {
            "users": {
                "total": len(self.users),
                "active": sum(1 for u in self.users.values() if u.active),
                "by_role": self._count_by_role()
            },
            "rules": {
                "total": len(self.rules),
                "enabled": sum(1 for r in self.rules.values() if r.enabled),
                "by_type": self._count_by_rule_type()
            },
            "audit_logs": {
                "total": len(self.audit_logs),
                "last_24h": self._count_logs_last_24h(),
                "recent_actions": [asdict(log) for log in self.audit_logs[-5:]]
            },
            "system_health": {
                "status": "healthy",
                "uptime_hours": 720,
                "last_backup": (datetime.now() - timedelta(hours=6)).isoformat()
            }
        }
    
    def _count_by_role(self) -> Dict[str, int]:
        """Count users by role"""
        counts = defaultdict(int)
        for user in self.users.values():
            counts[user.role] += 1
        return dict(counts)
    
    def _count_by_rule_type(self) -> Dict[str, int]:
        """Count rules by type"""
        counts = defaultdict(int)
        for rule in self.rules.values():
            counts[rule.rule_type] += 1
        return dict(counts)
    
    def _count_logs_last_24h(self) -> int:
        """Count audit logs in last 24 hours"""
        cutoff = (datetime.now() - timedelta(hours=24)).isoformat()
        return sum(1 for log in self.audit_logs if log.timestamp >= cutoff)
