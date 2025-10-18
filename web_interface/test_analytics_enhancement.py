"""
Test script for analytics dashboard enhancements.

Tests the new stress test metrics API endpoints.
"""

import requests
import json
import time


def test_stress_test_metrics():
    """Test stress test metrics endpoint"""
    print("\n" + "="*70)
    print("Testing Stress Test Metrics Endpoint")
    print("="*70)
    
    try:
        response = requests.get('http://127.0.0.1:5001/api/analytics/stress-test-metrics')
        
        if response.status_code == 200:
            data = response.json()
            print("\n✅ Stress Test Metrics Retrieved Successfully")
            print(f"\nCurrent Load: {data['current_load_tps']} TPS")
            print(f"Peak Load: {data['peak_load_tps']} TPS")
            print(f"Fraud Detection Accuracy: {data['fraud_detection_accuracy']*100:.1f}%")
            print(f"Pattern Recognition Rate: {data['pattern_recognition_rate']*100:.1f}%")
            print(f"\nML Model Performance:")
            print(f"  - Inference Time: {data['ml_model_performance']['inference_time_ms']:.0f}ms")
            print(f"  - Accuracy: {data['ml_model_performance']['accuracy']*100:.1f}%")
            print(f"  - Precision: {data['ml_model_performance']['precision']*100:.1f}%")
            print(f"  - Recall: {data['ml_model_performance']['recall']*100:.1f}%")
            
            print(f"\nAccuracy vs Load Data Points: {len(data['accuracy_vs_load'])}")
            print(f"Pattern Detection Rates: {len(data['pattern_detection_rates']['data'])} entries")
            
            return True
        else:
            print(f"\n❌ Failed: Status code {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("\n❌ Connection Error: Make sure the analytics server is running")
        print("   Run: python web_interface/analytics_server.py")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


def test_existing_endpoints():
    """Test that existing endpoints still work"""
    print("\n" + "="*70)
    print("Testing Existing Endpoints")
    print("="*70)
    
    endpoints = [
        'analytics/summary',
        'analytics/patterns',
        'analytics/decision-metrics',
        'analytics/statistics'
    ]
    
    all_passed = True
    
    for endpoint in endpoints:
        try:
            response = requests.get(f'http://127.0.0.1:5001/api/{endpoint}')
            if response.status_code == 200:
                print(f"✅ {endpoint}")
            else:
                print(f"❌ {endpoint} - Status {response.status_code}")
                all_passed = False
        except Exception as e:
            print(f"❌ {endpoint} - Error: {e}")
            all_passed = False
    
    return all_passed


def test_websocket_endpoints():
    """Test WebSocket control endpoints"""
    print("\n" + "="*70)
    print("Testing WebSocket Control Endpoints")
    print("="*70)
    
    try:
        # Test start streaming
        response = requests.get('http://127.0.0.1:5001/api/analytics/streaming/start')
        if response.status_code == 200:
            print("✅ Start streaming endpoint")
        else:
            print(f"❌ Start streaming - Status {response.status_code}")
            return False
        
        time.sleep(1)
        
        # Test stop streaming
        response = requests.get('http://127.0.0.1:5001/api/analytics/streaming/stop')
        if response.status_code == 200:
            print("✅ Stop streaming endpoint")
        else:
            print(f"❌ Stop streaming - Status {response.status_code}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("🧪 ANALYTICS DASHBOARD ENHANCEMENT TESTS")
    print("="*70)
    
    results = []
    
    # Test new stress test metrics
    results.append(("Stress Test Metrics", test_stress_test_metrics()))
    
    # Test existing endpoints
    results.append(("Existing Endpoints", test_existing_endpoints()))
    
    # Test WebSocket endpoints
    results.append(("WebSocket Endpoints", test_websocket_endpoints()))
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status} - {test_name}")
    
    all_passed = all(result[1] for result in results)
    
    print("\n" + "="*70)
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
    else:
        print("⚠️  SOME TESTS FAILED")
    print("="*70 + "\n")
    
    return all_passed


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
