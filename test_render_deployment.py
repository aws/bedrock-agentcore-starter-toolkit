"""
Test script to verify the analytics dashboard works in production-like environment.
Run this before deploying to Render to catch any issues.
"""

import os
import sys
import time
import requests
import subprocess
from pathlib import Path


def print_header(text):
    """Print formatted header"""
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70 + "\n")


def test_environment_variables():
    """Test that server respects environment variables"""
    print_header("🔧 Testing Environment Variables")
    
    # Set production-like environment variables
    os.environ['PORT'] = '8080'
    os.environ['HOST'] = '0.0.0.0'
    os.environ['DEBUG'] = 'False'
    
    print("✅ Environment variables set:")
    print(f"   PORT: {os.environ.get('PORT')}")
    print(f"   HOST: {os.environ.get('HOST')}")
    print(f"   DEBUG: {os.environ.get('DEBUG')}")
    
    return True


def start_test_server():
    """Start the analytics server in test mode"""
    print_header("🚀 Starting Test Server")
    
    server_path = Path(__file__).parent / 'web_interface' / 'analytics_server.py'
    
    try:
        process = subprocess.Popen(
            [sys.executable, str(server_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=os.environ.copy()
        )
        
        print("⏳ Waiting for server to start...")
        time.sleep(5)
        
        if process.poll() is None:
            print("✅ Server started successfully on port 8080")
            return process
        else:
            print("❌ Server failed to start")
            stdout, stderr = process.communicate()
            print(f"STDOUT: {stdout.decode()}")
            print(f"STDERR: {stderr.decode()}")
            return None
            
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        return None


def test_endpoints():
    """Test all API endpoints"""
    print_header("🧪 Testing API Endpoints")
    
    base_url = "http://localhost:8080"
    
    endpoints = [
        "/api/analytics/summary",
        "/api/analytics/patterns",
        "/api/analytics/decision-metrics",
        "/api/analytics/statistics",
        "/api/analytics/stress-test-metrics",
        "/api/analytics/heatmap",
        "/api/analytics/risk-distribution",
        "/api/analytics/top-indicators",
    ]
    
    passed = 0
    failed = 0
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            if response.status_code == 200:
                print(f"✅ {endpoint}")
                passed += 1
            else:
                print(f"❌ {endpoint} - Status: {response.status_code}")
                failed += 1
        except Exception as e:
            print(f"❌ {endpoint} - Error: {e}")
            failed += 1
    
    print(f"\n📊 Results: {passed} passed, {failed} failed")
    return failed == 0


def test_health_check():
    """Test the health check endpoint"""
    print_header("💚 Testing Health Check")
    
    try:
        response = requests.get("http://localhost:8080/api/analytics/summary", timeout=5)
        if response.status_code == 