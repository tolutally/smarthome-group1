import time
import random
import paho.mqtt.client as mqtt

class MQTTSensorClient:
    def __init__(self, broker_address="broker.hivemq.com", max_retries=3, retry_delay=2):
        self.broker_address = broker_address
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.network_available = False
        self.publishing = False
        
        # MQTT topics
        self.topic_temperature = "house/sensors/temperature"
        self.topic_humidity = "house/sensors/humidity"
        self.topic_co = "house/sensors/CO"
        
        # Initialize MQTT client
        self.client = mqtt.Client()
    
    def connect_to_network(self):
        """Connect to MQTT broker with retry logic"""
        retries = 0
        while not self.network_available and retries < self.max_retries:
            print(f"Attempting to connect... (Attempt {retries+1}/{self.max_retries})")
            try:
                self.client.connect(self.broker_address)
                self.client.loop_start()
                self.network_available = True
                print("Connected to MQTT broker!")
            except Exception as e:
                print(f"Connection failed: {e}")
                retries += 1
                time.sleep(self.retry_delay)
        
        if not self.network_available:
            print("Failed to connect after retries.")
        
        return self.network_available
    
    def publish_sensor_data(self):
        """Publish random sensor data to MQTT topics"""
        if not self.network_available:
            print("No network connection available.")
            return False
        
        temp = round(random.uniform(15, 35), 2)
        hum = round(random.uniform(30, 60), 2)
        co = round(random.uniform(0, 5), 2)
        
        try:
            self.client.publish(self.topic_temperature, str(temp))
            self.client.publish(self.topic_humidity, str(hum))
            self.client.publish(self.topic_co, str(co))
            print(f"Published -> T:{temp} | H:{hum} | CO:{co}")
            return True
        except Exception as e:
            print(f"Publishing failed: {e}")
            return False
    
    def start_publishing_loop(self, interval=2):
        """Start continuous publishing loop"""
        self.publishing = True
        while self.publishing:
            self.publish_sensor_data()
            time.sleep(interval)
    
    def stop_publishing(self):
        """Stop the publishing loop"""
        self.publishing = False
    
    def disconnect(self):
        """Disconnect from MQTT broker"""
        if self.network_available:
            self.client.loop_stop()
            self.client.disconnect()
            self.network_available = False
            print("Disconnected from MQTT broker.")