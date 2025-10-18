"""
Configuration management for stress testing framework.

This module provides utilities for loading, validating, and managing
stress test configurations.
"""

from typing import Dict, Any, Optional
import json
from pathlib import Path
from datetime import datetime

from .models import (
    StressTestConfig,
    TestScenario,
    LoadProfile,
    LoadProfileType,
    FailureScenario,
    FailureType
)


class ConfigurationManager:
    """Manages stress test configurations."""
    
    def __init__(self, config_dir: str = "stress_testing/configs"):
        """
        Initialize configuration manager.
        
        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def create_default_config(
        self,
        test_name: str,
        target_tps: int = 1000,
        duration_seconds: int = 300
    ) -> StressTestConfig:
        """
        Create a default stress test configuration.
        
        Args:
            test_name: Name of the test
            target_tps: Target transactions per second
            duration_seconds: Test duration in seconds
            
        Returns:
            StressTestConfig instance
        """
        test_id = f"test_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        return StressTestConfig(
            test_id=test_id,
            test_name=test_name,
            target_tps=target_tps,
            duration_seconds=duration_seconds,
            ramp_up_seconds=60,
            ramp_down_seconds=60,
            num_workers=10,
            enable_failure_injection=False,
            enable_presentation_mode=False,
            enable_real_time_metrics=True,
            test_environment="dev"
        )
    
    def load_config(self, config_path: str) -> StressTestConfig:
        """
        Load configuration from JSON file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            StressTestConfig instance
        """
        with open(config_path, 'r') as f:
            data = json.load(f)
        
        # Convert datetime strings
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        
        return StressTestConfig(**data)
    
    def save_config(self, config: StressTestConfig, filename: Optional[str] = None):
        """
        Save configuration to JSON file.
        
        Args:
            config: Configuration to save
            filename: Optional filename (defaults to test_id.json)
        """
        if filename is None:
            filename = f"{config.test_id}.json"
        
        filepath = self.config_dir / filename
        
        # Convert to dict and handle datetime
        config_dict = {
            'test_id': config.test_id,
            'test_name': config.test_name,
            'description': config.description,
            'target_tps': config.target_tps,
            'duration_seconds': config.duration_seconds,
            'ramp_up_seconds': config.ramp_up_seconds,
            'ramp_down_seconds': config.ramp_down_seconds,
            'num_workers': config.num_workers,
            'enable_failure_injection': config.enable_failure_injection,
            'enable_presentation_mode': config.enable_presentation_mode,
            'enable_real_time_metrics': config.enable_real_time_metrics,
            'test_environment': config.test_environment,
            'max_error_rate': config.max_error_rate,
            'max_p99_latency_ms': config.max_p99_latency_ms,
            'min_success_rate': config.min_success_rate,
            'max_cost_per_hour': config.max_cost_per_hour,
            'auto_stop_on_budget_exceed': config.auto_stop_on_budget_exceed,
            'created_at': config.created_at.isoformat(),
            'created_by': config.created_by,
            'tags': config.tags
        }
        
        with open(filepath, 'w') as f:
            json.dump(config_dict, f, indent=2)
    
    def validate_config(self, config: StressTestConfig) -> tuple[bool, list[str]]:
        """
        Validate configuration parameters.
        
        Args:
            config: Configuration to validate
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        # Validate TPS
        if config.target_tps <= 0:
            errors.append("target_tps must be positive")
        if config.target_tps > 50000:
            errors.append("target_tps exceeds maximum (50000)")
        
        # Validate duration
        if config.duration_seconds <= 0:
            errors.append("duration_seconds must be positive")
        if config.duration_seconds > 7200:  # 2 hours
            errors.append("duration_seconds exceeds maximum (7200)")
        
        # Validate ramp times
        if config.ramp_up_seconds < 0:
            errors.append("ramp_up_seconds cannot be negative")
        if config.ramp_down_seconds < 0:
            errors.append("ramp_down_seconds cannot be negative")
        
        # Validate workers
        if config.num_workers <= 0:
            errors.append("num_workers must be positive")
        if config.num_workers > 100:
            errors.append("num_workers exceeds maximum (100)")
        
        # Validate thresholds
        if not 0 <= config.max_error_rate <= 1:
            errors.append("max_error_rate must be between 0 and 1")
        if config.max_p99_latency_ms <= 0:
            errors.append("max_p99_latency_ms must be positive")
        if not 0 <= config.min_success_rate <= 1:
            errors.append("min_success_rate must be between 0 and 1")
        
        # Validate environment
        valid_envs = ['dev', 'staging', 'production']
        if config.test_environment not in valid_envs:
            errors.append(f"test_environment must be one of {valid_envs}")
        
        return len(errors) == 0, errors


