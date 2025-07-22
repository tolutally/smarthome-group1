import json
import time
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional
from collections import deque
import paho.mqtt.client as mqtt
import logging

class Sensor:
    """Sensor class for handling data buffering and MQTT message forwarding"""
    
    def __init__(self, sensor_id: str, sensor_type: str, room: str, 
                 mqtt_client: Optional[mqtt.Client] = None,
                 buffer_size: int = 1000):
        """
        Initialize sensor with buffering capabilities
        
        Args:
            sensor_id: Unique identifier for the sensor
            sensor_type: Type of sensor (temperature, humidity, co)
            room: Room where sensor is located
            mqtt_client: MQTT client for message forwarding
            buffer_size: Maximum number of messages to buffer
        """
        self.sensor_id = sensor_id
        self.sensor_type = sensor_type.lower()
        self.room = room.lower()
        self.mqtt_client = mqtt_client
        self.buffer_size = buffer_size
        
        # Buffer for storing data when offline
        self.data_buffer = deque(maxlen=buffer_size)
        
        # Connection status
        self.is_online = True
        self.last_successful_send = datetime.utcnow()
        
        # Threading lock for thread-safe operations
        self.buffer_lock = threading.Lock()
        
        # Statistics
        self.total_readings = 0
        self.buffered_readings = 0
        self.failed_sends = 0
        
        # MQTT topic for this sensor
        self.mqtt_topic = f"sensor/{self.room}"
        
        logging.info(f"Sensor {self.sensor_id} initialized for {self.sensor_type} in {self.room}")
    
    def bufferData(self, value: float, timestamp: Optional[datetime] = None) -> bool:
        """
        Buffer sensor data with thread-safe operations
        
        Args:
            value: Sensor reading value
            timestamp: Reading timestamp (defaults to current time)
            
        Returns:
            bool: True if data was buffered successfully
        """
        try:
            if timestamp is None:
                timestamp = datetime.utcnow()
            
            # Create sensor data message
            sensor_data = {
                'sensor_id': self.sensor_id,
                'sensor_type': self.sensor_type,
                'value': float(value),
                'room': self.room,
                'timestamp': timestamp.isoformat(),
                'buffer_time': datetime.utcnow().isoformat(),
                'reading_count': self.total_readings + 1
            }
            
            # Thread-safe buffer operation
            with self.buffer_lock:
                self.data_buffer.append(sensor_data)
                self.buffered_readings += 1
                self.total_readings += 1
            
            logging.debug(f"Sensor {self.sensor_id}: Buffered reading {value} at {timestamp}")
            
            # Try to forward message immediately if online
            if self.is_online:
                return self._attemptForward(sensor_data)
            
            return True
            
        except Exception as e:
            logging.error(f"Error buffering data for sensor {self.sensor_id}: {e}")
            return False
    
    def forwardMessage(self, force_all: bool = False) -> int:
        """
        Forward buffered messages to MQTT broker
        
        Args:
            force_all: If True, forward all buffered messages regardless of connection status
            
        Returns:
            int: Number of messages successfully forwarded
        """
        if not self.mqtt_client:
            logging.warning(f"Sensor {self.sensor_id}: No MQTT client configured")
            return 0
        
        forwarded_count = 0
        failed_messages = []
        
        with self.buffer_lock:
            messages_to_send = list(self.data_buffer) if force_all else [self.data_buffer[-1]] if self.data_buffer else []
            
            if not messages_to_send:
                logging.debug(f"Sensor {self.sensor_id}: No messages to forward")
                return 0
        
        for message in messages_to_send:
            if self._attemptForward(message):
                forwarded_count += 1
                # Remove from buffer on successful send
                with self.buffer_lock:
                    try:
                        self.data_buffer.remove(message)
                        self.buffered_readings -= 1
                    except ValueError:
                        pass  # Message already removed
            else:
                failed_messages.append(message)
        
        if failed_messages:
            logging.warning(f"Sensor {self.sensor_id}: Failed to forward {len(failed_messages)} messages")
            self.is_online = False
        else:
            if forwarded_count > 0:
                self.is_online = True
                self.last_successful_send = datetime.utcnow()
        
        logging.info(f"Sensor {self.sensor_id}: Forwarded {forwarded_count} messages")
        return forwarded_count
    
    def _attemptForward(self, message: Dict[str, Any]) -> bool:
        """
        Attempt to forward a single message via MQTT
        
        Args:
            message: Sensor data message to forward
            
        Returns:
            bool: True if message was sent successfully
        """
        if not self.mqtt_client:
            return False
        
        try:
            # Convert message to JSON
            payload = json.dumps(message)
            
            # Publish to MQTT topic
            result = self.mqtt_client.publish(self.mqtt_topic, payload, qos=1)
            
            # Check if publish was successful
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logging.debug(f"Sensor {self.sensor_id}: Successfully sent message to {self.mqtt_topic}")
                return True
            else:
                logging.error(f"Sensor {self.sensor_id}: MQTT publish failed with code {result.rc}")
                self.failed_sends += 1
                return False
                
        except Exception as e:
            logging.error(f"Sensor {self.sensor_id}: Error forwarding message: {e}")
            self.failed_sends += 1
            return False
    
    def flushBuffer(self) -> int:
        """
        Forward all buffered messages and clear buffer
        
        Returns:
            int: Number of messages successfully forwarded
        """
        forwarded = self.forwardMessage(force_all=True)
        
        # Clear any remaining messages in buffer
        with self.buffer_lock:
            remaining = len(self.data_buffer)
            self.data_buffer.clear()
            self.buffered_readings = 0
            
        if remaining > 0:
            logging.warning(f"Sensor {self.sensor_id}: Cleared {remaining} unsent messages from buffer")
        
        return forwarded
    
    def getBufferStatus(self) -> Dict[str, Any]:
        """
        Get current buffer status and statistics
        
        Returns:
            dict: Buffer status information
        """
        with self.buffer_lock:
            buffer_count = len(self.data_buffer)
            oldest_message = self.data_buffer[0] if self.data_buffer else None
            newest_message = self.data_buffer[-1] if self.data_buffer else None
        
        return {
            'sensor_id': self.sensor_id,
            'sensor_type': self.sensor_type,
            'room': self.room,
            'is_online': self.is_online,
            'buffer_count': buffer_count,
            'buffer_size': self.buffer_size,
            'total_readings': self.total_readings,
            'buffered_readings': self.buffered_readings,
            'failed_sends': self.failed_sends,
            'last_successful_send': self.last_successful_send.isoformat(),
            'oldest_buffered': oldest_message.get('timestamp') if oldest_message else None,
            'newest_buffered': newest_message.get('timestamp') if newest_message else None,
            'mqtt_topic': self.mqtt_topic
        }
    
    def setOnlineStatus(self, is_online: bool):
        """
        Manually set the online status and attempt to flush buffer if coming online
        
        Args:
            is_online: New online status
        """
        previous_status = self.is_online
        self.is_online = is_online
        
        logging.info(f"Sensor {self.sensor_id}: Status changed from {'online' if previous_status else 'offline'} to {'online' if is_online else 'offline'}")
        
        # If coming back online, try to forward buffered messages
        if is_online and not previous_status:
            self.forwardMessage(force_all=True)
    
    def updateMqttClient(self, mqtt_client: mqtt.Client):
        """
        Update the MQTT client reference
        
        Args:
            mqtt_client: New MQTT client instance
        """
        self.mqtt_client = mqtt_client
        logging.info(f"Sensor {self.sensor_id}: MQTT client updated")
    
    def __str__(self) -> str:
        """String representation of the sensor"""
        return f"Sensor(id={self.sensor_id}, type={self.sensor_type}, room={self.room}, buffered={len(self.data_buffer)})"
    
    def __repr__(self) -> str:
        """Detailed string representation of the sensor"""
        return f"Sensor(sensor_id='{self.sensor_id}', sensor_type='{self.sensor_type}', room='{self.room}', buffer_size={self.buffer_size}, is_online={self.is_online})" 