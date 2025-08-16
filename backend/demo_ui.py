#!/usr/bin/env python3
"""
Smart Home Backend Demo UI
Interactive web-based demonstration of all backend capabilities
"""
from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_socketio import SocketIO, emit
import json
import time
import threading
import random
from datetime import datetime, timedelta
from typing import Dict, Any
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import our modules
from tests.test_payloads import MockPayloads
from websocket_handlers import WebSocketManager

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'demo-secret-key-12345'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Global demo state
demo_state = {
    'sensors': {},
    'alerts': [],
    'notifications': [],
    'azure_function_logs': [],
    'mqtt_messages': [],
    'api_requests': [],
    'websocket_events': [],
    'system_status': 'running',
    'simulation_active': False
}

# Initialize WebSocket manager
ws_manager = None

class DemoBackend:
    """Demo backend that simulates all smart home capabilities"""
    
    def __init__(self):
        self.running = False
        self.simulation_thread = None
        
    def start_simulation(self):
        """Start the demo simulation"""
        if not self.running:
            self.running = True
            self.simulation_thread = threading.Thread(target=self._simulation_loop, daemon=True)
            self.simulation_thread.start()
            demo_state['simulation_active'] = True
            
    def stop_simulation(self):
        """Stop the demo simulation"""
        self.running = False
        demo_state['simulation_active'] = False
        
    def _simulation_loop(self):
        """Main simulation loop"""
        while self.running:
            try:
                # Generate random sensor data
                self._simulate_sensor_data()
                
                # Occasionally generate alerts
                if random.random() < 0.3:  # 30% chance
                    self._simulate_alert()
                
                # Simulate Azure Function monitoring
                self._simulate_azure_function()
                
                # Simulate MQTT messages
                self._simulate_mqtt_message()
                
                # Simulate API requests
                self._simulate_api_request()
                
                time.sleep(3)  # Update every 3 seconds
                
            except Exception as e:
                print(f"Simulation error: {str(e)}")
                time.sleep(1)
    
    def _simulate_sensor_data(self):
        """Simulate sensor data updates"""
        rooms = ['Living Room', 'Kitchen', 'Garage', 'Basement', 'Bedroom']
        
        for room in rooms:
            # Generate realistic sensor data
            temp = round(random.uniform(18, 32), 1)
            humidity = round(random.uniform(30, 70), 1)
            co_level = round(random.uniform(0.5, 6.0), 1)
            battery = round(random.uniform(10, 100), 1)
            
            sensor_data = {
                'sensor_id': f'SENSOR_{room.replace(" ", "_").upper()}',
                'room': room,
                'temperature': temp,
                'humidity': humidity,
                'co_level': co_level,
                'battery_level': battery,
                'signal_strength': random.randint(-80, -30),
                'timestamp': datetime.now().isoformat(),
                'status': 'normal' if co_level < 5.0 and temp < 30 else 'alert'
            }
            
            demo_state['sensors'][room] = sensor_data
            
            # Emit WebSocket update
            socketio.emit('sensor_update', {
                'room': room,
                'data': sensor_data,
                'timestamp': datetime.now().isoformat()
            })
            
            # Add to WebSocket events log
            demo_state['websocket_events'].insert(0, {
                'event': 'sensor_update',
                'room': room,
                'timestamp': datetime.now().isoformat(),
                'data': f"Temp: {temp}°C, Humidity: {humidity}%, CO: {co_level}ppm"
            })
    
    def _simulate_alert(self):
        """Simulate alert generation"""
        alert_types = [
            {'type': 'HIGH_TEMPERATURE', 'severity': 'WARNING', 'threshold': 30},
            {'type': 'HIGH_CO_LEVEL', 'severity': 'CRITICAL', 'threshold': 5.0},
            {'type': 'LOW_BATTERY', 'severity': 'WARNING', 'threshold': 20},
            {'type': 'SENSOR_OFFLINE', 'severity': 'WARNING', 'threshold': None}
        ]
        
        alert_config = random.choice(alert_types)
        room = random.choice(['Living Room', 'Kitchen', 'Garage', 'Basement'])
        
        alert = {
            'id': f'alert_{int(time.time())}_{random.randint(100, 999)}',
            'type': alert_config['type'],
            'severity': alert_config['severity'],
            'room': room,
            'message': self._generate_alert_message(alert_config['type'], room),
            'timestamp': datetime.now().isoformat(),
            'status': 'ACTIVE',
            'acknowledged': False
        }
        
        demo_state['alerts'].insert(0, alert)
        
        # Keep only last 10 alerts
        demo_state['alerts'] = demo_state['alerts'][:10]
        
        # Emit alert via WebSocket
        socketio.emit('alert_notification', {
            'alert': alert,
            'timestamp': datetime.now().isoformat()
        })
        
        # Simulate notification sending
        self._simulate_notification(alert)
        
        # Add to WebSocket events
        demo_state['websocket_events'].insert(0, {
            'event': 'alert_notification',
            'alert_type': alert['type'],
            'severity': alert['severity'],
            'room': room,
            'timestamp': datetime.now().isoformat()
        })
    
    def _simulate_azure_function(self):
        """Simulate Azure Function threshold monitoring"""
        sensor_data = random.choice(list(demo_state['sensors'].values())) if demo_state['sensors'] else None
        
        if sensor_data:
            log_entry = {
                'function': 'threshold_monitor',
                'sensor_id': sensor_data['sensor_id'],
                'room': sensor_data['room'],
                'status': 'executed',
                'alerts_triggered': 0,
                'timestamp': datetime.now().isoformat()
            }
            
            # Check thresholds
            if sensor_data['temperature'] > 30:
                log_entry['alerts_triggered'] += 1
                log_entry['threshold_exceeded'] = 'temperature'
            
            if sensor_data['co_level'] > 5.0:
                log_entry['alerts_triggered'] += 1
                log_entry['threshold_exceeded'] = 'co_level'
            
            demo_state['azure_function_logs'].insert(0, log_entry)
            demo_state['azure_function_logs'] = demo_state['azure_function_logs'][:15]
            
            # Emit Azure Function update
            socketio.emit('azure_function_update', log_entry)
    
    def _simulate_mqtt_message(self):
        """Simulate MQTT message transmission"""
        if demo_state['sensors']:
            sensor_data = random.choice(list(demo_state['sensors'].values()))
            
            mqtt_message = {
                'topic': f'smarthome/sensors/{sensor_data["room"].lower().replace(" ", "_")}/data',
                'payload': json.dumps(sensor_data),
                'qos': 1,
                'retained': False,
                'timestamp': datetime.now().isoformat(),
                'size': len(json.dumps(sensor_data))
            }
            
            demo_state['mqtt_messages'].insert(0, mqtt_message)
            demo_state['mqtt_messages'] = demo_state['mqtt_messages'][:10]
            
            # Emit MQTT update
            socketio.emit('mqtt_message', mqtt_message)
    
    def _simulate_api_request(self):
        """Simulate API request processing"""
        endpoints = [
            {'method': 'POST', 'path': '/api/sensors/data', 'status': 200},
            {'method': 'GET', 'path': '/api/sensors/current', 'status': 200},
            {'method': 'GET', 'path': '/api/alerts', 'status': 200},
            {'method': 'POST', 'path': '/api/alerts/acknowledge', 'status': 200},
            {'method': 'GET', 'path': '/api/sensors/history', 'status': 200}
        ]
        
        endpoint = random.choice(endpoints)
        
        api_request = {
            'method': endpoint['method'],
            'path': endpoint['path'],
            'status': endpoint['status'],
            'response_time': round(random.uniform(10, 150), 1),
            'timestamp': datetime.now().isoformat(),
            'client_ip': f'192.168.1.{random.randint(100, 200)}'
        }
        
        demo_state['api_requests'].insert(0, api_request)
        demo_state['api_requests'] = demo_state['api_requests'][:15]
        
        # Emit API update
        socketio.emit('api_request', api_request)
    
    def _simulate_notification(self, alert):
        """Simulate notification sending"""
        channels = ['email', 'sms', 'push', 'websocket', 'webhook']
        
        for channel in channels:
            notification = {
                'id': f'notif_{int(time.time())}_{random.randint(100, 999)}',
                'alert_id': alert['id'],
                'channel': channel,
                'status': 'sent' if random.random() > 0.05 else 'failed',
                'timestamp': datetime.now().isoformat(),
                'message': alert['message'][:50] + '...'
            }
            
            demo_state['notifications'].insert(0, notification)
        
        # Keep only last 20 notifications
        demo_state['notifications'] = demo_state['notifications'][:20]
        
        # Emit notification update
        socketio.emit('notification_sent', {
            'alert_id': alert['id'],
            'channels': channels,
            'timestamp': datetime.now().isoformat()
        })
    
    def _generate_alert_message(self, alert_type, room):
        """Generate alert messages"""
        messages = {
            'HIGH_TEMPERATURE': f'High temperature detected in {room}',
            'HIGH_CO_LEVEL': f'Dangerous CO level detected in {room}',
            'LOW_BATTERY': f'Low battery warning for sensor in {room}',
            'SENSOR_OFFLINE': f'Sensor in {room} is offline'
        }
        return messages.get(alert_type, f'Alert in {room}')

