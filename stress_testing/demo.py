"""
Quick Demo Script - Runs investor presentation with dashboard.

This script starts both the stress test and the dashboard server.
"""

import asyncio
import subprocess
import sys
import time
import webbrowser
from pathlib import Path


def start_dashboard_server():
    """Start the dashboard server in a separate process."""
    print("🚀 Starting dashboard server...")
    dashboard_script = Path(__file__).parent / "dashboard_server.py"
    process = subprocess.Popen(
        [sys.executable, str(dashboard_script)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for server to start
    time.sleep(2)
    
    # Open browser
    print("🌐 Opening investor dashboard in browser...")
    webbrowser.open("http://localhost:5000/investor")
    
    return process


async def run_demo():
    """Run the complete demo."""
    print("=" * 80)
    print("🎬 AI FRAUD DETECTION - INVESTOR PRESENTATION DEMO")
    print("=" * 80)
    print()
    
    # Start dashboard server
    dashboard_process = start_dashboard_server()
    
    try:
        # Wait a moment for dashboard to be ready
        await asyncio.sleep(3)
        
        # Run stress test
        print("⚡ Starting stress test...")
        print("📊 Watch the metrics update in real-time on the dashboard!")
        print()
        
        from .run_stress_test import StressTestRunner
        runner = StressTestRunner()
        await runner.run_investor_presentation_scenario()
        
        print()
        print("=" * 80)
        print("✅ DEMO COMPLETED SUCCESSFULLY!")
        print("=" * 80)
        print()
        print("📊 Dashboard: http://localhost:5000/investor")
        print("📁 Results: stress_testing/results/")
        print()
        print("Press Ctrl+C to stop the dashboard server...")
        
        # Keep dashboard running
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping demo...")
    finally:
        # Clean up
        dashboard_process.terminate()
        dashboard_process.wait()
        print("✅ Demo stopped")


if __name__ == "__main__":
    try:
        asyncio.run(run_demo())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
