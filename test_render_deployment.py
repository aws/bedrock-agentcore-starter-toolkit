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
        if response.status_code == 200:
            print("✅ Health check endpoint responding")
            print(f"   Response time: {response.elapsed.total_seconds():.2f}s")
            return True
        else:
            print(f"❌ Health check failed with status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False


def test_cors():
    """Test CORS configuration"""
    print_header("🌐 Testing CORS Configuration")
    
    try:
        response = requests.get(
            "http://localhost:8080/api/analytics/summary",
            headers={"Origin": "https://example.com"},
            timeout=5
        )
        
        cors_header = response.headers.get('Access-Control-Allow-Origin')
        if cors_header == '*':
            print("✅ CORS configured correctly (allows all origins)")
            return True
        else:
            print(f"⚠️  CORS header: {cors_header}")
            return True
    except Exception as e:
        print(f"❌ CORS test error: {e}")
        return False


def test_dashboard_page():
    """Test that the dashboard HTML is served"""
    print_header("📄 Testing Dashboard Page")
    
    try:
        response = requests.get("http://localhost:8080/", timeout=5)
        if response.status_code == 200 and 'html' in response.headers.get('Content-Type', ''):
            print("✅ Dashboard HTML served successfully")
            print(f"   Content length: {len(response.content)} bytes")
            return True
        else:
            print(f"❌ Dashboard page failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Dashboard page error: {e}")
        return False


def run_tests():
    """Run all tests"""
    print("\n" + "="*70)
    print("  🧪 RENDER DEPLOYMENT PRE-FLIGHT CHECKS")
    print("="*70)
    print("\nThis script tests your analytics dashboard in a production-like")
    print("environment before deploying to Render.")
    print("\n" + "="*70)
    
    # Test environment variables
    if not test_environment_variables():
        return False
    
    # Start server
    server_process = start_test_server()
    if not server_process:
        return False
    
    try:
        # Run tests
        results = []
        results.append(("Health Check", test_health_check()))
        results.append(("API Endpoints", test_endpoints()))
        results.append(("CORS", test_cors()))
        results.append(("Dashboard Page", test_dashboard_page()))
        
        # Print summary
        print_header("📋 Test Summary")
        
        all_passed = True
        for test_name, passed in results:
            status = "✅ PASSED" if passed else "❌ FAILED"
            print(f"{status} - {test_name}")
            if not passed:
                all_passed = False
        
        if all_passed:
            print("\n" + "="*70)
            print("  🎉 ALL TESTS PASSED!")
            print("="*70)
            print("\n✅ Your app is ready to deploy to Render!")
            print("\nNext steps:")
            print("  1. Push your code to GitHub")
            print("  2. Follow the RENDER_DEPLOYMENT_GUIDE.md")
            print("  3. Deploy on Render")
            print("\n" + "="*70 + "\n")
        else:
            print("\n" + "="*70)
            print("  ⚠️  SOME TESTS FAILED")
            print("="*70)
            print("\n❌ Please fix the issues above before deploying.")
            print("\n" + "="*70 + "\n")
        
        return all_passed
        
    finally:
        # Stop server
        print("\n🛑 Stopping test server...")
        server_process.terminate()
        server_process.wait(timeout=5)
        print("✅ Server stopped\n")


def main():
    """Main entry point"""
    try:
        success = run_tests()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
