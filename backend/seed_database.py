#!/usr/bin/env python3
"""
Database Seeding Script for Smart Home System
Populates MongoDB with realistic dummy data for testing and demonstration
"""

import os
import sys
import json
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any
from pymongo import MongoClient
import redis
from dotenv import load_dotenv

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import our mock data generators
from tests.test_payloads import MockPayloads

# Load environment variables
load_dotenv()

class DatabaseSeeder:
    """Seeds the database with realistic dummy data"""
    
    def __init__(self):
        """Initialize database connections"""
        # MongoDB connection
        mongodb_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/smarthome')
        self.mongo_client = MongoClient(mongodb_uri)
        self.db = self.mongo_client.smarthome
        
        # Redis connection (optional)
        try:
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
            self.redis_client = redis.from_url(redis_url)
            self.redis_available = True
        except:
            self.redis_client = None
            self.redis_available = False
        
        # Collections
        self.sensor_data = self.db.sensor_data
        self.alerts = self.db.alerts
        self.users = self.db.users
        self.settings = self.db.settings
        
        print("🏠 Smart Home Database Seeder")
        print("=" * 40)
    
    def seed_all_data(self, days_back: int = 7, sensors_per_hour: int = 12):
        """Seed all database collections with dummy data"""
        print(f"📊 Seeding database with {days_back} days of historical data...")
        
        # Clear existing data (optional)
        choice = input("❓ Clear existing data? (y/N): ").lower()
        if choice == 'y':
            self.clear_all_data()
        
        # Seed different types of data
        self.seed_sensor_data(days_back, sensors_per_hour)
        self.seed_alerts_data(days_back)
        self.seed_users_data()
        self.seed_settings_data()
        
        if self.redis_available:
            self.update_redis_cache()
        
        print("✅ Database seeding completed!")
        self.print_summary()
    
    def clear_all_data(self):
        """Clear all existing data from collections"""
        print("🗑️ Clearing existing data...")
        
        self.sensor_data.delete_many({})
        self.alerts.delete_many({})
        self.users.delete_many({})
        self.settings.delete_many({})
        
        if self.redis_available:
            self.redis_client.flushall()
        
        print("   Cleared sensor_data, alerts, users, settings collections")
    
    def seed_sensor_data(self, days_back: int, sensors_per_hour: int):
        """Generate realistic sensor data for the past N days"""
        print(f"🌡️ Generating {days_back} days of sensor data...")
        
        rooms = ["Living Room", "Kitchen", "Garage", "Basement", "Bedroom"]
        
        total_records = days_back * 24 * sensors_per_hour * len(rooms)
        records = []
        
        # Generate data for each day
        for day in range(days_back):
            current_date = datetime.now() - timedelta(days=day)
            
            # Generate hourly data with realistic patterns
            for hour in range(24):
                for interval in range(sensors_per_hour):
                    timestamp = current_date.replace(
                        hour=hour, 
                        minute=interval * (60 // sensors_per_hour),
                        second=0,
                        microsecond=0
                    )
                    
                    # Generate data for each room
                    for room in rooms:
                        sensor_data = self.generate_realistic_sensor_reading(
                            room, timestamp, hour
                        )
                        records.append(sensor_data)
        
        # Insert in batches for better performance
        batch_size = 1000
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            self.sensor_data.insert_many(batch)
            print(f"   Inserted {min(i + batch_size, len(records))}/{len(records)} records")
        
        print(f"✅ Generated {len(records)} sensor readings")
    
    def generate_realistic_sensor_reading(self, room: str, timestamp: datetime, hour: int) -> Dict[str, Any]:
        """Generate realistic sensor reading based on time and room"""
        
        # Base values by room
        room_profiles = {
            "Living Room": {"temp_base": 22, "humidity_base": 45, "co_base": 1.0},
            "Kitchen": {"temp_base": 24, "humidity_base": 50, "co_base": 2.0},
            "Garage": {"temp_base": 18, "humidity_base": 40, "co_base": 3.0},
            "Basement": {"temp_base": 19, "humidity_base": 60, "co_base": 1.5},
            "Bedroom": {"temp_base": 21, "humidity_base": 45, "co_base": 0.8}
        }
        
        profile = room_profiles.get(room, room_profiles["Living Room"])
        
        # Time-based variations
        # Temperature varies throughout the day
        temp_variation = 3 * abs(hour - 14) / 14  # Cooler at night, warmer at 2 PM
        temperature = profile["temp_base"] + random.uniform(-2, 2) - temp_variation
        
        # Humidity varies inversely with temperature
        humidity = profile["humidity_base"] + random.uniform(-10, 10) + (temp_variation * 2)
        
        # CO level varies slightly
        co_level = profile["co_base"] + random.uniform(-0.5, 0.5)
        
        # Battery level decreases over time
        days_since_start = (datetime.now() - timestamp).days
        battery_drain = min(days_since_start * 2, 80)  # 2% per day
        battery_level = 100 - battery_drain + random.uniform(-5, 5)
        
        # Occasionally simulate issues
        if random.random() < 0.05:  # 5% chance of issues
            if random.random() < 0.5:
                temperature += random.uniform(5, 15)  # High temp
            else:
                co_level += random.uniform(3, 8)  # High CO
        
        return {
            "sensor_id": f"{room.replace(' ', '_').upper()}_001",
            "room": room,
            "temperature": round(max(0, temperature), 1),
            "humidity": round(max(0, min(100, humidity)), 1),
            "co_level": round(max(0, co_level), 1),
            "battery_level": round(max(0, min(100, battery_level)), 1),
            "signal_strength": random.randint(-80, -30),
            "timestamp": timestamp,
            "created_at": timestamp,
            "status": "normal" if co_level < 5.0 and temperature < 30 else "alert"
        }
    
    def seed_alerts_data(self, days_back: int):
        """Generate alert data based on sensor anomalies"""
        print("�� Generating alert data...")
        
        alert_types = [
            {"type": "HIGH_TEMPERATURE", "severity": "WARNING", "threshold": 30},
            {"type": "HIGH_CO_LEVEL", "severity": "CRITICAL", "threshold": 5.0},
            {"type": "LOW_BATTERY", "severity": "WARNING", "threshold": 20},
            {"type": "SENSOR_OFFLINE", "severity": "WARNING", "threshold": None}
        ]
        
        alerts = []
        
        # Generate 3-5 alerts per day
        for day in range(days_back):
            current_date = datetime.now() - timedelta(days=day)
            num_alerts = random.randint(2, 6)
            
            for _ in range(num_alerts):
                alert_time = current_date.replace(
                    hour=random.randint(0, 23),
                    minute=random.randint(0, 59),
                    second=random.randint(0, 59)
                )
                
                alert_config = random.choice(alert_types)
                room = random.choice(["Living Room", "Kitchen", "Garage", "Basement", "Bedroom"])
                
                alert = {
                    "id": f"alert_{int(alert_time.timestamp())}_{random.randint(100, 999)}",
                    "type": alert_config["type"],
                    "severity": alert_config["severity"],
                    "room": room,
                    "sensor_id": f"{room.replace(' ', '_').upper()}_001",
                    "message": self.generate_alert_message(alert_config["type"], room),
                    "timestamp": alert_time,
                    "created_at": alert_time,
                    "status": "RESOLVED" if random.random() > 0.3 else "ACTIVE",
                    "acknowledged": random.random() > 0.4,
                    "threshold_value": alert_config["threshold"],
                    "current_value": self.generate_alert_value(alert_config["type"])
                }
                
                alerts.append(alert)
        
        if alerts:
            self.alerts.insert_many(alerts)
            print(f"✅ Generated {len(alerts)} alerts")
    
    def generate_alert_message(self, alert_type: str, room: str) -> str:
        """Generate appropriate alert message"""
        messages = {
            "HIGH_TEMPERATURE": f"High temperature detected in {room}",
            "HIGH_CO_LEVEL": f"Dangerous CO level detected in {room}",
            "LOW_BATTERY": f"Low battery warning for sensor in {room}",
            "SENSOR_OFFLINE": f"Sensor in {room} is offline"
        }
        return messages.get(alert_type, f"Alert in {room}")
    
    def generate_alert_value(self, alert_type: str) -> float:
        """Generate realistic values that would trigger alerts"""
        values = {
            "HIGH_TEMPERATURE": random.uniform(30, 40),
            "HIGH_CO_LEVEL": random.uniform(5.0, 12.0),
            "LOW_BATTERY": random.uniform(5, 19),
            "SENSOR_OFFLINE": 0
        }
        return round(values.get(alert_type, 0), 1)
    
    def seed_users_data(self):
        """Generate sample user data"""
        print("👥 Generating user data...")
        
        users = [
            {
                "id": "user_demo_001",
                "name": "Demo User",
                "email": "demo@smarthome.com",
                "role": "admin",
                "created_at": datetime.now() - timedelta(days=30),
                "last_login": datetime.now() - timedelta(hours=2),
                "preferences": {
                    "notifications": True,
                    "email_alerts": True,
                    "sms_alerts": False,
                    "theme": "light"
                }
            },
            {
                "id": "user_test_002", 
                "name": "Test User",
                "email": "test@smarthome.com",
                "role": "user",
                "created_at": datetime.now() - timedelta(days=15),
                "last_login": datetime.now() - timedelta(days=1),
                "preferences": {
                    "notifications": True,
                    "email_alerts": False,
                    "sms_alerts": True,
                    "theme": "dark"
                }
            }
        ]
        
        self.users.insert_many(users)
        print(f"✅ Generated {len(users)} users")
    
    def seed_settings_data(self):
        """Generate system settings"""
        print("⚙️ Generating system settings...")
        
        settings = [
            {
                "key": "alert_thresholds",
                "value": {
                    "temperature": {"min": 10, "max": 30},
                    "humidity": {"min": 30, "max": 70},
                    "co_level": {"max": 5.0},
                    "battery_level": {"min": 20}
                },
                "updated_at": datetime.now(),
                "updated_by": "admin"
            },
            {
                "key": "notification_settings",
                "value": {
                    "email_enabled": True,
                    "sms_enabled": True,
                    "push_enabled": True,
                    "webhook_enabled": True,
                    "default_recipients": ["admin@smarthome.com"]
                },
                "updated_at": datetime.now(),
                "updated_by": "admin"
            },
            {
                "key": "system_config",
                "value": {
                    "data_retention_days": 90,
                    "backup_enabled": True,
                    "maintenance_mode": False,
                    "api_rate_limit": 1000
                },
                "updated_at": datetime.now(),
                "updated_by": "admin"
            }
        ]
        
        self.settings.insert_many(settings)
        print(f"✅ Generated {len(settings)} system settings")
    
    def update_redis_cache(self):
        """Populate Redis cache with current statistics"""
        print("📊 Updating Redis cache...")
        
        # Calculate current statistics
        total_sensors = self.sensor_data.count_documents({})
        active_alerts = self.alerts.count_documents({"status": "ACTIVE"})
        
        # Current sensor readings (last hour)
        one_hour_ago = datetime.now() - timedelta(hours=1)
        recent_readings = list(self.sensor_data.find({
            "timestamp": {"$gte": one_hour_ago}
        }).sort("timestamp", -1).limit(50))
        
        # Cache statistics
        stats = {
            "total_sensors": total_sensors,
            "active_alerts": active_alerts,
            "last_updated": datetime.now().isoformat(),
            "system_status": "operational"
        }
        
        self.redis_client.set("sensor_stats", json.dumps(stats))
        self.redis_client.set("recent_readings", json.dumps(recent_readings, default=str))
        
        print("✅ Redis cache updated")
    
    def print_summary(self):
        """Print summary of seeded data"""
        print("\n📋 Database Seeding Summary:")
        print("=" * 40)
        
        sensor_count = self.sensor_data.count_documents({})
        alert_count = self.alerts.count_documents({})
        user_count = self.users.count_documents({})
        settings_count = self.settings.count_documents({})
        
        print(f"📊 Sensor Readings: {sensor_count:,}")
        print(f"🚨 Alerts: {alert_count}")
        print(f"👥 Users: {user_count}")
        print(f"⚙️ Settings: {settings_count}")
        
        # Show recent data
        print(f"\n🕐 Most Recent Sensor Reading:")
        latest = self.sensor_data.find_one(sort=[("timestamp", -1)])
        if latest:
            print(f"   {latest['room']}: {latest['temperature']}°C, {latest['humidity']}%, {latest['co_level']} ppm")
            print(f"   Timestamp: {latest['timestamp']}")
        
        print(f"\n🚨 Active Alerts: {self.alerts.count_documents({'status': 'ACTIVE'})}")
        
        print(f"\n✅ Database is ready for testing!")


def main():
    """Main seeding function"""
    try:
        seeder = DatabaseSeeder()
        
        # Check database connectivity
        seeder.mongo_client.admin.command('ismaster')
        print("✅ MongoDB connection successful")
        
        if seeder.redis_available:
            seeder.redis_client.ping()
            print("✅ Redis connection successful")
        else:
            print("⚠️ Redis not available (optional)")
        
        # Default: seed 7 days of data with 12 readings per hour per room
        seeder.seed_all_data(days_back=7, sensors_per_hour=12)
        
    except Exception as e:
        print(f"❌ Error seeding database: {str(e)}")
        print("💡 Make sure MongoDB is running:")
        print("   docker run -d --name mongodb -p 27017:27017 mongo:latest")
        print("   docker run -d --name redis -p 6379:6379 redis:latest  # optional")


if __name__ == "__main__":
    main()
