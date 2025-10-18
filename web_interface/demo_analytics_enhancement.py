"""
Demo script for analytics dashboard enhancements.

This script demonstrates the new stress test metrics and real-time updates.
"""

import time
import webbrowser
import subprocess
import sys
from pathlib import Path


def print_banner():
    """Print demo banner"""
    print("\n" + "="*70)
    print("🎯 ANALYTICS DASHBOARD ENHANCEMENT DEMO")
    print("="*70)
    print("\nThis demo showcases the enhanced analytics dashboard with:")
    print("  ✅ Stress test metrics section")
    print("  ✅ Real-time chart components")
    print("  ✅ WebSocket live updates")
    print("\n" + "="*70 + "\n")


def print_instructions():
    """Print usage instructions"""
    print("\n" + "="*70)
    print("📋 DEMO INSTRUCTIONS")
    print("="*70)
    print("\n1. The analytics server will start automatically")
    print("2. Your browser will open to the dashboard")
    print("3. Click '📡 Start Live Stream' to enable real-time updates")
    print("4. Watch the charts update every 2 seconds")
    print("\n🎨 Features to Explore:")
    print("  • Stress Test Metrics - Current load, accuracy, pattern recognition")
    print("  • Accuracy vs Load Chart - Performance across different TPS levels")
    print("  • Pattern Detection Heatmap - Detection rates by pattern and load")
    print("  • Performance Trend - Real-time accuracy tracking")
    print("  • Gauge Charts - Visual indicators for key metrics")
    print("\n💡 Tips:")
    print("  • Hover over charts for detailed tooltips")
    print("  • Watch the connection status (🟢 Live / 🔴 Offline)")
    print("  • Try the manual refresh button")
    print("  • Enable/disable auto-refresh")
    print("\n" + "="*70 + "\n")


def start_server():
    """Start the analytics server"""
    print("🚀 Starting analytics server...")
    
    server_path = Path(__file__).parent / 'analytics_server.py'
    
    try:
        # Start server in background
        process = subprocess.Popen(
            [sys.executable, str(server_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for server to start
        print("⏳ Waiting for server to initialize...")
        time.sleep(3)
        
        # Check if server is running
        if process.poll() is None:
            print("✅ Server started successfully!")
            return process
        else:
            print("❌ Server failed to start")
            stdout, stderr = process.communicate()
            print(f"Error: {stderr.decode()}")
            return None
            
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        return None


def open_dashboard():
    """Open dashboard in browser"""
    print("\n🌐 Opening dashboard in browser...")
    
    try:
        webbrowser.open('http://127.0.0.1:5001')
        print("✅ Dashboard opened!")
        return True
    except Exception as e:
        print(f"❌ Error opening browser: {e}")
        print("   Please manually open: http://127.0.0.1:5001")
        return False


def run_demo():
    """Run the demo"""
    print_banner()
    print_instructions()
    
    # Start server
    server_process = start_server()
    
    if not server_process:
        print("\n❌ Demo failed to start. Please check the error messages above.")
        return False
    
    # Open dashboard
    open_dashboard()
    
    print("\n" + "="*70)
    print("✨ DEMO RUNNING")
    print("="*70)
    print("\nThe dashboard is now running with all enhancements!")
    print("\n📊 Dashboard URL: http://127.0.0.1:5001")
    print("\n⚠️  Press Ctrl+C to stop the demo and server")
    print("="*70 + "\n")
    
    try:
        # Keep running until interrupted
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n" + "="*70)
        print("🛑 STOPPING DEMO")
        print("="*70)
        print("\nShutting down server...")
        
        # Terminate server
        server_process.terminate()
        server_process.wait(timeout=5)
        
        print("✅ Server stopped")
        print("\n" + "="*70)
        print("👋 Thank you for trying the analytics dashboard enhancements!")
        print("="*70 + "\n")
        
        return True


def main():
    """Main entry point"""
    try:
        success = run_demo()
        return 0 if success else 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1


if __name__ == '__main__':
    exit(main())
