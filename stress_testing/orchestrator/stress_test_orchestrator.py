"""
Stress Test Orchestrator - Central coordinator for stress testing operations.

This module implements the core orchestrator that manages test execution,
scenario lifecycle, and coordinates all stress testing activities.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any, Callable
from enum import Enum

from ..models import (
    TestScenario,
    StressTestConfig,
    TestStatus,
    TestResults,
    SystemMetrics,
    BusinessMetrics,
    AgentMetrics
)
from ..config import ConfigurationManager


logger = logging.getLogger(__name__)


class TestExecutionState(Enum):
    """Internal state machine states for test execution."""
    IDLE = "idle"
    VALIDATING = "validating"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    COMPLETED = "completed"
    FAILED = "failed"


class StressTestOrchestrator:
    """
    Central orchestrator for stress testing operations.
    
    Manages test scenario execution, lifecycle, and coordination of all
    stress testing components including load generation, metrics collection,
    and dashboard updates.
    """
    
    def __init__(self, config: Optional[StressTestConfig] = None):
        """
        Initialize the stress test orchestrator.
        
        Args:
            config: Optional stress test configuration
        """
        self.config = config
        self.config_manager = ConfigurationManager()
        
        # Current test state
        self.current_scenario: Optional[TestScenario] = None
        self.current_test_id: Optional[str] = None
        self.execution_state = TestExecutionState.IDLE
        self.test_status = TestStatus.NOT_STARTED
        
        # Test execution tracking
        self.start_time: Optional[datetime] = None
        self.pause_time: Optional[datetime] = None
        self.paused_duration: float = 0.0
        
        # Results tracking
        self.test_results: Optional[TestResults] = None
        
        # Component references (to be injected)
        self.load_generator = None
        self.metrics_aggregator = None
        self.dashboard_controller = None
        self.failure_injector = None
        
        # Callbacks for lifecycle events
        self.lifecycle_callbacks: Dict[str, list[Callable]] = {
            'on_start': [],
            'on_pause': [],
            'on_resume': [],
            'on_stop': [],
            'on_complete': [],
            'on_error': []
        }
        
        logger.info("StressTestOrchestrator initialized")
    
    def set_components(
        self,
        load_generator=None,
        metrics_aggregator=None,
        dashboard_controller=None,
        failure_injector=None
    ):
        """
        Inject component dependencies.
        
        Args:
            load_generator: Load generation component
            metrics_aggregator: Metrics aggregation component
            dashboard_controller: Dashboard update component
            failure_injector: Failure injection component
        """
        if load_generator:
            self.load_generator = load_generator
        if metrics_aggregator:
            self.metrics_aggregator = metrics_aggregator
        if dashboard_controller:
            self.dashboard_controller = dashboard_controller
        if failure_injector:
            self.failure_injector = failure_injector
        
        logger.info("Components injected into orchestrator")
    
    def register_lifecycle_callback(self, event: str, callback: Callable):
        """
        Register a callback for lifecycle events.
        
        Args:
            event: Event name (on_start, on_pause, on_resume, on_stop, on_complete, on_error)
            callback: Callback function to execute
        """
        if event in self.lifecycle_callbacks:
            self.lifecycle_callbacks[event].append(callback)
            logger.debug(f"Registered callback for {event}")
        else:
            raise ValueError(f"Invalid event: {event}")
    
    async def _trigger_callbacks(self, event: str, **kwargs):
        """
        Trigger all callbacks for a lifecycle event.
        
        Args:
            event: Event name
            **kwargs: Additional arguments to pass to callbacks
        """
        for callback in self.lifecycle_callbacks.get(event, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(**kwargs)
                else:
                    callback(**kwargs)
            except Exception as e:
                logger.error(f"Error in {event} callback: {e}")
    
    def load_scenario(self, scenario: TestScenario) -> bool:
        """
        Load and validate a test scenario.
        
        Args:
            scenario: Test scenario to load
            
        Returns:
            True if scenario loaded successfully, False otherwise
        """
        try:
            logger.info(f"Loading scenario: {scenario.name} ({scenario.scenario_id})")
            
            # Validate scenario
            is_valid, errors = self._validate_scenario(scenario)
            if not is_valid:
                logger.error(f"Scenario validation failed: {errors}")
                return False
            
            # Store scenario
            self.current_scenario = scenario
            logger.info(f"Scenario loaded successfully: {scenario.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading scenario: {e}")
            return False
    
    def _validate_scenario(self, scenario: TestScenario) -> tuple[bool, list[str]]:
        """
        Validate a test scenario.
        
        Args:
            scenario: Scenario to validate
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        # Validate basic fields
        if not scenario.scenario_id:
            errors.append("scenario_id is required")
        if not scenario.name:
            errors.append("name is required")
        if scenario.duration_seconds <= 0:
            errors.append("duration_seconds must be positive")
        
        # Validate load profile
        if not scenario.load_profile:
            errors.append("load_profile is required")
        else:
            if scenario.load_profile.peak_tps <= 0:
                errors.append("peak_tps must be positive")
            if scenario.load_profile.peak_tps > 50000:
                errors.append("peak_tps exceeds maximum (50000)")
        
        # Validate failure scenarios timing
        for failure in scenario.failure_scenarios:
            if failure.start_time_seconds < 0:
                errors.append(f"Failure {failure.failure_type} has negative start_time")
            if failure.start_time_seconds >= scenario.duration_seconds:
                errors.append(f"Failure {failure.failure_type} starts after test ends")
            if failure.duration_seconds <= 0:
                errors.append(f"Failure {failure.failure_type} has invalid duration")
        
        return len(errors) == 0, errors
    
    async def start_test(self, scenario: Optional[TestScenario] = None) -> bool:
        """
        Start a stress test execution.
        
        Args:
            scenario: Optional scenario to execute (uses current_scenario if not provided)
            
        Returns:
            True if test started successfully, False otherwise
        """
        try:
            # Load scenario if provided
            if scenario:
                if not self.load_scenario(scenario):
                    return False
            
            # Validate we have a scenario
            if not self.current_scenario:
                logger.error("No scenario loaded")
                return False
            
            # Check state
            if self.execution_state not in [TestExecutionState.IDLE, TestExecutionState.COMPLETED, TestExecutionState.FAILED]:
                logger.error(f"Cannot start test in state: {self.execution_state}")
                return False
            
            # Transition to initializing
            self._transition_state(TestExecutionState.VALIDATING)
            self.test_status = TestStatus.INITIALIZING
            
            # Generate test ID
            self.current_test_id = f"test_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{self.current_scenario.scenario_id}"
            
            # Initialize test results
            self.test_results = TestResults(
                test_id=self.current_test_id,
                test_name=self.current_scenario.name,
                config=self.config or self._create_default_config(),
                scenario=self.current_scenario,
                start_time=datetime.utcnow(),
                status=TestStatus.INITIALIZING
            )
            
            logger.info(f"Starting test: {self.current_test_id}")
            
            # Trigger on_start callbacks
            await self._trigger_callbacks('on_start', test_id=self.current_test_id, scenario=self.current_scenario)
            
            # Transition to running
            self._transition_state(TestExecutionState.RUNNING)
            self.test_status = TestStatus.RUNNING
            self.start_time = datetime.utcnow()
            
            logger.info(f"Test started successfully: {self.current_test_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error starting test: {e}")
            self._transition_state(TestExecutionState.FAILED)
            self.test_status = TestStatus.FAILED
            await self._trigger_callbacks('on_error', error=str(e))
            return False
    
    async def pause_test(self) -> bool:
        """
        Pause the current test execution.
        
        Returns:
            True if test paused successfully, False otherwise
        """
        try:
            if self.execution_state != TestExecutionState.RUNNING:
                logger.error(f"Cannot pause test in state: {self.execution_state}")
                return False
            
            logger.info(f"Pausing test: {self.current_test_id}")
            
            # Transition to paused
            self._transition_state(TestExecutionState.PAUSED)
            self.test_status = TestStatus.PAUSED
            self.pause_time = datetime.utcnow()
            
            # Trigger on_pause callbacks
            await self._trigger_callbacks('on_pause', test_id=self.current_test_id)
            
            logger.info(f"Test paused: {self.current_test_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error pausing test: {e}")
            return False
    
    async def resume_test(self) -> bool:
        """
        Resume a paused test execution.
        
        Returns:
            True if test resumed successfully, False otherwise
        """
        try:
            if self.execution_state != TestExecutionState.PAUSED:
                logger.error(f"Cannot resume test in state: {self.execution_state}")
                return False
            
            logger.info(f"Resuming test: {self.current_test_id}")
            
            # Calculate paused duration
            if self.pause_time:
                self.paused_duration += (datetime.utcnow() - self.pause_time).total_seconds()
                self.pause_time = None
            
            # Transition to running
            self._transition_state(TestExecutionState.RUNNING)
            self.test_status = TestStatus.RUNNING
            
            # Trigger on_resume callbacks
            await self._trigger_callbacks('on_resume', test_id=self.current_test_id)
            
            logger.info(f"Test resumed: {self.current_test_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error resuming test: {e}")
            return False
    
    async def stop_test(self, reason: str = "User requested") -> bool:
        """
        Stop the current test execution.
        
        Args:
            reason: Reason for stopping the test
            
        Returns:
            True if test stopped successfully, False otherwise
        """
        try:
            if self.execution_state not in [TestExecutionState.RUNNING, TestExecutionState.PAUSED]:
                logger.error(f"Cannot stop test in state: {self.execution_state}")
                return False
            
            logger.info(f"Stopping test: {self.current_test_id} - Reason: {reason}")
            
            # Transition to stopping
            self._transition_state(TestExecutionState.STOPPING)
            self.test_status = TestStatus.STOPPING
            
            # Trigger on_stop callbacks
            await self._trigger_callbacks('on_stop', test_id=self.current_test_id, reason=reason)
            
            # Finalize test results
            if self.test_results:
                self.test_results.end_time = datetime.utcnow()
                self.test_results.duration_seconds = (
                    self.test_results.end_time - self.test_results.start_time
                ).total_seconds() - self.paused_duration
                self.test_results.status = TestStatus.CANCELLED
            
            # Transition to completed
            self._transition_state(TestExecutionState.COMPLETED)
            
            logger.info(f"Test stopped: {self.current_test_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping test: {e}")
            return False
    
    async def complete_test(self, success: bool = True) -> bool:
        """
        Mark the current test as completed.
        
        Args:
            success: Whether the test completed successfully
            
        Returns:
            True if test completed successfully, False otherwise
        """
        try:
            if self.execution_state != TestExecutionState.RUNNING:
                logger.error(f"Cannot complete test in state: {self.execution_state}")
                return False
            
            logger.info(f"Completing test: {self.current_test_id} - Success: {success}")
            
            # Finalize test results
            if self.test_results:
                self.test_results.end_time = datetime.utcnow()
                self.test_results.duration_seconds = (
                    self.test_results.end_time - self.test_results.start_time
                ).total_seconds() - self.paused_duration
                self.test_results.status = TestStatus.COMPLETED if success else TestStatus.FAILED
            
            # Transition to completed
            self._transition_state(TestExecutionState.COMPLETED if success else TestExecutionState.FAILED)
            self.test_status = TestStatus.COMPLETED if success else TestStatus.FAILED
            
            # Trigger on_complete callbacks
            await self._trigger_callbacks('on_complete', test_id=self.current_test_id, success=success, results=self.test_results)
            
            logger.info(f"Test completed: {self.current_test_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error completing test: {e}")
            return False
    
    def _transition_state(self, new_state: TestExecutionState):
        """
        Transition to a new execution state.
        
        Args:
            new_state: New state to transition to
        """
        old_state = self.execution_state
        self.execution_state = new_state
        logger.debug(f"State transition: {old_state.value} -> {new_state.value}")
    
    def _create_default_config(self) -> StressTestConfig:
        """
        Create a default configuration based on current scenario.
        
        Returns:
            Default StressTestConfig
        """
        if not self.current_scenario:
            raise ValueError("No scenario loaded")
        
        return StressTestConfig(
            test_id=self.current_test_id or "unknown",
            test_name=self.current_scenario.name,
            description=self.current_scenario.description,
            target_tps=self.current_scenario.load_profile.peak_tps,
            duration_seconds=self.current_scenario.duration_seconds,
            ramp_up_seconds=60,
            num_workers=10,
            enable_failure_injection=len(self.current_scenario.failure_scenarios) > 0,
            enable_presentation_mode=False,
            test_environment="dev"
        )
    
    def get_current_status(self) -> Dict[str, Any]:
        """
        Get current test execution status.
        
        Returns:
            Dictionary with current status information
        """
        elapsed_seconds = 0.0
        if self.start_time:
            elapsed_seconds = (datetime.utcnow() - self.start_time).total_seconds() - self.paused_duration
        
        return {
            'test_id': self.current_test_id,
            'execution_state': self.execution_state.value,
            'test_status': self.test_status.value,
            'scenario_name': self.current_scenario.name if self.current_scenario else None,
            'scenario_id': self.current_scenario.scenario_id if self.current_scenario else None,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'elapsed_seconds': elapsed_seconds,
            'paused_duration': self.paused_duration,
            'is_paused': self.execution_state == TestExecutionState.PAUSED
        }
    
    def get_test_results(self) -> Optional[TestResults]:
        """
        Get the current test results.
        
        Returns:
            TestResults object or None if no test is running
        """
        return self.test_results
