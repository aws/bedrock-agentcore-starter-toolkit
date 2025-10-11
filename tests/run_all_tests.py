#!/usr/bin/env python3
"""
Test Runner for Fraud Detection System

Runs all test suites and generates comprehensive test report.
"""

import sys
import subprocess
import time
from datetime import datetime
from typing import Dict, List


class TestRunner:
    """Orchestrates test execution and reporting."""
    
    def __init__(self):
        self.results = {}
        self.start_time = None
        self.end_time = None
    
    def run_test_suite(self, test_file: str, markers: str = None) -> Dict:
        """Run a specific test suite."""
        print(f"\n{'='*80}")
        print(f"Running: {test_file}")
        print(f"{'='*80}\n")
        
        cmd = ["pytest", test_file, "-v", "--asyncio-mode=auto", "--tb=short"]
        
        if markers:
            cmd.extend(["-m", markers])
        
        start = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True)
        duration = time.time() - start
        
        return {
            "file": test_file,
            "duration": duration,
            "return_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "passed": result.returncode == 0
        }
    
    def run_all_tests(self, skip_slow: bool = False):
        """Run all test suites."""
        self.start_time = datetime.now()
        
        print("\n" + "="*80)
        print("FRAUD DETECTION SYSTEM - COMPREHENSIVE TEST SUITE")
        print("="*80)
        print(f"Start Time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
        
        # Test suites to run
        test_suites = [
            {
                "name": "Integration Tests",
                "file": "tests/test_integration.py",
                "markers": None
            },
            {
                "name": "Load & Performance Tests",
                "file": "tests/test_load_performance.py",
                "markers": "not slow" if skip_slow else None
            },
            {
                "name": "AI Agent Validation",
                "file": "tests/test_ai_agent_validation.py",
                "markers": None
            }
        ]
        
        # Run each test suite
        for suite in test_suites:
            result = self.run_test_suite(suite["file"], suite["markers"])
            self.results[suite["name"]] = result
        
        self.end_time = datetime.now()
        
        # Generate report
        self.print_summary()
    
    def print_summary(self):
        """Print test execution summary."""
        print("\n" + "="*80)
        print("TEST EXECUTION SUMMARY")
        print("="*80)
        
        total_duration = (self.end_time - self.start_time).total_seconds()
        
        print(f"\nStart Time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"End Time: {self.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total Duration: {total_duration:.2f} seconds")
        
        print("\n" + "-"*80)
        print("Test Suite Results:")
        print("-"*80)
        
        all_passed = True
        for name, result in self.results.items():
            status = "✓ PASSED" if result["passed"] else "✗ FAILED"
            print(f"\n{name}:")
            print(f"  Status: {status}")
            print(f"  Duration: {result['duration']:.2f}s")
            print(f"  Return Code: {result['return_code']}")
            
            if not result["passed"]:
                all_passed = False
                print(f"\n  Error Output:")
                print(f"  {result['stderr'][:500]}")  # First 500 chars
        
        print("\n" + "="*80)
        if all_passed:
            print("✓ ALL TESTS PASSED")
        else:
            print("✗ SOME TESTS FAILED")
        print("="*80 + "\n")
        
        return 0 if all_passed else 1
    
    def run_quick_tests(self):
        """Run quick smoke tests only."""
        print("\n" + "="*80)
        print("RUNNING QUICK SMOKE TESTS")
        print("="*80 + "\n")
        
        # Run subset of fast tests
        cmd = [
            "pytest",
            "tests/",
            "-v",
            "--asyncio-mode=auto",
            "-k", "test_legitimate_transaction or test_agent_coordination or test_response_time",
            "--tb=short"
        ]
        
        result = subprocess.run(cmd)
        return result.returncode


def main():
    """Main test runner entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run fraud detection system tests")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick smoke tests only"
    )
    parser.add_argument(
        "--skip-slow",
        action="store_true",
        help="Skip slow performance tests"
    )
    parser.add_argument(
        "--suite",
        choices=["integration", "performance", "ai-validation", "all"],
        default="all",
        help="Specific test suite to run"
    )
    
    args = parser.parse_args()
    
    runner = TestRunner()
    
    if args.quick:
        return runner.run_quick_tests()
    
    if args.suite == "integration":
        result = runner.run_test_suite("tests/test_integration.py")
        return 0 if result["passed"] else 1
    elif args.suite == "performance":
        markers = "not slow" if args.skip_slow else None
        result = runner.run_test_suite("tests/test_load_performance.py", markers)
        return 0 if result["passed"] else 1
    elif args.suite == "ai-validation":
        result = runner.run_test_suite("tests/test_ai_agent_validation.py")
        return 0 if result["passed"] else 1
    else:
        runner.run_all_tests(skip_slow=args.skip_slow)
        return 0 if all(r["passed"] for r in runner.results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
