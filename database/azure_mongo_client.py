from pymongo import MongoClient, ASCENDING
from pymongo.errors import CollectionInvalid, ConnectionFailure
from datetime import datetime, timedelta
import logging
from config.azure_config import AzureMongoConfig

class AzureMongoSensorDB:
    def __init__(self):
        self.config = AzureMongoConfig()
        self.client = None
        self.db = None
        self.sensor_collection = None
        self.alerts_collection = None
        self.connect()
    
    def connect(self):
        """Connect to Azure Cosmos DB MongoDB API"""
        try:
            connection_params = self.config.get_connection_params()
            self.client = MongoClient(**connection_params)
            
            # Test connection
            self.client.admin.command('ping')
            print("Successfully connected to Azure Cosmos DB!")
            
            self.db = self.client[self.config.database_name]
            self.sensor_collection = self.db.sensor_readings
            self.alerts_collection = self.db.alerts
            
            self.setup_collections()
            
        except ConnectionFailure as e:
            logging.error(f"Failed to connect to Azure Cosmos DB: {e}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error connecting to database: {e}")
            raise
    
    def setup_collections(self):
        """Setup collections and indexes"""
        try:
            # Create indexes for sensor_readings
            self.sensor_collection.create_index([
                ("location", ASCENDING),
                ("timestamp", ASCENDING)
            ])
            self.sensor_collection.create_index("sensor_type")
            self.sensor_collection.create_index("timestamp")
            
            # Create indexes for alerts
            self.alerts_collection.create_index([
                ("location", ASCENDING),
                ("timestamp", ASCENDING)
            ])
            self.alerts_collection.create_index("alert_type")
            
            print("Database indexes created successfully")
            
        except Exception as e:
            logging.warning(f"Could not create indexes: {e}")
    
    def insert_sensor_data(self, location, sensor_type, value, unit):
        """Insert sensor reading into Azure Cosmos DB"""
        document = {
            "timestamp": datetime.utcnow(),
            "location": location,
            "sensor_type": sensor_type,
            "value": float(value),
            "unit": unit,
            "quality": self._determine_quality(sensor_type, value),
            "device_id": f"{location.lower().replace(' ', '_')}_sensor"
        }
        
        try:
            result = self.sensor_collection.insert_one(document)
            return result.inserted_id
        except Exception as e:
            logging.error(f"Failed to insert sensor data: {e}")
            return None
    
    def get_latest_readings(self, location=None, limit=100):
        """Get latest sensor readings"""
        query = {}
        if location:
            query["location"] = location
        
        try:
            cursor = self.sensor_collection.find(query).sort("timestamp", -1).limit(limit)
            return list(cursor)
        except Exception as e:
            logging.error(f"Failed to fetch readings: {e}")
            return []
    
    def insert_alert(self, location, alert_type, message, severity="warning"):
        """Insert alert into database"""
        alert_doc = {
            "timestamp": datetime.utcnow(),
            "location": location,
            "alert_type": alert_type,
            "message": message,
            "severity": severity,
            "acknowledged": False
        }
        
        try:
            result = self.alerts_collection.insert_one(alert_doc)
            return result.inserted_id
        except Exception as e:
            logging.error(f"Failed to insert alert: {e}")
            return None
    
    def _determine_quality(self, sensor_type, value):
        """Determine data quality based on thresholds"""
        thresholds = {
            "temperature": {"min": 18, "max": 30},
            "humidity": {"min": 30, "max": 70},
            "co_level": {"min": 0, "max": 50}
        }
        
        if sensor_type in thresholds:
            thresh = thresholds[sensor_type]
            if thresh["min"] <= value <= thresh["max"]:
                return "good"
            else:
                return "critical"
        return "good"