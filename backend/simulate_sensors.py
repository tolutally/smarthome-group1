#!/usr/bin/env python3

import json
import time
import random
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any
import paho.mqtt.client as mqtt
import logging
from models.sensor import Sensor
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class SensorSimulator:
    """Simulates multiple smart home sensors with realistic data patterns"""
    
    def __init__(self, mqtt_broker: str = 'localhost', mqtt_port: int = 1883):
        """
        Initialize sensor simulator
        
        Args:
            mqtt_broker: MQTT broker hostname
            mqtt_port: MQTT broker port
        """
        self.mqtt_broker = mqtt_broker
        self.mqtt_port = mqtt_port
        
        # MQTT client setup
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_disconnect = self._on_mqtt_disconnect
        
        # Simulation settings
        self.simulation_interval = 5  # seconds between readings
        self.rooms = ['living_room', 'bedroom', 'kitchen']
        self.running = False
        
        # Sensor instances
        self.sensors: List[Sensor] = []
        self._initialize_sensors()
        
        # Data generation settings for realistic patterns
        self.time_start = datetime.utcnow()
        self.daily_patterns = self._setup_daily_patterns()
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def _initialize_sensors(self):
        """Initialize sensor instances for each room and type"""
        sensor_types = ['temperature', 'humidity', 'co']
        
        for room in self.rooms:
            for sensor_type in sensor_types:
                sensor_id = f"{sensor_type}_sensor_{room}_{random.randint(1000, 9999)}"
                
                sensor = Sensor(
                    sensor_id=sensor_id,
                    sensor_type=sensor_type,
                    room=room,
                    mqtt_client=self.mqtt_client
                )
                
                self.sensors.append(sensor)
                self.logger.info(f"Initialized sensor: {sensor}")
    
    def _setup_daily_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Setup realistic daily patterns for different sensor types"""
        return {
            'temperature': {
                'base_value': 22.0,  # Base temperature in Celsius
                'daily_variation': 5.0,  # Daily temperature swing
                'room_variations': {
                    'living_room': 0.0,
                    'bedroom': -1.0,  # Slightly cooler
                    'kitchen': 2.0   # Warmer due to cooking
                },
                'noise_level': 0.5  # Random noise amplitude
            },
            'humidity': {
                'base_value': 45.0,  # Base humidity percentage
                'daily_variation': 15.0,  # Daily humidity swing
                'room_variations': {
                    'living_room': 0.0,
                    'bedroom': -5.0,  # Drier
                    'kitchen': 10.0   # More humid due to cooking
                },
                'noise_level': 2.0
            },
            'co': {
                'base_value': 5.0,   # Base CO level in ppm
                'daily_variation': 3.0,  # Daily CO variation
                'room_variations': {
                    'living_room': 0.0,
                    'bedroom': -2.0,  # Lower CO
                    'kitchen': 3.0    # Higher CO due to appliances
                },
                'noise_level': 1.0,
                'spike_probability': 0.05  # 5% chance of spike (cooking, etc.)
            }
        }
    
    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """Callback for MQTT connection"""
        if rc == 0:
            self.logger.info(f"Connected to MQTT broker at {self.mqtt_broker}:{self.mqtt_port}")
            # Update all sensors with the connected client
            for sensor in self.sensors:
                sensor.updateMqttClient(client)
        else:
            self.logger.error(f"Failed to connect to MQTT broker, return code {rc}")
    
    def _on_mqtt_disconnect(self, client, userdata, rc):
        """Callback for MQTT disconnection"""
        self.logger.warning("Disconnected from MQTT broker")
        # Mark all sensors as offline
        for sensor in self.sensors:
            sensor.setOnlineStatus(False)
    
    def _generate_realistic_value(self, sensor_type: str, room: str, current_time: datetime) -> float:
        """
        Generate realistic sensor values with daily patterns and noise
        
        Args:
            sensor_type: Type of sensor
            room: Room location
            current_time: Current timestamp
            
        Returns:
            float: Generated sensor value
        """
        patterns = self.daily_patterns[sensor_type]
        
        # Calculate time-based factors
        hours_since_start = (current_time - self.time_start).total_seconds() / 3600
        daily_cycle = (hours_since_start % 24) / 24  # 0-1 for 24 hour cycle
        
        # Base value with room variation
        base_value = patterns['base_value'] + patterns['room_variations'].get(room, 0)
        
        # Daily pattern (sinusoidal)
        daily_variation = patterns['daily_variation'] * math.sin(2 * math.pi * daily_cycle)
        
        # Random noise
        noise = random.gauss(0, patterns['noise_level'])
        
        # Calculate final value
        value = base_value + daily_variation + noise
        
        # Special handling for CO sensors (occasional spikes)
        if sensor_type == 'co' and random.random() < patterns.get('spike_probability', 0):
            spike = random.uniform(20, 45)  # CO spike
            value += spike
            self.logger.info(f"Generated CO spike: {spike:.1f} ppm in {room}")
        
        # Ensure values stay within reasonable bounds
        value = max(0, value)  # No negative values
        
        # Specific bounds for each sensor type
        if sensor_type == 'temperature':
            value = max(-10, min(50, value))  # -10°C to 50°C
        elif sensor_type == 'humidity':
            value = max(0, min(100, value))   # 0% to 100%
        elif sensor_type == 'co':
            value = max(0, min(100, value))   # 0 to 100 ppm
        
        return round(value, 2)
    
    def _simulate_sensor_reading(self, sensor: Sensor):
        """
        Generate and buffer a single sensor reading
        
        Args:
            sensor: Sensor instance to generate reading for
        """
        try:
            current_time = datetime.utcnow()
            
            # Generate realistic value
            value = self._generate_realistic_value(
                sensor.sensor_type, 
                sensor.room, 
                current_time
            )
            
            # Buffer the data (will attempt to forward if online)
            success = sensor.bufferData(value, current_time)
            
            if success:
                self.logger.debug(f"Generated reading for {sensor.sensor_id}: {value}")
            else:
                self.logger.error(f"Failed to buffer reading for {sensor.sensor_id}")
                
        except Exception as e:
            self.logger.error(f"Error generating reading for {sensor.sensor_id}: {e}")
    
    def _simulation_loop(self):
        """Main simulation loop"""
        self.logger.info("Starting sensor simulation loop")
        
        while self.running:
            try:
                # Generate readings for all sensors
                for sensor in self.sensors:
                    self._simulate_sensor_reading(sensor)
                
                # Wait for next interval
                time.sleep(self.simulation_interval)
                
            except KeyboardInterrupt:
                self.logger.info("Simulation interrupted by user")
                break
            except Exception as e:
                self.logger.error(f"Error in simulation loop: {e}")
                time.sleep(1)  # Brief pause before continuing
        
        self.logger.info("Sensor simulation loop ended")
    
    def start_simulation(self):
        """Start the sensor simulation"""
        if self.running:
            self.logger.warning("Simulation is already running")
            return
        
        try:
            # Connect to MQTT broker
            self.logger.info(f"Connecting to MQTT broker at {self.mqtt_broker}:{self.mqtt_port}")
            self.mqtt_client.connect(self.mqtt_broker, self.mqtt_port, 60)
            self.mqtt_client.loop_start()
            
            # Start simulation
            self.running = True
            
            # Run simulation in a separate thread
            simulation_thread = threading.Thread(target=self._simulation_loop)
            simulation_thread.daemon = True
            simulation_thread.start()
            
            self.logger.info("Sensor simulation started")
            return simulation_thread
            
        except Exception as e:
            self.logger.error(f"Failed to start simulation: {e}")
            self.running = False
            raise
    
    def stop_simulation(self):
        """Stop the sensor simulation"""
        self.logger.info("Stopping sensor simulation")
        self.running = False
        
        # Flush all sensor buffers
        for sensor in self.sensors:
            buffered_count = sensor.flushBuffer()
            if buffered_count > 0:
                self.logger.info(f"Flushed {buffered_count} buffered messages from {sensor.sensor_id}")
        
        # Disconnect MQTT
        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()
        
        self.logger.info("Sensor simulation stopped")
    
    def get_simulation_status(self) -> Dict[str, Any]:
        """Get current simulation status"""
        sensor_status = []
        for sensor in self.sensors:
            sensor_status.append(sensor.getBufferStatus())
        
        return {
            'running': self.running,
            'mqtt_broker': f"{self.mqtt_broker}:{self.mqtt_port}",
            'simulation_interval': self.simulation_interval,
            'total_sensors': len(self.sensors),
            'rooms': self.rooms,
            'sensors': sensor_status,
            'uptime': str(datetime.utcnow() - self.time_start)
        }

# Import math for sinusoidal patterns
import math

def main():
    """Main function to run the sensor simulator"""
    # Configuration from environment variables
    mqtt_broker = os.getenv('MQTT_BROKER', 'localhost')
    mqtt_port = int(os.getenv('MQTT_PORT', 1883))
    
    # Create and start simulator
    simulator = SensorSimulator(mqtt_broker, mqtt_port)
    
    try:
        # Start simulation
        simulation_thread = simulator.start_simulation()
        
        print(f"🏠 Smart Home Sensor Simulator Started")
        print(f"📡 MQTT Broker: {mqtt_broker}:{mqtt_port}")
        print(f"🏠 Rooms: {', '.join(simulator.rooms)}")
        print(f"📊 Sensors: {len(simulator.sensors)} total")
        print(f"⏱️  Interval: {simulator.simulation_interval} seconds")
        print("📈 Generating realistic sensor data...")
        print("\nPress Ctrl+C to stop\n")
        
        # Print status updates every 30 seconds
        last_status_time = time.time()
        
        while simulator.running:
            current_time = time.time()
            if current_time - last_status_time >= 30:
                status = simulator.get_simulation_status()
                total_buffered = sum(s['buffer_count'] for s in status['sensors'])
                total_readings = sum(s['total_readings'] for s in status['sensors'])
                
                print(f"📊 Status: {total_readings} readings generated, {total_buffered} buffered, uptime: {status['uptime']}")
                last_status_time = current_time
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping sensor simulation...")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        simulator.stop_simulation()
        print("✅ Sensor simulation stopped")

if __name__ == "__main__":
    main() 