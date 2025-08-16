"""
WebSocket handlers for real-time Smart Home updates
Handles sensor data streaming, alerts, and bi-directional communication
"""
import json
import logging
import threading
import time
from datetime import datetime
from typing import Dict, Any, Set
from flask_socketio import emit, disconnect, join_room, leave_room
from flask import request


class WebSocketManager:
    """Manages WebSocket connections and real-time updates"""
    
    def __init__(self, socketio, sensor_service, alert_service, notification_service):
        """Initialize WebSocket manager"""
        self.socketio = socketio
        self.sensor_service = sensor_service
        self.alert_service = alert_service
        self.notification_service = notification_service
        
        self.connected_clients: Set[str] = set()
        self.streaming_active = False
        self.stream_thread = None
        self.logger = logging.getLogger(__name__)
        
        # Register event handlers
        self._register_handlers()
        
        self.logger.info("WebSocket manager initialized")
    
    def _register_handlers(self):
        """Register all WebSocket event handlers"""
        
        @self.socketio.on('connect')
        def handle_connect():
            """Handle client connection"""
            client_id = request.sid
            self.connected_clients.add(client_id)
            
            self.logger.info(f"Client connected: {client_id}")
            
            # Send welcome message
            emit('connection_status', {
                'status': 'connected',
                'client_id': client_id,
                'timestamp': datetime.now().isoformat(),
                'message': 'Welcome to Smart Home real-time updates'
            })
            
            # Send current sensor data
            self._send_current_sensor_data()
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection"""
            client_id = request.sid
            if client_id in self.connected_clients:
                self.connected_clients.remove(client_id)
            
            self.logger.info(f"Client disconnected: {client_id}")
            
            # Stop streaming if no clients connected
            if not self.connected_clients and self.streaming_active:
                self.stop_sensor_streaming()
        
        @self.socketio.on('start_sensor_stream')
        def handle_start_sensor_stream():
            """Start real-time sensor data streaming"""
            client_id = request.sid
            self.logger.info(f"Starting sensor stream for client: {client_id}")
            
            # Join streaming room
            join_room('sensor_stream')
            
            if not self.streaming_active:
                self.start_sensor_streaming()
            
            emit('stream_status', {
                'status': 'started',
                'message': 'Real-time sensor streaming started',
                'timestamp': datetime.now().isoformat()
            })
        
        @self.socketio.on('stop_sensor_stream')
        def handle_stop_sensor_stream():
            """Stop real-time sensor data streaming"""
            client_id = request.sid
            self.logger.info(f"Stopping sensor stream for client: {client_id}")
            
            # Leave streaming room
            leave_room('sensor_stream')
            
            emit('stream_status', {
                'status': 'stopped',
                'message': 'Real-time sensor streaming stopped',
                'timestamp': datetime.now().isoformat()
            })
        
        @self.socketio.on('request_sensor_data')
        def handle_request_sensor_data():
            """Handle request for current sensor data"""
            self._send_current_sensor_data()
        
        @self.socketio.on('request_alerts')
        def handle_request_alerts():
            """Handle request for current alerts"""
            self._send_current_alerts()
        
        @self.socketio.on('acknowledge_alert')
        def handle_acknowledge_alert(data):
            """Handle alert acknowledgment"""
            alert_id = data.get('alert_id')
            if alert_id:
                self._acknowledge_alert(alert_id)
        
        @self.socketio.on('subscribe_room')
        def handle_subscribe_room(data):
            """Subscribe to room-specific updates"""
            room = data.get('room')
            if room:
                join_room(f"room_{room}")
                emit('subscription_status', {
                    'room': room,
                    'status': 'subscribed',
                    'timestamp': datetime.now().isoformat()
                })
        
        @self.socketio.on('unsubscribe_room')
        def handle_unsubscribe_room(data):
            """Unsubscribe from room-specific updates"""
            room = data.get('room')
            if room:
                leave_room(f"room_{room}")
                emit('subscription_status', {
                    'room': room,
                    'status': 'unsubscribed',
                    'timestamp': datetime.now().isoformat()
                })
        
        @self.socketio.on('send_command')
        def handle_send_command(data):
            """Handle device control commands"""
            self._handle_device_command(data)
        
        @self.socketio.on('heartbeat')
        def handle_heartbeat():
            """Handle client heartbeat"""
            emit('heartbeat_response', {
                'timestamp': datetime.now().isoformat(),
                'status': 'alive'
            })
    
    def start_sensor_streaming(self):
        """Start periodic sensor data streaming"""
        if self.streaming_active:
            return
        
        self.streaming_active = True
        self.stream_thread = threading.Thread(target=self._stream_sensor_data, daemon=True)
        self.stream_thread.start()
        
        self.logger.info("Sensor streaming started")
    
    def stop_sensor_streaming(self):
        """Stop sensor data streaming"""
        self.streaming_active = False
        if self.stream_thread:
            self.stream_thread.join(timeout=1)
        
        self.logger.info("Sensor streaming stopped")
    
    def _stream_sensor_data(self):
        """Continuously stream sensor data"""
        while self.streaming_active and self.connected_clients:
            try:
                # Get current sensor data
                sensor_data = self._get_mock_sensor_data()
                
                # Emit to streaming room
                self.socketio.emit('sensor_data_update', {
                    'event': 'sensor_data_update',
                    'data': sensor_data,
                    'timestamp': datetime.now().isoformat()
                }, room='sensor_stream')
                
                # Check for alerts
                self._check_and_emit_alerts(sensor_data)
                
                # Sleep for 5 seconds
                time.sleep(5)
                
            except Exception as e:
                self.logger.error(f"Error in sensor streaming: {str(e)}")
                time.sleep(1)
    
    def _send_current_sensor_data(self):
        """Send current sensor data to requesting client"""
        try:
            sensor_data = self._get_mock_sensor_data()
            
            emit('current_sensor_data', {
                'event': 'current_sensor_data',
                'data': sensor_data,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            self.logger.error(f"Error sending current sensor data: {str(e)}")
            emit('error', {
                'message': 'Failed to retrieve sensor data',
                'error': str(e)
            })
    
    def _send_current_alerts(self):
        """Send current alerts to requesting client"""
        try:
            # Mock alerts data - replace with actual alert service call
            alerts = [
                {
                    'id': 'alert_001',
                    'type': 'HIGH_TEMPERATURE',
                    'room': 'Kitchen',
                    'message': 'High temperature detected: 35.0°C',
                    'severity': 'WARNING',
                    'timestamp': datetime.now().isoformat(),
                    'status': 'ACTIVE'
                }
            ]
            
            emit('current_alerts', {
                'event': 'current_alerts',
                'alerts': alerts,
                'total': len(alerts),
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            self.logger.error(f"Error sending current alerts: {str(e)}")
            emit('error', {
                'message': 'Failed to retrieve alerts',
                'error': str(e)
            })
    
    def _get_mock_sensor_data(self) -> Dict[str, Any]:
        """Get mock sensor data - replace with actual sensor service call"""
        import random
        
        return {
            "Living Room": {
                "temperature": round(random.uniform(20, 26), 1),
                "humidity": round(random.uniform(40, 60), 1),
                "co_level": round(random.uniform(0.5, 2.5), 1),
                "battery_level": round(random.uniform(70, 100), 1),
                "timestamp": datetime.now().isoformat()
            },
            "Kitchen": {
                "temperature": round(random.uniform(22, 28), 1),
                "humidity": round(random.uniform(45, 65), 1),
                "co_level": round(random.uniform(0.8, 3.2), 1),
                "battery_level": round(random.uniform(70, 100), 1),
                "timestamp": datetime.now().isoformat()
            },
            "Garage": {
                "temperature": round(random.uniform(15, 25), 1),
                "humidity": round(random.uniform(35, 55), 1),
                "co_level": round(random.uniform(1.0, 4.0), 1),
                "battery_level": round(random.uniform(70, 100), 1),
                "timestamp": datetime.now().isoformat()
            },
            "Basement": {
                "temperature": round(random.uniform(18, 22), 1),
                "humidity": round(random.uniform(50, 70), 1),
                "co_level": round(random.uniform(0.3, 2.0), 1),
                "battery_level": round(random.uniform(70, 100), 1),
                "timestamp": datetime.now().isoformat()
            }
        }
    
    def _check_and_emit_alerts(self, sensor_data: Dict[str, Any]):
        """Check sensor data for alerts and emit if found"""
        for room, data in sensor_data.items():
            # Check temperature
            if data.get('temperature', 0) > 30:
                self.emit_alert({
                    'id': f"temp_alert_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    'type': 'HIGH_TEMPERATURE',
                    'room': room,
                    'message': f"High temperature in {room}: {data['temperature']}°C",
                    'severity': 'WARNING',
                    'current_value': data['temperature'],
                    'threshold': 30.0
                })
            
            # Check CO level
            if data.get('co_level', 0) > 5.0:
                self.emit_alert({
                    'id': f"co_alert_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    'type': 'HIGH_CO_LEVEL',
                    'room': room,
                    'message': f"Critical CO level in {room}: {data['co_level']} ppm",
                    'severity': 'CRITICAL',
                    'current_value': data['co_level'],
                    'threshold': 5.0
                })
            
            # Check battery level
            if data.get('battery_level', 100) < 20:
                self.emit_alert({
                    'id': f"battery_alert_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    'type': 'LOW_BATTERY',
                    'room': room,
                    'message': f"Low battery in {room}: {data['battery_level']}%",
                    'severity': 'WARNING',
                    'current_value': data['battery_level'],
                    'threshold': 20.0
                })
    
    def emit_alert(self, alert: Dict[str, Any]):
        """Emit alert to all connected clients"""
        alert_payload = {
            'event': 'alert_notification',
            'alert': {
                **alert,
                'timestamp': datetime.now().isoformat(),
                'status': 'ACTIVE'
            },
            'timestamp': datetime.now().isoformat()
        }
        
        # Emit to all clients
        self.socketio.emit('alert_notification', alert_payload)
        
        # Also emit to specific room if room is specified
        if alert.get('room'):
            room_name = f"room_{alert['room']}"
            self.socketio.emit('room_alert', alert_payload, room=room_name)
        
        self.logger.warning(f"Alert emitted: {alert['type']} in {alert.get('room', 'unknown')}")
    
    def emit_sensor_update(self, room: str, sensor_data: Dict[str, Any]):
        """Emit sensor update for specific room"""
        update_payload = {
            'event': 'room_sensor_update',
            'room': room,
            'data': sensor_data,
            'timestamp': datetime.now().isoformat()
        }
        
        # Emit to all clients
        self.socketio.emit('sensor_update', update_payload)
        
        # Emit to room-specific subscribers
        room_name = f"room_{room}"
        self.socketio.emit('room_sensor_update', update_payload, room=room_name)
    
    def _acknowledge_alert(self, alert_id: str):
        """Handle alert acknowledgment"""
        try:
            # Update alert status in database
            # This would typically call alert_service.acknowledge_alert(alert_id)
            
            ack_payload = {
                'event': 'alert_acknowledged',
                'alert_id': alert_id,
                'acknowledged_by': request.sid,
                'timestamp': datetime.now().isoformat()
            }
            
            # Emit acknowledgment to all clients
            self.socketio.emit('alert_acknowledged', ack_payload)
            
            self.logger.info(f"Alert {alert_id} acknowledged by client {request.sid}")
            
        except Exception as e:
            self.logger.error(f"Error acknowledging alert {alert_id}: {str(e)}")
            emit('error', {
                'message': f'Failed to acknowledge alert {alert_id}',
                'error': str(e)
            })
    
    def _handle_device_command(self, data: Dict[str, Any]):
        """Handle device control commands"""
        try:
            device_id = data.get('device_id')
            command = data.get('command')
            parameters = data.get('parameters', {})
            
            # Mock device command processing
            result = {
                'device_id': device_id,
                'command': command,
                'status': 'executed',
                'timestamp': datetime.now().isoformat()
            }
            
            # Emit command result
            emit('command_result', {
                'event': 'command_result',
                'result': result
            })
            
            # Broadcast device status change
            self.socketio.emit('device_status_changed', {
                'event': 'device_status_changed',
                'device_id': device_id,
                'status': result,
                'timestamp': datetime.now().isoformat()
            })
            
            self.logger.info(f"Device command executed: {device_id} - {command}")
            
        except Exception as e:
            self.logger.error(f"Error executing device command: {str(e)}")
            emit('error', {
                'message': 'Failed to execute device command',
                'error': str(e)
            })
    
    def broadcast_system_notification(self, message: str, notification_type: str = 'info'):
        """Broadcast system notification to all clients"""
        notification_payload = {
            'event': 'system_notification',
            'notification': {
                'type': notification_type,
                'message': message,
                'timestamp': datetime.now().isoformat()
            }
        }
        
        self.socketio.emit('system_notification', notification_payload)
        self.logger.info(f"System notification broadcast: {message}")
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get WebSocket connection statistics"""
        return {
            'connected_clients': len(self.connected_clients),
            'streaming_active': self.streaming_active,
            'timestamp': datetime.now().isoformat()
        }


# WebSocket event handlers for Flask-SocketIO integration
def setup_websocket_handlers(socketio, sensor_service=None, alert_service=None, notification_service=None):
    """Setup WebSocket handlers with services"""
    
    # Create WebSocket manager
    ws_manager = WebSocketManager(socketio, sensor_service, alert_service, notification_service)
    
    # Additional custom handlers can be added here
    @socketio.on('ping')
    def handle_ping():
        """Handle ping from client"""
        emit('pong', {'timestamp': datetime.now().isoformat()})
    
    @socketio.on('get_connection_stats')
    def handle_get_connection_stats():
        """Handle request for connection statistics"""
        stats = ws_manager.get_connection_stats()
        emit('connection_stats', stats)
    
    return ws_manager 