"""
Integration tests for Smart Home System
Tests the complete flow: Sensor → Hub → API → Mongo → Web
"""
import pytest
import json
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, socketio, mqtt_client, sensor_service, alert_service
from tests.test_payloads import MockPayloads
from models.sensor_data import SensorData


class TestIntegrationFlow:
    """Test the complete integration flow"""
    
    @pytest.fixture
    def client(self):
        """Flask test client"""
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        with app.test_client() as client:
            yield client
    
    @pytest.fixture
    def socketio_client(self):
        """SocketIO test client"""
        return socketio.test_client(app)
    
    @pytest.fixture
    def mock_db(self):
        """Mock MongoDB database"""
        mock_db = Mock()
        mock_collection = Mock()
        mock_db.sensor_data = mock_collection
        mock_db.alerts = mock_collection
        return mock_db
    
    def test_sensor_to_mqtt_flow(self, mock_db):
        """Test 1: Sensor data → MQTT → Processing"""
        # Arrange
        sensor_payload = MockPayloads.mqtt_payload_normal()
        
        # Mock MQTT message
        mock_msg = Mock()
        mock_msg.payload = sensor_payload.encode()
        mock_msg.topic = "smarthome/sensors/living_room/data"
        
        received_data = []
        
        def capture_data(data):
            received_data.append(data)
        
        # Act - Simulate MQTT message reception
        with patch('app.sensor_service') as mock_service:
            mock_service.process_sensor_data = capture_data
            
            # Simulate MQTT callback
            from app import on_mqtt_message
            on_mqtt_message(None, None, mock_msg)
        
        # Assert
        assert len(received_data) == 1
        data = json.loads(received_data[0])
        assert data['sensor_id'] == "TEMP_001_LIVING"
        assert data['room'] == "Living Room"
        assert 'timestamp' in data
    
    def test_api_to_mongo_flow(self, client, mock_db):
        """Test 2: API → MongoDB storage"""
        # Arrange
        sensor_data = MockPayloads.sensor_data_normal()
        
        with patch('app.sensor_service') as mock_service:
            mock_service.save_sensor_data.return_value = {"_id": "mock_id"}
            
            # Act - POST sensor data via API
            response = client.post('/api/sensors/data', 
                                 data=json.dumps(sensor_data),
                                 content_type='application/json')
        
        # Assert
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['status'] == 'success'
        mock_service.save_sensor_data.assert_called_once()
    
    def test_threshold_alert_flow(self, mock_db, socketio_client):
        """Test 3: Threshold exceeded → Alert generation → WebSocket notification"""
        # Arrange
        high_co_data = MockPayloads.sensor_data_high_co()
        
        with patch('app.alert_service') as mock_alert_service:
            mock_alert = {
                "id": "alert_001",
                "type": "HIGH_CO_LEVEL",
                "severity": "CRITICAL",
                "message": "Dangerous CO level detected"
            }
            mock_alert_service.check_thresholds.return_value = mock_alert
            
            # Act - Process sensor data that exceeds threshold
            with app.test_request_context():
                from app import process_sensor_reading
                process_sensor_reading(high_co_data)
        
        # Assert alert was triggered
        mock_alert_service.check_thresholds.assert_called_once()
    
    def test_websocket_real_time_updates(self, socketio_client):
        """Test 4: Real-time WebSocket updates"""
        # Arrange
        socketio_client.connect()
        
        # Act - Simulate sensor data update
        sensor_update = MockPayloads.websocket_sensor_update()
        
        # Emit sensor data update
        socketio_client.emit('request_sensor_data')
        
        # Assert - Check if client receives updates
        received = socketio_client.get_received()
        assert len(received) > 0
    
    def test_end_to_end_normal_flow(self, client, socketio_client, mock_db):
        """Test 5: Complete end-to-end flow for normal operation"""
        # Arrange
        sensor_data = MockPayloads.sensor_data_normal()
        
        with patch('app.sensor_service') as mock_sensor_service, \
             patch('app.alert_service') as mock_alert_service:
            
            mock_sensor_service.save_sensor_data.return_value = {"_id": "test_id"}
            mock_alert_service.check_thresholds.return_value = None  # No alert
            
            # Act 1: Sensor sends data via MQTT (simulated via API)
            response = client.post('/api/sensors/data',
                                 data=json.dumps(sensor_data),
                                 content_type='application/json')
            
            # Act 2: Frontend requests current sensor data
            response2 = client.get('/api/sensors/current')
            
            # Assert
            assert response.status_code == 200
            assert response2.status_code == 200
            
            # Verify data was processed
            mock_sensor_service.save_sensor_data.assert_called()
            mock_alert_service.check_thresholds.assert_called()
    
    def test_end_to_end_alert_flow(self, client, socketio_client, mock_db):
        """Test 6: Complete end-to-end flow with alert generation"""
        # Arrange
        alert_data = MockPayloads.sensor_data_high_co()
        
        with patch('app.sensor_service') as mock_sensor_service, \
             patch('app.alert_service') as mock_alert_service:
            
            mock_sensor_service.save_sensor_data.return_value = {"_id": "test_id"}
            mock_alert_service.check_thresholds.return_value = {
                "id": "alert_001",
                "type": "HIGH_CO_LEVEL",
                "severity": "CRITICAL"
            }
            mock_alert_service.save_alert.return_value = {"_id": "alert_id"}
            
            # Connect WebSocket client
            socketio_client.connect()
            
            # Act: Send alert-triggering sensor data
            response = client.post('/api/sensors/data',
                                 data=json.dumps(alert_data),
                                 content_type='application/json')
            
            # Assert
            assert response.status_code == 200
            
            # Verify alert was processed
            mock_alert_service.check_thresholds.assert_called()
            mock_alert_service.save_alert.assert_called()
    
    def test_data_persistence_and_retrieval(self, client, mock_db):
        """Test 7: Data persistence and historical retrieval"""
        # Arrange - Mock historical data
        historical_data = MockPayloads.batch_sensor_data(5)
        
        with patch('app.sensor_service') as mock_service:
            mock_service.get_sensor_history.return_value = historical_data
            
            # Act - Request historical data
            response = client.get('/api/sensors/history?hours=24')
            
            # Assert
            assert response.status_code == 200
            response_data = json.loads(response.data)
            assert 'data' in response_data
            mock_service.get_sensor_history.assert_called_once()
    
    def test_mqtt_connection_and_subscription(self):
        """Test 8: MQTT connection and topic subscription"""
        with patch('paho.mqtt.client.Client') as mock_mqtt_class:
            mock_client = Mock()
            mock_mqtt_class.return_value = mock_client
            
            # Act - Initialize MQTT client
            from app import setup_mqtt_client
            client = setup_mqtt_client()
            
            # Assert
            mock_client.connect.assert_called()
            mock_client.subscribe.assert_called()
            mock_client.loop_start.assert_called()
    
    def test_error_handling_invalid_sensor_data(self, client):
        """Test 9: Error handling for invalid sensor data"""
        # Arrange - Invalid payload
        invalid_data = {"invalid": "data"}
        
        # Act
        response = client.post('/api/sensors/data',
                             data=json.dumps(invalid_data),
                             content_type='application/json')
        
        # Assert
        assert response.status_code == 400
    
    def test_concurrent_sensor_updates(self, client, mock_db):
        """Test 10: Concurrent sensor data processing"""
        # Arrange
        def send_sensor_data(sensor_id):
            data = MockPayloads.sensor_data_normal()
            data['sensor_id'] = sensor_id
            client.post('/api/sensors/data',
                       data=json.dumps(data),
                       content_type='application/json')
        
        with patch('app.sensor_service') as mock_service:
            mock_service.save_sensor_data.return_value = {"_id": "test"}
            
            # Act - Send concurrent requests
            threads = []
            for i in range(5):
                t = threading.Thread(target=send_sensor_data, args=[f"SENSOR_{i}"])
                threads.append(t)
                t.start()
            
            for t in threads:
                t.join()
            
            # Assert - All requests were processed
            assert mock_service.save_sensor_data.call_count == 5


