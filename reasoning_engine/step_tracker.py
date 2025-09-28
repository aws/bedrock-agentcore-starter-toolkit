#!/usr/bin/env python3
"""
Reasoning Step Tracker
Tracks and manages intermediate reasoning steps and results
"""

import json
import logging
import uuid
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import defaultdict
import threading

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class StepDependency:
    """Represents a dependency between reasoning steps"""
    dependent_step_id: str
    prerequisite_step_id: str
    dependency_type: str  # 'input', 'validation', 'enhancement'
    strength: float  # 0.0 to 1.0, how critical this dependency is

@dataclass
class StepMetrics:
    """Performance metrics for a reasoning step"""
    execution_time_ms: float
    memory_usage_mb: float
    api_calls_made: int
    tokens_processed: int
    cache_hits: int
    cache_misses: int

@dataclass
class StepValidation:
    """Validation results for a reasoning step"""
    is_valid: bool
    validation_score: float
    validation_issues: List[str]
    validation_timestamp: str
    validator_id: str

class ReasoningStepTracker:
    """
    Tracks reasoning steps, their dependencies, and intermediate results
    """
    
    def __init__(self):
        """Initialize the step tracker"""
        self.steps: Dict[str, Any] = {}  # step_id -> step data
        self.dependencies: Dict[str, List[StepDependency]] = defaultdict(list)
        self.step_metrics: Dict[str, StepMetrics] = {}
        self.step_validations: Dict[str, StepValidation] = {}
        self.execution_order: List[str] = []
        self.step_cache: Dict[str, Any] = {}  # Cache for expensive computations
        
        # Thread safety
        self._lock = threading.RLock()
        
        logger.info("ReasoningStepTracker initialized")
    
    def register_step(self, step_id: str, step_data: Dict[str, Any], 
                     dependencies: Optional[List[str]] = None) -> bool:
        """Register a new reasoning step"""
        with self._lock:
            try:
                # Validate step data
                if not self._validate_step_data(step_data):
                    logger.error(f"Invalid step data for step {step_id}")
                    return False
                
                # Store step
                self.steps[step_id] = {
                    **step_data,
                    'registration_time': datetime.now().isoformat(),
                    'status': 'registered'
                }
                
                # Register dependencies
                if dependencies:
                    for dep_id in dependencies:
                        if dep_id in self.steps:
                            dependency = StepDependency(
                                dependent_step_id=step_id,
                                prerequisite_step_id=dep_id,
                                dependency_type='input',
                                strength=1.0
                            )
                            self.dependencies[step_id].append(dependency)
                        else:
                            logger.warning(f"Dependency {dep_id} not found for step {step_id}")
                
                logger.debug(f"Registered reasoning step: {step_id}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to register step {step_id}: {str(e)}")
                return False
    
    def start_step_execution(self, step_id: str) -> bool:
        """Mark a step as starting execution"""
        with self._lock:
            if step_id not in self.steps:
                logger.error(f"Step {step_id} not registered")
                return False
            
            # Check dependencies are satisfied
            if not self._check_dependencies_satisfied(step_id):
                logger.error(f"Dependencies not satisfied for step {step_id}")
                return False
            
            # Update step status
            self.steps[step_id]['status'] = 'executing'
            self.steps[step_id]['execution_start'] = datetime.now().isoformat()
            
            # Add to execution order
            if step_id not in self.execution_order:
                self.execution_order.append(step_id)
            
            logger.debug(f"Started execution of step: {step_id}")
            return True
    
    def complete_step_execution(self, step_id: str, result: Dict[str, Any], 
                              metrics: Optional[StepMetrics] = None) -> bool:
        """Mark a step as completed with results"""
        with self._lock:
            if step_id not in self.steps:
                logger.error(f"Step {step_id} not registered")
                return False
            
            if self.steps[step_id]['status'] != 'executing':
                logger.warning(f"Step {step_id} was not in executing state")
            
            # Update step with results
            self.steps[step_id].update({
                'status': 'completed',
                'execution_end': datetime.now().isoformat(),
                'result': result
            })
            
            # Calculate execution time if not provided in metrics
            if 'execution_start' in self.steps[step_id]:
                start_time = datetime.fromisoformat(self.steps[step_id]['execution_start'])
                end_time = datetime.fromisoformat(self.steps[step_id]['execution_end'])
                execution_time = (end_time - start_time).total_seconds() * 1000
                
                if metrics is None:
                    metrics = StepMetrics(
                        execution_time_ms=execution_time,
                        memory_usage_mb=0.0,
                        api_calls_made=0,
                        tokens_processed=0,
                        cache_hits=0,
                        cache_misses=0
                    )
                else:
                    metrics.execution_time_ms = execution_time
            
            # Store metrics
            if metrics:
                self.step_metrics[step_id] = metrics
            
            # Cache result for potential reuse
            self._cache_step_result(step_id, result)
            
            logger.debug(f"Completed execution of step: {step_id}")
            return True
    
    def fail_step_execution(self, step_id: str, error: str) -> bool:
        """Mark a step as failed"""
        with self._lock:
            if step_id not in self.steps:
                logger.error(f"Step {step_id} not registered")
                return False
            
            self.steps[step_id].update({
                'status': 'failed',
                'execution_end': datetime.now().isoformat(),
                'error': error
            })
            
            logger.error(f"Step {step_id} failed: {error}")
            return True
    
    def get_step_result(self, step_id: str) -> Optional[Dict[str, Any]]:
        """Get the result of a completed step"""
        with self._lock:
            if step_id not in self.steps:
                return None
            
            step = self.steps[step_id]
            if step['status'] == 'completed':
                return step.get('result')
            
            return None
    
    def get_step_status(self, step_id: str) -> Optional[str]:
        """Get the current status of a step"""
        with self._lock:
            if step_id in self.steps:
                return self.steps[step_id]['status']
            return None
    
    def get_dependent_steps(self, step_id: str) -> List[str]:
        """Get steps that depend on the given step"""
        with self._lock:
            dependent_steps = []
            
            for dep_step_id, deps in self.dependencies.items():
                for dep in deps:
                    if dep.prerequisite_step_id == step_id:
                        dependent_steps.append(dep_step_id)
            
            return dependent_steps
    
    def get_prerequisite_steps(self, step_id: str) -> List[str]:
        """Get steps that the given step depends on"""
        with self._lock:
            if step_id in self.dependencies:
                return [dep.prerequisite_step_id for dep in self.dependencies[step_id]]
            return []
    
    def get_execution_path(self, step_id: str) -> List[str]:
        """Get the execution path leading to a step"""
        with self._lock:
            path = []
            visited = set()
            
            def build_path(current_step_id):
                if current_step_id in visited:
                    return  # Avoid cycles
                
                visited.add(current_step_id)
                prerequisites = self.get_prerequisite_steps(current_step_id)
                
                for prereq in prerequisites:
                    build_path(prereq)
                
                if current_step_id not in path:
                    path.append(current_step_id)
            
            build_path(step_id)
            return path
    
    def validate_step(self, step_id: str, validator_id: str = "default") -> StepValidation:
        """Validate a reasoning step"""
        with self._lock:
            if step_id not in self.steps:
                return StepValidation(
                    is_valid=False,
                    validation_score=0.0,
                    validation_issues=["Step not found"],
                    validation_timestamp=datetime.now().isoformat(),
                    validator_id=validator_id
                )
            
            step = self.steps[step_id]
            issues = []
            score = 1.0
            
            # Check if step has required fields
            required_fields = ['step_type', 'description', 'reasoning']
            for field in required_fields:
                if field not in step:
                    issues.append(f"Missing required field: {field}")
                    score -= 0.2
            
            # Check if step has results (if completed)
            if step['status'] == 'completed':
                if 'result' not in step or not step['result']:
                    issues.append("Completed step has no result")
                    score -= 0.3
                
                # Validate result structure
                result = step.get('result', {})
                if isinstance(result, dict):
                    if 'confidence' in result:
                        confidence = result['confidence']
                        if not isinstance(confidence, (int, float)) or not (0 <= confidence <= 1):
                            issues.append("Invalid confidence value")
                            score -= 0.2
                else:
                    issues.append("Result is not a dictionary")
                    score -= 0.1
            
            # Check dependencies
            if step_id in self.dependencies:
                for dep in self.dependencies[step_id]:
                    if dep.prerequisite_step_id not in self.steps:
                        issues.append(f"Missing prerequisite step: {dep.prerequisite_step_id}")
                        score -= 0.1
                    elif self.steps[dep.prerequisite_step_id]['status'] not in ['completed']:
                        issues.append(f"Prerequisite step not completed: {dep.prerequisite_step_id}")
                        score -= 0.1
            
            # Check reasoning quality
            if 'reasoning' in step:
                reasoning = step['reasoning']
                if isinstance(reasoning, str):
                    if len(reasoning) < 20:
                        issues.append("Reasoning too short")
                        score -= 0.1
                    elif len(reasoning) > 5000:
                        issues.append("Reasoning too long")
                        score -= 0.05
                else:
                    issues.append("Reasoning is not a string")
                    score -= 0.2
            
            validation = StepValidation(
                is_valid=len(issues) == 0,
                validation_score=max(0.0, score),
                validation_issues=issues,
                validation_timestamp=datetime.now().isoformat(),
                validator_id=validator_id
            )
            
            # Store validation result
            self.step_validations[step_id] = validation
            
            return validation
    
    def get_step_metrics(self, step_id: str) -> Optional[StepMetrics]:
        """Get performance metrics for a step"""
        with self._lock:
            return self.step_metrics.get(step_id)
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get summary of all step executions"""
        with self._lock:
            total_steps = len(self.steps)
            completed_steps = sum(1 for step in self.steps.values() if step['status'] == 'completed')
            failed_steps = sum(1 for step in self.steps.values() if step['status'] == 'failed')
            executing_steps = sum(1 for step in self.steps.values() if step['status'] == 'executing')
            
            # Calculate total execution time
            total_execution_time = 0.0
            for metrics in self.step_metrics.values():
                total_execution_time += metrics.execution_time_ms
            
            # Get average confidence
            confidences = []
            for step in self.steps.values():
                if step['status'] == 'completed' and 'result' in step:
                    result = step['result']
                    if isinstance(result, dict) and 'confidence' in result:
                        confidences.append(result['confidence'])
            
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            return {
                'total_steps': total_steps,
                'completed_steps': completed_steps,
                'failed_steps': failed_steps,
                'executing_steps': executing_steps,
                'success_rate': completed_steps / total_steps if total_steps > 0 else 0.0,
                'total_execution_time_ms': total_execution_time,
                'average_confidence': avg_confidence,
                'execution_order': self.execution_order.copy(),
                'cache_hit_rate': self._calculate_cache_hit_rate()
            }
    
    def export_execution_trace(self) -> Dict[str, Any]:
        """Export complete execution trace for analysis"""
        with self._lock:
            return {
                'steps': {step_id: step.copy() for step_id, step in self.steps.items()},
                'dependencies': {
                    step_id: [asdict(dep) for dep in deps] 
                    for step_id, deps in self.dependencies.items()
                },
                'metrics': {step_id: asdict(metrics) for step_id, metrics in self.step_metrics.items()},
                'validations': {step_id: asdict(validation) for step_id, validation in self.step_validations.items()},
                'execution_order': self.execution_order.copy(),
                'export_timestamp': datetime.now().isoformat()
            }
    
    def clear_completed_steps(self, older_than_hours: int = 24):
        """Clear completed steps older than specified hours"""
        with self._lock:
            cutoff_time = datetime.now() - timedelta(hours=older_than_hours)
            steps_to_remove = []
            
            for step_id, step in self.steps.items():
                if step['status'] == 'completed' and 'execution_end' in step:
                    end_time = datetime.fromisoformat(step['execution_end'])
                    if end_time < cutoff_time:
                        steps_to_remove.append(step_id)
            
            # Remove old steps and related data
            for step_id in steps_to_remove:
                del self.steps[step_id]
                if step_id in self.step_metrics:
                    del self.step_metrics[step_id]
                if step_id in self.step_validations:
                    del self.step_validations[step_id]
                if step_id in self.dependencies:
                    del self.dependencies[step_id]
                if step_id in self.execution_order:
                    self.execution_order.remove(step_id)
                if step_id in self.step_cache:
                    del self.step_cache[step_id]
            
            logger.info(f"Cleared {len(steps_to_remove)} completed steps older than {older_than_hours} hours")
    
    def _validate_step_data(self, step_data: Dict[str, Any]) -> bool:
        """Validate step data structure"""
        required_fields = ['step_type', 'description']
        return all(field in step_data for field in required_fields)
    
    def _check_dependencies_satisfied(self, step_id: str) -> bool:
        """Check if all dependencies for a step are satisfied"""
        if step_id not in self.dependencies:
            return True  # No dependencies
        
        for dep in self.dependencies[step_id]:
            prereq_id = dep.prerequisite_step_id
            if prereq_id not in self.steps:
                return False
            
            prereq_status = self.steps[prereq_id]['status']
            if prereq_status != 'completed':
                return False
        
        return True
    
    def _cache_step_result(self, step_id: str, result: Dict[str, Any]):
        """Cache step result for potential reuse"""
        # Create cache key based on step input
        step = self.steps[step_id]
        cache_key = self._generate_cache_key(step)
        
        self.step_cache[cache_key] = {
            'result': result,
            'step_id': step_id,
            'cached_at': datetime.now().isoformat()
        }
        
        # Limit cache size
        if len(self.step_cache) > 1000:
            # Remove oldest entries
            sorted_cache = sorted(
                self.step_cache.items(),
                key=lambda x: x[1]['cached_at']
            )
            for key, _ in sorted_cache[:100]:  # Remove oldest 100
                del self.step_cache[key]
    
    def _generate_cache_key(self, step: Dict[str, Any]) -> str:
        """Generate cache key for a step"""
        # Use step type, input data, and dependencies to create key
        key_data = {
            'step_type': step.get('step_type', ''),
            'input_data': step.get('input_data', {}),
            'dependencies': sorted(self.get_prerequisite_steps(step.get('step_id', '')))
        }
        
        return str(hash(json.dumps(key_data, sort_keys=True)))
    
    def _calculate_cache_hit_rate(self) -> float:
        """Calculate cache hit rate from metrics"""
        total_hits = sum(metrics.cache_hits for metrics in self.step_metrics.values())
        total_misses = sum(metrics.cache_misses for metrics in self.step_metrics.values())
        total_requests = total_hits + total_misses
        
        return total_hits / total_requests if total_requests > 0 else 0.0
    
    def get_step_dependency_graph(self) -> Dict[str, Any]:
        """Get dependency graph for visualization"""
        with self._lock:
            nodes = []
            edges = []
            
            # Create nodes
            for step_id, step in self.steps.items():
                nodes.append({
                    'id': step_id,
                    'label': step.get('description', step_id),
                    'type': step.get('step_type', 'unknown'),
                    'status': step['status']
                })
            
            # Create edges
            for step_id, deps in self.dependencies.items():
                for dep in deps:
                    edges.append({
                        'from': dep.prerequisite_step_id,
                        'to': dep.dependent_step_id,
                        'type': dep.dependency_type,
                        'strength': dep.strength
                    })
            
            return {
                'nodes': nodes,
                'edges': edges,
                'execution_order': self.execution_order.copy()
            }