class ScenarioBuilder:
    """Builder for creating test scenarios."""
    
    @staticmethod
    def create_peak_load_scenario() -> TestScenario:
        """Create peak load test scenario (10,000 TPS)."""
        load_profile = LoadProfile(
            profile_type=LoadProfileType.RAMP_UP,
            start_tps=0,
            peak_tps=10000,
            sustained_tps=10000
        )
        
        return TestScenario(
            scenario_id="peak_load_test",
            name="Peak Load Test",
            description="Validate system handles 10,000 TPS peak load",
            load_profile=load_profile,
            duration_seconds=1800,  # 30 minutes
            success_criteria={
                'zero_data_loss': True,
                'p95_latency_ms': 2000,
                'p99_latency_ms': 5000,
                'error_rate': 0.001,
                'all_agents_healthy': True
            },
            tags=['peak', 'high-volume', 'scalability']
        )
    
    @staticmethod
    def create_sustained_load_scenario() -> TestScenario:
        """Create sustained load test scenario (2,000 TPS for 2 hours)."""
        load_profile = LoadProfile(
            profile_type=LoadProfileType.SUSTAINED,
            start_tps=2000,
            peak_tps=2000,
            sustained_tps=2000
        )
        
        return TestScenario(
            scenario_id="sustained_load_test",
            name="Sustained Load Test",
            description="Validate system stability over 2 hours at 2,000 TPS",
            load_profile=load_profile,
            duration_seconds=7200,  # 2 hours
            success_criteria={
                'no_memory_leaks': True,
                'consistent_performance': True,
                'no_degradation': True
            },
            tags=['sustained', 'stability', 'endurance']
        )
    
    @staticmethod
    def create_burst_traffic_scenario() -> TestScenario:
        """Create burst traffic test scenario."""
        load_profile = LoadProfile(
            profile_type=LoadProfileType.BURST,
            start_tps=1000,
            sustained_tps=1000,
            burst_tps=10000,
            burst_duration_seconds=5,
            burst_interval_seconds=180
        )
        
        return TestScenario(
            scenario_id="burst_traffic_test",
            name="Burst Traffic Test",
            description="Validate burst handling with 10,000 TPS spikes",
            load_profile=load_profile,
            duration_seconds=900,  # 15 minutes
            success_criteria={
                'all_transactions_queued': True,
                'auto_scaling_triggered': True,
                'no_transaction_loss': True
            },
            tags=['burst', 'auto-scaling', 'queue']
        )
    
    @staticmethod
    def create_failure_recovery_scenario() -> TestScenario:
        """Create failure recovery test scenario."""
        load_profile = LoadProfile(
            profile_type=LoadProfileType.SUSTAINED,
            start_tps=3000,
            sustained_tps=3000
        )
        
        failure_scenarios = [
            FailureScenario(
                failure_type=FailureType.LAMBDA_CRASH,
                start_time_seconds=300,
                duration_seconds=60,
                severity=0.3
            ),
            FailureScenario(
                failure_type=FailureType.DYNAMODB_THROTTLE,
                start_time_seconds=600,
                duration_seconds=120,
                severity=0.5
            ),
            FailureScenario(
                failure_type=FailureType.NETWORK_LATENCY,
                start_time_seconds=900,
                duration_seconds=90,
                severity=0.4,
                parameters={'latency_ms': 500}
            ),
            FailureScenario(
                failure_type=FailureType.BEDROCK_RATE_LIMIT,
                start_time_seconds=1200,
                duration_seconds=60,
                severity=0.6
            )
        ]
        
        return TestScenario(
            scenario_id="failure_recovery_test",
            name="Failure Recovery Test",
            description="Validate resilience with continuous load and failure injection",
            load_profile=load_profile,
            duration_seconds=2700,  # 45 minutes
            failure_scenarios=failure_scenarios,
            success_criteria={
                'automatic_recovery': True,
                'no_cascading_failures': True,
                'graceful_degradation': True
            },
            tags=['resilience', 'failure-injection', 'recovery']
        )
    
    @staticmethod
    def create_investor_presentation_scenario() -> TestScenario:
        """Create investor presentation demo scenario."""
        load_profile = LoadProfile(
            profile_type=LoadProfileType.RAMP_UP,
            start_tps=0,
            peak_tps=8000,
            sustained_tps=5000
        )
        
        failure_scenarios = [
            FailureScenario(
                failure_type=FailureType.LAMBDA_CRASH,
                start_time_seconds=300,
                duration_seconds=30,
                severity=0.3
            )
        ]
        
        return TestScenario(
            scenario_id="investor_presentation",
            name="Investor Presentation Demo",
            description="10-minute impressive demo for investors",
            load_profile=load_profile,
            duration_seconds=600,  # 10 minutes
            failure_scenarios=failure_scenarios,
            success_criteria={
                'visually_stunning': True,
                'business_value_clear': True,
                'recovery_demonstrated': True
            },
            tags=['demo', 'presentation', 'investor']
        )
