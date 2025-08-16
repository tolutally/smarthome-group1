"""
Test payloads and mock data for Smart Home System
"""
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List

class MockPayloads:
    """Mock payloads for testing sensor data, alerts, and API responses"""
    
    @staticmethod
    def sensor_data_normal() -> Dict[str, Any]:
        """Normal sensor readings within acceptable ranges"""
        return {
            "sensor_id": "TEMP_001_LIVING",
            "room": "Living Room",
            "timestamp": datetime.now().isoformat(),
            "temperature": 22.5,
            "humidity": 45.0,
            "co_level": 1.2,
            "battery_level": 85,
            "signal_strength": -45
        }
    
    @staticmethod
    def sensor_data_high_temp() -> Dict[str, Any]:
        """High temperature alert scenario"""
        return {
            "sensor_id": "TEMP_002_KITCHEN", 
            "room": "Kitchen",
            "timestamp": datetime.now().isoformat(),
            "temperature": 35.0,  # Above threshold
            "humidity": 55.0,
            "co_level": 1.8,
            "battery_level": 75,
            "signal_strength": -50
        }
    
    @staticmethod
    def sensor_data_high_co() -> Dict[str, Any]:
        """High CO level alert scenario"""
        return {
            "sensor_id": "CO_001_GARAGE",
            "room": "Garage", 
            "timestamp": datetime.now().isoformat(),
            "temperature": 20.0,
            "humidity": 60.0,
            "co_level": 8.5,  # Above threshold (danger level)
            "battery_level": 65,
            "signal_strength": -55
        }
    
    @staticmethod
    def sensor_data_low_battery() -> Dict[str, Any]:
        """Low battery alert scenario"""
        return {
            "sensor_id": "TEMP_003_BASEMENT",
            "room": "Basement",
            "timestamp": datetime.now().isoformat(),
            "temperature": 18.5,
            "humidity": 65.0,
            "co_level": 0.8,
            "battery_level": 15,  # Low battery
            "signal_strength": -60
        }
    
    @staticmethod
    def sensor_data_offline() -> Dict[str, Any]:
        """Offline sensor scenario (old timestamp)"""
        old_timestamp = datetime.now() - timedelta(hours=2)
        return {
            "sensor_id": "TEMP_004_BEDROOM",
            "room": "Bedroom",
            "timestamp": old_timestamp.isoformat(),
            "temperature": None,
            "humidity": None,
            "co_level": None,
            "battery_level": 0,
            "signal_strength": -100
        }
    
    @staticmethod
    def mqtt_payload_normal() -> str:
        """MQTT message payload for normal readings"""
        data = MockPayloads.sensor_data_normal()
        return json.dumps(data)
    
    @staticmethod
    def mqtt_payload_alert() -> str:
        """MQTT message payload for alert condition"""
        data = MockPayloads.sensor_data_high_co()
        return json.dumps(data)
    
    @staticmethod
    def api_response_sensors() -> Dict[str, Any]:
        """Mock API response for sensors endpoint"""
        return {
            "status": "success",
            "data": [
                MockPayloads.sensor_data_normal(),
                MockPayloads.sensor_data_high_temp(),
                MockPayloads.sensor_data_low_battery()
            ],
            "total": 3,
            "timestamp": datetime.now().isoformat()
        }
    
    @staticmethod
    def api_response_alerts() -> Dict[str, Any]:
        """Mock API response for alerts endpoint"""
        return {
            "status": "success", 
            "alerts": [
                {
                    "id": "alert_001",
                    "type": "HIGH_TEMPERATURE",
                    "sensor_id": "TEMP_002_KITCHEN",
                    "room": "Kitchen",
                    "message": "High temperature detected: 35.0°C",
                    "severity": "WARNING",
                    "timestamp": datetime.now().isoformat(),
                    "status": "ACTIVE",
                    "threshold_value": 30.0,
                    "current_value": 35.0
                },
                {
                    "id": "alert_002", 
                    "type": "HIGH_CO_LEVEL",
                    "sensor_id": "CO_001_GARAGE",
                    "room": "Garage",
                    "message": "Dangerous CO level detected: 8.5 ppm",
                    "severity": "CRITICAL",
                    "timestamp": datetime.now().isoformat(),
                    "status": "ACTIVE",
                    "threshold_value": 5.0,
                    "current_value": 8.5
                }
            ],
            "total": 2,
            "timestamp": datetime.now().isoformat()
        }
    
    @staticmethod
    def websocket_sensor_update() -> Dict[str, Any]:
        """WebSocket real-time sensor data update"""
        return {
            "event": "sensor_data_update",
            "data": {
                "Living Room": MockPayloads.sensor_data_normal(),
                "Kitchen": MockPayloads.sensor_data_high_temp(),
                "Garage": MockPayloads.sensor_data_high_co(),
                "Basement": MockPayloads.sensor_data_low_battery()
            },
            "timestamp": datetime.now().isoformat()
        }
    
    @staticmethod
    def websocket_alert_notification() -> Dict[str, Any]:
        """WebSocket real-time alert notification"""
        return {
            "event": "alert_notification",
            "alert": {
                "id": "alert_003",
                "type": "HIGH_CO_LEVEL", 
                "sensor_id": "CO_001_GARAGE",
                "room": "Garage",
                "message": "CRITICAL: CO level 8.5 ppm exceeds safe threshold!",
                "severity": "CRITICAL",
                "timestamp": datetime.now().isoformat(),
                "actions_required": [
                    "Evacuate the area immediately",
                    "Ventilate the space",
                    "Check CO source"
                ]
            },
            "timestamp": datetime.now().isoformat()
        }
    
    @staticmethod
    def azure_function_trigger() -> Dict[str, Any]:
        """Azure Function trigger payload for threshold monitoring"""
        return {
            "sensor_data": MockPayloads.sensor_data_high_co(),
            "threshold_config": {
                "temperature": {"min": 10, "max": 30},
                "humidity": {"min": 30, "max": 70},
                "co_level": {"max": 5.0}
            },
            "notification_config": {
                "email": "admin@smarthome.com",
                "sms": "+1234567890",
                "webhook": "https://webhook.site/uuid"
            }
        }
    
    @staticmethod
    def notification_payload() -> Dict[str, Any]:
        """Notification service payload"""
        return {
            "type": "alert",
            "priority": "high",
            "recipients": ["admin@smarthome.com"],
            "subject": "Smart Home Alert: High CO Level Detected",
            "message": "Critical CO level of 8.5 ppm detected in Garage. Immediate action required.",
            "data": {
                "sensor_id": "CO_001_GARAGE",
                "room": "Garage", 
                "value": 8.5,
                "threshold": 5.0,
                "timestamp": datetime.now().isoformat()
            },
            "channels": ["email", "sms", "push", "websocket"]
        }

    @staticmethod
    def batch_sensor_data(count: int = 10) -> List[Dict[str, Any]]:
        """Generate batch of sensor data for load testing"""
        rooms = ["Living Room", "Kitchen", "Garage", "Basement", "Bedroom"]
        sensors = []
        
        for i in range(count):
            room = rooms[i % len(rooms)]
            sensors.append({
                "sensor_id": f"SENSOR_{i:03d}_{room.replace(' ', '_').upper()}",
                "room": room,
                "timestamp": (datetime.now() - timedelta(minutes=i)).isoformat(),
                "temperature": 20 + (i % 15),
                "humidity": 40 + (i % 30),
                "co_level": 0.5 + (i % 3),
                "battery_level": 100 - (i % 80),
                "signal_strength": -40 - (i % 40)
            })
        
        return sensors 