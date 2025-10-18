"""
CLI for Stress Testing Framework.

Simple command-line interface for running stress tests.
"""

import asyncio
import argparse
import sys
from pathlib import Path

from .run_stress_test import StressTestRunner
from .config import ScenarioBuilder


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Stress Testing Framework for AI Fraud Detection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run investor presentation demo
  python -m stress_testing.cli --scenario investor
  
  # Run peak load test
  python -m stress_testing.cli --scenario peak-load
  
  # Start dashboard server only
  python -m stress_testing.cli --dashboard-only
        """
    )
    
    parser.add_argument(
        '--scenario',
        choices=['investor', 'peak-load', 'sustained', 'burst', 'failure-recovery'],
        help='Test scenario to run'
    )
    
    parser.add_argument(
        '--dashboard-only',
        action='store_true',
        help='Start dashboard server only (no stress test)'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=5000,
        help='Dashboard server port (default: 5000)'
    )
    
    args = parser.parse_args()
    
    if args.dashboard_only:
        # Start dashboard server
        from .dashboard_server import run_server
        print(f"🚀 Starting dashboard server on port {args.port}...")
        print(f"📊 Open http://localhost:{args.port}/investor in your browser")
        run_server(port=args.port, debug=False)
        return
    
    if not args.scenario:
        parser.print_help()
        return
    
    # Run stress test
    print(f"🚀 Running {args.scenario} scenario...")
    
    runner = StressTestRunner()
    
    if args.scenario == 'investor':
        asyncio.run(runner.run_investor_presentation_scenario())
    elif args.scenario == 'peak-load':
        asyncio.run(runner.run_peak_load_scenario())
    else:
        print(f"❌ Scenario '{args.scenario}' not yet implemented")
        sys.exit(1)
    
    print("\n✅ Test completed!")
    print(f"📁 Results saved in: stress_testing/results/")


if __name__ == "__main__":
    main()
