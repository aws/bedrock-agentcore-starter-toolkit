#!/usr/bin/env python3
"""
Script to run baseline tests and record results before reorganization.
This establishes a baseline for comparison after the reorganization is complete.
"""

import subprocess
import json
import datetime
from pathlib import Path

def run_baseline_tests():
    """Run full test suite and record results."""
    print("Running baseline tests...")
    print("=" * 80)
    
    # Create output directory
    output_dir = Path("scripts/reorganization")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Run pytest with coverage
    result = subprocess.run(
        ["python", "-m", "pytest", "tests/", "tests_integ/", 
         "--tb=short", "-v", "--co", "-q"],
        capture_output=True,
        text=True
    )
    
    # Record results
    baseline = {
        "timestamp": datetime.datetime.now().isoformat(),
        "return_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "test_discovery_successful": result.returncode == 0 or result.returncode == 5
    }
    
    # Save baseline
    baseline_file = output_dir / "baseline_test_discovery.json"
    with open(baseline_file, "w") as f:
        json.dump(baseline, f, indent=2)
    
    print(f"\nBaseline test discovery saved to: {baseline_file}")
    print(f"Return code: {result.returncode}")
    print(f"Test discovery successful: {baseline['test_discovery_successful']}")
    
    return baseline

if __name__ == "__main__":
    baseline = run_baseline_tests()
    print("\n" + "=" * 80)
    print("Baseline test discovery complete!")
    print("=" * 80)
