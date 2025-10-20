"""
Example usage of the stress testing framework.

This module demonstrates how to use the core data models and configuration.
"""

from datetime import datetime
from src.models import (
    StressTestConfig,
    LoadProfile,
    LoadProfileType,
    TestScenario,
    FailureScenario,
    FailureType,
    SystemMetrics,
    AgentMetrics,
    BusinessMetrics,
    HeroMetrics,
    TestStatus
)
from src.config import ConfigurationManager, ScenarioBuilder


def example_create_basic_config():
    """Example: Create a basic stress test configuration."""
    config = StressTestConfig(
        test_id="test_001",
        test_name="Basic Load Test",
        description="Simple load test to validate system",
        target_tps=1000,
        duration_seconds=300,
        ramp_up_seconds=60,
        num_workers=5,
        test_environment="dev"
    )
    
    print(f"Created config: {config.test_name}")
    print(f"Target TPS: {config.target_tps}")
    print(f"Duration: {config.duration_seconds}s")
    return config


def example_create_load_profile():
    """Example: Create different load profiles."""
    
    # Ramp-up profile
    ramp_profile = LoadProfile(
        profile_type=LoadProfileType.RAMP_UP,
        start_tps=0,
        peak_tps=5000,
        sustained_tps=3000
    )
    
    # Burst profile
    burst_profile = LoadProfile(
        profile_type=LoadProfileType.BURST,
        sustained_tps=1000,
        burst_tps=10000,
        burst_duration_seconds=10,
        burst_interval_seconds=60
    )
    
    # Wave profile
    wave_profile = LoadProfile(
        profile_type=LoadProfileType.WAVE,
        sustained_tps=2000,
        wave_amplitude=1000,
        wave_period_seconds=120
    )
    
    print(f"Created {ramp_profile.profile_type.value} profile")
    print(f"Created {burst_profile.profile_type.value} profile")
    print(f"Created {wave_profile.profile_type.value} profile")
    
    return ramp_profile, burst_profile, wave_profile


def example_create_test_scenario():
    """Example: Create a complete test scenario."""
    load_profile = LoadProfile(
        profile_type=LoadProfileType.RAMP_UP,
        start_tps=0,
        peak_tps=5000
    )
    
    failure_scenario = FailureScenario(
        failure_type=FailureType.LAMBDA_CRASH,
        start_time_seconds=180,
        duration_seconds=60,
        severity=0.3
    )
    
    scenario = TestScenario(
        scenario_id="custom_scenario_001",
        name="Custom Load Test",
        description="Custom scenario with failure injection",
        load_profile=load_profile,
        duration_seconds=600,
        failure_scenarios=[failure_scenario],
        success_criteria={
            'max_error_rate': 0.01,
            'p99_latency_ms': 2000,
            'recovery_time_seconds': 120
        },
        tags=['custom', 'failure-injection']
    )
    
    print(f"Created scenario: {scenario.name}")
    print(f"Duration: {scenario.duration_seconds}s")
    print(f"Failures: {len(scenario.failure_scenarios)}")
    return scenario


def example_use_predefined_scenarios():
    """Example: Use predefined scenarios."""
    
    # Peak load scenario
    peak_scenario = ScenarioBuilder.create_peak_load_scenario()
    print(f"Peak Load: {peak_scenario.load_profile.peak_tps} TPS")
    
    # Sustained load scenario
    sustained_scenario = ScenarioBuilder.create_sustained_load_scenario()
    print(f"Sustained Load: {sustained_scenario.duration_seconds}s at {sustained_scenario.load_profile.sustained_tps} TPS")
    
    # Burst traffic scenario
    burst_scenario = ScenarioBuilder.create_burst_traffic_scenario()
    print(f"Burst Traffic: {burst_scenario.load_profile.burst_tps} TPS bursts")
    
    # Failure recovery scenario
    failure_scenario = ScenarioBuilder.create_failure_recovery_scenario()
    print(f"Failure Recovery: {len(failure_scenario.failure_scenarios)} failure injections")
    
    # Investor presentation scenario
    investor_scenario = ScenarioBuilder.create_investor_presentation_scenario()
    print(f"Investor Demo: {investor_scenario.duration_seconds}s presentation")
    
    return peak_scenario


