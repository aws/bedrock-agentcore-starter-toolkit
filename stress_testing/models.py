"""
Core data models for stress testing framework.

This module defines all data structures used throughout the stress testing system.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple


# Enums

class TestStatus(Enum):
    """Status of a stress test execution."""
    NOT_STARTED = "not_started"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class LoadProfileType(Enum):
    """Type of load generation pattern."""
    RAMP_UP = "ramp_up"
    SUSTAINED = "sustained"
    BURST = "burst"
    WAVE = "wave"
    CHAOS = "chaos"


class FailureType(Enum):
    """Type of failure to inject for resilience testing."""
    LAMBDA_CRASH = "lambda_crash"
    DYNAMODB_THROTTLE = "dynamodb_throttle"
    NETWORK_LATENCY = "network_latency"
    BEDROCK_RATE_LIMIT = "bedrock_rate_limit"
    KINESIS_LAG = "kinesis_lag"
    AGENT_TIMEOUT = "agent_timeout"
    MEMORY_PRESSURE = "memory_pressure"
    CASCADING_FAILURE = "cascading_failure"


class DegradationLevel(Enum):
    """Level of system degradation."""
    NONE = "none"
    MODERATE = "moderate"
    SEVERE = "severe"
    CRITICAL = "critical"


# Configuration Models

@dataclass
class StressTestConfig:
    """Configuration for stress testing execution."""
    
    # Test identification
    test_id: str
    test_name: str
    description: str = ""
    
    # Load configuration
    target_tps: int = 1000
    duration_seconds: int = 300
    ramp_up_seconds: int = 60
    ramp_down_seconds: int = 60
    
    # Worker configuration
    num_workers: int = 10
    
    # Feature flags
    enable_failure_injection: bool = False
    enable_presentation_mode: bool = False
    enable_real_time_metrics: bool = True
    
    # Environment
    test_environment: str = "dev"  # dev, staging, production
    
    # Thresholds
    max_error_rate: float = 0.01  # 1%
    max_p99_latency_ms: float = 5000
    min_success_rate: float = 0.99
    
    # Cost controls
    max_cost_per_hour: float = 100.0
    auto_stop_on_budget_exceed: bool = True
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = "system"
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class LoadProfile:
    """Defines load generation pattern."""
    
    profile_type: LoadProfileType
    
    # TPS configuration
    start_tps: int = 0
    peak_tps: int = 1000
    sustained_tps: int = 500
    
    # Burst configuration
    burst_tps: int = 5000
    burst_duration_seconds: int = 10
    burst_interval_seconds: int = 60
    
    # Wave configuration
    wave_amplitude: int = 500
    wave_period_seconds: int = 120
    
    # Chaos configuration
    chaos_min_tps: int = 100
    chaos_max_tps: int = 2000
    chaos_change_interval_seconds: int = 30


@dataclass
class TestScenario:
    """Defines a complete stress test scenario."""
    
    scenario_id: str
    name: str
    description: str
    
    # Load configuration
    load_profile: LoadProfile
    duration_seconds: int
    
    # Success criteria
    success_criteria: Dict[str, Any] = field(default_factory=dict)
    
    # Failure scenarios
    failure_scenarios: List['FailureScenario'] = field(default_factory=list)
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    tags: List[str] = field(default_factory=list)


@dataclass
class FailureScenario:
    """Defines a failure injection scenario."""
    
    failure_type: FailureType
    start_time_seconds: int  # When to inject failure (relative to test start)
    duration_seconds: int
    severity: float = 0.5  # 0.0 to 1.0
    target_component: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)


# Metrics Models

@dataclass
class SystemMetrics:
    """System-level performance metrics."""
    
    timestamp: datetime
    
    # Throughput
    throughput_tps: float
    requests_total: int
    requests_successful: int
    requests_failed: int
    
    # Latency
    avg_response_time_ms: float
    p50_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    max_response_time_ms: float
    
    # Error rates
    error_rate: float
    timeout_rate: float
    
    # Resource utilization
    cpu_utilization: float
    memory_utilization: float
    network_throughput_mbps: float
    
    # Queue metrics
    queue_depth: int = 0
    queue_latency_ms: float = 0.0


@dataclass
class AgentMetrics:
    """Agent-specific performance metrics."""
    
    agent_id: str
    agent_name: str
    timestamp: datetime
    
    # Performance
    requests_processed: int
    avg_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    
    # Success rates
    success_rate: float
    error_count: int
    timeout_count: int
    
    # Load
    current_load: float  # 0.0 to 1.0
    concurrent_requests: int
    
    # Health
    health_score: float  # 0.0 to 1.0
    status: str = "healthy"  # healthy, degraded, unhealthy
    
    # Decision quality (for fraud detection agents)
    decision_accuracy: Optional[float] = None
    false_positive_rate: Optional[float] = None
    false_negative_rate: Optional[float] = None


@dataclass
class BusinessMetrics:
    """Business value metrics."""
    
    timestamp: datetime
    
    # Transaction metrics
    transactions_processed: int
    transactions_per_second: float
    
    # Fraud detection
    fraud_detected: int
    fraud_prevented_amount: float
    fraud_detection_rate: float
    fraud_detection_accuracy: float
    
    # Cost metrics
    cost_per_transaction: float
    total_cost: float
    
    # ROI metrics
    roi_percentage: float
    money_saved: float
    payback_period_months: float
    
    # Customer impact
    customer_impact_score: float
    false_positive_impact: float
    
    # Competitive metrics
    performance_vs_baseline: float  # Percentage improvement
    cost_vs_baseline: float  # Percentage improvement
    
    # Optional fields with defaults (must come last)
    aws_cost_breakdown: Dict[str, float] = field(default_factory=dict)


@dataclass
class HeroMetrics:
    """Large-format hero metrics for investor presentation."""
    
    timestamp: datetime
    
    # Big numbers
    total_transactions: int
    fraud_blocked: int
    money_saved: float
    
    # Performance
    uptime_percentage: float
    transactions_per_second: int
    avg_response_time_ms: float
    
    # AI metrics
    ai_accuracy: float
    ai_confidence: float
    
    # Business value
    cost_per_transaction: float
    roi_percentage: float
    customer_satisfaction: float


# Presentation Models

@dataclass
class TransactionFlowNode:
    """Node in transaction flow visualization."""
    
    node_id: str
    node_type: str  # ingestion, agent, decision, output
    node_name: str
    
    # Status
    status: str  # processing, completed, failed, idle
    
    # Metrics
    throughput: int
    latency_ms: float
    error_rate: float
    
    # Visualization
    position: Tuple[int, int]  # x, y coordinates
    color: str = "#4CAF50"
    size: int = 50


@dataclass
class CompetitiveBenchmarks:
    """Competitive comparison data."""
    
    timestamp: datetime
    
    # Our performance
    our_performance: Dict[str, float]
    
    # Competitor averages
    competitor_avg: Dict[str, float]
    
    # Improvements
    improvement_percentage: Dict[str, float]
    
    # Unique advantages
    unique_advantages: List[str] = field(default_factory=list)
    
    # Market position
    market_position: str = "leader"  # leader, challenger, follower


@dataclass
class CostEfficiencyMetrics:
    """Cost efficiency and optimization metrics."""
    
    timestamp: datetime
    
    # Current costs
    current_hourly_cost: float
    current_daily_cost: float
    current_monthly_cost: float
    
    # Cost breakdown
    lambda_cost: float
    dynamodb_cost: float
    kinesis_cost: float
    bedrock_cost: float
    other_costs: float
    
    # Efficiency
    cost_per_transaction: float
    cost_per_fraud_detected: float
    
    # Optimization
    potential_savings: float
    optimization_recommendations: List[str] = field(default_factory=list)


@dataclass
class ResilienceMetrics:
    """System resilience and recovery metrics."""
    
    timestamp: datetime
    
    # Availability
    uptime_percentage: float
    downtime_seconds: float
    
    # Failure handling
    failures_injected: int
    failures_recovered: int
    recovery_time_avg_seconds: float
    
    # Degradation
    degradation_events: int
    degradation_level: DegradationLevel
    
    # Circuit breakers
    circuit_breaker_trips: int
    circuit_breaker_recoveries: int


@dataclass
class PresentationData:
    """Complete data package for investor presentation dashboard."""
    
    timestamp: datetime
    
    # Core metrics
    hero_metrics: HeroMetrics
    system_metrics: SystemMetrics
    business_metrics: BusinessMetrics
    
    # Visualizations
    transaction_flow_data: List[TransactionFlowNode]
    
    # Comparisons
    competitive_benchmarks: CompetitiveBenchmarks
    cost_efficiency: CostEfficiencyMetrics
    
    # Resilience
    resilience_demonstration: ResilienceMetrics
    
    # Narrative
    business_narrative: str = ""
    key_highlights: List[str] = field(default_factory=list)
    
    # Customization
    investor_profile: str = "general"  # general, technical, financial, strategic


# Test Results Models

@dataclass
class TestResults:
    """Complete results from a stress test execution."""
    
    test_id: str
    test_name: str
    config: StressTestConfig
    scenario: TestScenario
    
    # Execution info
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    status: TestStatus = TestStatus.NOT_STARTED
    
    # Metrics summary
    final_system_metrics: Optional[SystemMetrics] = None
    final_business_metrics: Optional[BusinessMetrics] = None
    agent_metrics_summary: Dict[str, AgentMetrics] = field(default_factory=dict)
    
    # Time series data
    metrics_history: List[SystemMetrics] = field(default_factory=list)
    
    # Success criteria evaluation
    success_criteria_met: bool = False
    criteria_results: Dict[str, bool] = field(default_factory=dict)
    
    # Issues and recommendations
    issues_detected: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    # Artifacts
    report_path: Optional[str] = None
    logs_path: Optional[str] = None


@dataclass
class RealTimeMetrics:
    """Real-time metrics snapshot for dashboard updates."""
    
    timestamp: datetime
    test_id: str
    test_status: TestStatus
    
    # Current state
    current_tps: float
    target_tps: float
    elapsed_seconds: float
    remaining_seconds: float
    
    # Latest metrics
    system_metrics: SystemMetrics
    agent_metrics: Dict[str, AgentMetrics]
    business_metrics: BusinessMetrics
    
    # Presentation data (if enabled)
    presentation_data: Optional[PresentationData] = None
