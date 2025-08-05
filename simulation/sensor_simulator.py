import time
import random
from datetime import datetime
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.sensor_service import SensorService

class SensorDataSimulator:
    def __init__(self):
        self.sensor_service = SensorService()
        self.locations = ["Living Room", "Kitchen", "Garage", "Basement"]
        self.running = False
        
        # Sensor value ranges
        self.ranges = {
            "temperature": {"min": 15.0, "max": 35.0},
            "humidity": {"min": 30.0, "max": 70.0},
            "co_level": {"min": 0.0, "max": 5.0}
        }
    
    def generate_sensor_reading(self, location):
        """Generate realistic sensor data for a location"""
        # Add some location-specific variations
        temp_offset = self._get_location_offset(location, "temperature")
        humidity_offset = self._get_location_offset(location, "humidity")
        
        temperature = round(random.uniform(
            self.ranges["temperature"]["min"] + temp_offset,
            self.ranges["temperature"]["max"] + temp_offset
        ), 1)
        
        humidity = round(random.uniform(
            self.ranges["humidity"]["min"] + humidity_offset,
            self.ranges["humidity"]["max"] + humidity_offset
        ), 1)
        
        co_level = round(random.uniform(
            self.ranges["co_level"]["min"],
            self.ranges["co_level"]["max"]
        ), 2)
        
        return {
            "location": location,
            "temperature": temperature,
            "humidity": humidity,
            "co_level": co_level,
            "timestamp": datetime.now().isoformat()
        }
    
    def _get_location_offset(self, location, sensor_type):
        """Get location-specific offset for more realistic data"""
        offsets = {
            "Kitchen": {"temperature": 2, "humidity": -5},
            "Garage": {"temperature": -3, "humidity": -10},
            "Basement": {"temperature": -2, "humidity": 10},
            "Living Room": {"temperature": 0, "humidity": 0}
        }
        return offsets.get(location, {}).get(sensor_type, 0)
    
    def simulate_single_reading(self, location=None):
        """Generate and save a single sensor reading"""
        if location is None:
            location = random.choice(self.locations)
        
        reading = self.generate_sensor_reading(location)
        
        # Save to database
        success = self.sensor_service.save_sensor_readings(
            reading["location"],
            reading["temperature"],
            reading["humidity"],
            reading["co_level"]
        )
        
        if success:
            print(f"✅ {reading['location']}: T={reading['temperature']}°C, "
                  f"H={reading['humidity']}%, CO={reading['co_level']}ppm")
        else:
            print(f"❌ Failed to save reading for {reading['location']}")
        
        return reading
    
    def start_continuous_simulation(self, interval=5):
        """Start continuous sensor data simulation"""
        self.running = True
        print(f"🚀 Starting sensor simulation (interval: {interval}s)")
        print("Press Ctrl+C to stop...")
        
        try:
            while self.running:
                for location in self.locations:
                    self.simulate_single_reading(location)
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n🛑 Simulation stopped by user")
        except Exception as e:
            print(f"❌ Simulation error: {e}")
        finally:
            self.running = False
    
    def stop_simulation(self):
        """Stop the simulation"""
        self.running = False
        print("🛑 Simulation stopped")
    
    def generate_batch_data(self, count=100):
        """Generate a batch of historical data"""
        print(f"📊 Generating {count} sensor readings...")
        
        for i in range(count):
            location = random.choice(self.locations)
            self.simulate_single_reading(location)
            
            if (i + 1) % 10 == 0:
                print(f"Progress: {i + 1}/{count} readings generated")
        
        print("✅ Batch data generation complete!")

if __name__ == "__main__":
    simulator = SensorDataSimulator()
    
    # Choose simulation mode
    print("Sensor Data Simulator")
    print("1. Continuous simulation")
    print("2. Generate batch data")
    print("3. Single reading test")
    
    choice = input("Select mode (1-3): ").strip()
    
    if choice == "1":
        interval = int(input("Enter interval in seconds (default 5): ") or 5)
        simulator.start_continuous_simulation(interval)
    elif choice == "2":
        count = int(input("Enter number of readings (default 100): ") or 100)
        simulator.generate_batch_data(count)
    elif choice == "3":
        location = input("Enter location (or press Enter for random): ").strip()
        simulator.simulate_single_reading(location if location else None)
    else:
        print("Invalid choice")
