#!/usr/bin/env python3
"""
Test Runner for Smart Home Backend System
Runs all tests and demonstrates system functionality
"""
import os
import sys
import subprocess
import time
import requests
import json
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tests.test_payloads import MockPayloads


class SmartHomeTestRunner:
    """Comprehensive test runner for the Smart Home system"""
    
    def __init__(self):
        self.base_url = "http://localhost:5000"
        self.test_results = {}
        
    def run_all_tests(self):
        """Run all test suites"""
        print("🏠 Smart Home Backend Test Suite")
        print("=" * 50)
        
        # 1. Run unit tests
        self.run_unit_tests()
        
        # 2. Run integration tests
        self.run_integration_tests()
        
        # 3. Test mock payloads
        self.test_mock_payloads()
        
        # 4. Test Azure Functions (if available)
        self.test_azure_functions()
        
        # 5. Test notification system
        self.test_notification_system()
        
        # 6. Test WebSocket functionality
        self.test_websocket_functionality()
        
        # 7. Generate test report
        self.generate_test_report()
    
    def run_unit_tests(self):
        """Run pytest unit tests"""
        print("\n📋 Running Unit Tests...")
        try:
            result = subprocess.run([
                'python', '-m', 'pytest', 
                'tests/', '-v', '--tb=short'
            ], capture_output=True, text=True, cwd=os.path.dirname(__file__))
            
            self.test_results['unit_tests'] = {
                'status': 'PASSED' if result.returncode == 0 else 'FAILED',
                'output': result.stdout,
                'errors': result.stderr
            }
            
            if result.returncode == 0:
                print("✅ Unit tests passed")
            else:
                print("❌ Unit tests failed")
                print(result.stderr)
                
        except Exception as e:
            print(f"❌ Failed to run unit tests: {str(e)}")
            self.test_results['unit_tests'] = {
                'status': 'ERROR',
                'error': str(e)
            }
    
    def run_integration_tests(self):
        """Run integration tests"""
        print("\n🔗 Running Integration Tests...")
        try:
            result = subprocess.run([
                'python', '-m', 'pytest', 
                'tests/test_integration.py', '-v', '--tb=short'
            ], capture_output=True, text=True, cwd=os.path.dirname(__file__))
            
            self.test_results['integration_tests'] = {
                'status': 'PASSED' if result.returncode == 0 else 'FAILED',
                'output': result.stdout,
                'errors': result.stderr
            }
            
            if result.returncode == 0:
                print("✅ Integration tests passed")
            else:
                print("❌ Integration tests failed")
                print(result.stderr)
                
        except Exception as e:
            print(f"❌ Failed to run integration tests: {str(e)}")
            self.test_results['integration_tests'] = {
                'status': 'ERROR',
                'error': str(e)
            }
    
    def test_mock_payloads(self):
        """Test mock payload generation"""
        print("\n📦 Testing Mock Payloads...")
        try:
            # Test normal sensor data
            normal_data = MockPayloads.sensor_data_normal()
            assert 'sensor_id' in normal_data
            assert 'temperature' in normal_data
            print("✅ Normal sensor data payload")
            
            # Test alert scenarios
            high_temp = MockPayloads.sensor_data_high_temp()
            assert high_temp['temperature'] > 30
            print("✅ High temperature payload")
            
            high_co = MockPayloads.sensor_data_high_co()
            assert high_co['co_level'] > 5.0
            print("✅ High CO level payload")
            
            # Test MQTT payloads
            mqtt_payload = MockPayloads.mqtt_payload_normal()
            mqtt_data = json.loads(mqtt_payload)
            assert 'sensor_id' in mqtt_data
            print("✅ MQTT payload format")
            
            # Test batch data
            batch_data = MockPayloads.batch_sensor_data(5)
            assert len(batch_data) == 5
            print("✅ Batch sensor data")
            
            self.test_results['mock_payloads'] = {'status': 'PASSED'}
            print("✅ All mock payload tests passed")
            
        except Exception as e:
            print(f"❌ Mock payload tests failed: {str(e)}")
            self.test_results['mock_payloads'] = {
                'status': 'FAILED',
                'error': str(e)
            }
    
    def test_azure_functions(self):
        """Test Azure Function threshold monitoring"""
        print("\n☁️ Testing Azure Function Logic...")
        try:
            # Import Azure Function logic
            sys.path.append('azure_functions/threshold_monitor')
            
            # Test threshold monitoring logic
            from azure_functions.threshold_monitor import process_threshold_monitoring
            
            # Test with normal data
            normal_payload = {
                'sensor_data': MockPayloads.sensor_data_normal(),
                'threshold_config': {
                    'temperature': {'max': 30.0},
                    'co_level': {'max': 5.0}
                }
            }
            
            result = process_threshold_monitoring(normal_payload)
            assert result['status'] == 'success'
            assert len(result['alerts_triggered']) == 0
            print("✅ Normal data processing")
            
            # Test with alert data
            alert_payload = {
                'sensor_data': MockPayloads.sensor_data_high_co(),
                'threshold_config': {
                    'temperature': {'max': 30.0},
                    'co_level': {'max': 5.0}
                }
            }
            
            result = process_threshold_monitoring(alert_payload)
            assert result['status'] == 'success'
            assert len(result['alerts_triggered']) > 0
            print("✅ Alert data processing")
            
            self.test_results['azure_functions'] = {'status': 'PASSED'}
            print("✅ Azure Function tests passed")
            
        except Exception as e:
            print(f"❌ Azure Function tests failed: {str(e)}")
            self.test_results['azure_functions'] = {
                'status': 'FAILED',
                'error': str(e)
            }
    
    def test_notification_system(self):
        """Test notification service"""
        print("\n📧 Testing Notification System...")
        try:
            from services.notification_service import NotificationService
            
            # Create mock SocketIO
            class MockSocketIO:
                def emit(self, event, data, room=None):
                    print(f"Mock emit: {event} - {data.get('notification', {}).get('message', '')}")
            
            # Initialize notification service
            notification_service = NotificationService(socketio=MockSocketIO())
            
            # Test WebSocket notification
            notification_data = {
                'type': 'alert',
                'priority': 'high',
                'subject': 'Test Alert',
                'message': 'This is a test alert message',
                'channels': ['websocket'],
                'data': MockPayloads.sensor_data_high_co()
            }
            
            result = notification_service.send_notification(notification_data)
            assert result['success'] == True
            assert 'websocket' in result['channels']
            print("✅ WebSocket notification")
            
            # Test alert notification
            alert = MockPayloads.api_response_alerts()['alerts'][0]
            result = notification_service.send_alert_notification(alert, ['websocket'])
            assert result['success'] == True
            print("✅ Alert notification")
            
            self.test_results['notification_system'] = {'status': 'PASSED'}
            print("✅ Notification system tests passed")
            
        except Exception as e:
            print(f"❌ Notification system tests failed: {str(e)}")
            self.test_results['notification_system'] = {
                'status': 'FAILED',
                'error': str(e)
            }
    
    def test_websocket_functionality(self):
        """Test WebSocket handlers"""
        print("\n🔌 Testing WebSocket Functionality...")
        try:
            from websocket_handlers import WebSocketManager
            
            # Create mock services
            class MockSocketIO:
                def __init__(self):
                    self.events = {}
                
                def on(self, event):
                    def decorator(func):
                        self.events[event] = func
                        return func
                    return decorator
                
                def emit(self, event, data, room=None):
                    print(f"WebSocket emit: {event}")
            
            mock_socketio = MockSocketIO()
            mock_sensor_service = None
            mock_alert_service = None
            mock_notification_service = None
            
            # Initialize WebSocket manager
            ws_manager = WebSocketManager(
                mock_socketio, 
                mock_sensor_service, 
                mock_alert_service, 
                mock_notification_service
            )
            
            # Test connection stats
            stats = ws_manager.get_connection_stats()
            assert 'connected_clients' in stats
            assert 'streaming_active' in stats
            print("✅ Connection statistics")
            
            # Test mock sensor data generation
            sensor_data = ws_manager._get_mock_sensor_data()
            assert 'Living Room' in sensor_data
            assert 'Kitchen' in sensor_data
            print("✅ Mock sensor data generation")
            
            self.test_results['websocket_functionality'] = {'status': 'PASSED'}
            print("✅ WebSocket functionality tests passed")
            
        except Exception as e:
            print(f"❌ WebSocket functionality tests failed: {str(e)}")
            self.test_results['websocket_functionality'] = {
                'status': 'FAILED',
                'error': str(e)
            }
    
    def test_api_endpoints(self):
        """Test API endpoints if server is running"""
        print("\n🌐 Testing API Endpoints...")
        try:
            # Test health check
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                print("✅ Health check endpoint")
                
                # Test sensor data endpoint
                sensor_data = MockPayloads.sensor_data_normal()
                response = requests.post(
                    f"{self.base_url}/api/sensors/data",
                    json=sensor_data,
                    timeout=5
                )
                
                if response.status_code in [200, 201]:
                    print("✅ Sensor data POST endpoint")
                
                self.test_results['api_endpoints'] = {'status': 'PASSED'}
            else:
                print("⚠️ Server not running - skipping API tests")
                self.test_results['api_endpoints'] = {'status': 'SKIPPED'}
                
        except requests.exceptions.RequestException:
            print("⚠️ Server not running - skipping API tests")
            self.test_results['api_endpoints'] = {'status': 'SKIPPED'}
        except Exception as e:
            print(f"❌ API endpoint tests failed: {str(e)}")
            self.test_results['api_endpoints'] = {
                'status': 'FAILED',
                'error': str(e)
            }
    
    def generate_test_report(self):
        """Generate comprehensive test report"""
        print("\n📊 Test Report")
        print("=" * 50)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result['status'] == 'PASSED')
        failed_tests = sum(1 for result in self.test_results.values() if result['status'] == 'FAILED')
        skipped_tests = sum(1 for result in self.test_results.values() if result['status'] == 'SKIPPED')
        
        print(f"Total Test Suites: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"⚠️ Skipped: {skipped_tests}")
        print()
        
        for test_name, result in self.test_results.items():
            status_icon = {
                'PASSED': '✅',
                'FAILED': '❌',
                'SKIPPED': '⚠️',
                'ERROR': '🚫'
            }.get(result['status'], '❓')
            
            print(f"{status_icon} {test_name.replace('_', ' ').title()}: {result['status']}")
            
            if result['status'] in ['FAILED', 'ERROR'] and 'error' in result:
                print(f"   Error: {result['error']}")
        
        print("\n" + "=" * 50)
        
        if failed_tests == 0:
            print("🎉 All tests completed successfully!")
        else:
            print(f"⚠️ {failed_tests} test suite(s) failed. Check logs above.")
        
        # Save report to file
        self.save_test_report()
    
    def save_test_report(self):
        """Save test report to file"""
        try:
            report_data = {
                'timestamp': datetime.now().isoformat(),
                'summary': {
                    'total': len(self.test_results),
                    'passed': sum(1 for r in self.test_results.values() if r['status'] == 'PASSED'),
                    'failed': sum(1 for r in self.test_results.values() if r['status'] == 'FAILED'),
                    'skipped': sum(1 for r in self.test_results.values() if r['status'] == 'SKIPPED')
                },
                'results': self.test_results
            }
            
            with open('test_report.json', 'w') as f:
                json.dump(report_data, f, indent=2)
            
            print(f"\n📄 Test report saved to: test_report.json")
            
        except Exception as e:
            print(f"❌ Failed to save test report: {str(e)}")


def main():
    """Main test runner function"""
    print("Starting Smart Home Backend Test Suite...")
    
    # Change to backend directory
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(backend_dir)
    
    # Run tests
    runner = SmartHomeTestRunner()
    runner.run_all_tests()


if __name__ == "__main__":
    main() 