def example_create_metrics():
    """Example: Create metrics objects."""
    
    # System metrics
    system_metrics = SystemMetrics(
        timestamp=datetime.utcnow(),
        throughput_tps=4523.5,
        requests_total=1000000,
        requests_successful=999500,
        requests_failed=500,
        avg_response_time_ms=245.3,
        p50_response_time_ms=180.0,
        p95_response_time_ms=450.0,
        p99_response_time_ms=850.0,
        max_response_time_ms=1200.0,
        error_rate=0.0005,
        timeout_rate=0.0001,
        cpu_utilization=0.75,
        memory_utilization=0.68,
        network_throughput_mbps=125.5
    )
    
    # Agent metrics
    agent_metrics = AgentMetrics(
        agent_id="agent_001",
        agent_name="Transaction Analyzer",
        timestamp=datetime.utcnow(),
        requests_processed=250000,
        avg_response_time_ms=120.5,
        p95_response_time_ms=280.0,
        p99_response_time_ms=450.0,
        success_rate=0.998,
        error_count=500,
        timeout_count=50,
        current_load=0.78,
        concurrent_requests=45,
        health_score=0.95,
        status="healthy",
        decision_accuracy=0.945,
        false_positive_rate=0.02,
        false_negative_rate=0.01
    )
    
    # Business metrics
    business_metrics = BusinessMetrics(
        timestamp=datetime.utcnow(),
        transactions_processed=1000000,
        transactions_per_second=4523.5,
        fraud_detected=15000,
        fraud_prevented_amount=4500000.0,
        fraud_detection_rate=0.015,
        fraud_detection_accuracy=0.945,
        cost_per_transaction=0.025,
        total_cost=25000.0,
        roi_percentage=180.0,
        money_saved=4475000.0,
        payback_period_months=4.5,
        customer_impact_score=0.92,
        false_positive_impact=0.02,
        performance_vs_baseline=250.0,
        cost_vs_baseline=-40.0
    )
    
    # Hero metrics for presentation
    hero_metrics = HeroMetrics(
        timestamp=datetime.utcnow(),
        total_transactions=1000000,
        fraud_blocked=15000,
        money_saved=4500000.0,
        uptime_percentage=99.97,
        transactions_per_second=4523,
        avg_response_time_ms=245.3,
        ai_accuracy=0.945,
        ai_confidence=0.89,
        cost_per_transaction=0.025,
        roi_percentage=180.0,
        customer_satisfaction=0.92
    )
    
    print(f"System TPS: {system_metrics.throughput_tps}")
    print(f"Agent Load: {agent_metrics.current_load * 100}%")
    print(f"Fraud Detected: {business_metrics.fraud_detected}")
    print(f"Money Saved: ${hero_metrics.money_saved:,.2f}")
    
    return system_metrics, agent_metrics, business_metrics, hero_metrics


def example_use_config_manager():
    """Example: Use configuration manager."""
    
    # Create config manager
    config_mgr = ConfigurationManager()
    
    # Create and validate config
    config = config_mgr.create_default_config(
        test_name="Example Test",
        target_tps=5000,
        duration_seconds=600
    )
    
    # Validate configuration
    is_valid, errors = config_mgr.validate_config(config)
    if is_valid:
        print("Configuration is valid")
        # Save configuration
        config_mgr.save_config(config)
        print(f"Saved config to: stress_testing/configs/{config.test_id}.json")
    else:
        print(f"Configuration errors: {errors}")
    
    return config


def main():
    """Run all examples."""
    print("=" * 60)
    print("Stress Testing Framework - Examples")
    print("=" * 60)
    
    print("\n1. Creating Basic Configuration")
    print("-" * 60)
    example_create_basic_config()
    
    print("\n2. Creating Load Profiles")
    print("-" * 60)
    example_create_load_profile()
    
    print("\n3. Creating Test Scenario")
    print("-" * 60)
    example_create_test_scenario()
    
    print("\n4. Using Predefined Scenarios")
    print("-" * 60)
    example_use_predefined_scenarios()
    
    print("\n5. Creating Metrics")
    print("-" * 60)
    example_create_metrics()
    
    print("\n6. Using Configuration Manager")
    print("-" * 60)
    example_use_config_manager()
    
    print("\n" + "=" * 60)
    print("Examples completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