class TestWebSocketIntegration:
    """Test WebSocket functionality"""
    
    @pytest.fixture
    def socketio_client(self):
        """SocketIO test client"""
        return socketio.test_client(app)
    
    def test_websocket_connection(self, socketio_client):
        """Test WebSocket connection establishment"""
        # Act
        connected = socketio_client.connect()
        
        # Assert
        assert connected
    
    def test_websocket_sensor_data_stream(self, socketio_client):
        """Test real-time sensor data streaming"""
        # Arrange
        socketio_client.connect()
        
        # Act - Start sensor data streaming
        socketio_client.emit('start_sensor_stream')
        
        # Wait for data
        time.sleep(1)
        
        # Assert
        received = socketio_client.get_received()
        assert len(received) > 0
    
    def test_websocket_alert_notifications(self, socketio_client):
        """Test real-time alert notifications"""
        # Arrange
        socketio_client.connect()
        alert_payload = MockPayloads.websocket_alert_notification()
        
        # Act - Emit alert notification
        with app.test_request_context():
            socketio.emit('alert_notification', alert_payload)
        
        # Assert - Client should receive alert
        received = socketio_client.get_received()
        # Check if alert was received by client
        assert any('alert_notification' in str(msg) for msg in received)


class TestPerformanceIntegration:
    """Test system performance under load"""
    
    def test_high_throughput_sensor_data(self, client):
        """Test handling high volume of sensor data"""
        # Arrange
        batch_data = MockPayloads.batch_sensor_data(100)
        
        with patch('app.sensor_service') as mock_service:
            mock_service.save_sensor_data.return_value = {"_id": "test"}
            
            start_time = time.time()
            
            # Act - Send batch data
            for data in batch_data:
                client.post('/api/sensors/data',
                           data=json.dumps(data),
                           content_type='application/json')
            
            end_time = time.time()
            
            # Assert - Performance check
            duration = end_time - start_time
            assert duration < 10  # Should process 100 records in under 10 seconds
            assert mock_service.save_sensor_data.call_count == 100


if __name__ == '__main__':
    pytest.main([__file__, '-v']) 