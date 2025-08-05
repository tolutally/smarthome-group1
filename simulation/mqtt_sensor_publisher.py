import time
import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mqtt_client import MQTTSensorClient
from simulation.sensor_simulator import SensorDataSimulator

class MQTTSensorPublisher:
    def __init__(self):
        self.mqtt_client = MQTTSensorClient()
        self.simulator = SensorDataSimulator()
        self.publishing = False
    
    def publish_sensor_reading(self, reading):
        """Publish a single sensor reading to MQTT"""
        if not self.mqtt_client.network_available:
            print("❌ MQTT not connected")
            return False
        
        try:
            # Publish to individual topics
            self.mqtt_client.client.publish(
                self.mqtt_client.topic_temperature, 
                json.dumps({
                    "location": reading["location"],
                    "value": reading["temperature"],
                    "unit": "°C",
                    "timestamp": reading["timestamp"]
                })
            )
            
            self.mqtt_client.client.publish(
                self.mqtt_client.topic_humidity,
                json.dumps({
                    "location": reading["location"], 
                    "value": reading["humidity"],
                    "unit": "%",
                    "timestamp": reading["timestamp"]
                })
            )
            
            self.mqtt_client.client.publish(
                self.mqtt_client.topic_co,
                json.dumps({
                    "location": reading["location"],
                    "value": reading["co_level"], 
                    "unit": "ppm",
                    "timestamp": reading["timestamp"]
                })
            )
            
            print(f"📡 Published {reading['location']} data to MQTT")
            return True
            
        except Exception as e:
            print(f"❌ MQTT publish failed: {e}")
            return False
    
    def start_mqtt_simulation(self, interval=10):
        """Start publishing simulated sensor data to MQTT"""
        if not self.mqtt_client.connect_to_network():
            print("❌ Failed to connect to MQTT broker")
            return
        
        self.publishing = True
        print(f"🚀 Starting MQTT sensor publishing (interval: {interval}s)")
        
        try:
            while self.publishing:
                for location in self.simulator.locations:
                    reading = self.simulator.generate_sensor_reading(location)
                    self.publish_sensor_reading(reading)
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n🛑 MQTT publishing stopped")
        finally:
            self.publishing = False
            self.mqtt_client.disconnect()

if __name__ == "__main__":
    publisher = MQTTSensorPublisher()
    publisher.start_mqtt_simulation()