# Initialize demo backend
demo_backend = DemoBackend()

@app.route('/')
def index():
    """Main demo dashboard"""
    return render_template('demo_dashboard.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve static files"""
    return send_from_directory('static', filename)

@app.route('/api/demo/status')
def demo_status():
    """Get demo status"""
    return jsonify({
        'status': 'running',
        'simulation_active': demo_state['simulation_active'],
        'sensors_count': len(demo_state['sensors']),
        'alerts_count': len(demo_state['alerts']),
        'notifications_count': len(demo_state['notifications']),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/demo/sensors')
def get_sensors():
    """Get current sensor data"""
    return jsonify(demo_state['sensors'])

@app.route('/api/demo/alerts')
def get_alerts():
    """Get current alerts"""
    return jsonify(demo_state['alerts'])

@app.route('/api/demo/notifications')
def get_notifications():
    """Get notifications log"""
    return jsonify(demo_state['notifications'])

@app.route('/api/demo/azure-functions')
def get_azure_functions():
    """Get Azure Function logs"""
    return jsonify(demo_state['azure_function_logs'])

@app.route('/api/demo/mqtt')
def get_mqtt_messages():
    """Get MQTT messages"""
    return jsonify(demo_state['mqtt_messages'])

@app.route('/api/demo/api-requests')
def get_api_requests():
    """Get API requests log"""
    return jsonify(demo_state['api_requests'])

@app.route('/api/demo/websocket-events')
def get_websocket_events():
    """Get WebSocket events log"""
    return jsonify(demo_state['websocket_events'])

@app.route('/api/demo/start', methods=['POST'])
def start_demo():
    """Start the demo simulation"""
    demo_backend.start_simulation()
    return jsonify({'status': 'started', 'timestamp': datetime.now().isoformat()})

@app.route('/api/demo/stop', methods=['POST'])
def stop_demo():
    """Stop the demo simulation"""
    demo_backend.stop_simulation()
    return jsonify({'status': 'stopped', 'timestamp': datetime.now().isoformat()})

@app.route('/api/demo/trigger-alert', methods=['POST'])
def trigger_alert():
    """Manually trigger an alert for demo"""
    demo_backend._simulate_alert()
    return jsonify({'status': 'alert_triggered', 'timestamp': datetime.now().isoformat()})

@app.route('/api/demo/acknowledge-alert/<alert_id>', methods=['POST'])
def acknowledge_alert(alert_id):
    """Acknowledge an alert"""
    for alert in demo_state['alerts']:
        if alert['id'] == alert_id:
            alert['acknowledged'] = True
            alert['acknowledged_at'] = datetime.now().isoformat()
            
            # Emit acknowledgment
            socketio.emit('alert_acknowledged', {
                'alert_id': alert_id,
                'timestamp': datetime.now().isoformat()
            })
            
            return jsonify({'status': 'acknowledged', 'alert_id': alert_id})
    
    return jsonify({'status': 'not_found', 'alert_id': alert_id}), 404

@app.route('/api/demo/test-payloads')
def test_payloads():
    """Get test payload examples"""
    return jsonify({
        'normal_sensor': MockPayloads.sensor_data_normal(),
        'high_temp_alert': MockPayloads.sensor_data_high_temp(),
        'high_co_alert': MockPayloads.sensor_data_high_co(),
        'mqtt_payload': MockPayloads.mqtt_payload_normal(),
        'websocket_update': MockPayloads.websocket_sensor_update(),
        'azure_function_trigger': MockPayloads.azure_function_trigger(),
        'notification_payload': MockPayloads.notification_payload()
    })

# WebSocket event handlers
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    emit('connection_status', {
        'status': 'connected',
        'client_id': request.sid,
        'timestamp': datetime.now().isoformat()
    })
    
    # Send current state
    emit('initial_state', {
        'sensors': demo_state['sensors'],
        'alerts': demo_state['alerts'][:5],  # Send last 5 alerts
        'simulation_active': demo_state['simulation_active']
    })

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print(f'Client disconnected: {request.sid}')

@socketio.on('request_full_state')
def handle_full_state_request():
    """Send complete demo state"""
    emit('full_state', demo_state)

@socketio.on('test_websocket')
def handle_test_websocket():
    """Test WebSocket functionality"""
    emit('websocket_test_response', {
        'message': 'WebSocket test successful!',
        'timestamp': datetime.now().isoformat(),
        'client_id': request.sid
    })

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    print("🏠 Smart Home Backend Demo UI Starting...")
    print("📊 Dashboard available at: http://localhost:5005")
    print("🔌 WebSocket server running on port 5005")
    print("🚀 Starting demo simulation...")
    
    # Start demo simulation
    demo_backend.start_simulation()
    
    # Run the app
    socketio.run(app, host='0.0.0.0', port=5005, debug=True, allow_unsafe_werkzeug=True) 